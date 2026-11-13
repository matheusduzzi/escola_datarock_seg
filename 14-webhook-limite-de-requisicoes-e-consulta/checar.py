"""Testa as falhas da aula «Webhook, limite de requisições e consulta parametrizada» e diz quais continuam abertas.

Sobe uma cópia do app numa porta livre de 127.0.0.1, com bancos novos numa pasta temporária para
cada checagem, manda os pedidos que um robô ou um curioso mandaria, sem passar pela tela, e desliga.
Não acessa nenhum outro endereço.

    python3 checar.py                   # testa o app.py desta pasta
    python3 checar.py --app ../copia    # testa o app.py de outra pasta

Sai com 0 quando todas as checagens passam e com 1 quando alguma continua aberta.
"""
import argparse
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST = '127.0.0.1'
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import gateway  # noqa: E402

# Sinais de detalhe interno numa resposta de erro: rastro do Python, caminho de arquivo, mensagem do banco.
DETALHE_INTERNO = ['Traceback', 'File "', '.py', 'sqlite', 'no such column', 'syntax error', 'near "',
                   'unrecognized token', 'Error(', 'Error:', 'object has no attribute', 'invalid literal', 'Expecting']


def carregar_app(pasta):
    pasta = Path(pasta).resolve()
    sys.path.insert(0, str(pasta))
    spec = importlib.util.spec_from_file_location('aurora_app', pasta / 'app.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class Cliente:
    def __init__(self, porta):
        self.base = f'http://{HOST}:{porta}'

    def pedir(self, metodo, caminho, corpo=None, token=None, bruto=None, cabecalhos=None):
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo, headers=cabecalhos or {})
        pedido.add_header('Content-Type', 'application/json')
        if token:
            pedido.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                status, texto, extras = r.status, r.read().decode(), dict(r.headers)
        except urllib.error.HTTPError as erro:
            status, texto, extras = erro.code, erro.read().decode(), dict(erro.headers)
        try:
            corpo = json.loads(texto)
        except ValueError:
            corpo = {'_texto': texto}
        return status, corpo, texto, extras

    def json(self, *args, **kwargs):
        status, corpo, _, _ = self.pedir(*args, **kwargs)
        return status, corpo

    def entrar(self, email, senha):
        status, corpo = self.json('POST', '/api/login', {'email': email, 'senha': senha})
        return corpo.get('token') if status == 200 else None


def busca(c, **parametros):
    return c.json('GET', '/api/produtos?' + urllib.parse.urlencode(parametros))


def consultar(banco, sql, parametros=()):
    con = sqlite3.connect(banco)
    try:
        return con.execute(sql, parametros).fetchone()[0]
    finally:
        con.close()


def status_do_pedido(ctx, pedido_id):
    return consultar(ctx['banco'], 'select status from pedidos where id = ?', (pedido_id,))


def checar_busca(c, ctx):
    status, corpo = busca(c, busca="d'Água")
    nomes = [p['nome'] for p in corpo.get('produtos', [])]
    if status != 200 or nomes != ["Abajur Gota d'Água"]:
        return False, f"a cliente que busca d'Água recebe {status} e não acha o abajur: o apóstrofo quebra a consulta"
    status, corpo = busca(c, busca="zzz' or 1=1 --")
    if status != 200 or corpo.get('produtos'):
        return False, f"um texto com apóstrofo muda a consulta (resposta {status}, {len(corpo.get('produtos', []))} produtos)"
    return True, "o texto da busca entra como dado: d'Água acha o abajur e o apóstrofo não muda a consulta"


