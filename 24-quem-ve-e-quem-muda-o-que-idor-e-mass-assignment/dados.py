"""Monta os bancos e o bucket de notas da Loja Aurora dessa aula, com produtos, contas e pedidos inventados.

- aurora.db: o banco do app (produtos, usuários com plano, crédito e is_admin, pedidos com endereço)
- aurora-provedor.db: o banco do provedor de autenticação, com as mesmas contas
- aurora-notas/: o bucket de notas, um arquivo por pedido (nota-0001.txt, nota-0002.txt...)

Rodar de novo apaga e recria tudo com os mesmos dados.

    python3 dados.py
"""
import shutil
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
]

# Contas de teste da loja. As senhas estão aqui de propósito: são do kit, não de ninguém.
# (nome, e-mail, senha, telefone, cidade, plano, is_admin, créditos de troca em centavos, id no gateway de pagamento)
USUARIOS = [
    ('Bia Santos', 'bia@cliente.example', 'Bia#teste1', '19 90000-0101', 'Campinas', 'clube', 0, 0, 'cus_aurora_0001'),
    ('Caio Lima', 'caio@cliente.example', 'Caio#teste2', '19 90000-0202', 'Valinhos', 'gratis', 0, 0, 'cus_aurora_0002'),
    ('Duda Rocha', 'duda@cliente.example', 'Duda#teste3', '19 90000-0303', 'Sumaré', 'gratis', 0, 1500, 'cus_aurora_0003'),
    ('Renata Alves', 'renata@aurora.example', 'Renata#teste4', '19 90000-0404', 'Campinas', 'gratis', 1, 0, 'cus_aurora_0004'),
]

PEDIDOS = [
    # (e-mail, produto, quantidade, status, endereço de entrega); os totais saem do preço do catálogo
    ('bia@cliente.example', 'Luminária de mesa Aurora', 1, 'pago', 'Rua das Acácias, 120, ap. 31, Campinas'),
    ('bia@cliente.example', 'Vela aromática Alecrim', 2, 'aguardando pagamento', 'Rua das Acácias, 120, ap. 31, Campinas'),
    ('caio@cliente.example', 'Luminária de piso Arco', 1, 'pago', 'Avenida dos Ipês, 45, Valinhos'),
    ('duda@cliente.example', 'Manta de algodão Serra', 1, 'aguardando pagamento', 'Rua do Cedro, 300, casa 2, Sumaré'),
]

GUIA_DO_CLUBE = [
    'Luz quente (2700 K) na sala e no quarto; luz neutra (4000 K) na cozinha e na bancada.',
    'Pendente sobre a mesa: de 70 a 80 cm acima do tampo.',
    'Fita de LED atrás do painel da TV cansa menos a vista do que a sala apagada.',
]


def caminho_provedor(banco):
    banco = Path(banco)
    return banco.with_name(banco.stem + '-provedor.db')


def caminho_notas(banco):
    banco = Path(banco)
    return banco.with_name(banco.stem + '-notas')


def reais(centavos):
    return f'R$ {centavos // 100},{centavos % 100:02d}'


def montar(caminho):
    caminho = Path(caminho)
    if caminho.exists():
        caminho.unlink()
    prov = provedor.Provedor.montar(caminho_provedor(caminho), [(u[1], u[2]) for u in USUARIOS])
    notas = caminho_notas(caminho)
    shutil.rmtree(notas, ignore_errors=True)
    notas.mkdir()
    con = sqlite3.connect(caminho)
    con.executescript('''
        create table produtos (id integer primary key, nome text, categoria text, preco_centavos integer);
        create table usuarios (id integer primary key, provedor_id text unique, nome text, email text unique,
                               telefone text, cidade text, plano text, is_admin integer default 0,
                               creditos integer default 0, gateway_id text, criado_em text);
        create table pedidos (id integer primary key, cliente_id integer, produto_id integer, quantidade integer,
                              desconto_centavos integer default 0, credito_centavos integer default 0,
                              total_centavos integer, status text, endereco text, nota text);
        create table guia_clube (id integer primary key, dica text);
    ''')
    con.executemany('insert into produtos (nome, categoria, preco_centavos) values (?, ?, ?)', PRODUTOS)
    for i, (nome, email, _senha, telefone, cidade, plano, admin, creditos, gateway) in enumerate(USUARIOS, start=1):
        con.execute('insert into usuarios (provedor_id, nome, email, telefone, cidade, plano, is_admin, creditos, gateway_id, criado_em)'
                    ' values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (prov.id_da_conta(email), nome, email, telefone, cidade, plano, admin, creditos, gateway, f'2026-0{i}-1{i}'))
    for n, (email, produto, qtd, status, endereco) in enumerate(PEDIDOS, start=1):
        cid, cliente = con.execute('select id, nome from usuarios where email = ?', (email,)).fetchone()
        pid, preco = con.execute('select id, preco_centavos from produtos where nome = ?', (produto,)).fetchone()
        arquivo = f'nota-{n:04d}.txt'
        con.execute('insert into pedidos (cliente_id, produto_id, quantidade, total_centavos, status, endereco, nota)'
                    ' values (?, ?, ?, ?, ?, ?, ?)', (cid, pid, qtd, preco * qtd, status, endereco, arquivo))
        (notas / arquivo).write_text(
            f'Loja Aurora · nota do pedido {n}\nCliente: {cliente}\nEntrega: {endereco}\n'
            f'{qtd} × {produto}\nTotal: {reais(preco * qtd)}\n', encoding='utf-8')
    con.executemany('insert into guia_clube (dica) values (?)', [(d,) for d in GUIA_DO_CLUBE])
    con.commit()
    con.close()
    return caminho


if __name__ == '__main__':
    banco = montar(Path(__file__).resolve().parent / 'aurora.db')
    print('criados', banco.name, caminho_provedor(banco).name, 'e', caminho_notas(banco).name + '/')
