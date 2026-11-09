"""Diz, para cada link, qual é o site de verdade e se ele é da loja.

    python3 dono_do_link.py links.txt
    python3 dono_do_link.py --link "https://aurora.example/pedidos"
    python3 dono_do_link.py links.txt --dominio suaempresa.com.br

O site de verdade é o que vem depois de "//" e antes da primeira "/", tirando o que estiver
antes de um "@". Ele é da loja quando é o domínio dela ou termina em ".dominio".
O programa não abre link nenhum: só lê o texto. Ser da loja diz quem é o dono do site,
não diz que a mensagem que trouxe o link é verdadeira.

Sai com 0 quando todos os links são da loja, com 1 quando algum não é (ou não dá para ler)
e com 2 quando não consegue ler o arquivo.
"""
import sys
from urllib.parse import urlsplit

DOMINIO = 'aurora.example'


def erro(msg):
    print('Erro: ' + msg, file=sys.stderr)
    sys.exit(2)


def em_ascii(host):
    try:
        return host.encode('idna').decode('ascii')
    except UnicodeError:
        return None


def ler_link(link, dominio):
    """Retorna (é da loja?, site de verdade, observação)."""
    if any(c.isspace() for c in link):
        return False, '-', 'tem espaço no meio: não dá para ler'
    if '://' not in link:
        return False, '-', 'falta o https:// no começo: não dá para saber o site'
    partes = urlsplit(link)
    if partes.scheme.lower() not in ('http', 'https'):
        return False, '-', f'começa com {partes.scheme}:, não é um site'
    autoridade = partes.netloc
    if '\\' in autoridade or '\\' in link.split('://', 1)[1].split('/', 1)[0]:
        return False, '-', 'tem barra invertida no endereço: cada navegador lê de um jeito'
    try:
        host = partes.hostname
    except ValueError:
        host = None
    if not host:
        return False, '-', 'não tem site depois do //'
    notas = []
    if '@' in autoridade:
        notas.append(f'antes do @ vem "{autoridade.rsplit("@", 1)[0]}", que não é o site')
    host = host.rstrip('.')
    if not host.isascii():
        convertido = em_ascii(host)
        notas.append('tem letra fora do alfabeto comum' + (f'; o navegador lê {convertido}' if convertido else ''))
        return False, host, '; '.join(notas)
    if '%' in host:
        return False, host, 'tem % no nome do site: o texto não mostra o site com certeza'
    if partes.scheme.lower() == 'http':
        notas.append('sem https')
    da_loja = host == dominio or host.endswith('.' + dominio)
    return da_loja, host, '; '.join(notas)


def main():
    args = sys.argv[1:]
    dominio, links, origem = DOMINIO, [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('--dominio', '--link'):
            if i + 1 >= len(args) or not args[i + 1].strip():
                erro(f'{a} precisa de um valor')
            if a == '--dominio':
                dominio = args[i + 1].strip().lower().rstrip('.')
            else:
                links.append(args[i + 1].strip())
            i += 2
        elif a.startswith('--'):
            erro(f'opção que não existe: {a}')
        else:
            if origem:
                erro('diga só um arquivo')
            origem = a
            i += 1
    if origem:
        try:
            with open(origem, encoding='utf-8-sig') as f:
                linhas = f.read().splitlines()
        except FileNotFoundError:
            erro(f'não achei o arquivo {origem}')
        except (IsADirectoryError, UnicodeDecodeError) as e:
            erro(f'não consegui ler {origem} ({e.__class__.__name__})')
        links += [l.strip() for l in linhas if l.strip() and not l.strip().startswith('#')]
    if not links:
        erro('nenhum link para ler. Exemplo: python3 dono_do_link.py links.txt')
    if not dominio or '/' in dominio or ' ' in dominio:
        erro(f'domínio "{dominio}" não dá para usar')

    fora = 0
    print(f'Domínio da loja: {dominio}')
    for n, link in enumerate(links, start=1):
        da_loja, host, nota = ler_link(link, dominio)
        fora += not da_loja
        rotulo = 'da loja    ' if da_loja else 'NÃO é da loja'
        print(f'{n:>2}. {rotulo:<13}  site: {host}')
        print(f'    {link}')
        if nota:
            print(f'    {nota}')
    print(f'{len(links)} link(s): {len(links) - fora} da loja, {fora} de outro site ou sem como ler.')
    sys.exit(1 if fora else 0)


if __name__ == '__main__':
    main()
