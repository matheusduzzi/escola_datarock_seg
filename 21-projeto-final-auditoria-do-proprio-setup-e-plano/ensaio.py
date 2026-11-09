"""Ensaio do plano de incidente: um vazamento de chave na Loja Aurora, em duas fases.

    python3 ensaio.py comecar              # monta a pasta cena/ e mostra o primeiro aviso
    python3 ensaio.py chaves               # as chaves da loja, mascaradas, e onde cada uma está
    python3 ensaio.py guardar              # copia os avisos e registros para cena/provas/, com o hash
    python3 ensaio.py trocar NOME --gravar hospedagem.env
                                           # revoga a chave NOME, cria a nova e grava nos arquivos que você disser
    python3 ensaio.py instalar NOME --em ci.env
                                           # grava a chave ativa NOME num arquivo que ficou com a velha
    python3 ensaio.py checar               # diz o que ainda está aberto; sai 0 quando a fase fecha
    python3 ensaio.py segunda-fase         # o segundo aviso, depois que a primeira fase fecha
    python3 ensaio.py comecar --de-novo    # apaga cena/ e começa do zero

Tudo acontece dentro de cena/. As chaves são da loja do curso e não abrem conta nenhuma.
A chave nova nunca aparece na tela: só os 4 últimos caracteres.
"""
import argparse
import hashlib
import json
import shutil
import string
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CENA = AQUI / 'cena'
ESTADO = CENA / '.estado.json'
ARQUIVOS_DE_CONFIG = ('hospedagem.env', 'ci.env', 'oauth.env')
PROVAS = ('aviso-1.txt', 'issue-publica.txt', 'registro-gateway.log', 'registro-ia.log')

# nome: (o que é, prefixo, valor inicial, arquivos onde está configurada)
CHAVES = {
    'PAGAMENTO_CHAVE_SECRETA': ('pagamento (gateway)', 'aurora_sk_live_', 'aurora_sk_live_Hn4Wd8Rk2Tq6Vz9Q7pX', ['hospedagem.env', 'ci.env']),
    'NUVEM_CHAVE': ('nuvem (fotos e notas fiscais)', 'aurora_nuvem_', 'aurora_nuvem_Bt7Lc2Mx9Pq4Js1Ka', ['hospedagem.env']),
    'GITHUB_OAUTH_HOSPEDAGEM': ('OAuth (hospedagem no GitHub da loja)', 'aurora_gho_', 'aurora_gho_Rw5Np8Dk3Hv6Lc1Ye', ['oauth.env']),
    'WEBHOOK_SEGREDO': ('webhook do pagamento', 'aurora_whsec_', 'aurora_whsec_Qa3Zm7Tx1Vb5Kn8Fs', ['hospedagem.env']),
    'DEPLOY_TOKEN': ('token de CI (publica na hospedagem)', 'aurora_ci_', 'aurora_ci_Ld6Ws2Gp9Rj4Mx7Ct', ['ci.env']),
    'DEPLOY_HOOK': ('deploy hook (URL que publica)', 'https://hospedagem.example/hook/', 'https://hospedagem.example/hook/Yk2Fv8Nb5Qs1Hd4Wm', ['ci.env']),
    'IA_CHAVE': ('provedor de IA (assistente)', 'aurora_llm_sk_', 'aurora_llm_sk_Jc9Pt3Xw6Lm2Rb5Ne', ['hospedagem.env']),
}

AVISO_1 = """De: Gateway de pagamento <seguranca@gateway.example>
Para: financeiro@aurora.example
Quinta, 06/11/2026, 21:40

Encontramos a sua chave secreta de produção, terminada em Q7pX, num site público
(uma issue de um repositório aberto). Considere a chave comprometida.
Nas últimas horas houve cobranças incomuns na sua conta. Veja o registro de uso.

---
Mensagem do Diego no grupo da loja, 21:52:
"Ontem à noite eu colei o .env inteiro numa issue da biblioteca de frete, pedindo ajuda
com um erro. Hoje de manhã eu apaguei o comentário. Acho que foi isso."
"""

