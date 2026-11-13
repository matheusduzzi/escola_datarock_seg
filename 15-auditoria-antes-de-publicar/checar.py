"""Diz quais dos sete itens da auditoria do PR continuam abertos numa branch do repo-aurora.

    python3 checar.py repo-aurora                       # a branch atual
    python3 checar.py repo-aurora --branch cupom-sexta  # outra branch

Usa o portão (portao.py) para segredos, dependências, código e testes. Para a regra da Sexta
Aurora, o papel de admin e o relatório, sobe uma cópia da loja da branch numa porta livre de
127.0.0.1, com banco novo, e manda os pedidos com o relógio da loja parado em horários
escolhidos. Por isso o app precisa continuar com o self.relogio, que o agente criou.

Sai com 0 quando os sete itens fecham e com 1 enquanto algum estiver aberto.
"""
import argparse
import importlib.util
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import portao  # noqa: E402

BRASILIA = timezone(timedelta(hours=-3))


def quando(texto):
    """'2026-11-26 22:00' no horário de Brasília, como o relógio da loja devolve: em UTC."""
    return datetime.strptime(texto, '%Y-%m-%d %H:%M').replace(tzinfo=BRASILIA).astimezone(timezone.utc)


class Loja:
    """Uma cópia da loja da branch, rodando numa porta livre, com o relógio na mão."""

    def __init__(self, pasta):
        sys.path.insert(0, str(pasta))
        spec = importlib.util.spec_from_file_location('app_da_branch', Path(pasta) / 'app.py')
        self.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.app)
        banco = Path(pasta) / 'checar.db'
        self.app.dados.montar(banco)
        self.loja = self.app.Loja(banco, self.app.ler_env(Path(pasta)))
        if not hasattr(self.loja, 'relogio'):
            raise RuntimeError('o app não tem o self.relogio que o PR criou, então não dá para testar o horário')
        self.servidor = self.app.criar_servidor(self.loja, 0)
        self.servidor.RequestHandlerClass.log_message = lambda *a, **k: None
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.servidor.server_address[1]}'
        self.tokens = {}

    def fechar(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def relogio(self, momento):
        self.loja.relogio = lambda: momento

    def pedir(self, metodo, caminho, corpo=None, quem=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        pedido.add_header('Content-Type', 'application/json')
        if quem:
            pedido.add_header('Authorization', 'Bearer ' + self.token(quem))
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                return r.status, json.loads(r.read().decode() or '{}')
        except urllib.error.HTTPError as erro:
            texto = erro.read().decode()
            try:
                return erro.code, json.loads(texto or '{}')
            except ValueError:
                return erro.code, {'_texto': texto}

    def token(self, quem):
        if quem not in self.tokens:
            senhas = {'bia': 'Bia#teste1', 'caio': 'Caio#teste2', 'renata': 'Renata#teste4'}
            dominio = 'aurora.example' if quem == 'renata' else 'cliente.example'
            _, corpo = self.pedir('POST', '/api/login', {'email': f'{quem}@{dominio}', 'senha': senhas[quem]})
            self.tokens[quem] = corpo.get('token', '')
        return self.tokens[quem]

    def comprar(self, quem, produto_id, momento):
        self.relogio(momento)
        return self.pedir('POST', '/api/pedidos', {'produto_id': produto_id, 'quantidade': 1}, quem)

    def vendas(self, dia, quem='renata'):
        return self.pedir('GET', '/api/admin/vendas?dia=' + urllib.parse.quote(dia), quem=quem)


# As sete checagens. Cada uma retorna (fechada?, motivo).

def checar_segredo(ctx):
    achados = [a for a in portao.segredos(ctx['repo'], ctx['base'], ctx['branch']) if a['tipo'] == 'secreta']
    if achados:
        a = achados[0]
        return False, f"a chave {a['chave']} continua no commit {a['commit'].split()[0]} do PR ({a['onde']}), mesmo que o último commit não tenha"
    return True, 'nenhum commit do PR acrescenta chave secreta'


def checar_dependencia(ctx):
    problemas, total = portao.dependencias(ctx['repo'], ctx['branch'])
    if problemas:
        return False, problemas[0]
    return True, f'{total} dependência(s) declarada(s), todas travadas e sem aviso' if total else 'o PR não declara dependência'


def checar_sql(ctx):
    achados = portao.codigo(ctx['pasta'])
    abertos = [a for a in achados if not a['ignorado']]
    if abertos:
        return False, 'consulta montada colando texto em ' + ', '.join(f"{a['funcao']} ({a['arquivo']}:{a['linha']})" for a in abertos)
    calados = [a for a in achados if a['ignorado'] and a['funcao'] != 'buscar_produtos']
    if calados:
        return False, f"o nosemgrep calou a regra em {calados[0]['funcao']}: a consulta continua colando texto do cliente"
    loja = ctx['loja']
    loja.comprar('caio', 1, quando('2026-11-25 10:00'))
    status, corpo = loja.vendas("2026-11-27' or '1'='1")
    if status == 200 and corpo.get('pedidos'):
        return False, f"o dia \"2026-11-27' or '1'='1\" trouxe {len(corpo['pedidos'])} pedido(s) de outros dias"
    if status >= 500:
        return False, f'um apóstrofo no dia derrubou o relatório (resposta {status})'
    for dia in ("2026-11-27' or '1'='1", '27/11/2026', '2026-11-27x'):
        status, _ = loja.vendas(dia)
        if status != 400:
            return False, f'o dia "{dia}" está fora do formato AAAA-MM-DD e respondeu {status}; o certo é 400'
    status, corpo = loja.vendas('2026-11-25')
    if status != 200 or len(corpo.get('pedidos', [])) != 1:
        return False, f'o relatório de um dia normal parou de funcionar (resposta {status})'
    return True, 'o dia do relatório entra como dado; o único nosemgrep que sobra é o da ordem da busca' if len(achados) else \
        'o dia do relatório entra como dado e nenhuma consulta cola texto'


def checar_admin(ctx):
    loja = ctx['loja']
    status_anonimo, _ = loja.pedir('GET', '/api/admin/vendas?dia=2026-11-25')
    status_caio, _ = loja.vendas('2026-11-25', quem='caio')
    status_renata, _ = loja.vendas('2026-11-25', quem='renata')
    if status_caio == 200:
        return False, 'o Caio, que é cliente, abriu o relatório de vendas da loja (resposta 200)'
    if (status_anonimo, status_caio, status_renata) != (401, 403, 200):
        return False, f'sem login {status_anonimo}, Caio {status_caio}, Renata {status_renata}; o esperado é 401, 403 e 200'
    return True, 'sem login 401, cliente 403, admin 200'


CASOS_SEXTA = [
    # (quem, produto, horário de Brasília, desconto esperado em centavos, o que é)
    ('caio', 1, '2026-11-26 22:00', 0, 'quinta às 22h'),
    ('caio', 1, '2026-11-27 00:30', 2499, 'sexta à 0h30'),
    ('caio', 1, '2026-11-27 22:00', 2499, 'sexta às 22h'),
    ('caio', 1, '2026-11-28 00:30', 0, 'sábado à 0h30'),
    ('bia', 7, '2026-11-27 15:00', 699, 'sexta às 15h, cliente do Clube'),
]


def checar_sexta(ctx):
    loja = ctx['loja']
    for quem, produto, hora, esperado, nome in CASOS_SEXTA:
        status, pedido = loja.comprar(quem, produto, quando(hora))
        if status != 201:
            return False, f'o pedido de {nome} não saiu (resposta {status})'
        if pedido.get('desconto_centavos') != esperado:
            return False, f"pedido de {nome} (horário de Brasília) saiu com {pedido.get('desconto_centavos')} centavos de desconto; o certo é {esperado}"
    return True, 'quinta às 22h sem desconto, sexta das 0h30 às 22h com 10%, sábado sem, Clube não acumula'


def checar_relatorio(ctx):
    loja = ctx['loja']
    _, quinta = loja.comprar('caio', 1, quando('2026-11-26 22:00'))
    _, sexta = loja.comprar('caio', 1, quando('2026-11-27 22:00'))
    resultado = {}
    for dia in ('2026-11-26', '2026-11-27'):
        status, corpo = loja.vendas(dia)
        if status != 200:
            return False, f'o relatório de {dia} respondeu {status}'
        resultado[dia] = {p['id'] for p in corpo.get('pedidos', [])}
    if sexta.get('pedido_id') not in resultado['2026-11-27'] or quinta.get('pedido_id') in resultado['2026-11-27']:
        return False, ('o pedido de sexta às 22h (Brasília) não aparece nas vendas de 27/11, ou o de quinta às 22h aparece: '
                       'o relatório conta o dia em UTC')
    if quinta.get('pedido_id') not in resultado['2026-11-26']:
        return False, 'o pedido de quinta às 22h (Brasília) não aparece nas vendas de 26/11'
    return True, 'o pedido de quinta às 22h fica em 26/11 e o de sexta às 22h, em 27/11'


def checar_testes(ctx):
    ok, rodou, saida = portao.testes(ctx['pasta'])
    if not ok:
        ultima = [l for l in saida.strip().splitlines() if l.strip()][-1]
        return False, f'{rodou} testes, com falha ({ultima})'
    return True, f'{rodou} testes, OK'


CHECAGENS = [
    ('segredo-no-pr', 'chave em commit do PR', checar_segredo),
    ('dependencia', 'dependência com aviso de falha', checar_dependencia),
    ('sql-do-relatorio', 'relatório montado colando o dia na consulta', checar_sql),
    ('admin-sem-papel', 'relatório de vendas aberto a qualquer cliente', checar_admin),
    ('sexta-no-fuso', 'desconto da sexta contado em UTC', checar_sexta),
    ('relatorio-no-fuso', 'vendas do dia contadas em UTC', checar_relatorio),
    ('testes', 'testes da branch', checar_testes),
]


def main():
    parser = argparse.ArgumentParser(description='Diz quais itens da auditoria do PR continuam abertos.')
    parser.add_argument('repo', help='pasta do repositório git (por exemplo, repo-aurora)')
    parser.add_argument('--base', default='main')
    parser.add_argument('--branch', help='padrão: a branch atual do repositório')
    args = parser.parse_args()
    if not (Path(args.repo) / '.git').exists():
        sys.exit(f'{args.repo} não é um repositório git. Rode antes: python3 montar.py')
    repo = Path(args.repo).resolve()
    branch = args.branch or portao.branch_atual(repo)
    print(f'Auditoria da branch {branch} contra {args.base}\n')
    abertas = 0
    with tempfile.TemporaryDirectory() as tmp:
        pasta = portao.extrair(repo, branch, tmp)
        ctx = {'repo': repo, 'base': args.base, 'branch': branch, 'pasta': pasta}
        try:
            ctx['loja'] = Loja(pasta)
        except Exception as erro:  # sem loja, as checagens que pedem a loja ficam abertas
            ctx['loja'] = None
            print(f'(a loja da branch não subiu: {type(erro).__name__}: {erro})\n')
        for codigo, nome, checar in CHECAGENS:
            try:
                if ctx['loja'] is None and checar in (checar_sql, checar_admin, checar_sexta, checar_relatorio):
                    raise RuntimeError('a loja da branch não subiu')
                ok, motivo = checar(ctx)
            except Exception as erro:  # uma checagem que quebra conta como aberta
                ok, motivo = False, f'a checagem quebrou: {type(erro).__name__}: {erro}'
            abertas += not ok
            print(f'{"fechada" if ok else "ABERTA ":7}  {codigo:18}  {nome}: {motivo}')
        if ctx['loja'] is not None:
            ctx['loja'].fechar()
    print(f'\n{len(CHECAGENS) - abertas} de {len(CHECAGENS)} fechadas.')
    return 0 if abertas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
