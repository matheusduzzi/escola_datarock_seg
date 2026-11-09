"""Checa como se entra no servidor do curso.

Dois jeitos de usar:

    docker exec servidor sshd -T | python3 checar_servidor.py config
    python3 checar_servidor.py acesso --porta 2222 --chave chave-aurora

O primeiro lê a configuração que o SSH do servidor está usando de verdade (a saída do
`sshd -T`) e diz o que continua aberto. O segundo bate na porta do servidor como um
cliente faria: vê se ele ainda oferece senha e se a sua chave entra, e com qual usuário.

Sai com 1 enquanto alguma linha estiver ABERTA (ou a chave não entrar) e com 0 quando
tudo fechar. Sai com 2 quando não recebe nada para checar.

Só para o servidor do curso, no seu computador. O `acesso` não confere a impressão
digital do servidor (ele muda a cada `docker build`); num servidor de verdade, confira.
"""
import argparse
import subprocess
import sys

ADMIN = {'root', 'docker'}      # grupos que, na prática, mandam no computador como root
SUDO = {'sudo', 'wheel'}        # grupos que viram root com sudo


def config(texto):
    valores = {}
    for linha in texto.splitlines():
        partes = linha.strip().split(None, 1)
        if len(partes) == 2:
            valores.setdefault(partes[0].lower(), partes[1].strip())
    if 'permitrootlogin' not in valores:
        print('Não recebi a saída do sshd -T. Rode: docker exec servidor sshd -T | python3 checar_servidor.py config')
        return 2
    linhas = []
    root = valores['permitrootlogin']
    if root == 'no':
        linhas.append(('FECHADA', 'login como root', 'permitrootlogin no'))
    elif root in ('prohibit-password', 'without-password', 'forced-commands-only'):
        linhas.append(('ABERTA', 'login como root', f'permitrootlogin {root}: root ainda entra com chave'))
    else:
        linhas.append(('ABERTA', 'login como root', f'permitrootlogin {root}'))
    for chave, nome in (('passwordauthentication', 'login por senha'),
                        ('kbdinteractiveauthentication', 'senha pelo teclado'),
                        ('permitemptypasswords', 'senha vazia')):
        v = valores.get(chave, '?')
        linhas.append(('ABERTA' if v == 'yes' else 'FECHADA', nome, f'{chave} {v}'))
    v = valores.get('pubkeyauthentication', '?')
    linhas.append(('FUNCIONA' if v == 'yes' else 'DESLIGADA', 'acesso por chave', f'pubkeyauthentication {v}'))
    for estado, nome, detalhe in linhas:
        print(f'{estado:<9} {nome}: {detalhe}')
    problemas = sum(1 for e, _, _ in linhas if e in ('ABERTA', 'DESLIGADA'))
    print('Resumo:', 'nada a resolver.' if not problemas else f'{problemas} a resolver.')
    return 1 if problemas else 0


def ssh(host, porta, usuario, extra, comando='true'):
    base = ['ssh', '-p', str(porta), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
            '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'LogLevel=ERROR']
    r = subprocess.run(base + extra + [f'{usuario}@{host}', comando], capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout, r.stderr


def metodos(stderr):
    for linha in stderr.splitlines():
        if 'Permission denied (' in linha:
            return linha.split('Permission denied (', 1)[1].rstrip(').').split(',')
    return None


def acesso(host, porta, usuario, chave):
    print(f'Servidor {host}:{porta}')
    problemas = 0
    # 1. Sem chave nenhuma, o servidor diz que jeitos de entrar ele aceita.
    _, _, err = ssh(host, porta, 'root', ['-o', 'PubkeyAuthentication=no'])
    oferece = metodos(err)
    if oferece is None:
        print('Não consegui falar com o servidor:', err.strip().splitlines()[-1] if err.strip() else 'sem resposta')
        return 2
    senha = [m for m in oferece if m in ('password', 'keyboard-interactive')]
    if senha:
        problemas += 1
        print(f'ABERTA    login por senha: o servidor oferece {", ".join(oferece)}')
    else:
        print(f'FECHADA   login por senha: o servidor só oferece {", ".join(oferece)}')
    # 2. Com a sua chave, entra? Como quem?
    codigo, out, err = ssh(host, porta, usuario, ['-i', chave, '-o', 'IdentitiesOnly=yes'], 'id -u; id -Gn')
    if codigo != 0:
        problemas += 1
        motivo = ', '.join(metodos(err) or []) or (err.strip().splitlines()[-1] if err.strip() else f'código {codigo}')
        print(f'NÃO ENTRA acesso por chave como {usuario}: recusado ({motivo})')
    else:
        uid, grupos = out.splitlines()[0].strip(), set(out.splitlines()[1].split()) if len(out.splitlines()) > 1 else set()
        print(f'FUNCIONA  acesso por chave como {usuario}')
        if uid == '0':
            problemas += 1
            print(f'ABERTA    usuário: {usuario} é root')
        elif grupos & ADMIN:
            problemas += 1
            print(f'ABERTA    usuário: {usuario} está no grupo {", ".join(sorted(grupos & ADMIN))}, que manda no computador como root')
        else:
            print(f'FECHADA   usuário: {usuario} não é root')
            if grupos & SUDO:
                print(f'AVISO     usuário: {usuario} vira root com sudo; serve para você, nunca para a conta de um agente')
    print('Resumo:', 'nada a resolver.' if not problemas else f'{problemas} a resolver.')
    return 1 if problemas else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='modo', required=True)
    sub.add_parser('config', help='lê a saída do sshd -T pela entrada')
    a = sub.add_parser('acesso', help='bate na porta do servidor')
    a.add_argument('--host', default='127.0.0.1')
    a.add_argument('--porta', type=int, default=2222)
    a.add_argument('--usuario', default='aurora')
    a.add_argument('--chave', default='chave-aurora')
    args = p.parse_args()
    if args.modo == 'config':
        return config(sys.stdin.read())
    return acesso(args.host, args.porta, args.usuario, args.chave)


if __name__ == '__main__':
    sys.exit(main())
