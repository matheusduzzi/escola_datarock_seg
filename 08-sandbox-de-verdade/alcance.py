"""Lista o que este processo alcança e o que não alcança: arquivos, variáveis e rede.

Rode dentro do contêiner (é o comando padrão da imagem) ou no seu computador, para comparar:

    python3 alcance.py

Só olha se o arquivo existe e se dá para ler. Nunca mostra o conteúdo de arquivo nem o
valor de variável. Na rede, abre a conexão e fecha, sem mandar nada.
Sai sempre com 0: é um relatório, não um teste.
"""
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

INTERNET = ('example.com', 443)       # um site qualquer da internet
COLETOR = ('coletor', 9000)           # o servidor de fora do kit (coletor.py)
PERMITIDO = ('api.anthropic.com', 443)  # o endereço que a porta de saída deixa passar
SOQUETE = os.environ.get('AURORA_SOQUETE', '/var/run/docker.sock')
PALAVRAS = ('KEY', 'TOKEN', 'SECRET', 'SECRETA', 'SEGREDO', 'SENHA', 'PASSWORD', 'CHAVE')


def enderecos():
    """AURORA_ENDERECOS="coletor=127.0.0.1:9000,porta=127.0.0.1:3128" troca nome por endereço.

    Serve só para os testes do curso rodarem fora do Docker, com os mesmos nomes na saída."""
    mapa = {}
    for par in filter(None, os.environ.get('AURORA_ENDERECOS', '').split(',')):
        nome, alvo = par.split('=')
        host, porta = alvo.rsplit(':', 1)
        mapa[nome.strip()] = (host, int(porta))
    return mapa


def conectar(host, porta, tempo=4):
    host, porta = enderecos().get(host, (host, porta))
    return socket.create_connection((host, porta), timeout=tempo)


def direto(alvo):
    try:
        conectar(*alvo).close()
        return True, 'conecta'
    except OSError:
        return False, 'sem conexão'


def pela_porta(alvo):
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if not proxy:
        return None, 'sem porta de saída configurada'
    p = urlsplit(proxy if '://' in proxy else 'http://' + proxy)
    try:
        s = conectar(p.hostname, p.port or 3128)
    except OSError:
        return False, 'a porta de saída não responde'
    try:
        s.sendall(f'CONNECT {alvo[0]}:{alvo[1]} HTTP/1.1\r\nHost: {alvo[0]}:{alvo[1]}\r\n\r\n'.encode())
        resposta = s.recv(1024).decode('latin-1').split('\r\n')[0]
    except OSError:
        return False, 'a porta de saída não respondeu'
    finally:
        s.close()
    codigo = resposta.split(' ')[1] if len(resposta.split(' ')) > 1 else '?'
    return codigo == '200', f'a porta respondeu {codigo}'


def arquivos_env(raizes):
    achados = []
    for raiz in raizes:
        if not raiz.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(raiz):
            if dirpath.count(os.sep) - str(raiz).count(os.sep) >= 4:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if d not in ('node_modules', '.git', '__pycache__')]
            for f in filenames:
                if f == '.env' or (f.startswith('.env.') and not f.endswith(('exemplo', 'example'))):
                    achados.append(Path(dirpath) / f)
    return sorted(set(achados))


def legivel(p):
    try:
        with open(p, 'rb') as f:
            f.read(1)
        return True
    except OSError:
        return False


def escreve(pasta):
    try:
        with tempfile.NamedTemporaryFile(dir=pasta, prefix='.alcance-'):
            pass
        return True
    except OSError:
        return False


def curto(p):
    casa, aqui = Path.home(), Path.cwd()
    p = Path(p)
    if p == aqui:
        return '.'
    for base, rotulo in ((aqui, '.'), (casa, '~')):
        try:
            return rotulo + '/' + str(p.relative_to(base))
        except ValueError:
            pass
    return str(p)


def main():
    linhas = []

    def anota(alcanca, o_que, detalhe):
        linhas.append((alcanca, o_que, detalhe))

    casa, aqui = Path.home(), Path.cwd()
    anota(True, 'pasta de trabalho (.)', 'lê e escreve' if escreve(aqui) else 'só lê')
    anota(escreve(casa), 'pasta de usuário (~)', 'escreve' if escreve(casa) else 'não escreve')
    ssh = [p for p in (casa / '.ssh').glob('*') if p.is_file() and legivel(p)] if (casa / '.ssh').is_dir() else []
    anota(bool(ssh), 'chaves SSH (~/.ssh)', ', '.join(p.name for p in ssh) if ssh else 'nada')
    nuvem = [p for p in (casa / '.aws/credentials', casa / '.config/gcloud', casa / '.azure') if p.exists() and (p.is_dir() or legivel(p))]
    anota(bool(nuvem), 'credenciais de nuvem (~/.aws, ~/.config/gcloud, ~/.azure)', ', '.join(curto(p) for p in nuvem) if nuvem else 'nada')
    envs = [p for p in arquivos_env([aqui, casa]) if legivel(p)]
    anota(bool(envs), 'arquivos .env', ', '.join(curto(p) for p in envs) if envs else 'nada')
    nomes = sorted(n for n in os.environ if any(w in n.upper() for w in PALAVRAS))
    anota(bool(nomes), 'variáveis com cara de segredo', ', '.join(nomes) if nomes else 'nenhuma')
    anota(os.path.exists(SOQUETE), 'o Docker do computador (docker.sock)', 'o soquete está aqui' if os.path.exists(SOQUETE) else 'não está aqui')
    ok, d = direto(INTERNET)
    anota(ok, f'internet direta ({INTERNET[0]}:{INTERNET[1]})', d)
    ok, d = direto(COLETOR)
    anota(ok, f'servidor de fora, direto ({COLETOR[0]}:{COLETOR[1]})', d)
    for alvo, rotulo in ((PERMITIDO, 'destino da lista, pela porta'), (COLETOR, 'servidor de fora, pela porta')):
        ok, d = pela_porta(alvo)
        anota(ok, f'{rotulo} ({alvo[0]}:{alvo[1]})', d)

    usuario = 'root' if hasattr(os, 'geteuid') and os.geteuid() == 0 else 'não é root'
    print(f'Usuário: {usuario}')
    for alcanca, o_que, detalhe in linhas:
        marca = 'ALCANÇA    ' if alcanca else ('—          ' if alcanca is None else 'NÃO ALCANÇA')
        print(f'{marca}  {o_que}: {detalhe}')
    total = sum(1 for a, _, _ in linhas if a)
    print(f'Resumo: alcança {total} de {len(linhas)}.')


if __name__ == '__main__':
    main()
