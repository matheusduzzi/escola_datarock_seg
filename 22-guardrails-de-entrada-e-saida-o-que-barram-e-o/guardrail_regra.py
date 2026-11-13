"""Guardrail de regra fixa: lista de palavras, expressões regulares e lista de sites permitidos.

    python3 guardrail_regra.py entrada            # as 16 mensagens da manhã, antes do assistente
    python3 guardrail_regra.py saida              # as 16 respostas do assistente, antes de sair
    python3 guardrail_regra.py entrada --regras minhas-regras.json
    python3 guardrail_regra.py entrada --texto "uma frase sua"   # testa só essa frase

As regras ficam em regras.json. O guardrail só olha os campos listados em "campos".
Ele não lê imagem: quando uma mensagem traz um anexo, a saída avisa que o anexo não foi lido.
Sai 0 quando roda (barrar uma mensagem não é erro) e 2 quando um arquivo ou uma regra está errado.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MENSAGENS = [AQUI.parent / "mensagens" / "mensagens-clientes.json", AQUI / "mensagem-16.json"]
RESPOSTAS = AQUI / "respostas-do-assistente.json"


def parar(msg):
    print("erro: " + msg, file=sys.stderr)
    sys.exit(2)


def normalizar(texto):
    """Minúsculas e sem acento, para que «Esqueça» e «esqueca» sejam a mesma palavra."""
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def ler_json(caminho):
    if not caminho.is_file():
        parar(f"não achei {caminho}. Rode o comando dentro da pasta 10-guardrails do kit.")
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        parar(f"{caminho.name} não é um JSON válido (linha {e.lineno}, coluna {e.colno}).")


def carregar_itens(lado):
    if lado == "entrada":
        itens = []
        for caminho in MENSAGENS:
            itens += ler_json(caminho)["mensagens"]
        return itens
    return ler_json(RESPOSTAS)["respostas"]


def carregar_regras(caminho, lado):
    regras = ler_json(caminho)
    if lado not in regras:
        parar(f"{caminho.name} não tem a seção \"{lado}\".")
    r = regras[lado]
    campos = r.get("campos") or ["texto"]
    palavras = r.get("palavras", [])
    if any(not str(p).strip() for p in palavras):
        parar(f"{caminho.name}: há uma palavra vazia em \"{lado}\". Palavra vazia aparece em todo texto e barraria tudo.")
    padroes = []
    for nome, padrao in r.get("regex", {}).items():
        try:
            padroes.append((nome, re.compile(padrao)))
        except re.error as e:
            parar(f"{caminho.name}: a regex \"{nome}\" não compila ({e}).")
        if re.compile(padrao).search(""):
            parar(f"{caminho.name}: a regex \"{nome}\" casa com texto vazio e barraria tudo.")
    return campos, [(normalizar(p), p) for p in palavras], padroes, [normalizar(u) for u in r.get("urls_permitidas", [])]


def checar(texto, palavras, padroes, permitidas, olhar_urls):
    """Devolve a lista de motivos para barrar. Lista vazia quer dizer que passa."""
    t = normalizar(texto)
    motivos = [f"palavra «{original}»" for p, original in palavras if p in t]
    for url in re.findall(r"https?://[^\s\"'<>)]+", t) if olhar_urls else []:
        host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
        if not any(host == d or host.endswith("." + d) for d in permitidas):
            motivos.append(f"site fora da lista «{host}»")
    for nome, rx in padroes:
        if rx.search(t):
            motivos.append(f"regex «{nome}»")
    return motivos


def main(argv):
    if not argv or argv[0] not in ("entrada", "saida"):
        print(__doc__.strip())
        return 2
    lado = argv[0]
    caminho_regras = AQUI / "regras.json"
    if "--regras" in argv:
        i = argv.index("--regras")
        if i + 1 >= len(argv):
            parar("faltou o nome do arquivo depois de --regras.")
        caminho_regras = Path(argv[i + 1])
        if not caminho_regras.is_absolute():
            caminho_regras = Path.cwd() / caminho_regras
    campos, palavras, padroes, permitidas = carregar_regras(caminho_regras, lado)
    if "--texto" in argv:
        i = argv.index("--texto")
        if i + 1 >= len(argv) or not argv[i + 1].strip():
            parar("faltou a frase depois de --texto.")
        itens = [{"id": 0, "texto": argv[i + 1]}]
        campos = ["texto"]
    else:
        itens = carregar_itens(lado)
    if not any(c in item for item in itens for c in campos):
        parar(f"nenhum item tem os campos {campos}. Os campos que existem: {sorted(set(k for i in itens for k in i))}.")

    print(f"Guardrail de regra fixa, {lado}, campos: {', '.join(campos)}")
    barrados = 0
    for item in itens:
        texto = " ".join(str(item.get(c) or "") for c in campos)
        motivos = checar(texto, palavras, padroes, permitidas, olhar_urls=(lado == "saida"))
        linha = f"{item['id']:02d} " + ("BARRA  " + "; ".join(motivos) if motivos else "passa")
        if lado == "entrada" and item.get("imagem"):
            linha += f"  (anexo {item['imagem']} não foi lido)"
        print(linha)
        barrados += bool(motivos)
    print(f"Barrou {barrados} de {len(itens)}. Passaram {len(itens) - barrados}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
