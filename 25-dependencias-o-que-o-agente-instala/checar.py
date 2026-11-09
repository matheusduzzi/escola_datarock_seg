"""Checa as dependências da vitrine da Loja Aurora: o que continua aberto e o que já fechou.

    python3 checar.py            # olha a pasta vitrine/ ao lado
    python3 checar.py OUTRA      # olha outra pasta de projeto

Não instala nada e não acessa a internet. Lê o package.json, o package-lock.json, o .gitignore,
o código .js, o .github/dependabot.yml e o contrato-agente.csv do projeto. Os avisos de vulnerabilidade
vêm da pasta avisos/, no formato do banco OSV; o npm audit de verdade fica com você, no terminal.

Saída: 0 quando tudo fechou; 1 quando alguma linha continua ABERTA; 2 quando o projeto não pode ser lido.
"""
import csv
import fnmatch
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REGISTRO_NPM = 'https://registry.npmjs.org/'
CABECALHO_CONTRATO = ['ferramenta', 'tipo', 'coluna', 'confirmacao']
GRAVIDADE = {'CRITICAL': 'crítica', 'HIGH': 'alta', 'MODERATE': 'moderada', 'LOW': 'baixa'}
UMA_FUNCAO = ('is-even',)


class Ilegivel(Exception):
    pass


def versao(v):
    nucleo = re.split(r'[-+]', v, maxsplit=1)[0]
    return tuple(int(x) for x in nucleo.split('.'))


def atende(v, faixa):
    """Versão exata ou com ^, como no package.json da vitrine. Outra forma de faixa: não dá para dizer."""
    faixa = faixa.strip()
    if re.fullmatch(r'\d+\.\d+\.\d+', faixa):
        return v == faixa
    m = re.fullmatch(r'\^(\d+\.\d+\.\d+)', faixa)
    if not m:
        return None
    base, x = versao(m.group(1)), versao(v)
    if x < base:
        return False
    if base[0] > 0:
        return x[0] == base[0]
    if base[1] > 0:
        return x[0] == 0 and x[1] == base[1]
    return x == base