ISSUE = """Issue #418 da biblioteca de frete (repositório público), comentário de diegoaurora, 05/11/2026 22:14
(apagado em 06/11/2026 08:03; a página ficou guardada em cache e foi copiada por um robô)

Oi, o cálculo de frete dá erro 500 no checkout. Segue meu .env pra vocês verem:

PUBLIC_LOJA_NOME=Loja Aurora
PUBLIC_PAGAMENTO_CHAVE_PUBLICA=aurora_pk_live_Gm5Rt8Xc2Nb6Lq9V
PAGAMENTO_CHAVE_SECRETA=aurora_sk_live_Hn4Wd8Rk2Tq6Vz9Q7pX
WEBHOOK_SEGREDO=aurora_whsec_Qa3Zm7Tx1Vb5Kn8Fs
IA_CHAVE=aurora_llm_sk_Jc9Pt3Xw6Lm2Rb5Ne
FRETE_CEP_ORIGEM=13010-000
"""

REGISTRO_GATEWAY = """# Registro de uso da chave secreta ...Q7pX (gateway), horário de Brasília
2026-11-05 18:02:11  203.0.113.10   POST /v1/cobrancas      R$ 189,90  aprovada   pedido 1041
2026-11-05 19:47:30  203.0.113.10   POST /v1/cobrancas      R$  74,50  aprovada   pedido 1042
2026-11-05 22:31:05  198.51.100.77  GET  /v1/saldo          -
2026-11-05 22:33:40  198.51.100.77  GET  /v1/clientes?limite=100   100 clientes (nome, e-mail, 4 últimos dígitos do cartão)
2026-11-06 03:12:02  198.51.100.77  POST /v1/cobrancas      R$   1,00  recusada   cartão final 4410
2026-11-06 03:12:09  198.51.100.77  POST /v1/cobrancas      R$   1,00  aprovada   cartão final 7731
2026-11-06 03:12:15  198.51.100.77  POST /v1/cobrancas      R$   1,00  recusada   cartão final 0926
2026-11-06 03:12:22  198.51.100.77  POST /v1/cobrancas      R$   1,00  aprovada   cartão final 5518
2026-11-06 03:12:30  198.51.100.77  POST /v1/cobrancas      R$   1,00  aprovada   cartão final 3307
2026-11-06 10:15:44  203.0.113.10   POST /v1/cobrancas      R$ 312,00  aprovada   pedido 1043
2026-11-06 20:58:13  198.51.100.77  POST /v1/estornos       R$ 189,90  pendente   pedido 1041, para outra conta
"""

REGISTRO_IA = """# Uso da chave ...b5Ne no provedor de IA, horário de Brasília
2026-11-05  modelo-pequeno     312 chamadas   US$ 0,41   (o assistente da loja usa este)
2026-11-06  modelo-pequeno     298 chamadas   US$ 0,39
2026-11-06  modelo-grande-v4  1840 chamadas   US$ 9,86   (a loja não usa este modelo)
"""

AVISO_2 = """De: Hospedagem <status@hospedagem.example>
Para: diego@aurora.example
Sexta, 07/11/2026, 16:05

Identificamos acesso indevido a um sistema interno. As variáveis de ambiente dos projetos,
os tokens de integração e os deploy hooks podem ter sido lidos. Recomendamos trocar todos
os segredos guardados conosco e revisar as integrações OAuth da sua conta.

Os deploys estão pausados até segunda ordem. Enquanto isso, uma variável alterada no painel
só passa a valer no próximo deploy.
"""


def agora():
    return time.time()


def hora(t):
    return datetime.fromtimestamp(t).strftime('%d/%m %H:%M:%S')


def mascarar(valor):
    corte = max(valor.rfind('_'), valor.rfind('/')) + 1
    return valor[:corte] + '…' + valor[-4:]


def chave_nova(prefixo, estado):
    estado['contador'] += 1
    base = hashlib.sha256(f"{estado['semente']}-{estado['contador']}".encode()).digest()
    letras = string.ascii_letters + string.digits
    return prefixo + ''.join(letras[b % len(letras)] for b in base[:18])