def checar_ordem_e_limite(c, ctx):
    status, corpo = busca(c, busca='Luminária', ordem='preco_centavos', limite='2')
    precos = [p['preco_centavos'] for p in corpo.get('produtos', [])]
    if status != 200 or precos != sorted(precos) or len(precos) != 2:
        return False, f'a busca normal com ordem=preco_centavos e limite=2 precisa trazer 2 produtos do mais barato ao mais caro (veio {status}, {precos})'
    status, _ = busca(c, ordem='(select count(*) from usuarios)')
    if status != 400:
        return False, f'uma ordem fora da lista (um pedaço de SQL) foi aceita (resposta {status})'
    for limite in ['-1', '100000', 'abc', '5 union select 1']:
        status, corpo = busca(c, limite=limite)
        if status != 400:
            return False, f'limite={limite} foi aceito (resposta {status}, {len(corpo.get("produtos", []))} produtos)'
    status, _ = busca(c, busca='a' * 61)
    if status != 400:
        return False, f'um texto de busca com 61 caracteres foi aceito (resposta {status})'
    return True, 'ordem, limite e tamanho da busca só aceitam o que está na lista; o resto leva 400'


def checar_erro(c, ctx):
    segredo = ctx['env'].get('WEBHOOK_SEGREDO', '')
    lista = b'[1, 2]'
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    tentativas = [
        ('POST', '/api/pedidos', b'{}', {'Authorization': 'Bearer ' + (caio or '')}),   # pedido sem produto: erro que ninguém previu
        ('GET', '/api/pedidos/abc', None, None),
        ('GET', '/api/produtos?limite=abc', None, None),
        ('POST', '/api/newsletter', b'{', None),
        ('POST', '/webhook/pagamento', lista, {gateway.CABECALHO: gateway.assinar(segredo, lista)}),
    ]
    for metodo, caminho, bruto, cabecalhos in tentativas:
        status, _, texto, _ = c.pedir(metodo, caminho, bruto=bruto, cabecalhos=cabecalhos)
        vazou = [d for d in DETALHE_INTERNO if d in texto]
        if vazou:
            return False, f'{metodo} {caminho} respondeu {status} com detalhe interno ({vazou[0]})'
        if status < 400:
            return False, f'{metodo} {caminho} com dado inválido respondeu {status}'
    return True, 'pedido inválido leva uma mensagem curta, sem rastro do Python nem mensagem do banco'


def checar_webhook(c, ctx):
    bruto = json.dumps({'evento_id': 'evt_falso_1', 'pedido_id': 4, 'status': 'pago'}).encode()
    status, _ = c.json('POST', '/webhook/pagamento', bruto=bruto)
    if 200 <= status < 300 or status_do_pedido(ctx, 4) == 'pago':
        return False, f'um evento sem assinatura marcou o pedido 4 como pago (resposta {status})'
    status, _ = c.json('POST', '/webhook/pagamento', bruto=bruto, cabecalhos={gateway.CABECALHO: 'qualquer-coisa'})
    if 200 <= status < 300 or status_do_pedido(ctx, 4) == 'pago':
        return False, 'uma assinatura inventada foi aceita: o app só olha se o cabeçalho existe'
    errado = {gateway.CABECALHO: gateway.assinar('segredo-errado', bruto)}
    status, _ = c.json('POST', '/webhook/pagamento', bruto=bruto, cabecalhos=errado)
    if 200 <= status < 300 or status_do_pedido(ctx, 4) == 'pago':
        return False, 'um evento assinado com outro segredo foi aceito'
    estranho, cab_estranho = gateway.evento(ctx['env']['WEBHOOK_SEGREDO'], 4, 'qualquer coisa')
    status, _ = c.json('POST', '/webhook/pagamento', bruto=estranho, cabecalhos=cab_estranho)
    if status != 400 or status_do_pedido(ctx, 4) != 'aguardando pagamento':
        return False, f'um evento assinado com status fora da lista mudou o pedido 4 para "{status_do_pedido(ctx, 4)}" (resposta {status})'
    bruto, cabecalhos = gateway.evento(ctx['env']['WEBHOOK_SEGREDO'], 4, 'pago')
    status, _ = c.json('POST', '/webhook/pagamento', bruto=bruto, cabecalhos=cabecalhos)
    if not 200 <= status < 300 or status_do_pedido(ctx, 4) != 'pago':
        return False, f'o evento assinado do gateway também foi recusado (resposta {status})'
    return True, 'só o evento assinado com o segredo e com status da lista muda o pedido'


