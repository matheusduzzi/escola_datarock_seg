"""Guardrail com modelo: manda cada texto a um modelo classificador e barra quando ele diz que é violação.

Contar as chamadas, sem rede e sem chave:
    python3 guardrail_modelo.py entrada --contar

Rodar de verdade, num provedor com API no formato de chat completions (o mais comum):
    export GUARDRAIL_CHAVE=...        # a chave do curso, com teto de gasto; nunca no código
    python3 guardrail_modelo.py entrada --url https://<provedor>/v1 --modelo <nome-do-modelo>

Opções:
    --limiar 0.7          confiança mínima para barrar (de 0 a 1; padrão 0.7)
    --imagens             manda o anexo da mensagem 16 junto (só para modelo que lê imagem)
    --preco-entrada X     preço em dólar por milhão de tokens de entrada, da página do provedor, no dia
    --preco-saida Y       o mesmo para os tokens de saída
    --salvar arquivo.json guarda o resultado de cada texto para a sua tabela

Modelo no seu computador (por exemplo, pelo Ollama): --url http://localhost:11434/v1, sem chave.

Quando o modelo não responde, responde fora do formato ou a conexão cai, o texto é BARRADO e a saída
diz "erro". Guardrail que deixa passar quando quebra não protege nada.
Sai 0 quando roda e 2 quando falta argumento, chave ou arquivo.
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from guardrail_regra import AQUI, carregar_itens, parar

PROMPTS = {"entrada": AQUI / "prompt-entrada.txt", "saida": AQUI / "prompt-saida.txt"}
LOCAIS = ("localhost", "127.0.0.1", "::1")


def opcao(argv, nome, padrao=None, tipo=str):
    if nome not in argv:
        return padrao
    i = argv.index(nome)
    if i + 1 >= len(argv):
        parar(f"faltou o valor depois de {nome}.")
    try:
        return tipo(argv[i + 1])
    except ValueError:
        parar(f"{nome} precisa de um número, veio «{argv[i + 1]}».")


def conteudo(item, lado, com_imagem):
    texto = str(item.get("texto") or "")
    if lado == "entrada" and item.get("de"):
        texto = f"De: {item['de']}\n\n{texto}"
    if not (com_imagem and item.get("imagem")):
        return texto
    png = (AQUI / item["imagem"]).read_bytes()
    url = "data:image/png;base64," + base64.b64encode(png).decode()
    return [{"type": "text", "text": texto}, {"type": "image_url", "image_url": {"url": url}}]


def ler_veredito(resposta):
    """Tira o JSON da resposta do modelo. Qualquer coisa fora do formato vira erro (e o texto é barrado)."""
    achado = re.search(r"\{.*\}", resposta, flags=re.S)
    if not achado:
        raise ValueError("resposta sem JSON")
    v = json.loads(achado.group(0))
    if not isinstance(v.get("violacao"), bool):
        raise ValueError("campo violacao não é true nem false")
    conf = float(v.get("confianca"))
    if not 0 <= conf <= 1:
        raise ValueError("confianca fora de 0 a 1")
    return v["violacao"], conf, str(v.get("motivo", ""))[:80]


def chamar(url, modelo, chave, prompt, corpo, espera=60):
    dados = json.dumps({"model": modelo, "temperature": 0,
                        "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": corpo}]}).encode()
    cab = {"Content-Type": "application/json"}
    if chave:
        cab["Authorization"] = "Bearer " + chave
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=dados, headers=cab, method="POST")
    with urllib.request.urlopen(req, timeout=espera) as r:
        resposta = json.loads(r.read().decode())
    texto = resposta["choices"][0]["message"]["content"]
    uso = resposta.get("usage") or {}
    return texto, int(uso.get("prompt_tokens") or 0), int(uso.get("completion_tokens") or 0)


def main(argv):
    if not argv or argv[0] not in ("entrada", "saida"):
        print(__doc__.strip())
        return 2
    lado = argv[0]
    prompt = PROMPTS[lado].read_text(encoding="utf-8").strip()
    itens = carregar_itens(lado)
    com_imagem = "--imagens" in argv

    if "--contar" in argv:
        caracteres = [len(prompt) + len(conteudo(i, lado, False)) for i in itens]
        imagens = sum(1 for i in itens if i.get("imagem"))
        print(f"Guardrail com modelo, {lado}: {len(itens)} textos, {len(itens)} chamadas ao modelo")
        print(f"Instruções do classificador: {len(prompt)} caracteres, repetidas em toda chamada")
        print(f"Texto a checar: de {min(c - len(prompt) for c in caracteres)} a {max(c - len(prompt) for c in caracteres)} caracteres por chamada")
        print(f"Total enviado: {sum(caracteres)} caracteres, {round(100 * len(prompt) * len(itens) / sum(caracteres))}% são as instruções")
        if lado == "entrada":
            print(f"Imagens anexadas: {imagens} (só vão ao modelo com --imagens)")
        print("Tokens e custo de verdade: rode sem --contar; o provedor informa os tokens de cada chamada.")
        return 0

    url = opcao(argv, "--url")
    modelo = opcao(argv, "--modelo")
    if not url or not modelo:
        parar("informe --url e --modelo, ou use --contar para só contar as chamadas.")
    host = re.sub(r"^https?://", "", url).split("/")[0].rsplit(":", 1)[0].strip("[]")
    chave = os.environ.get("GUARDRAIL_CHAVE", "")
    if not chave and host not in LOCAIS:
        parar("falta a variável GUARDRAIL_CHAVE. Use a chave do curso, com teto de gasto, e nunca a escreva no código.")
    limiar = opcao(argv, "--limiar", 0.7, float)
    if not 0 <= limiar <= 1:
        parar("--limiar vai de 0 a 1.")
    p_ent = opcao(argv, "--preco-entrada", None, float)
    p_sai = opcao(argv, "--preco-saida", None, float)

    print(f"Guardrail com modelo, {lado}, modelo {modelo}, limiar {limiar}" + (", com imagens" if com_imagem else ""))
    resultados, t_ent, t_sai, erros, barrados, inicio = [], 0, 0, 0, 0, time.time()
    for item in itens:
        t0 = time.time()
        try:
            texto, te, ts = chamar(url, modelo, chave, prompt, conteudo(item, lado, com_imagem))
            violacao, conf, motivo = ler_veredito(texto)
            barra = violacao and conf >= limiar
            situacao = "BARRA" if barra else "passa"
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            te = ts = 0
            violacao, conf, motivo, barra, situacao = None, None, f"erro: {e}"[:80], True, "BARRA"
            erros += 1
        ms = round(1000 * (time.time() - t0))
        t_ent, t_sai, barrados = t_ent + te, t_sai + ts, barrados + barra
        conf_txt = "-" if conf is None else f"{conf:.2f}"
        print(f"{item['id']:02d} {situacao:5}  confiança {conf_txt:>4}  {te:>5}+{ts:<4} tokens  {ms:>5} ms  {motivo}")
        resultados.append({"id": item["id"], "barra": barra, "violacao": violacao, "confianca": conf, "motivo": motivo,
                           "tokens_entrada": te, "tokens_saida": ts, "ms": ms})
    total_s = time.time() - inicio
    print(f"Barrou {barrados} de {len(itens)}. Passaram {len(itens) - barrados}. Erros (barrados por segurança): {erros}.")
    print(f"Chamadas: {len(itens)}. Tokens: {t_ent} de entrada e {t_sai} de saída. Tempo: {total_s:.1f} s, média {1000 * total_s / len(itens):.0f} ms por texto.")
    if p_ent is not None and p_sai is not None:
        custo = (t_ent * p_ent + t_sai * p_sai) / 1_000_000
        print(f"Custo dessa rodada: US$ {custo:.6f} (preços que você informou, por milhão de tokens).")
    destino = opcao(argv, "--salvar")
    if destino:
        Path(destino).write_text(json.dumps({"lado": lado, "modelo": modelo, "limiar": limiar, "imagens": com_imagem,
                                             "resultados": resultados}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Resultado salvo em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
