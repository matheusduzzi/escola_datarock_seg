"""O bucket de arquivos da Loja Aurora nessa aula. Não edite este arquivo.

Ele faz, no seu computador e sem internet, o papel que no app de verdade é de um serviço de
arquivos como o Supabase Storage ou o Amazon S3:

- guarda os arquivos numa pasta (aqui, as notas dos pedidos);
- num bucket público, entrega o arquivo para qualquer um que tenha o endereço;
- num bucket privado, só entrega com um link assinado que ainda vale;
- cria o link assinado com validade em segundos (criar_link_assinado).

O bucket diz SE o link vale. QUEM pode pedir o link de cada arquivo é decisão do seu servidor.
"""
import hashlib
import hmac
import re
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode

NOME_VALIDO = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
LINK_INVALIDO = {'erro': 'link inválido ou vencido'}


class Bucket:
    def __init__(self, pasta, publico, nome='notas'):
        self.pasta = Path(pasta)
        self.publico = bool(publico)
        self.nome = nome
        self.relogio = time.time            # o checar.py adianta este relógio para testar o link vencido
        self._chave = secrets.token_bytes(32)  # a chave que assina os links fica dentro do bucket

    def url_publica(self, arquivo):
        """O endereço fixo do arquivo, como o getPublicUrl do Supabase. Só abre se o bucket for público."""
        return f'/arquivos/{self.nome}/{arquivo}'

    def criar_link_assinado(self, arquivo, validade_segundos):
        """Um link que vale por validade_segundos, como o createSignedUrl(caminho, expiresIn) do Supabase."""
        validade = int(validade_segundos)
        if validade <= 0:
            raise ValueError('a validade do link precisa ser maior que zero')
        expira = int(self.relogio()) + validade
        return self.url_publica(arquivo) + '?' + urlencode({'expira': expira, 'token': self._assinar(arquivo, expira)})

    def _assinar(self, arquivo, expira):
        return hmac.new(self._chave, f'{self.nome}/{arquivo}:{expira}'.encode(), hashlib.sha256).hexdigest()

    def baixar(self, arquivo, consulta=''):
        """Retorna (status, conteúdo do arquivo ou erro). É o que o endereço /arquivos/<bucket>/<arquivo> responde."""
        if not NOME_VALIDO.match(arquivo or '') or not (self.pasta / arquivo).is_file():
            return 404, {'erro': 'arquivo não encontrado'}
        if not self.publico:
            q = parse_qs(consulta or '')
            expira, token = q.get('expira', [''])[0], q.get('token', [''])[0]
            if not expira.isdigit() or not token:
                return 403, LINK_INVALIDO
            if not hmac.compare_digest(token, self._assinar(arquivo, int(expira))) or int(expira) <= self.relogio():
                return 403, LINK_INVALIDO
        return 200, (self.pasta / arquivo).read_bytes()
