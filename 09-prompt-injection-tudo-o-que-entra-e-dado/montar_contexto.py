"""Mostra o que o assistente da Loja Aurora recebe para uma mensagem, e o que uma pessoa vê na caixa de entrada.

    python3 montar_contexto.py 6            o que vai para o modelo com a mensagem 6
    python3 montar_contexto.py 6 --pessoa   o que a pessoa da equipe vê na caixa de entrada
    python3 montar_contexto.py G2           um dos textos da tarde (G1, G2, G3)

Não chama modelo nenhum e não precisa de internet. Lê as 15 mensagens em ../mensagens/,
os textos da tarde em tarde.json e as instruções e ferramentas do assistente nesta pasta.
"""
import argparse
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MANHA = AQUI.parent / "mensagens" / "mensagens-clientes.json"
TARDE = AQUI / "tarde.json"

# O que uma pessoa não vê na tela: comentário de HTML e texto pintado da cor do fundo.
ESCONDIDO = [
    ("comentário de HTML, que o navegador não mostra", re.compile(r"<!--.*?-->", re.S)),
    ("texto em branco sobre fundo branco", re.compile(r"\[texto em branco sobre fundo branco[^\]]*\].*", re.S)),
]


def carregar():
    if not MANHA.is_file():
        sys.exit(f"Não achei {MANHA}. Rode o script dentro da pasta da aula, com a pasta mensagens/ ao lado.")
    msgs = {str(m["id"]): m for m in json.loads(MANHA.read_text(encoding="utf-8"))["mensagens"]}
    msgs.update({m["id"]: m for m in json.loads(TARDE.read_text(encoding="utf-8"))["mensagens"]})
    return msgs


def ferramentas():
    linhas = (AQUI / "ferramentas.txt").read_text(encoding="utf-8").splitlines()
    return [l.split(":")[0].strip() for l in linhas if l.strip() and not l.startswith("#")]


def partes_escondidas(texto):
    achadas = []
    for nome, rx in ESCONDIDO:
        achadas += [nome for _ in rx.finditer(texto)]
    return achadas


def visto_pela_pessoa(texto):
    for _, rx in ESCONDIDO:
        texto = rx.sub("", texto)
    return texto.rstrip()


def main():
    p = argparse.ArgumentParser(description="Mostra o que o assistente recebe para uma mensagem.")
    p.add_argument("mensagem", help="número de 1 a 15, ou G1, G2, G3")
    p.add_argument("--pessoa", action="store_true", help="mostra o que a pessoa da equipe vê na caixa de entrada")
    a = p.parse_args()
    msgs = carregar()
    chave = a.mensagem.strip().upper().lstrip("0") or "0"
    if chave not in msgs:
        print(f"Mensagem {a.mensagem!r} não existe. Use um número de 1 a 15, ou G1, G2, G3.", file=sys.stderr)
        return 2
    m = msgs[chave]
    nome = f"mensagem {chave}" if chave.isdigit() else f"texto {chave}"
    escondidas = partes_escondidas(m["texto"])
    if a.pessoa:
        print(f"O que a pessoa vê na caixa de entrada: {nome} ({m['canal']})")
        print(f"de: {m['de']}")
        print(visto_pela_pessoa(m["texto"]))
        print("---")
        print(f"Partes que não aparecem na tela: {len(escondidas)}" + (f" ({'; '.join(escondidas)})" if escondidas else ""))
        return 0
    instrucoes = (AQUI / "prompt-do-assistente.txt").read_text(encoding="utf-8").strip()
    sistema = instrucoes + "\nFerramentas: " + ", ".join(ferramentas())
    usuario = f"canal: {m['canal']}\nde: {m['de']}\n{m['texto']}"
    print(f"O que o assistente recebe: {nome} ({m['canal']})")
    print("--- papel: system, escrito pela loja ---")
    print(sistema)
    print("--- papel: user, o que chegou ---")
    print(usuario)
    print("---")
    print(f"Vai tudo para o modelo numa sequência só: {len(sistema) + len(usuario)} caracteres, "
          f"{len(sistema)} da loja e {len(usuario)} do que chegou.")
    print(f"Partes que uma pessoa não vê na tela: {len(escondidas)}" + (f" ({'; '.join(escondidas)})" if escondidas else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
