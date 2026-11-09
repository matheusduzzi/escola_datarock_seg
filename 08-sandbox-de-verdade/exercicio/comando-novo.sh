# Mensagem do Diego, quarta à noite:
#
# "Arrumei. Agora tem porta de saída, a chave SSH vai só para leitura e eu não monto mais
# a minha pasta inteira. Pus o soquete do Docker porque o agente roda os testes da loja em
# outro contêiner. E o .env de produção vai junto, senão os testes de pagamento não passam."

docker run --rm -it \
  --network aurora-aberta \
  -e HTTPS_PROXY=http://porta:3128 \
  -v "$PWD/casa-do-diego/.ssh:/home/node/.ssh:ro" \
  -v "$PWD/projeto:/trabalho" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file casa-do-diego/projetos/loja-aurora/.env \
  aurora-sandbox
