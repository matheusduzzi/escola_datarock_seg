"""O agente da noite da Loja Aurora, de roteiro: não tem modelo de IA e faz sempre a mesma tarefa.

    python3 agente_noturno.py

A tarefa: "apague os pedidos duplicados antes do relatório de segunda". Ele chama de
duplicado o pedido com o mesmo cliente, o mesmo produto e o mesmo dia de outro, e apaga
o segundo. É o erro que um agente de verdade comete fácil: compra repetida parece
duplicata.

O agente só age pelas ferramentas abaixo. Cada ferramenta anota na trilha o que foi
pedido e o que aconteceu antes de responder ao agente, inclusive o que foi recusado.
"""
import sqlite3
import sys
from pathlib import Path

from trilha import Trilha

AGENTE = 'agente-noturno'
BANCO = Path('loja/loja.db')
RASCUNHOS = Path('rascunhos')


class Ferramentas:
    def __init__(self, trilha):
        self.trilha = trilha

    def consultar_semana(self, inicio, fim):
        con = sqlite3.connect(f'file:{BANCO}?mode=ro', uri=True)
        linhas = con.execute('select codigo, cliente, produto, substr(criado_em, 1, 10) from pedidos'
                             ' where substr(criado_em, 1, 10) between ? and ? order by codigo', (inicio, fim)).fetchall()
        con.close()
        self.trilha.anotar(AGENTE, 'consultar', f'pedidos de {inicio} a {fim}', f'{len(linhas)} pedidos')
        return linhas

    def apagar_pedidos(self, codigos, motivo):
        con = sqlite3.connect(BANCO)
        with con:
            apagados = sum(con.execute('delete from pedidos where codigo = ?', (c,)).rowcount for c in codigos)
        con.close()
        self.trilha.anotar(AGENTE, 'apagar', f'{", ".join(codigos)} ({motivo})', (f'{apagados} pedidos apagados' if apagados != 1 else '1 pedido apagado'))
        return apagados

    def enviar_email(self, para, assunto):
        # Envio a pessoa ou cliente pede confirmação de alguém (contrato de acesso do agente).
        resultado = 'recusado: envio pede confirmação de uma pessoa'
        self.trilha.anotar(AGENTE, 'enviar_email', f'para {para}: {assunto}', resultado)
        return resultado

    def criar_rascunho(self, nome, texto):
        RASCUNHOS.mkdir(exist_ok=True)
        (RASCUNHOS / nome).write_text(texto, encoding='utf-8')
        caminho = (RASCUNHOS / nome).as_posix()
        self.trilha.anotar(AGENTE, 'criar_rascunho', caminho, f'rascunho com {len(texto.splitlines())} linhas')
        return caminho


def main():
    if not BANCO.exists():
        print(f'Não achei {BANCO.as_posix()}. Rode da pasta da aula, depois de: python3 loja/preparar.py')
        return 2
    trilha = Trilha()
    f = Ferramentas(trilha)
    tarefa = 'apagar pedidos duplicados antes do relatório de segunda'
    print(f'Tarefa: {tarefa}.')
    trilha.anotar(AGENTE, 'inicio', tarefa, 'começou')

    semana = f.consultar_semana('2026-11-02', '2026-11-08')
    print(f'Consultei {len(semana)} pedidos de 02/11 a 08/11.')
    vistos, duplicados = set(), []
    for codigo, cliente, produto, dia in semana:
        chave = (cliente, produto, dia)
        if chave in vistos:
            duplicados.append(codigo)
        vistos.add(chave)
    if duplicados:
        print(f'Achei {len(duplicados)} duplicados: {", ".join(duplicados)}.')
        n = f.apagar_pedidos(duplicados, 'mesmo cliente, produto e dia de outro pedido')
        print(f'Apaguei {n} pedidos.')
    else:
        print('Não achei duplicados.')

    relatorio = [f'Limpeza da noite: {len(duplicados)} pedidos duplicados apagados.'] + [f'- {c}' for c in duplicados]
    resposta = f.enviar_email('a Renata', 'relatório da limpeza')
    print(f'Tentei mandar o relatório por e-mail para a Renata. A ferramenta respondeu: {resposta}.')
    caminho = f.criar_rascunho('relatorio-da-noite.txt', '\n'.join(relatorio) + '\n')
    print(f'Deixei o relatório em rascunho: {caminho}')
    trilha.anotar(AGENTE, 'fim', tarefa, 'terminou')
    total = len(trilha.caminho.read_text(encoding='utf-8').splitlines())
    print(f'Cada ação ficou na trilha: {trilha.caminho.as_posix()} ({total} linhas).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
