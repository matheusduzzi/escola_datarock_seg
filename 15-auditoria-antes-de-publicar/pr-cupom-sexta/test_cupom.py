"""Testes da Sexta Aurora: 10% de desconto às sextas e o relatório de vendas do dia.

    python3 -m unittest -v test_cupom
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_app  # noqa: E402

SEXTA = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
QUARTA = datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)


class SextaAurora(unittest.TestCase):
    # Mesma loja de teste do test_app.py, sem rodar de novo os testes de lá.
    setUp = test_app.LojaFunciona.setUp
    tearDown = test_app.LojaFunciona.tearDown
    pedir = test_app.LojaFunciona.pedir
    entrar = test_app.LojaFunciona.entrar

    def no_dia(self, quando):
        self.loja.relogio = lambda: quando

    def pedido_do_caio(self):
        token = self.entrar('caio@cliente.example', 'Caio#teste2')
        return self.pedir('POST', '/api/pedidos', {'produto_id': 1, 'quantidade': 1}, token)

    def test_sexta_tem_10_por_cento(self):
        self.no_dia(SEXTA)
        status, pedido = self.pedido_do_caio()
        self.assertEqual((status, pedido['desconto_centavos'], pedido['total_centavos']), (201, 2499, 22491))

    def test_quarta_nao_tem_desconto(self):
        self.no_dia(QUARTA)
        status, pedido = self.pedido_do_caio()
        self.assertEqual((status, pedido['desconto_centavos']), (201, 0))

    def test_clube_nao_acumula_com_a_sexta(self):
        self.no_dia(SEXTA)
        token = self.entrar('bia@cliente.example', 'Bia#teste1')
        status, pedido = self.pedir('POST', '/api/pedidos', {'produto_id': 7, 'quantidade': 1}, token)
        self.assertEqual((status, pedido['desconto_centavos']), (201, 699))

    def test_renata_ve_as_vendas_da_sexta(self):
        self.no_dia(SEXTA)
        self.pedido_do_caio()
        token = self.entrar('renata@aurora.example', 'Renata#teste4')
        status, corpo = self.pedir('GET', '/api/admin/vendas?dia=2026-11-27', token=token)
        self.assertEqual((status, len(corpo['pedidos']), corpo['total_centavos']), (200, 1, 22491))


if __name__ == '__main__':
    unittest.main()
