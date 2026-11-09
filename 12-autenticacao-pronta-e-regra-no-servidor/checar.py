"""Testa as falhas da aula «Autenticação pronta e regra no servidor» e diz quais continuam abertas.

Sobe uma cópia do app numa porta livre de 127.0.0.1, com bancos novos numa pasta temporária,
faz os pedidos que um cliente curioso faria pelo navegador e desliga. Não acessa nenhum outro endereço.

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
import urllib.request
from pathlib import Path

HOST = '127.0.0.1'
LUMINARIA = 24990   # produto 1, Luminária de mesa Aurora
FITA_LED = 8990     # produto 5, Fita de LED quente 5 m


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

    def pedir(self, metodo, caminho, corpo=None, token=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        pedido.add_header('Content-Type', 'application/json')
        if token:
            pedido.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                status, texto = r.status, r.read().decode()
        except urllib.error.HTTPError as erro:
            status, texto = erro.code, erro.read().decode()
        try:
            return status, json.loads(texto)
        except ValueError:
            return status, {'_texto': texto}

    def entrar(self, email, senha):
        status, corpo = self.pedir('POST', '/api/login', {'email': email, 'senha': senha})
        return corpo.get('token') if status == 200 else None


def total_gravado(banco, pedido_id):
    con = sqlite3.connect(banco)
    try:
        linha = con.execute('select total_centavos from pedidos where id = ?', (pedido_id,)).fetchone()
    finally:
        con.close()
    return linha[0] if linha else None


def contar_pedidos(banco):
    con = sqlite3.connect(banco)
    try:
        return con.execute('select count(*) from pedidos').fetchone()[0]
    finally:
        con.close()


def checar_senha_fixa(c, ctx):
    if c.entrar('admin@aurora.example', 'Aurora@2026'):
        return False, 'a senha de administrador escrita no código ainda entra'
    if not c.entrar('renata@aurora.example', 'Renata#teste4'):
        return False, 'a Renata precisa entrar com a conta dela no provedor'
    return True, 'a senha escrita no código não entra; a Renata entra com a conta dela'


def checar_login_no_provedor(c, ctx):
    ctx['loja'].provedor.definir_senha('bia@cliente.example', 'Bia#nova9')
    antiga = c.entrar('bia@cliente.example', 'Bia#teste1')
    nova = c.entrar('bia@cliente.example', 'Bia#nova9')
    ctx['loja'].provedor.definir_senha('bia@cliente.example', 'Bia#teste1')
    if antiga or not nova:
        return False, 'a senha trocada no provedor não mudou o login: o app ainda confere a senha na tabela dele'
    status, _ = c.pedir('GET', '/api/eu', token='token-inventado-pelo-navegador')
    if status != 401:
        return False, f'um token inventado foi aceito em /api/eu (resposta {status})'
    c.pedir('POST', '/api/sair', token=nova)
    status, _ = c.pedir('GET', '/api/eu', token=nova)
    if status != 401:
        return False, f'o token continua valendo depois de sair (resposta {status})'
    return True, 'quem confere a senha e o token é o provedor'


def checar_erro_do_login(c, ctx):
    a = c.pedir('POST', '/api/login', {'email': 'caio@cliente.example', 'senha': 'errada'})
    b = c.pedir('POST', '/api/login', {'email': 'ninguem@cliente.example', 'senha': 'errada'})
    if a != b:
        return False, f'e-mail cadastrado responde {a[0]} e e-mail que não existe responde {b[0]}: dá para saber quem é cliente'
    if a[0] < 400:
        return False, f'senha errada respondeu {a[0]}'
    a = c.pedir('POST', '/api/esqueci-senha', {'email': 'caio@cliente.example'})
    b = c.pedir('POST', '/api/esqueci-senha', {'email': 'ninguem@cliente.example'})
    if a != b:
        return False, f'"esqueci a senha" responde {a[0]} para quem tem conta e {b[0]} para quem não tem'
    return True, 'login e "esqueci a senha" respondem igual para e-mail cadastrado e não cadastrado'


def checar_preco(c, ctx):
    token = c.entrar('caio@cliente.example', 'Caio#teste2')
    if not token:
        return False, 'o Caio precisa conseguir entrar'
    status, normal = c.pedir('POST', '/api/pedidos', {'produto_id': 1, 'quantidade': 1, 'preco_centavos': LUMINARIA}, token)
    if status != 201 or normal.get('total_centavos') != LUMINARIA:
        return False, f'um pedido normal da luminária precisa sair com {LUMINARIA} centavos (saiu {status} {normal.get("total_centavos")})'
    antes = contar_pedidos(ctx['banco'])
    status, alterado = c.pedir('POST', '/api/pedidos', {'produto_id': 1, 'quantidade': 2, 'preco_centavos': 100}, token)
    if status == 201:
        if total_gravado(ctx['banco'], alterado.get('pedido_id')) != 2 * LUMINARIA:
            return False, f'o preço mandado pelo navegador virou o total do pedido ({alterado.get("total_centavos")} centavos)'
        return True, 'o total sai do preço do banco, não do que o navegador manda'
    if contar_pedidos(ctx['banco']) != antes:
        return False, f'o servidor respondeu {status}, mas gravou o pedido mesmo assim'
    return True, f'o pedido com preço alterado foi recusado ({status}) e nada foi gravado'


def checar_admin(c, ctx):
    status, _ = c.pedir('GET', '/api/admin/pedidos')
    if status not in (401, 403):
        return False, f'sem login nenhum, /api/admin/pedidos respondeu {status}'
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    status, corpo = c.pedir('GET', '/api/admin/pedidos', token=caio)
    if status != 403:
        n = len(corpo.get('pedidos', [])) if isinstance(corpo, dict) else '?'
        return False, f'o Caio, cliente comum, abriu /api/admin/pedidos (resposta {status}, {n} pedidos)'
    renata = c.entrar('renata@aurora.example', 'Renata#teste4')
    status, corpo = c.pedir('GET', '/api/admin/pedidos', token=renata)
    if status != 200 or not corpo.get('pedidos'):
        return False, f'a Renata, admin, precisa continuar vendo o painel (resposta {status})'
    return True, 'o papel de admin vem do banco: o Caio leva 403, a Renata vê o painel'


def checar_plano(c, ctx):
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    status, _ = c.pedir('GET', '/api/clube/guia?plano=clube', token=caio)
    if status != 403:
        return False, f'o Caio, do plano grátis, abriu o guia do Clube pedindo ?plano=clube (resposta {status})'
    bia = c.entrar('bia@cliente.example', 'Bia#teste1')
    status, _ = c.pedir('GET', '/api/clube/guia?plano=clube', token=bia)
    if status != 200:
        return False, f'a Bia, do Clube, precisa continuar abrindo o guia (resposta {status})'
    status, pedido = c.pedir('POST', '/api/pedidos', {'produto_id': 1, 'quantidade': 1, 'preco_centavos': LUMINARIA, 'plano': 'clube'}, caio)
    if status == 201 and total_gravado(ctx['banco'], pedido.get('pedido_id')) != LUMINARIA:
        return False, f'o Caio mandou "plano": "clube" e ganhou o desconto do Clube (total {pedido.get("total_centavos")})'
    status, pedido = c.pedir('POST', '/api/pedidos', {'produto_id': 1, 'quantidade': 1, 'preco_centavos': LUMINARIA, 'plano': 'clube'}, bia)
    if status != 201 or total_gravado(ctx['banco'], pedido.get('pedido_id')) != LUMINARIA - LUMINARIA * 10 // 100:
        return False, f'a Bia, do Clube, precisa ter os 10% de desconto (resposta {status}, total {pedido.get("total_centavos")})'
    return True, 'o plano vem do banco: o grátis não abre o guia nem ganha o desconto'


def checar_credito(c, ctx):
    caio = c.entrar('caio@cliente.example', 'Caio#teste2')
    status, pedido = c.pedir('POST', '/api/pedidos', {'produto_id': 5, 'quantidade': 1, 'preco_centavos': FITA_LED, 'credito_centavos': 8000}, caio)
    if status == 201 and total_gravado(ctx['banco'], pedido.get('pedido_id')) != FITA_LED:
        return False, f'o Caio não tem crédito, mandou "credito_centavos": 8000 e pagou {pedido.get("total_centavos")}'
    duda = c.entrar('duda@cliente.example', 'Duda#teste3')
    corpo = {'produto_id': 5, 'quantidade': 1, 'preco_centavos': FITA_LED, 'credito_centavos': 1500}
    status, primeiro = c.pedir('POST', '/api/pedidos', corpo, duda)
    if status != 201 or total_gravado(ctx['banco'], primeiro.get('pedido_id')) != FITA_LED - 1500:
        return False, f'a Duda tem 1500 de crédito e o primeiro pedido precisa sair com {FITA_LED - 1500} (saiu {status} {primeiro.get("total_centavos")})'
    status, segundo = c.pedir('POST', '/api/pedidos', corpo, duda)
    if status == 201 and total_gravado(ctx['banco'], segundo.get('pedido_id')) != FITA_LED:
        return False, f'a Duda usou os mesmos 1500 de crédito duas vezes (segundo pedido: {segundo.get("total_centavos")})'
    return True, 'o crédito vem do saldo no banco e sai do saldo quando é usado'


CHECAGENS = [
    ('senha-fixa', 'senha de administrador no código', checar_senha_fixa),
    ('login-no-provedor', 'login caseiro no lugar do provedor', checar_login_no_provedor),
    ('erro-do-login', 'erro que revela se o e-mail existe', checar_erro_do_login),
    ('preco-do-navegador', 'total calculado com o preço do navegador', checar_preco),
    ('admin-pela-tela', 'painel de admin protegido só pela tela', checar_admin),
    ('plano-do-navegador', 'plano do Clube lido do navegador', checar_plano),
    ('credito-do-navegador', 'crédito de troca lido do navegador', checar_credito),
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
            banco = Path(tmp) / codigo / 'aurora.db'   # banco novo para cada checagem
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
            print(f'{"fechada" if ok else "ABERTA ":7}  {codigo:21}  {nome}: {motivo}')
    print(f'\n{len(CHECAGENS) - abertas} de {len(CHECAGENS)} fechadas.')
    return 0 if abertas == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
