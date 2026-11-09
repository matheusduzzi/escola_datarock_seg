"""A máscara que roda antes de qualquer linha ir para o log.

Cada regra troca o que casa com o padrão por um marcador. A ordem conta:
o e-mail vem primeiro porque ele pode ter números no meio.
"""
import re

REGRAS = [
    ('[EMAIL]', re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')),
    ('[CPF]', re.compile(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b')),
    ('[TELEFONE]', re.compile(r'\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b')),
]


def mascarar(texto):
    for marcador, padrao in REGRAS:
        texto = padrao.sub(marcador, texto)
    return texto
