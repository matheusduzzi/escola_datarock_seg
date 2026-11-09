"""A porta de saída: um proxy que só abre túnel https para os endereços de permitidos.txt.

Cada tentativa vira uma linha em registro/saida.jsonl (e aparece no terminal), liberada ou bloqueada.
O registro fica do lado de fora do contêiner do agente: ele não consegue apagar.

    python3 porta_de_saida.py                       # escuta em 0.0.0.0:3128
    python3 porta_de_saida.py --escuta 127.0.0.1 --porta 3128 --lista permitidos.txt --registro registro

Regras, nessa ordem:
1. pedido que não dá para ler: bloqueado;
2. destino fora da lista: bloqueado (nome igual, sem diferença de maiúscula; *.exemplo.com libera
   os subdomínios, não o exemplo.com);
3. destino da lista, mas sem ser túnel https (CONNECT na porta 443): bloqueado;
4. destino da lista que aponta para a rede local (127.x, 10.x, 192.168.x, 169.254.x...): bloqueado;
5. o resto passa.
"""
import argparse
import datetime
import ipaddress
import json
import os
import select
import socket
import threading
from pathlib import Path
from urllib.parse import urlsplit

AQUI = Path(__file__).resolve().parent
TRAVA = threading.Lock()


def ler_lista(caminho):
    nomes = []
    for linha in Path(caminho).read_text(encoding='utf-8').splitlines():
        linha = linha.split('#', 1)[0].strip().lower().rstrip('.')
        if linha:
            nomes.append(linha)
    return nomes


def na_lista(host, lista):
    host = host.lower().rstrip('.')
    for item in lista:
        if item.startswith('*.'):
            if host.endswith(item[1:]) and host != item[2:]:
                return True
        elif host == item:
            return True
    return False


def local(host, porta):
    """True se todos os endereços do nome são da rede local. Nome que não resolve conta como não local."""
    try:
        ips = {i[4][0] for i in socket.getaddrinfo(host, porta, proto=socket.IPPROTO_TCP)}
    except OSError:
        return False
    return bool(ips) and all(not ipaddress.ip_address(ip.split('%')[0]).is_global for ip in ips)


def decidir(metodo, alvo, lista):
    """Retorna (host, porta, motivo do bloqueio ou None)."""
    if metodo == 'CONNECT':
        host, _, porta = alvo.rpartition(':')
        host = host.strip('[]')
        if not host or not porta.isdigit():
            return alvo, 0, 'pedido ilegível'
        porta = int(porta)
    else:
        u = urlsplit(alvo)
        if not u.hostname:
            return alvo, 0, 'pedido ilegível'
        host, porta = u.hostname, u.port or (443 if u.scheme == 'https' else 80)
    if not na_lista(host, lista):
        return host, porta, 'fora da lista'
    if metodo != 'CONNECT' or porta != 443:
        return host, porta, 'só túnel https na porta 443'
    if local(host, porta):
        return host, porta, 'aponta para a rede local'
    return host, porta, None


def anotar(pasta, linha):
    texto = json.dumps(linha, ensure_ascii=False)
    with TRAVA:
        print(('LIBERADA ' if linha['decisao'] == 'liberada' else 'BLOQUEADA') + f"  {linha['destino']}  {linha.get('motivo', '')}".rstrip(), flush=True)
        if pasta:
            try:
                pasta.mkdir(parents=True, exist_ok=True)
                with open(pasta / 'saida.jsonl', 'a', encoding='utf-8') as f:
                    f.write(texto + '\n')
            except OSError as erro:
                print(f'(não consegui gravar o registro em {pasta}: {erro.strerror}; a linha acima é a mesma)', flush=True)


def tunel(a, b):
    pares = {a: b, b: a}
    try:
        while True:
            prontos, _, _ = select.select(list(pares), [], [], 60)
            if not prontos:
                return
            for s in prontos:
                dados = s.recv(65536)
                if not dados:
                    return
                pares[s].sendall(dados)
    except OSError:
        return


def atender(cliente, origem, lista, pasta):
    destino = None
    try:
        cliente.settimeout(10)
        bruto = b''
        while b'\r\n\r\n' not in bruto and len(bruto) < 16384:
            pedaco = cliente.recv(4096)
            if not pedaco:
                break
            bruto += pedaco
        primeira = bruto.split(b'\r\n', 1)[0].decode('latin-1')
        partes = primeira.split(' ')
        hora = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        if len(partes) != 3 or not partes[2].startswith('HTTP/'):
            anotar(pasta, {'hora': hora, 'origem': origem, 'metodo': '?', 'destino': primeira[:80] or '(vazio)',
                           'decisao': 'bloqueada', 'motivo': 'pedido ilegível'})
            cliente.sendall(b'HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n')
            return
        metodo, alvo = partes[0].upper(), partes[1]
        host, porta, motivo = decidir(metodo, alvo, lista)
        linha = {'hora': hora, 'origem': origem, 'metodo': metodo, 'destino': f'{host}:{porta}' if porta else host}
        if motivo:
            anotar(pasta, dict(linha, decisao='bloqueada', motivo=motivo))
            corpo = f'bloqueado pela porta de saída: {motivo}\n'.encode()
            cliente.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: '
                            + str(len(corpo)).encode() + b'\r\n\r\n' + corpo)
            return
        try:
            destino = socket.create_connection((host, porta), timeout=10)
        except OSError:
            anotar(pasta, dict(linha, decisao='liberada', motivo='mas o destino não respondeu'))
            cliente.sendall(b'HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n')
            return
        anotar(pasta, dict(linha, decisao='liberada'))
        cliente.sendall(b'HTTP/1.1 200 Connection established\r\n\r\n')
        tunel(cliente, destino)
    except OSError:
        pass
    finally:
        for s in (cliente, destino):
            if s:
                try:
                    s.close()
                except OSError:
                    pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--escuta', default='0.0.0.0')
    ap.add_argument('--porta', type=int, default=3128)
    ap.add_argument('--lista', default=os.environ.get('PORTA_LISTA', str(AQUI / 'permitidos.txt')))
    ap.add_argument('--registro', default=os.environ.get('PORTA_REGISTRO', '/registro' if Path('/registro').is_dir() else str(AQUI / 'registro')))
    a = ap.parse_args()
    lista = ler_lista(a.lista)
    pasta = Path(a.registro)
    servidor = socket.create_server((a.escuta, a.porta), reuse_port=False)
    print(f'Porta de saída em {a.escuta}:{a.porta}. Liberados: {", ".join(lista) or "nenhum"}. Registro: {pasta}/saida.jsonl', flush=True)
    try:
        while True:
            cliente, endereco = servidor.accept()
            threading.Thread(target=atender, args=(cliente, endereco[0], lista, pasta), daemon=True).start()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
