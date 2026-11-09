"""Testa as falhas da aula «Quem vê e quem muda o quê: IDOR e mass assignment» e diz quais continuam abertas.

Sobe uma cópia do app numa porta livre de 127.0.0.1, com bancos e bucket novos numa pasta temporária,
faz os pedidos que um cliente curioso, já logado, faria pelo navegador e desliga. Não acessa nenhum
outro endereço.

    python3 checar.py                   # testa o app.py desta pasta
    python3 checar.py --app ../copia    # testa o app.py de outra pasta

Os números de pedido e os nomes de arquivo que ele usa vêm do banco, como de quem achou o link
num print ou num e-mail encaminhado: trocar o número por um código difícil de adivinhar não fecha
nenhuma checagem.

Sai com 0 quando todas as checagens passam e com 1 quando alguma continua aberta.
"""
import argparse
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = '127.0.0.1'
TELA_DE_PERFIL = {'nome', 'email', 'telefone', 'cidade', 'plano', 'creditos'}
VALIDADE_MAXIMA = 3600  # segundos: link de nota que vale mais de uma hora não conta como link com validade


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

    def bruto(self, metodo, caminho, corpo=None, token=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        pedido.add_header('Content-Type', 'application/json')
        if token:
            pedido.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as erro:
            return erro.code, erro.read().decode()

    def pedir(self, *args, **kwargs):
        status, texto = self.bruto(*args, **kwargs)
        try:
            return status, json.loads(texto)
        except ValueError:
            return status, {'_texto': texto}

    def entrar(self, email, senha):
        status, corpo = self.pedir('POST', '/api/login', {'email': email, 'senha': senha})
        if status != 200 or not corpo.get('token'):
            raise RuntimeError(f'{email} precisa conseguir entrar (login respondeu {status})')
        return corpo['token']


def consulta(banco, sql, args=()):
    con = sqlite3.connect(banco)
    try:
        return con.execute(sql, args).fetchone()
    finally:
        con.close()


def pedido_da_bia(banco):
    return consulta(banco, "select p.id, p.endereco, p.nota from pedidos p join usuarios u on u.id = p.cliente_id"
                           " where u.email = 'bia@cliente.example' order by p.id")


def conta(banco, email):
    return consulta(banco, 'select creditos, plano, gateway_id, is_admin, nome from usuarios where email = ?', (email,))


def checar_pedido_de_outro(c, ctx):
    pid, endereco, _ = pedido_da_bia(ctx['banco'])
    status, _ = c.pedir('GET', f'/api/pedidos/{pid}')
    if status != 401:
        return False, f'sem login nenhum, /api/pedidos/{pid} respondeu {status}'
    bia = c.entrar('bia@cliente.example', 'Bia#teste1')
    status, proprio = c.pedir('GET', f'/api/pedidos/{pid}', token=bia)
    if status != 200 or proprio.get('endereco') != endereco:
        return False, f'a Bia precisa continuar vendo o pedido {pid}, que é dela (resposta {status})'
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    status, corpo = c.bruto('GET', f'/api/pedidos/{pid}', token=caio)
    if status == 200 or endereco in corpo:
        return False, f'o Caio, logado, trocou o número na URL e leu o pedido {pid} da Bia, com o endereço de entrega (resposta {status})'
    return True, f'o Caio leva {status} no pedido {pid} da Bia; a Bia continua vendo o dela'


def checar_perfil_de_outro(c, ctx):
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    outro, corpo = c.bruto('GET', '/api/usuarios?email=bia@cliente.example', token=caio)
    if 'Bia Santos' in corpo or '90000-0101' in corpo:
        return False, f'o Caio pediu /api/usuarios?email=bia@cliente.example e recebeu o perfil da Bia (resposta {outro})'
    status, proprio = c.pedir('GET', '/api/usuarios?email=caio@cliente.example', token=caio)
    if status != 200 or proprio.get('nome') != 'Caio Lima':
        return False, f'o Caio precisa continuar abrindo o próprio perfil (resposta {status})'
    return True, f'o perfil da Bia não sai para o Caio (resposta {outro}); o dele sai normal'


def checar_campos_demais(c, ctx):
    bia = c.entrar('bia@cliente.example', 'Bia#teste1')
    status, perfil = c.pedir('GET', '/api/usuarios?email=bia@cliente.example', token=bia)
    if status != 200:
        return False, f'a Bia precisa continuar abrindo o perfil dela (resposta {status})'
    sobra = sorted(set(perfil) - TELA_DE_PERFIL)
    if sobra:
        return False, f'a resposta traz {len(perfil)} campos, {len(sobra)} que a tela não usa: {", ".join(sobra)}'
    falta = sorted(TELA_DE_PERFIL - {'email'} - set(perfil))
    if falta:
        return False, f'a tela de perfil usa {", ".join(falta)}, e a resposta não trouxe'
    return True, f'a resposta traz só os {len(perfil)} campos da tela'


def checar_patch_creditos(c, ctx):
    banco = ctx['banco']
    antes = conta(banco, 'caio@cliente.example')
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    tentativas = [{'creditos': 999999}, {'plano': 'clube'}, {'gateway_id': 'cus_aurora_0001'},
                  {'telefone': '19 90000-9999', 'creditos': 5000}]
    for corpo in tentativas:
        status, _ = c.pedir('PATCH', '/api/perfil', corpo, caio)
        depois = conta(banco, 'caio@cliente.example')
        if depois[:3] != antes[:3]:
            return False, (f'o Caio mandou {json.dumps(corpo, ensure_ascii=False)} no PATCH /api/perfil (resposta {status}) e ficou com '
                           f'crédito {depois[0]}, plano {depois[1]}, gateway {depois[2]}')
    honesto = {'nome': 'Caio Lima', 'telefone': '19 90000-2222', 'cidade': 'Campinas'}
    status, _ = c.pedir('PATCH', '/api/perfil', honesto, caio)
    if status != 200 or consulta(banco, "select telefone, cidade from usuarios where email = 'caio@cliente.example'") != ('19 90000-2222', 'Campinas'):
        return False, f'o PATCH que a tela manda (nome, telefone e cidade) precisa continuar gravando (resposta {status})'
    return True, 'crédito, plano e id do gateway não mudam pelo PATCH; nome, telefone e cidade gravam'


def checar_patch_is_admin(c, ctx):
    banco = ctx['banco']
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    tentativas = [{'is_admin': 1}, {'Is_Admin': 1}, {"nome = 'Caio Lima', is_admin": 1}]
    for corpo in tentativas:
        status, _ = c.pedir('PATCH', '/api/perfil', corpo, caio)
        if conta(banco, 'caio@cliente.example')[3]:
            _, painel = c.pedir('GET', '/api/admin/pedidos', token=caio)
            n = len(painel.get('pedidos', [])) if isinstance(painel, dict) else '?'
            return False, (f'o Caio mandou {json.dumps(corpo, ensure_ascii=False)} no PATCH /api/perfil (resposta {status}), '
                           f'virou admin e abriu o painel da Renata ({n} pedidos)')
    status, _ = c.pedir('GET', '/api/admin/pedidos', token=caio)
    if status != 403:
        return False, f'o Caio, cliente comum, abriu o painel (resposta {status})'
    return True, 'nenhum PATCH do Caio mexe em is_admin; o painel continua 403 para ele'


def checar_nota_publica(c, ctx):
    banco = ctx['banco']
    pid, _, arquivo = pedido_da_bia(banco)
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    status, corpo = c.pedir('GET', f'/api/pedidos/{pid}/nota', token=caio)
    if status == 200 and corpo.get('url'):
        return False, f'o Caio pediu /api/pedidos/{pid}/nota, a nota da Bia, e recebeu o link (resposta 200)'
    abertas = []
    for n in range(1, 5):
        nome = f'nota-{n:04d}.txt'
        status, texto = c.bruto('GET', f'/arquivos/notas/{nome}')
        if status == 200:
            abertas.append(nome)
    if abertas:
        return False, (f'sem login nenhum, {len(abertas)} notas abriram pelo endereço fixo, com nome e endereço de entrega '
                       f'({", ".join(abertas)}): o bucket é público e os nomes vão em sequência')
    return True, 'a nota da Bia não sai para o Caio, e nenhuma nota abre pelo endereço fixo'


def checar_link_assinado(c, ctx):
    banco, loja = ctx['banco'], ctx['loja']
    pid, endereco, arquivo = pedido_da_bia(banco)
    bia = c.entrar('bia@cliente.example', 'Bia#teste1')
    status, corpo = c.pedir('GET', f'/api/pedidos/{pid}/nota', token=bia)
    url = corpo.get('url', '') if status == 200 else ''
    if not url:
        return False, f'a Bia precisa continuar recebendo o link da nota dela (resposta {status})'
    q = parse_qs(urlparse(url).query)
    expira = q.get('expira', [''])[0]
    if not expira.isdigit():
        return False, f'o link da nota não tem validade: {url}'
    validade = int(expira) - int(time.time())
    if not 0 < validade <= VALIDADE_MAXIMA:
        return False, f'o link da nota vale por {validade} segundos; o combinado é até {VALIDADE_MAXIMA} (uma hora)'
    status, texto = c.bruto('GET', url)
    if status != 200 or endereco not in texto:
        return False, f'o link assinado precisa abrir a nota da Bia (resposta {status})'
    outro = url.replace(arquivo, 'nota-0003.txt', 1)
    status, _ = c.bruto('GET', outro)
    if status == 200:
        return False, 'o mesmo token abriu a nota-0003.txt, que é do Caio: o link não está preso ao arquivo'
    relogio = loja.notas.relogio
    loja.notas.relogio = lambda: int(expira) + 1
    try:
        status, _ = c.bruto('GET', url)
    finally:
        loja.notas.relogio = relogio
    if status == 200:
        return False, 'o link da nota continuou abrindo depois de vencer'
    return True, f'o link da nota vale {validade} segundos, abre só a nota da Bia e para de abrir quando vence'


CHECAGENS = [
    ('pedido-de-outro', 'pedido de outro cliente pela URL', checar_pedido_de_outro),
    ('perfil-de-outro', 'perfil de outro cliente pelo e-mail', checar_perfil_de_outro),
    ('campos-demais', 'perfil com campos que a tela não usa', checar_campos_demais),
    ('patch-creditos', 'PATCH do perfil grava crédito e plano', checar_patch_creditos),
    ('patch-is-admin', 'PATCH do perfil grava is_admin', checar_patch_is_admin),
    ('nota-publica', 'nota do pedido aberta para qualquer um', checar_nota_publica),
    ('link-assinado', 'link da nota sem validade', checar_link_assinado),
]


def main():
    parser = argparse.ArgumentParser(description='Testa as falhas da aula na Loja Aurora.')
    parser.add_argument('--app', default=str(Path(__file__).resolve().parent), help='pasta do app (padrão: esta)')
    args = parser.parse_args()
    modulo = carregar_app(args.app)
    env = modulo.ler_env(Path(args.app).resolve())
    abertas = 0
    with tempfile.TemporaryDirectory() as tmp:
        for codigo, nome, checar in CHECAGENS:
            banco = Path(tmp) / codigo / 'aurora.db'   # banco e bucket novos para cada checagem
            banco.parent.mkdir()
            modulo.dados.montar(banco)
            loja = modulo.Loja(banco, env)
            servidor = modulo.criar_servidor(loja, 0)
            servidor.RequestHandlerClass.log_message = lambda *a, **k: None
            threading.Thread(target=servidor.serve_forever, daemon=True).start()
            try:
                ok, motivo = checar(Cliente(servidor.server_address[1]), {'loja': loja, 'banco': banco})
            except Exception as erro:  # uma checagem que quebra conta como aberta
                ok, motivo = False, f'a checagem quebrou: {type(erro).__name__}: {erro}'
            finally:
                servidor.shutdown()
                servidor.server_close()
            abertas += not ok
            print(f'{"fechada" if ok else "ABERTA ":7}  {codigo:16}  {nome}: {motivo}')
    print(f'\n{len(CHECAGENS) - abertas} de {len(CHECAGENS)} fechadas.')
    return 0 if abertas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
