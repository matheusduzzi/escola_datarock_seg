"""Testa as portas por onde o dado da Loja Aurora sai mesmo com o RLS ligado na tabela.

    python3 portas.py montar                     # cria o banco da aula (loja.sql e notas.sql)
    python3 portas.py aplicar minha-correcao.sql # roda o seu SQL no banco
    python3 portas.py sondar                     # diz quais portas continuam abertas
    python3 portas.py advisor splinter.sql       # roda as regras do Security Advisor (opcional)

O sondar entra no banco como a Bia, o Caio, a Renata, um visitante sem login e a chave
secreta, faz cada teste dentro de uma transação e desfaz tudo no fim. Não muda nenhum dado.
Sai com 0 quando todas as portas fecham e a loja continua funcionando, e com 1 quando não.

Como ele chega no banco: pelo comando que está em AURORA_PSQL. Sem a variável, ele usa o
psql no banco do Supabase local:
    psql postgresql://postgres:postgres@127.0.0.1:54322/postgres
Sem psql no computador, use o que vem dentro do contêiner do Supabase:
    AURORA_PSQL="docker exec -i NOME_DO_CONTEINER psql -U postgres" python3 portas.py sondar
(o nome sai de: docker ps --format '{{.Names}}' | grep supabase_db)
"""
import base64
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
PADRAO = 'psql postgresql://postgres:postgres@127.0.0.1:54322/postgres'

BIA = 'b1a00000-0000-4000-8000-000000000001'
CAIO = 'ca100000-0000-4000-8000-000000000002'
RENATA = 'a0000000-0000-4000-8000-0000000000aa'

# O que vem dentro do token de cada um. O do Caio é o token depois de ele mudar o
# próprio user_metadata, que qualquer usuário logado consegue mudar pela API de Auth.
QUEM = {
    'bia': ('authenticated', {'sub': BIA, 'role': 'authenticated', 'email': 'bia@cliente.example',
                              'app_metadata': {}, 'user_metadata': {}}),
    'caio_promovido': ('authenticated', {'sub': CAIO, 'role': 'authenticated', 'email': 'caio@cliente.example',
                                         'app_metadata': {}, 'user_metadata': {'papel': 'admin'}}),
    'renata': ('authenticated', {'sub': RENATA, 'role': 'authenticated', 'email': 'renata@loja-aurora.example',
                                 'app_metadata': {'papel': 'admin'}, 'user_metadata': {'papel': 'admin'}}),
    'visitante': ('anon', {'role': 'anon'}),
    'chave_secreta': ('service_role', {'role': 'service_role'}),
}

# (nome, quem, corpo plpgsql que põe o resultado em v). Erro vira "ERRO <código>".
TESTES = [
    ('montado', None, "v := (to_regclass('public.clientes') is not null)::text;"),
    ('quem_sou', 'bia', "v := auth.uid()::text;"),
    ('view_bia', 'bia', "select count(*) into v from public.v_clientes;"),
    ('view_bia_propria', 'bia', f"select count(*) into v from public.v_clientes where id = '{BIA}';"),
    ('view_visitante', 'visitante', "select count(*) into v from public.v_clientes;"),
    # Depois de chamar, o "reset role" volta ao dono do banco para ler o status de verdade.
    ('funcao_bia', 'bia',
     "perform public.marcar_pago(2); reset role; select status into v from public.pedidos where id = 2;"),
    ('funcao_caio_promovido', 'caio_promovido',
     "perform public.marcar_pago(2); reset role; select status into v from public.pedidos where id = 2;"),
    ('funcao_visitante', 'visitante',
     "perform public.marcar_pago(4); reset role; select status into v from public.pedidos where id = 4;"),
    ('funcao_renata', 'renata', "perform public.marcar_pago(4); select status into v from public.pedidos where id = 4;"),
    ('funcao_search_path', None,
     "select coalesce((select c from unnest(p.proconfig) c where c like 'search_path=%'), 'nenhum') into v "
     "from pg_proc p where p.oid = to_regprocedure('public.marcar_pago(bigint)');"),
    ('meta_caio', 'caio_promovido', "select count(*) into v from public.pedidos;"),
    ('meta_caio_grava_papel', 'caio_promovido',
     f"insert into public.papeis (user_id, papel) values ('{CAIO}', 'admin'); v := 'gravou';"),
    ('meta_renata', 'renata', "select count(*) into v from public.pedidos;"),
    ('chave_ve', 'chave_secreta', "select count(*) into v from public.clientes;"),
    ('bucket_publico', None, "select public::text into v from storage.buckets where id = 'notas';"),
    ('bucket_bia', 'bia', "select count(*) into v from storage.objects where bucket_id = 'notas';"),
    ('bucket_bia_propria', 'bia',
     f"select count(*) into v from storage.objects where bucket_id = 'notas' and owner_id = '{BIA}';"),
    ('bucket_visitante', 'visitante', "select count(*) into v from storage.objects where bucket_id = 'notas';"),
    ('cupons_rls', None, "select relrowsecurity::text into v from pg_class where oid = to_regclass('public.cupons');"),
    ('cupons_visitante_le', 'visitante', "select count(*) into v from public.cupons;"),
    ('cupons_visitante_muda', 'visitante',
     "update public.cupons set desconto_pct = 100 where codigo = 'AURORA10'; get diagnostics n = row_count; v := n::text;"),
    ('cupons_servidor', 'chave_secreta', "select count(*) into v from public.cupons;"),
]


