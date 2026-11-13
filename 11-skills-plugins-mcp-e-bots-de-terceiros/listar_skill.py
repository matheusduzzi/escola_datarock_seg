"""Lista o que uma skill traz antes de você instalar. Só lê os arquivos: não roda nada da skill.

Uso: python3 listar_skill.py <pasta-da-skill>

Ele aponta onde olhar. Quem decide se a linha é problema é você, lendo o arquivo.
"""
import re
import sys
from pathlib import Path

SINAIS = [
    ("roda ao carregar", re.compile(r"!`[^`]+`")),
    ("texto escondido", re.compile(r"<!--")),
    ("endereço externo", re.compile(r"https?://[^\s)>\"']+")),
    ("segredo", re.compile(r"\.env\b|\.ssh|token|senha|password|api[_-]?key", re.I)),
    ("rede ou comando", re.compile(r"\b(subprocess|os\.system|urllib|requests|socket|curl|wget|eval|exec)\b")),
]


def frontmatter(texto):
    m = re.match(r"---\n(.*?)\n---\n", texto, re.S)
    return dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M)) if m else {}


def listar(pasta):
    pasta = Path(pasta)
    skill = pasta / "SKILL.md"
    if not skill.is_file():
        print(f"{pasta}: sem SKILL.md, não parece uma skill")
        return 2
    campos = frontmatter(skill.read_text(encoding="utf-8"))
    print(f"Skill: {campos.get('name', '?')}")
    ferramentas = campos.get("allowed-tools", "").strip()
    print(f"allowed-tools: {ferramentas or '(nenhuma)'}")
    for item in re.split(r"[\s,]+", ferramentas):
        if item and "(" not in item:
            print(f"  ! {item} pré-aprovada sem limite: roda sem pedir licença, em qualquer uso")
    print("Arquivos:")
    arquivos = sorted(p for p in pasta.rglob("*") if p.is_file())
    for p in arquivos:
        print(f"  {p.relative_to(pasta)} ({p.stat().st_size} bytes)")
    print("Linhas para ler com calma:")
    achou = 0
    for p in arquivos:
        try:
            linhas = p.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            print(f"  {p.relative_to(pasta)}: arquivo binário, abra com outra ferramenta")
            continue
        for n, linha in enumerate(linhas, 1):
            tipos = [nome for nome, rx in SINAIS if rx.search(linha)]
            if tipos:
                achou += 1
                trecho = linha.strip()
                trecho = trecho if len(trecho) <= 90 else trecho[:87] + "..."
                print(f"  {p.relative_to(pasta)}:{n} [{', '.join(tipos)}] {trecho}")
    if not achou:
        print("  nenhuma")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[2])
        sys.exit(2)
    sys.exit(listar(sys.argv[1]))
