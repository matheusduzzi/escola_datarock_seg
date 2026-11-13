"""O modelo de IA do assistente de iluminação da Loja Aurora. Não edite este arquivo.

No app de verdade, o assistente chama a API paga de um provedor de modelo, e cada chamada entra
na conta da loja. Aqui o modelo roda no seu computador, sem internet e sem custo: ele responde
com uma dica pronta e anota cada chamada na tabela chamadas_modelo, que faz o papel do painel
de uso do provedor. É por essa tabela que o checar.py sabe quantas vezes o modelo foi chamado.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DICAS = [
    ('sala', 'Na sala, luz quente (2700 K) e mais de um ponto de luz: um pendente ou plafon e uma luminária de piso.'),
    ('quarto', 'No quarto, luz quente e baixa. Um abajur de cada lado da cama resolve a leitura.'),
    ('cozinha', 'Na cozinha, luz neutra (4000 K) sobre a bancada. Fita de LED embaixo do armário ajuda no preparo.'),
    ('mesa', 'Sobre a mesa de jantar, pendente de 70 a 80 cm acima do tampo.'),
]
PADRAO = 'Me conte qual cômodo você quer iluminar e eu sugiro o tipo de luz e de luminária.'


class Modelo:
    def __init__(self, banco):
        self.banco = Path(banco)

    def responder(self, pergunta, usuario_id=None):
        """Responde à pergunta e anota a chamada, como o provedor anota no painel de uso."""
        con = sqlite3.connect(self.banco)
        try:
            con.execute('insert into chamadas_modelo (usuario_id, caracteres, criado_em) values (?, ?, ?)',
                        (usuario_id, len(pergunta), datetime.now(timezone.utc).isoformat(timespec='seconds')))
            con.commit()
        finally:
            con.close()
        texto = pergunta.lower()
        return next((dica for chave, dica in DICAS if chave in texto), PADRAO)

    def chamadas(self):
        con = sqlite3.connect(self.banco)
        try:
            return con.execute('select count(*) from chamadas_modelo').fetchone()[0]
        finally:
            con.close()