def comando():
    return shlex.split(os.environ.get('AURORA_PSQL', PADRAO)) + ['-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1']


def psql(sql):
    cmd = comando()
    try:
        r = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(f'Não achei o comando "{cmd[0]}". Instale o psql ou use AURORA_PSQL (veja o README).')
    return r.returncode, r.stdout + r.stderr


def bloco(nome, quem, corpo):
    linhas = ['begin;']
    if quem:
        papel, token = QUEM[quem]
        linhas.append(f'set local role {papel};')
        claims = json.dumps(token).replace("'", "''")
        linhas.append(f"select set_config('request.jwt.claims', '{claims}', true) is null as _;")
    linhas.append(
        "do $t$ declare v text; n bigint; begin " + corpo +
        f" raise notice 'R:{nome}=%', coalesce(v, 'vazio');"
        f" exception when others then raise notice 'R:{nome}=ERRO %', sqlstate; end $t$;")
    linhas.append('rollback;')
    return '\n'.join(linhas)


def medir():
    sql = '\n'.join(bloco(*t) for t in TESTES)
    codigo, saida = psql(sql)
    r = dict(re.findall(r'R:(\w+)=(.*)', saida))
    if codigo != 0 or len(r) != len(TESTES):
        print(saida.strip())
        sys.exit('\nO banco não respondeu a todos os testes. O Supabase está rodando? Você rodou "python3 portas.py montar"?')
    return {k: v.strip() for k, v in r.items()}


def numero(v):
    return int(v) if v.isdigit() else None


def efeito(v):
    return f"recusada ({v[5:]})" if v.startswith('ERRO') else f"o pedido ficou {v}"


def qtd(v):
    return 'nada (o banco recusou)' if v.startswith('ERRO') else v


def chaves_no_front():
    achados = []
    for arq in sorted((PASTA / 'front').rglob('*')):
        if not arq.is_file():
            continue
        for i, linha in enumerate(arq.read_text(errors='replace').splitlines(), start=1):
            if re.search(r'sb_secret_\w+', linha):
                achados.append(f'{arq.relative_to(PASTA)}:{i} (sb_secret_)')
            for jwt in re.findall(r'eyJ[\w-]+\.(eyJ[\w-]+)\.[\w-]+', linha):
                try:
                    corpo = json.loads(base64.urlsafe_b64decode(jwt + '=' * (-len(jwt) % 4)))
                except ValueError:
                    continue
                if corpo.get('role') == 'service_role':
                    achados.append(f'{arq.relative_to(PASTA)}:{i} (JWT com role service_role)')
    return achados


