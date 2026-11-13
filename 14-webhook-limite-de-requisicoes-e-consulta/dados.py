"""Monta os dois bancos da Loja Aurora dessa aula (SQLite), com produtos, contas e pedidos inventados.

- aurora.db: o banco do app (produtos, usuários, pedidos, inscrições da newsletter e as chamadas ao modelo)
- aurora-provedor.db: o banco do provedor de autenticação, com as mesmas contas

Rodar de novo apaga e recria os dois bancos com os mesmos dados.

    python3 dados.py
"""
import hashlib
import sqlite3
from pathlib import Path

import provedor

PRODUTOS = [
    ('Luminária de mesa Aurora', 'luminárias', 24990),
    ('Luminária de piso Arco', 'luminárias', 58900),
    ('Pendente de vidro Bruma', 'luminárias', 31950),
    ('Arandela de parede Fresta', 'luminárias', 18900),
    ('Fita de LED quente 5 m', 'iluminação', 8990),
    ('Lâmpada filamento 4 W', 'iluminação', 2490),
    ('Vela aromática Alecrim', 'decoração', 6990),
    ('Vaso de cerâmica Duna', 'decoração', 12900),
    ('Manta de algodão Serra', 'têxteis', 15990),
    ('Almofada linho Cru', 'têxteis', 7990),
    ('Espelho redondo Lago', 'decoração', 27900),
    ('Bandeja de madeira Copa', 'decoração', 9990),
    ("Abajur Gota d'Água", 'luminárias', 14990),
]

# Contas de teste da loja. As senhas estão aqui de propósito: são do kit, não de ninguém.
# (nome, e-mail, senha, papel, plano, crédito de troca em centavos)
USUARIOS = [
    ('Bia Santos', 'bia@cliente.example', 'Bia#teste1', 'cliente', 'clube', 0),
    ('Caio Lima', 'caio@cliente.example', 'Caio#teste2', 'cliente', 'gratis', 0),
    ('Duda Rocha', 'duda@cliente.example', 'Duda#teste3', 'cliente', 'gratis', 1500),
    ('Renata Alves', 'renata@aurora.example', 'Renata#teste4', 'admin', 'gratis', 0),
]

PEDIDOS = [
    # (e-mail, produto, quantidade, status); os totais saem do preço do catálogo
    ('bia@cliente.example', 'Luminária de mesa Aurora', 1, 'pago'),
    ('bia@cliente.example', 'Vela aromática Alecrim', 2, 'aguardando pagamento'),
    ('caio@cliente.example', 'Luminária de piso Arco', 1, 'pago'),
    ('duda@cliente.example', 'Manta de algodão Serra', 1, 'aguardando pagamento'),
]

GUIA_DO_CLUBE = [
    'Luz quente (2700 K) na sala e no quarto; luz neutra (4000 K) na cozinha e na bancada.',
    'Pendente sobre a mesa: de 70 a 80 cm acima do tampo.',
    'Fita de LED atrás do painel da TV cansa menos a vista do que a sala apagada.',
]


def hash_senha(senha, sal):
    return hashlib.pbkdf2_hmac('sha256', senha.encode(), sal, 200_000).hex()


def caminho_provedor(banco):
    banco = Path(banco)
    return banco.with_name(banco.stem + '-provedor.db')


def montar(caminho):
    caminho = Path(caminho)
    if caminho.exists():
        caminho.unlink()
    prov = provedor.Provedor.montar(caminho_provedor(caminho), [(u[1], u[2]) for u in USUARIOS])
    con = sqlite3.connect(caminho)
    con.executescript('''
        create table produtos (id integer primary key, nome text, categoria text, preco_centavos integer);
        create table usuarios (id integer primary key, nome text, email text unique, sal text, senha_hash text,
                               provedor_id text unique, papel text, plano text, credito_centavos integer);
        create table pedidos (id integer primary key, cliente_id integer, produto_id integer, quantidade integer,
                              desconto_centavos integer default 0, credito_centavos integer default 0,
                              total_centavos integer, status text);
        create table guia_clube (id integer primary key, dica text);
        create table newsletter (id integer primary key, email text, ip text, criado_em text);
        create table chamadas_modelo (id integer primary key, usuario_id integer, caracteres integer, criado_em text);
    ''')
    con.executemany('insert into produtos (nome, categoria, preco_centavos) values (?, ?, ?)', PRODUTOS)
    for i, (nome, email, senha, papel, plano, credito) in enumerate(USUARIOS, start=1):
        sal = hashlib.sha256(f'aurora-{i}'.encode()).digest()[:16]
        con.execute('insert into usuarios (nome, email, sal, senha_hash, provedor_id, papel, plano, credito_centavos)'
                    ' values (?, ?, ?, ?, ?, ?, ?, ?)',
                    (nome, email, sal.hex(), hash_senha(senha, sal), prov.id_da_conta(email), papel, plano, credito))
    for email, produto, qtd, status in PEDIDOS:
        cid = con.execute('select id from usuarios where email = ?', (email,)).fetchone()[0]
        pid, preco = con.execute('select id, preco_centavos from produtos where nome = ?', (produto,)).fetchone()
        con.execute('insert into pedidos (cliente_id, produto_id, quantidade, total_centavos, status) values (?, ?, ?, ?, ?)',
                    (cid, pid, qtd, preco * qtd, status))
    con.executemany('insert into guia_clube (dica) values (?)', [(d,) for d in GUIA_DO_CLUBE])
    con.commit()
    con.close()
    return caminho


if __name__ == '__main__':
    banco = montar(Path(__file__).resolve().parent / 'aurora.db')
    print('bancos criados em', banco, 'e', caminho_provedor(banco))
