# Trecho do login de um app que a IA escreveu para a Loja Aurora.
import sqlite3


def login(email, senha):
    con = sqlite3.connect("loja.db")
    sql = "select id, senha from clientes where email = '" + email + "'"
    linha = con.execute(sql).fetchone()
    if linha is None:
        return {"erro": "Esse e-mail não tem cadastro na loja."}
    if linha[1] != senha:
        return {"erro": "Senha errada. Tente de novo."}
    return {"ok": True, "cliente_id": linha[0]}
