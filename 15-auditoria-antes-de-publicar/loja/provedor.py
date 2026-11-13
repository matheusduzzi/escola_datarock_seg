"""O provedor de autenticação da Loja Aurora. Não edite este arquivo.

Ele faz, no seu computador e sem internet, o papel que no app de verdade é de um serviço
como o Supabase Auth, o Auth0, o Firebase Authentication ou o Clerk:

- guarda as contas e as senhas (só o hash, com sal);
- confere e-mail e senha e entrega um token de sessão com validade;
- diz quem é o dono de um token (quem_e), que é o que o seu servidor pergunta a cada pedido;
- responde igual para e-mail cadastrado e não cadastrado, no login e no "esqueci a senha";
- segura quem erra a senha muitas vezes seguidas.

O provedor diz QUEM a pessoa é. O que ela PODE fazer (papel, plano, crédito) fica no banco do app.
"""
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path

VALIDADE_SEGUNDOS = 3600
TENTATIVAS = 5             # erros seguidos aceitos por e-mail
JANELA_SEGUNDOS = 300      # em 5 minutos
ERRO_LOGIN = {'erro': 'invalid_credentials', 'mensagem': 'E-mail ou senha inválidos.'}
MUITAS_TENTATIVAS = {'erro': 'too_many_requests', 'mensagem': 'Muitas tentativas. Espere alguns minutos.'}
RESPOSTA_NOVA_SENHA = {'mensagem': 'Se existir uma conta com esse e-mail, enviamos um link para criar uma senha nova.'}


def _hash(senha, sal):
    return hashlib.pbkdf2_hmac('sha256', senha.encode(), sal, 200_000).hex()


def _id(email):
    return 'usr_' + hashlib.sha256(email.lower().encode()).hexdigest()[:12]


class Provedor:
    def __init__(self, banco):
        self.banco = Path(banco)
        self.sessoes = {}      # token -> (id da conta, e-mail, expira em)
        self.erros = {}        # e-mail -> horários dos últimos erros
        self.caixa_saida = []  # links de nova senha que seriam enviados por e-mail (o kit não envia nada)

    @classmethod
    def montar(cls, banco, contas):
        banco = Path(banco)
        if banco.exists():
            banco.unlink()
        con = sqlite3.connect(banco)
        con.execute('create table contas (id text primary key, email text unique, sal text, senha_hash text)')
        for email, senha in contas:
            sal = secrets.token_bytes(16)
            con.execute('insert into contas values (?, ?, ?, ?)', (_id(email), email.lower(), sal.hex(), _hash(senha, sal)))
        con.commit()
        con.close()
        return cls(banco)

    def _conta(self, email):
        con = sqlite3.connect(self.banco)
        try:
            return con.execute('select id, email, sal, senha_hash from contas where email = ?', (email.lower(),)).fetchone()
        finally:
            con.close()

    def id_da_conta(self, email):
        conta = self._conta(email)
        return conta[0] if conta else None

    def _bloqueado(self, email, agora):
        recentes = [t for t in self.erros.get(email, []) if agora - t < JANELA_SEGUNDOS]
        self.erros[email] = recentes
        return len(recentes) >= TENTATIVAS

    def entrar(self, email, senha):
        """Confere e-mail e senha. Retorna (status, corpo), como a API de um provedor."""
        email = (email or '').strip().lower()
        agora = time.time()
        if self._bloqueado(email, agora):
            return 429, dict(MUITAS_TENTATIVAS)
        conta = self._conta(email)
        sal = bytes.fromhex(conta[2]) if conta else b'conta-que-nao-ha'
        calculado = _hash(senha or '', sal)  # calcula sempre: o tempo de resposta não denuncia a conta
        if conta is None or not hmac.compare_digest(calculado, conta[3]):
            self.erros.setdefault(email, []).append(agora)
            return 400, dict(ERRO_LOGIN)
        self.erros.pop(email, None)
        token = secrets.token_urlsafe(32)
        self.sessoes[token] = (conta[0], conta[1], agora + VALIDADE_SEGUNDOS)
        return 200, {'access_token': token, 'token_type': 'bearer', 'expires_in': VALIDADE_SEGUNDOS,
                     'user': {'id': conta[0], 'email': conta[1]}}

    def quem_e(self, token):
        """Diz de quem é o token: {'id', 'email'}, ou None se o token não vale (inventado, vencido ou encerrado)."""
        sessao = self.sessoes.get(token or '')
        if sessao is None:
            return None
        if time.time() >= sessao[2]:
            self.sessoes.pop(token, None)
            return None
        return {'id': sessao[0], 'email': sessao[1]}

    def sair(self, token):
        self.sessoes.pop(token or '', None)
        return 200, {'ok': True}

    def pedir_nova_senha(self, email):
        """Mesma resposta exista a conta ou não. O link só vai para a caixa de quem tem conta."""
        conta = self._conta((email or '').strip())
        if conta:
            self.caixa_saida.append((conta[1], 'link-de-nova-senha-' + secrets.token_urlsafe(8)))
        return 200, dict(RESPOSTA_NOVA_SENHA)

    def definir_senha(self, email, senha):
        """Troca a senha de uma conta, como o painel do provedor faz. Usado pelo checar.py."""
        sal = secrets.token_bytes(16)
        con = sqlite3.connect(self.banco)
        try:
            con.execute('update contas set sal = ?, senha_hash = ? where email = ?', (sal.hex(), _hash(senha, sal), email.lower()))
            con.commit()
        finally:
            con.close()
