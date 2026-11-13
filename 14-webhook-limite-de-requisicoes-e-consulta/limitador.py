"""Limite de requisições por janela de tempo. Não edite este arquivo.

Faz o papel de uma biblioteca pronta de limite de requisições (no Python, Flask-Limiter ou
SlowAPI; no Node, express-rate-limit) ou do limite que o host e o gateway de API oferecem.
Você só decide a chave (o IP, o id do usuário), o máximo e a janela.

    from limitador import Limitador
    limite = Limitador(maximo=5, janela_segundos=600)    # 5 pedidos a cada 10 minutos
    liberado, espera = limite.permitir('127.0.0.1')     # chame uma vez por pedido
    if not liberado:
        ...  # responda 429 e diga em quantos segundos tentar de novo (cabeçalho Retry-After)

A conta fica na memória do processo: reiniciar o app zera os contadores. Com mais de um
servidor, o contador precisa ficar num lugar comum a todos (um Redis, o próprio banco ou o gateway).
"""
import math
import threading
import time
from collections import defaultdict, deque


class Limitador:
    def __init__(self, maximo, janela_segundos, relogio=time.monotonic):
        if maximo < 1 or janela_segundos <= 0:
            raise ValueError('maximo precisa ser 1 ou mais e janela_segundos, maior que zero')
        self.maximo = maximo
        self.janela = janela_segundos
        self.relogio = relogio
        self._pedidos = defaultdict(deque)   # chave -> horários dos pedidos aceitos na janela
        self._trava = threading.Lock()

    def permitir(self, chave):
        """Conta um pedido para a chave. Retorna (True, 0) se cabe na janela ou (False, segundos para liberar)."""
        agora = self.relogio()
        with self._trava:
            fila = self._pedidos[str(chave)]
            while fila and agora - fila[0] >= self.janela:
                fila.popleft()
            if len(fila) >= self.maximo:
                return False, max(1, math.ceil(self.janela - (agora - fila[0])))
            fila.append(agora)
            return True, 0