def ler_json(caminho):
    try:
        return json.loads(caminho.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise Ilegivel(f'{caminho.name} não é um JSON válido: {e}')


def pacotes_do_lock(lock):
    return {k[len('node_modules/'):]: v for k, v in lock.get('packages', {}).items() if k.startswith('node_modules/')}


def nomes_do_registro_do_curso():
    return {p.stem for p in (AQUI / 'registro').glob('*.json')}


def checar_lockfile(projeto, pkg, lock):
    ignorados = []
    gi = projeto / '.gitignore'
    if gi.is_file():
        for linha in gi.read_text(encoding='utf-8').splitlines():
            padrao = linha.strip().lstrip('/')
            if padrao and not padrao.startswith(('#', '!')) and fnmatch.fnmatch('package-lock.json', padrao):
                ignorados.append(linha.strip())
    if lock is None:
        return False, 'não há package-lock.json: cada instalação escolhe as versões de novo'
    if ignorados:
        return False, f'o .gitignore tem «{ignorados[0]}»: o lockfile fica fora do git e a próxima máquina resolve as versões de novo'
    deps = pkg.get('dependencies', {})
    raiz = lock.get('packages', {}).get('', {}).get('dependencies', {})
    if raiz != deps:
        return False, f'o package.json pede {fmt(deps)} e o lockfile foi feito para {fmt(raiz)}: rode o npm install de novo e guarde o lockfile novo'
    pacotes = pacotes_do_lock(lock)
    for nome, faixa in sorted(deps.items()):
        p = pacotes.get(nome)
        if p is None or atende(p.get('version', ''), faixa) is False:
            achado = p.get('version') if p else 'nada'
            return False, f'o package.json pede {nome} {faixa} e o lockfile tem {achado}'
    usados, fila = set(), list(deps)
    while fila:
        n = fila.pop()
        if n in usados or n not in pacotes:
            continue
        usados.add(n)
        fila.extend(pacotes[n].get('dependencies', {}))
    sobrando = sorted(set(pacotes) - usados)
    if sobrando:
        return False, f'o lockfile tem pacotes que ninguém pede: {", ".join(sobrando)}'
    return True, f'o lockfile está no git e bate com o package.json ({len(pacotes)} {"pacote" if len(pacotes) == 1 else "pacotes"})'


def fmt(deps):
    return ', '.join(f'{n} {v}' for n, v in sorted(deps.items())) or 'nenhum pacote'


def afetada(v, aviso, nome):
    for a in aviso.get('affected', []):
        if a.get('package', {}).get('ecosystem') != 'npm' or a.get('package', {}).get('name') != nome:
            continue
        for r in a.get('ranges', []):
            if r.get('type') != 'SEMVER':
                continue
            inicio, fim = None, None
            for ev in r.get('events', []):
                if 'introduced' in ev:
                    inicio = (0, 0, 0) if ev['introduced'] == '0' else versao(ev['introduced'])
                if 'fixed' in ev:
                    fim = versao(ev['fixed'])
            if inicio is not None and versao(v) >= inicio and (fim is None or versao(v) < fim):
                return r
    return None


def checar_vulneravel(lock):
    if lock is None:
        return False, 'sem lockfile não dá para saber que versão entra; a auditoria do npm também precisa dele'
    avisos = []
    for arq in sorted((AQUI / 'avisos').glob('*.json')):
        avisos.append(json.loads(arq.read_text(encoding='utf-8')))
    achados = []
    for nome, p in sorted(pacotes_do_lock(lock).items()):
        for aviso in avisos:
            r = afetada(p.get('version', '0.0.0'), aviso, nome)
            if r:
                fixed = next((ev['fixed'] for ev in r['events'] if 'fixed' in ev), None)
                grav = GRAVIDADE.get(aviso.get('database_specific', {}).get('severity', ''), 'sem gravidade')
                achados.append(f'{nome} {p["version"]} está no aviso {aviso["id"]} ({aviso.get("summary", "")}, {grav})'
                               + (f', corrigido na {fixed}' if fixed else ''))
    if achados:
        return False, '; '.join(achados)
    return True, 'nenhum pacote do lockfile está nos avisos da pasta avisos/'


def arquivos_js(projeto):
    for p in sorted(projeto.rglob('*.js')):
        if 'node_modules' not in p.relative_to(projeto).parts:
            yield p


def checar_uma_funcao(projeto, pkg, lock):
    onde = []
    deps = pkg.get('dependencies', {}) | pkg.get('devDependencies', {})
    pacotes = pacotes_do_lock(lock) if lock else {}
    for nome in UMA_FUNCAO:
        if nome in deps:
            onde.append(f'{nome} no package.json')
        if nome in pacotes:
            onde.append(f'{nome} no lockfile')
        for js in arquivos_js(projeto):
            if re.search(r"""require\(\s*['"]%s['"]\s*\)|from\s+['"]%s['"]""" % (re.escape(nome), re.escape(nome)),
                         js.read_text(encoding='utf-8')):
                onde.append(f'{nome} no {js.relative_to(projeto).as_posix()}')
    if onde:
        return False, ', '.join(onde)
    return True, 'nenhum pacote de uma função no projeto'


def checar_alerta(projeto, pkg):
    faltam = []
    yml = projeto / '.github' / 'dependabot.yml'
    if not yml.is_file():
        yml = projeto / '.github' / 'dependabot.yaml'
    if not yml.is_file():
        faltam.append('não há .github/dependabot.yml')
    else:
        t = yml.read_text(encoding='utf-8')
        if not re.search(r"""package-ecosystem:\s*['"]?npm['"]?\s*$""", t, re.M):
            faltam.append('o dependabot.yml não tem package-ecosystem npm')
        if not re.search(r'^\s*interval:\s*\S+', t, re.M):
            faltam.append('o dependabot.yml não tem schedule.interval')
    scripts = pkg.get('scripts', {})
    if not any(re.search(r'\bnpm audit\b', s or '') for s in scripts.values()):
        faltam.append('o package.json não tem um script com npm audit')
    if faltam:
        return False, '; '.join(faltam)
    return True, 'dependabot.yml para o npm e script de auditoria no package.json'


def checar_contrato(projeto):
    arq = projeto / 'contrato-agente.csv'
    if not arq.is_file():
        return False, 'não há contrato-agente.csv no projeto'
    linhas = list(csv.reader(arq.read_text(encoding='utf-8').splitlines()))
    if not linhas or [c.strip() for c in linhas[0]] != CABECALHO_CONTRATO:
        return False, 'o cabeçalho do contrato precisa ser ' + ','.join(CABECALHO_CONTRATO)
    achadas = [dict(zip(CABECALHO_CONTRATO, (c.strip() for c in l))) for l in linhas[1:] if l and l[0].strip() == 'instalar_pacote']
    if not achadas:
        return False, 'o contrato não tem a linha instalar_pacote'
    if len(achadas) > 1:
        return False, 'instalar_pacote aparece mais de uma vez; cada ferramenta fica numa coluna só'
    d = achadas[0]
    if d.get('coluna') != 'confirma':
        return False, f'instalar_pacote está em «{d.get("coluna")}»: instalar ou atualizar pacote pede confirmação'
    if d.get('confirmacao') != 'digitada':
        return False, f'instalar_pacote pede confirmação «{d.get("confirmacao") or "(vazia)"}»: a pessoa digita a frase com o nome do pacote'
    return True, 'instalar_pacote pede confirmação digitada, com o nome do pacote na frase'


def checar_nome(pkg, lock):
    do_curso = nomes_do_registro_do_curso()
    nomes = set(pkg.get('dependencies', {})) | set(pkg.get('devDependencies', {}))
    achados = sorted(n for n in nomes if n in do_curso)
    fora = []
    for nome, p in sorted((pacotes_do_lock(lock) if lock else {}).items()):
        if nome in do_curso:
            achados.append(nome)
        elif p.get('resolved') and not p['resolved'].startswith(REGISTRO_NPM):
            fora.append(f'{nome} ({p["resolved"]})')
    achados = sorted(set(achados))
    if achados or fora:
        partes = []
        if achados:
            partes.append('o projeto pede ' + ', '.join(achados) + ', que só existe no registro do curso')
        if fora:
            partes.append('o lockfile baixa de fora do registro do npm: ' + ', '.join(fora))
        return False, '; '.join(partes)
    return True, 'todo pacote vem do registro do npm e nenhum é o nome que o agente sugeriu'


CHECAGENS = [
    ('lockfile', 'lockfile no git e em dia'),
    ('vulneravel', 'versão com aviso de vulnerabilidade'),
    ('uma-funcao', 'pacote de uma função só'),
    ('alerta', 'alerta e auditoria ligados'),
    ('contrato', 'instalar pacote no contrato do agente'),
    ('nome-parecido', 'pacote com nome parecido'),
]


def main(argv):
    projeto = Path(argv[1]) if len(argv) > 1 else AQUI / 'vitrine'
    try:
        pkg = ler_json(projeto / 'package.json')
        if pkg is None:
            raise Ilegivel(f'não achei {projeto / "package.json"}')
        lock = ler_json(projeto / 'package-lock.json')
        resultados = {
            'lockfile': checar_lockfile(projeto, pkg, lock),
            'vulneravel': checar_vulneravel(lock),
            'uma-funcao': checar_uma_funcao(projeto, pkg, lock),
            'alerta': checar_alerta(projeto, pkg),
            'contrato': checar_contrato(projeto),
            'nome-parecido': checar_nome(pkg, lock),
        }
    except Ilegivel as e:
        print(f'ERRO {e}', file=sys.stderr)
        return 2
    fechadas = 0
    for chave, titulo in CHECAGENS:
        ok, detalhe = resultados[chave]
        fechadas += ok
        print(f'{"fechada" if ok else "ABERTA":<8} {chave:<14} {titulo}: {detalhe}')
    print(f'\n{fechadas} de {len(CHECAGENS)} fechadas.')
    return 0 if fechadas == len(CHECAGENS) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