def sondar():
    r = medir()
    if r['montado'] != 'true':
        sys.exit('Não achei a tabela clientes nesse banco. Você rodou "python3 portas.py montar"?')
    if r['quem_sou'] != BIA:
        sys.exit(f'Troquei para a Bia e o banco disse que eu sou "{r["quem_sou"]}". '
                 'A troca de usuário não funcionou nesse banco; os testes não valem.')
    front = chaves_no_front()
    portas = [
        ('1', 'view sem security_invoker',
         numero(r['view_bia']) not in (None, 0, 1) or numero(r['view_visitante']) not in (None, 0),
         f"a Bia vê {qtd(r['view_bia'])} cliente(s) pela v_clientes; o visitante vê {qtd(r['view_visitante'])}"),
        ('2', 'função security definer',
         'pago' in (r['funcao_bia'], r['funcao_caio_promovido'], r['funcao_visitante'])
         or r['funcao_search_path'] == 'nenhum',
         f"a Bia chamou marcar_pago(2): {efeito(r['funcao_bia'])}; o Caio, com papel=admin no user_metadata, "
         f"chamou marcar_pago(2): {efeito(r['funcao_caio_promovido'])}; o visitante chamou marcar_pago(4): "
         f"{efeito(r['funcao_visitante'])}; search_path: {r['funcao_search_path']}"),
        ('3', 'papel no user_metadata',
         numero(r['meta_caio']) not in (None, 0, 1) or r['meta_caio_grava_papel'] == 'gravou',
         f"o Caio pôs papel=admin no próprio user_metadata e lê {qtd(r['meta_caio'])} pedido(s); "
         f"quando tenta se gravar como admin em papeis: {r['meta_caio_grava_papel']}"),
        ('4', 'chave secreta no front', bool(front),
         ('achei em ' + ', '.join(front)) if front else 'nenhuma chave secreta em front/'),
        ('5', 'bucket de notas',
         r['bucket_publico'] == 'true' or numero(r['bucket_bia']) not in (None, 0, 1, 2)
         or numero(r['bucket_visitante']) not in (None, 0),
         f"bucket público: {r['bucket_publico']}; a Bia lista {qtd(r['bucket_bia'])} nota(s); "
         f"o visitante lista {qtd(r['bucket_visitante'])}"),
        ('6', 'tabela cupons sem RLS',
         r['cupons_rls'] == 'false' or numero(r['cupons_visitante_le']) not in (None, 0)
         or numero(r['cupons_visitante_muda']) not in (None, 0),
         f"RLS ligado: {r['cupons_rls']}; o visitante lê {qtd(r['cupons_visitante_le'])} cupom(ns) "
         f"e muda {qtd(r['cupons_visitante_muda'])}"),
    ]
    loja = [
        ('a Bia lê o próprio cadastro pela v_clientes', r['view_bia_propria'] == '1', r['view_bia_propria']),
        ('a Renata marca o pedido 4 como pago', r['funcao_renata'] == 'pago', r['funcao_renata']),
        ('a Renata lê os 4 pedidos no painel', r['meta_renata'] == '4', r['meta_renata']),
        ('a Bia lista as 2 notas dela', r['bucket_bia_propria'] == '2', r['bucket_bia_propria']),
        ('o servidor lê os 3 cupons para validar a compra', r['cupons_servidor'] == '3', r['cupons_servidor']),
    ]
    print('Portas')
    for n, nome, aberta, motivo in portas:
        print(f'{"ABERTA " if aberta else "fechada"}  {n}. {nome}: {motivo}')
    print('\nA loja continua funcionando?')
    for nome, ok, valor in loja:
        print(f'{"ok     " if ok else "QUEBROU"}  {nome} (deu {valor})')
    print(f"\nCom a chave secreta, o banco retorna {r['chave_ve']} clientes: ela não passa por policy nenhuma.")
    abertas = sum(p[2] for p in portas)
    quebradas = sum(not l[1] for l in loja)
    print(f'{len(portas) - abertas} de {len(portas)} portas fechadas. {len(loja) - quebradas} de {len(loja)} funções da loja ok.')
    return 0 if abertas == 0 and quebradas == 0 else 1


def rodar_arquivo(caminho):
    arq = Path(caminho)
    if not arq.is_file():
        sys.exit(f'Não achei o arquivo {caminho}.')
    codigo, saida = psql(arq.read_text())
    if saida.strip():
        print(saida.strip())
    return codigo


def montar():
    if rodar_arquivo(PASTA / 'loja.sql') != 0:
        sys.exit('O loja.sql parou com erro (acima). Nada foi para o storage.')
    if rodar_arquivo(PASTA / 'notas.sql') != 0:
        sys.exit('As tabelas foram criadas, mas o notas.sql parou com erro (acima). '
                 'Sem o bucket, a porta 5 não dá para testar. Deixe um comentário na aula com essa saída.')
    print('Banco da aula montado: 3 clientes, 4 pedidos, 1 admin, 3 cupons, 4 notas no bucket "notas".')
    return 0


def advisor(caminho):
    arq = Path(caminho)
    if not arq.is_file():
        sys.exit(f'Não achei {caminho}. Baixe o splinter.sql (veja o README).')
    texto = arq.read_text().strip().rstrip(';')
    corte = texto.find('\n(')
    if corte < 0:
        sys.exit(f'{caminho} não tem o formato do splinter.sql.')
    preparo, consulta = texto[:corte], texto[corte:]
    sql = ('begin;\n' + preparo + '\n'
           "select 'L:' || json_build_object('name', name, 'level', level, 'categories', categories, "
           "'detail', detail)::text from (" + consulta + '\n) as alertas;\nrollback;\n')
    codigo, saida = psql(sql)
    if codigo != 0:
        print(saida.strip())
        return codigo
    alertas = [json.loads(l[2:]) for l in saida.splitlines() if l.startswith('L:')]
    seguranca = [a for a in alertas if 'SECURITY' in (a['categories'] or [])]
    for a in seguranca:
        print(f"{a['level']:6} {a['name']:48} {a['detail'].replace(chr(92) + '`', '`')}")
    print(f'\n{len(seguranca)} alerta(s) de segurança.')
    return 0


def main(args):
    if not args or args[0] == 'sondar':
        return sondar()
    if args[0] == 'montar':
        return montar()
    if args[0] == 'aplicar' and len(args) == 2:
        return rodar_arquivo(args[1])
    if args[0] == 'advisor' and len(args) == 2:
        return advisor(args[1])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
