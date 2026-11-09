"""Testes do uso normal da Loja Aurora dessa aula. Eles não testam as falhas: isso é o checar.py.

Passam antes e depois da correção. Se um deles quebrar depois que você mexeu no app,
a correção tirou algo que o cliente honesto usa.

    python3 -m unittest -v
"""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app  # noqa: E402


class LojaFunciona(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        banco = Path(self.tmp.name) / 'aurora.db'
        app.dados.montar(banco)
        self.servidor = app.criar_servidor(app.Loja(banco, app.ler_env()), 0)
        self.servidor.RequestHandlerClass.log_message = lambda *a, **k: None
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.servidor.server_address[1]}'

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.tmp.cleanup()

    def pedir(self, metodo, caminho, corpo=None, token=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo)
        pedido.add_header('Content-Type', 'application/json')
        if token:
            pedido.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(pedido, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read().decode())

    def entrar(self, email, senha):
        status, corpo = self.pedir('POST', '/api/login', {'email': email, 'senha': senha})
        self.assertEqual(status, 200, corpo)
        return corpo['token']

    def comprar(self, token, produto_id, preco, eu):
        """Faz o pedido como o front faz: com o preço da tela, o plano e o crédito da conta."""
        subtotal = preco
        desconto = subtotal * 10 // 100 if eu['plano'] == 'clube' else 0
        credito = min(eu['credito_centavos'], subtotal - desconto)
        return self.pedir('POST', '/api/pedidos', {'produto_id': produto_id, 'quantidade': 1, 'preco_centavos': preco,
                                                   'plano': eu['plano'], 'credito_centavos': credito}, token)

    def test_so_escuta_no_proprio_computador(self):
        self.assertEqual(self.servidor.server_address[0], '127.0.0.1')

    def test_catalogo_tem_12_produtos(self):
        status, corpo = self.pedir('GET', '/api/produtos')
        self.assertEqual((status, len(corpo['produtos'])), (200, 12))

    def test_cliente_do_clube_tem_desconto_e_guia(self):
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        status, eu = self.pedir('GET', '/api/eu', token=token)
        self.assertEqual((status, eu['plano'], eu['papel']), (200, 'clube', 'cliente'))
        status, pedido = self.comprar(token, 7, 6990, eu)
        self.assertEqual((status, pedido['total_centavos']), (201, 6291))
        status, guia = self.pedir('GET', '/api/clube/guia?plano=clube', token=token)
        self.assertEqual((status, len(guia['dicas'])), (200, 3))

    def test_cliente_do_plano_gratis_paga_o_preco_da_tela(self):
        token = self.entrar('caio@cliente.example', 'Caio#teste2')
        _, eu = self.pedir('GET', '/api/eu', token=token)
        status, pedido = self.comprar(token, 1, 24990, eu)
        self.assertEqual((status, pedido['total_centavos']), (201, 24990))

    def test_credito_de_troca_entra_no_pedido(self):
        token = self.entrar('duda@cliente.example', 'Duda#teste3')
        _, eu = self.pedir('GET', '/api/eu', token=token)
        self.assertEqual(eu['credito_centavos'], 1500)
        status, pedido = self.comprar(token, 5, 8990, eu)
        self.assertEqual((status, pedido['total_centavos']), (201, 7490))

    def test_renata_ve_o_painel(self):
        token = self.entrar('renata@aurora.example', 'Renata#teste4')
        status, corpo = self.pedir('GET', '/api/admin/pedidos', token=token)
        self.assertEqual((status, len(corpo['pedidos'])), (200, 4))

    def test_senha_errada_nao_entra(self):
        status, _ = self.pedir('POST', '/api/login', {'email': 'bia@cliente.example', 'senha': 'errada'})
        self.assertGreaterEqual(status, 400)

    def test_sair_encerra_a_sessao(self):
        token = self.entrar('caio@cliente.example', 'Caio#teste2')
        self.pedir('POST', '/api/sair', token=token)
        status, _ = self.pedir('GET', '/api/eu', token=token)
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