def checar_repetido(c, ctx):
    segredo = ctx['env']['WEBHOOK_SEGREDO']
    pago, cab_pago = gateway.evento(segredo, 4, 'pago', 'evt_pago_4')
    estorno, cab_estorno = gateway.evento(segredo, 4, 'estornado', 'evt_estorno_4')
    s1, _ = c.json('POST', '/webhook/pagamento', bruto=pago, cabecalhos=cab_pago)
    s2, _ = c.json('POST', '/webhook/pagamento', bruto=estorno, cabecalhos=cab_estorno)
    if not (200 <= s1 < 300 and 200 <= s2 < 300) or status_do_pedido(ctx, 4) != 'estornado':
        return False, f'os dois eventos assinados do gateway (pago, depois estornado) precisam passar (respostas {s1} e {s2})'
    s3, _ = c.json('POST', '/webhook/pagamento', bruto=pago, cabecalhos=cab_pago)
    if status_do_pedido(ctx, 4) != 'estornado':
        return False, f'o evento "pago" reenviado depois do estorno marcou o pedido 4 como pago de novo (resposta {s3})'
    if not 200 <= s3 < 300:
        return False, f'o evento repetido levou {s3}: o pedido ficou certo, mas sem 2xx o gateway reenvia de novo'
    return True, f'o evento repetido não muda nada (resposta {s3}): o pedido 4 continua estornado'


def checar_esquecido(c, ctx):
    corpo = {'pedido_id': 4, 'status': 'approved', 'email': 'duda@cliente.example'}
    status, _ = c.json('POST', '/webhook/pagafacil', corpo)
    if 200 <= status < 300 or status_do_pedido(ctx, 4) == 'pago':
        return False, f'o webhook do PagaFácil, o gateway antigo, marcou o pedido 4 como pago sem segredo nenhum (resposta {status})'
    return True, f'o webhook do gateway antigo não muda pedido nenhum (resposta {status})'


def checar_cadastro(c, ctx):
    status, _ = c.json('POST', '/api/newsletter', {'email': '<b>oi</b>@lixo.example'})
    if status != 400:
        return False, f'um e-mail com HTML foi aceito na newsletter (resposta {status})'
    status, _ = c.json('POST', '/api/newsletter', {'email': 'x@' + 'a' * 300 + '.example'})
    if status != 400:
        return False, f'um e-mail com mais de 300 caracteres foi aceito (resposta {status})'
    respostas, espera = [], None
    for i in range(30):
        status, _, _, extras = c.pedir('POST', '/api/newsletter', {'email': f'robo{i:03d}@lixo.example'})
        respostas.append(status)
        if status == 429:
            espera = extras.get('Retry-After')
    gravados = consultar(ctx['banco'], 'select count(*) from newsletter')
    if respostas[0] not in (200, 201, 202):
        return False, f'a primeira inscrição válida precisa passar (resposta {respostas[0]})'
    if 429 not in respostas or gravados > 5:
        return False, f'30 inscrições seguidas do mesmo IP: {gravados} gravadas, nenhuma resposta 429'
    if not espera:
        return False, 'o 429 da newsletter não diz em quantos segundos tentar de novo (cabeçalho Retry-After)'
    return True, f'dois e-mails inválidos levaram 400; das 30 inscrições seguidas, {gravados} foram gravadas e o resto levou 429 (Retry-After: {espera})'


def checar_modelo_login(c, ctx):
    antes = ctx['loja'].modelo.chamadas()
    status, _ = c.json('POST', '/api/assistente', {'pergunta': 'qual luminária para a sala?'})
    depois = ctx['loja'].modelo.chamadas()
    if status != 401 or depois != antes:
        return False, f'sem login nenhum, o assistente respondeu {status} e chamou o modelo {depois - antes} vez(es)'
    return True, 'sem login, o assistente responde 401 e não chama o modelo'


