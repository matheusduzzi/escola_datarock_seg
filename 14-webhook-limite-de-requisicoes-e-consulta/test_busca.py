"""O teste que quebrou a busca: uma cliente procura o abajur Gota d'Água.

É um pedido de cliente honesta, não de atacante. Enquanto a busca colar o texto na consulta,
o apóstrofo de d'Água fecha o texto antes da hora e a consulta quebra.

    python3 -m unittest -v test_busca
"""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app  # noqa: E402


class BuscaComApostrofo(unittest.TestCase):
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

    def buscar(self, texto):
        url = self.base + '/api/produtos?busca=' + urllib.parse.quote(texto)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as erro:
            return erro.code, json.loads(erro.read().decode())

    def test_busca_por_dagua_acha_o_abajur(self):
        status, corpo = self.buscar("d'Água")
        self.assertEqual(status, 200, corpo)
        self.assertEqual([p['nome'] for p in corpo['produtos']], ["Abajur Gota d'Água"])


if __name__ == '__main__':
    unittest.main()
