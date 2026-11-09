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
        return status, json.loads(texto)

    def entrar(self, email, senha):
        status, corpo = self.pedir('POST', '/api/login', {'email': email, 'senha': senha})
        self.assertEqual(status, 200, corpo)
        return corpo['token']

    def test_so_escuta_no_proprio_computador(self):
        self.assertEqual(self.servidor.server_address[0], '127.0.0.1')

    def test_catalogo_tem_12_produtos(self):
        status, corpo = self.pedir('GET', '/api/produtos')
        self.assertEqual((status, len(corpo['produtos'])), (200, 12))

    def test_bia_ve_os_pedidos_dela(self):
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        status, corpo = self.pedir('GET', '/api/meus-pedidos', token=token)
        self.assertEqual((status, [p['produto'] for p in corpo['pedidos']]),
                         (200, ['Luminária de mesa Aurora', 'Vela aromática Alecrim']))
        status, pedido = self.pedir('GET', f'/api/pedidos/{corpo["pedidos"][0]["id"]}', token=token)
        self.assertEqual((status, pedido['endereco']), (200, 'Rua das Acácias, 120, ap. 31, Campinas'))

    def test_bia_baixa_a_nota_do_pedido_dela(self):
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        _, corpo = self.pedir('GET', '/api/meus-pedidos', token=token)
        status, nota = self.pedir('GET', f'/api/pedidos/{corpo["pedidos"][0]["id"]}/nota', token=token)
        self.assertEqual(status, 200)
        status, texto = self.bruto('GET', nota['url'])
        self.assertEqual(status, 200)
        self.assertIn('Cliente: Bia Santos', texto)
        self.assertIn('Total: R$ 249,90', texto)

    def test_tela_de_perfil_abre_com_os_dados_da_bia(self):
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        status, u = self.pedir('GET', '/api/usuarios?email=bia@cliente.example', token=token)
        self.assertEqual(status, 200)
        self.assertEqual((u['nome'], u['telefone'], u['cidade'], u['plano'], u['creditos']),
                         ('Bia Santos', '19 90000-0101', 'Campinas', 'clube', 0))

    def test_perfil_salva_o_que_a_tela_manda(self):
        token = self.entrar('duda@cliente.example', 'Duda#teste3')
        status, _ = self.pedir('PATCH', '/api/perfil', {'nome': 'Duda Rocha', 'telefone': '19 98888-0303', 'cidade': 'Hortolândia'}, token)
        self.assertEqual(status, 200)
        _, u = self.pedir('GET', '/api/usuarios?email=duda@cliente.example', token=token)
        self.assertEqual((u['telefone'], u['cidade'], u['creditos']), ('19 98888-0303', 'Hortolândia', 1500))

    def test_credito_de_troca_entra_no_pedido(self):
        token = self.entrar('duda@cliente.example', 'Duda#teste3')
        status, pedido = self.pedir('POST', '/api/pedidos', {'produto_id': 5, 'quantidade': 1, 'preco_centavos': 8990}, token)
        self.assertEqual((status, pedido['total_centavos']), (201, 7490))

    def test_renata_ve_o_painel(self):
        token = self.entrar('renata@aurora.example', 'Renata#teste4')
        status, corpo = self.pedir('GET', '/api/admin/pedidos', token=token)
        self.assertEqual((status, len(corpo['pedidos'])), (200, 4))

    def test_sem_login_nao_ve_pedido(self):
        status, _ = self.pedir('GET', '/api/meus-pedidos')
        self.assertEqual(status, 401)


if __name__ == '__main__':
    unittest.main()
