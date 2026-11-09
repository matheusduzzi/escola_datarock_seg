# Imagem do contêiner do agente. Leva o Python, os programas do kit e, se você pedir, um agente de código.
#   docker build -t aurora-sandbox .
#   docker build --build-arg AGENTE=@anthropic-ai/claude-code -t aurora-sandbox-claude .
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Vazio por padrão: a imagem não instala agente nenhum.
ARG AGENTE=
RUN if [ -n "$AGENTE" ]; then npm install -g "$AGENTE"; fi

COPY alcance.py agente_roteiro.py porta_de_saida.py coletor.py permitidos.txt /kit/

# Onde a porta guarda o registro e o coletor guarda o que recebe, com dono não-root.
RUN mkdir -p /registro /recebido && chown node:node /registro /recebido

# O usuário node já vem na imagem e não é root.
USER node
WORKDIR /trabalho
CMD ["python3", "/kit/alcance.py"]
