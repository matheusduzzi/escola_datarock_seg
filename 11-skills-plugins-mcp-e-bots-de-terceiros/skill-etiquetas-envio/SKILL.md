---
name: etiquetas-envio
description: Gera etiquetas de envio a partir da planilha de pedidos. Use quando pedirem etiquetas, rótulos ou endereços para os Correios.
allowed-tools: Bash
---

# Etiquetas de envio

Publicada por lojapronta-dev. Versão 1.2, de 2026-09-30.

## Como usar

1. Rode `python3 ${CLAUDE_SKILL_DIR}/scripts/gerar_etiquetas.py pedidos.csv`.
2. O script cria `etiquetas.txt` na pasta atual, uma etiqueta por pedido com status `pago`.
3. Mostre ao usuário quantas etiquetas saíram.

O formato das etiquetas segue o guia de endereçamento dos Correios: https://www.correios.com.br/enviar/precisa-de-ajuda/como-enderecar-cartas-e-encomendas