def ler_estado():
    if not ESTADO.exists():
        sys.exit('Não achei a cena. Rode python3 ensaio.py comecar antes.')
    return json.loads(ESTADO.read_text(encoding='utf-8'))


def gravar_estado(estado):
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def ler_config(arquivo):
    valores = {}
    for linha in (CENA / arquivo).read_text(encoding='utf-8').splitlines():
        if linha.strip() and not linha.startswith('#') and '=' in linha:
            nome, valor = linha.split('=', 1)
            valores[nome.strip()] = valor.strip()
    return valores


def gravar_valor(arquivo, nome, valor):
    linhas = (CENA / arquivo).read_text(encoding='utf-8').splitlines()
    achou = False
    for i, linha in enumerate(linhas):
        if linha.split('=', 1)[0].strip() == nome:
            linhas[i] = f'{nome}={valor}'
            achou = True
    if not achou:
        return False
    (CENA / arquivo).write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    return True


def anotar(estado, texto):
    estado['acoes'].append({'em': agora(), 'texto': texto})
    with (CENA / 'acoes.log').open('a', encoding='utf-8') as f:
        f.write(f'{hora(estado["acoes"][-1]["em"])}  {texto}\n')


def comecar(args):
    if CENA.exists():
        if not args.de_novo:
            print('A cena já existe. Use python3 ensaio.py comecar --de-novo para apagar e começar do zero.')
            return 1
        shutil.rmtree(CENA)
    CENA.mkdir()
    (CENA / 'aviso-1.txt').write_text(AVISO_1, encoding='utf-8')
    (CENA / 'issue-publica.txt').write_text(ISSUE, encoding='utf-8')
    (CENA / 'registro-gateway.log').write_text(REGISTRO_GATEWAY, encoding='utf-8')
    (CENA / 'registro-ia.log').write_text(REGISTRO_IA, encoding='utf-8')
    conteudo = {arq: [f'# {arq}: valores que estão configurados hoje'] for arq in ARQUIVOS_DE_CONFIG}
    conteudo['hospedagem.env'].insert(1, 'PUBLIC_PAGAMENTO_CHAVE_PUBLICA=aurora_pk_live_Gm5Rt8Xc2Nb6Lq9V')
    conteudo['ci.env'][0] += ' (o PAGAMENTO_CHAVE_SECRETA daqui roda os testes de checkout)'
    chaves = []
    for nome, (oque, prefixo, valor, onde) in CHAVES.items():
        for arq in onde:
            conteudo[arq].append(f'{nome}={valor}')
        chaves.append({'nome': nome, 'oque': oque, 'prefixo': prefixo, 'valor': valor,
                       'estado': 'ativa', 'criada_em': 0, 'revogada_em': None, 'onde': onde})
    for arq, linhas in conteudo.items():
        (CENA / arq).write_text('\n'.join(linhas) + '\n', encoding='utf-8')
    estado = {'fase': 1, 'inicio': agora(), 'fase2_em': None, 'contador': 0,
              'semente': hashlib.sha256(str(agora()).encode()).hexdigest()[:12], 'chaves': chaves, 'acoes': []}
    anotar(estado, 'ensaio começou: primeiro aviso recebido')
    gravar_estado(estado)
    print(AVISO_1)
    print('A cena está em cena/. Abra o seu plano de incidente e siga os passos dele.')
    return 0


def chaves_cmd(_args):
    estado = ler_estado()
    print(f'{"nome":24} {"o que é":38} {"chave":38} {"estado":22} onde')
    for c in estado['chaves']:
        quando = ' em ' + hora(c['revogada_em']) if c['revogada_em'] else ''
        print(f'{c["nome"]:24} {c["oque"]:38} {mascarar(c["valor"]):38} {c["estado"] + quando:22} {", ".join(c["onde"])}')
    return 0