def checar_modelo_limite(c, ctx):
    bia = c.entrar('bia@cliente.example', 'Bia#teste1')
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    if not bia or not caio:
        return False, 'as contas de teste precisam conseguir entrar'
    antes = ctx['loja'].modelo.chamadas()
    status, _ = c.json('POST', '/api/assistente', {'pergunta': 'luz para a sala ' * 400}, token=caio)
    if status not in (400, 413) or ctx['loja'].modelo.chamadas() != antes:
        return False, f'uma pergunta de {len("luz para a sala " * 400)} caracteres foi para o modelo (resposta {status})'
    respostas = [c.pedir('POST', '/api/assistente', {'pergunta': 'qual luminária para a sala?'}, token=bia) for _ in range(6)]
    codigos = [r[0] for r in respostas]
    if codigos[:5] != [200] * 5 or codigos[5] != 429:
        return False, f'seis perguntas seguidas da Bia: respostas {codigos}; o modelo foi chamado {ctx["loja"].modelo.chamadas() - antes} vezes'
    if not respostas[5][3].get('Retry-After'):
        return False, 'o 429 do assistente não diz em quantos segundos tentar de novo (cabeçalho Retry-After)'
    status, _ = c.json('POST', '/api/assistente', {'pergunta': 'e para o quarto?'}, token=caio)
    if status != 200:
        return False, f'a Bia passou do limite e o Caio também ficou sem assistente (resposta {status}): o limite precisa ser por cliente'
    return True, 'pergunta grande leva 400 sem chamar o modelo; a sexta pergunta seguida da Bia leva 429, e o Caio segue'


CHECAGENS = [
    ('busca-concatenada', 'busca montada colando texto na consulta', checar_busca),
    ('ordem-e-limite', 'ordem e limite fora da lista do que é aceito', checar_ordem_e_limite),
    ('erro-com-detalhe', 'erro que mostra o rastro do Python e o banco', checar_erro),
    ('webhook-sem-segredo', 'webhook que aceita evento sem assinatura', checar_webhook),
    ('webhook-repetido', 'webhook que aplica o mesmo evento duas vezes', checar_repetido),
    ('webhook-esquecido', 'webhook do gateway antigo ainda no ar', checar_esquecido),
    ('cadastro-em-massa', 'newsletter sem validação e sem limite', checar_cadastro),
    ('modelo-sem-login', 'assistente de IA aberto para quem não entrou', checar_modelo_login),
    ('modelo-sem-limite', 'assistente de IA sem limite de perguntas', checar_modelo_limite),
]


def main():
    parser = argparse.ArgumentParser(description='Testa as falhas da aula na Loja Aurora.')
    parser.add_argument('--app', default=str(AQUI), help='pasta do app (padrão: esta)')
    args = parser.parse_args()
    modulo = carregar_app(args.app)
    env = modulo.ler_env(Path(args.app).resolve())
    abertas = 0
    with tempfile.TemporaryDirectory() as tmp:
        for codigo, nome, checar in CHECAGENS:
            banco = Path(tmp) / codigo / 'aurora.db'   # banco novo para cada checagem
            banco.parent.mkdir()
            modulo.dados.montar(banco)
            loja = modulo.Loja(banco, env)
            servidor = modulo.criar_servidor(loja, 0)
            servidor.RequestHandlerClass.log_message = lambda *a, **k: None
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
            try:
                ok, motivo = checar(Cliente(servidor.server_address[1]), {'loja': loja, 'banco': banco, 'env': env})
            except Exception as erro:  # uma checagem que quebra conta como aberta
                ok, motivo = False, f'a checagem quebrou: {type(erro).__name__}: {erro}'
            finally:
                servidor.shutdown()
                servidor.server_close()
            abertas += not ok
            print(f'{"fechada" if ok else "ABERTA ":7}  {codigo:19}  {nome}: {motivo}')
    print(f'\n{len(CHECAGENS) - abertas} de {len(CHECAGENS)} fechadas.')
    return 0 if abertas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
