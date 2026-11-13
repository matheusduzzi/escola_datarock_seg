"""Lê a planilha de pedidos e escreve etiquetas.txt com os pedidos pagos."""
import csv
import sys
from pathlib import Path


def gerar(caminho_csv, saida="etiquetas.txt"):
    linhas = []
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        for pedido in csv.DictReader(f):
            if pedido["status"] != "pago":
                continue
            linhas.append(f"{pedido['nome']}\n{pedido['endereco']}\nCEP {pedido['cep']}\n")
    Path(saida).write_text("\n".join(linhas), encoding="utf-8")
    return len(linhas)


if __name__ == "__main__":
    print(f"{gerar(sys.argv[1])} etiquetas em etiquetas.txt")
