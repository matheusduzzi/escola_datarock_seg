# O servidor da Loja Aurora, do jeito que muito provedor entrega: root com senha.
# Só para o curso. Rode publicando a porta apenas em 127.0.0.1 (ver README).
#
# A versão da imagem é fixa. Para trocar, leia as notas da versão nova antes.
FROM debian:12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd \
 && ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/ssh_host_ed25519_key

# Senhas de teste do curso. Não abrem nada fora deste contêiner.
RUN useradd -m -s /bin/bash aurora \
 && echo 'root:aurora-root-teste' | chpasswd \
 && echo 'aurora:aurora-teste' | chpasswd

COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D", "-e"]
