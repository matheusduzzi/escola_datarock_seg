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
import gateway  # noqa: E402


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

    def pedir(self, metodo, caminho, corpo=None, token=None, bruto=None, cabecalhos=None):
        dados = bruto if bruto is not None else (json.dumps(corpo).encode() if corpo is not None else None)
        pedido = urllib.request.Request(self.base + caminho, data=dados, method=metodo, headers=cabecalhos or {})
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

    def test_catalogo_tem_13_produtos(self):
        status, corpo = self.pedir('GET', '/api/produtos')
        self.assertEqual((status, len(corpo['produtos'])), (200, 13))

    def test_busca_com_ordem_e_limite(self):
        status, corpo = self.pedir('GET', '/api/produtos?busca=Lumin%C3%A1ria&ordem=preco_centavos&limite=2')
        self.assertEqual((status, [p['preco_centavos'] for p in corpo['produtos']]), (200, [24990, 58900]))
        status, corpo = self.pedir('GET', '/api/produtos?ordem=nome&limite=3')
        self.assertEqual((status, [p['nome'] for p in corpo['produtos']]),
                         (200, ["Abajur Gota d'Água", 'Almofada linho Cru', 'Arandela de parede Fresta']))

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

    def test_gateway_marca_o_pedido_como_pago(self):
        bruto, cabecalhos = gateway.evento(app.ler_env()['WEBHOOK_SEGREDO'], 4, 'pago')
        status, _ = self.pedir('POST', '/webhook/pagamento', bruto=bruto, cabecalhos=cabecalhos)
        self.assertEqual(status, 200)
        token = self.entrar('duda@cliente.example', 'Duda#teste3')
        status, pedido = self.pedir('GET', '/api/pedidos/4', token=token)
        self.assertEqual((status, pedido['status']), (200, 'pago'))

    def test_newsletter_aceita_uma_inscricao(self):
        status, _ = self.pedir('POST', '/api/newsletter', {'email': 'leitora@cliente.example'})
        self.assertIn(status, (200, 201, 202))

    def test_assistente_responde_a_cliente(self):
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        status, corpo = self.pedir('POST', '/api/assistente', {'pergunta': 'Que luz eu ponho na cozinha?'}, token)
        self.assertEqual(status, 200)
        self.assertIn('4000 K', corpo['resposta'])

    def test_sair_encerra_a_sessao(self):
        token = self.entrar('caio@cliente.example', 'Caio#teste2')
        self.pedir('POST', '/api/sair', token=token)
        status, _ = self.pedir('GET', '/api/eu', token=token)
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
