"""A hora que os programas do kit anotam.

Sem nada configurado, é a hora do seu computador. Os testes do curso definem
AURORA_RELOGIO (por exemplo 2026-11-09T03:00:00-03:00) para a saída sair sempre igual;
cada chamada anda um segundo a partir dessa hora.
"""
import datetime
import os

_passo = 0


def agora():
    global _passo
    base = os.environ.get('AURORA_RELOGIO')
    if base:
        t = datetime.datetime.fromisoformat(base) + datetime.timedelta(seconds=_passo)
        _passo += 1
        return t
    return datetime.datetime.now().astimezone().replace(microsecond=0)