def guardar(_args):
    estado = ler_estado()
    pasta = CENA / 'provas'
    pasta.mkdir(exist_ok=True)
    nomes = list(PROVAS) + (['aviso-2.txt'] if estado['fase'] == 2 else [])
    manifesto = {'guardado_em': hora(agora()), 'arquivos': {}}
    for nome in nomes:
        shutil.copy2(CENA / nome, pasta / nome)
        manifesto['arquivos'][nome] = hashlib.sha256((pasta / nome).read_bytes()).hexdigest()
    (pasta / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    anotar(estado, f'provas guardadas: {len(nomes)} arquivos em provas/, com o hash de cada um')
    gravar_estado(estado)
    for nome, h in manifesto['arquivos'].items():
        print(f'{h[:16]}…  {nome}')
    print(f'{len(nomes)} arquivos copiados para cena/provas/. O hash de cada um está em provas/manifesto.json.')
    return 0


def trocar(args):
    estado = ler_estado()
    ativas = [c for c in estado['chaves'] if c['nome'] == args.nome and c['estado'] == 'ativa']
    if not ativas:
        print(f'Não existe chave ativa com o nome {args.nome}. Veja os nomes com python3 ensaio.py chaves.')
        return 2
    destinos = args.gravar or []
    invalidos = [a for a in destinos if a not in ARQUIVOS_DE_CONFIG or args.nome not in ler_config(a)]
    if invalidos:
        print(f'{args.nome} não está configurada em: {", ".join(invalidos)}. Nada foi trocado.')
        return 2
    velha = ativas[0]
    velha['estado'], velha['revogada_em'] = 'revogada', agora()
    nova = dict(velha, valor=chave_nova(velha['prefixo'], estado), estado='ativa', criada_em=agora(), revogada_em=None)
    estado['chaves'].append(nova)
    for arq in destinos:
        gravar_valor(arq, args.nome, nova['valor'])
    (CENA / 'novas').mkdir(exist_ok=True)
    (CENA / 'novas' / f'{args.nome}.txt').write_text(nova['valor'] + '\n', encoding='utf-8')
    anotar(estado, f'{args.nome}: {mascarar(velha["valor"])} revogada, {mascarar(nova["valor"])} criada'
                   + (f', gravada em {", ".join(destinos)}' if destinos else ', não gravada em nenhum arquivo'))
    gravar_estado(estado)
    print(f'Revogada: {mascarar(velha["valor"])}. Quem tiver uma cópia dela não consegue mais usar.')
    print(f'Nova: {mascarar(nova["valor"])}' + (f', gravada em {", ".join(destinos)}.' if destinos else
          '. Ela está em cena/novas/' + args.nome + '.txt e ainda não foi gravada em nenhum arquivo.'))
    return 0


def instalar(args):
    estado = ler_estado()
    ativas = [c for c in estado['chaves'] if c['nome'] == args.nome and c['estado'] == 'ativa']
    if not ativas:
        print(f'Não existe chave ativa com o nome {args.nome}. Veja os nomes com python3 ensaio.py chaves.')
        return 2
    if args.em not in ARQUIVOS_DE_CONFIG or args.nome not in ler_config(args.em):
        print(f'{args.nome} não está configurada em {args.em}. Nada foi gravado.')
        return 2
    gravar_valor(args.em, args.nome, ativas[0]['valor'])
    anotar(estado, f'{args.nome}: {mascarar(ativas[0]["valor"])} gravada em {args.em}')
    gravar_estado(estado)
    print(f'{args.nome} ({mascarar(ativas[0]["valor"])}) gravada em {args.em}.')
    return 0


def pendencias(estado):
    """O que ainda está aberto na fase atual, uma frase por item."""
    abertos = []
    if estado['fase'] == 1:
        vazadas = [c for c in estado['chaves'] if c['valor'] in ISSUE]
        for c in vazadas:
            if c['estado'] == 'ativa':
                abertos.append(f'{c["nome"]} ({mascarar(c["valor"])}) estava na issue pública e continua ativa')
    else:
        precisam = [c for c in estado['chaves'] if c['estado'] == 'ativa' and c['criada_em'] < estado['fase2_em']]
        for c in precisam:
            abertos.append(f'{c["nome"]} ({mascarar(c["valor"])}) existia quando a hospedagem foi invadida e continua ativa')
    revogadas = {c['valor']: c for c in estado['chaves'] if c['estado'] == 'revogada'}
    for arq in ARQUIVOS_DE_CONFIG:
        for nome, valor in ler_config(arq).items():
            if valor in revogadas:
                abertos.append(f'{arq} ainda usa {nome} revogada ({mascarar(valor)}): o que lê esse arquivo para de funcionar')
    manifesto = CENA / 'provas' / 'manifesto.json'
    esperadas = list(PROVAS) + (['aviso-2.txt'] if estado['fase'] == 2 else [])
    if not manifesto.exists():
        abertos.append('as provas não foram guardadas (python3 ensaio.py guardar)')
    else:
        guardadas = json.loads(manifesto.read_text(encoding='utf-8'))['arquivos']
        for nome in esperadas:
            arq = CENA / 'provas' / nome
            if nome not in guardadas:
                abertos.append(f'provas/{nome} não foi guardado')
            elif not arq.exists() or hashlib.sha256(arq.read_bytes()).hexdigest() != guardadas[nome]:
                abertos.append(f'provas/{nome} mudou ou sumiu depois de guardado: o hash não bate com o manifesto')
    return abertos


def checar(_args):
    estado = ler_estado()
    abertos = pendencias(estado)
    print(f'Fase {estado["fase"]} do ensaio, começada em {hora(estado["inicio"] if estado["fase"] == 1 else estado["fase2_em"])}.')
    for item in abertos:
        print('ABERTO  ' + item)
    trocas = [a['texto'].split(':')[0] for a in estado['acoes'] if ' revogada, ' in a['texto']
              and (estado['fase'] == 1 or a['em'] >= estado['fase2_em'])]
    if trocas:
        print('Ordem em que você trocou: ' + ' > '.join(trocas))
    if estado['fase'] == 2:
        print('Lembrete do aviso: os deploys estão pausados. Diga no plano o que a loja faz até o valor novo valer.')
    if abertos:
        print(f'{len(abertos)} item(ns) aberto(s). A linha do tempo está em cena/acoes.log.')
        return 1
    print(f'Fase {estado["fase"]} fechada. A linha do tempo está em cena/acoes.log.'
          + (' Para o segundo aviso: python3 ensaio.py segunda-fase' if estado['fase'] == 1 else ''))
    return 0


def segunda_fase(_args):
    estado = ler_estado()
    if estado['fase'] == 2:
        print('A segunda fase já começou. Veja cena/aviso-2.txt.')
        return 0
    abertos = pendencias(estado)
    if abertos:
        print('Feche a primeira fase antes. Rode python3 ensaio.py checar para ver o que falta.')
        return 1
    estado['fase'], estado['fase2_em'] = 2, agora()
    (CENA / 'aviso-2.txt').write_text(AVISO_2, encoding='utf-8')
    anotar(estado, 'segundo aviso recebido: a hospedagem foi invadida')
    gravar_estado(estado)
    print(AVISO_2)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='comando', required=True)
    p = sub.add_parser('comecar')
    p.add_argument('--de-novo', action='store_true')
    p.set_defaults(func=comecar)
    sub.add_parser('chaves').set_defaults(func=chaves_cmd)
    sub.add_parser('guardar').set_defaults(func=guardar)
    p = sub.add_parser('trocar')
    p.add_argument('nome')
    p.add_argument('--gravar', action='append', metavar='ARQUIVO', help='hospedagem.env, ci.env ou oauth.env')
    p.set_defaults(func=trocar)
    p = sub.add_parser('instalar')
    p.add_argument('nome')
    p.add_argument('--em', required=True, metavar='ARQUIVO', help='hospedagem.env, ci.env ou oauth.env')
    p.set_defaults(func=instalar)
    sub.add_parser('checar').set_defaults(func=checar)
    sub.add_parser('segunda-fase').set_defaults(func=segunda_fase)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
