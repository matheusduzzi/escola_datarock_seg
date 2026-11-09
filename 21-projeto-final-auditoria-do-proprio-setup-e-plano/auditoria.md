# Auditoria do meu setup

Preencha com o que você fez nas aulas do curso. Cada parte pede uma prova: um arquivo, uma saída de comando, um print de painel com conta de teste. Nenhuma chave, senha ou dado pessoal entra aqui, nem borrado.

Setup de: ______________________  Data: ____/____/______

## 1. Lista de credenciais

Todas as ferramentas da sua ficha inicial entram. Os apps autorizados por OAuth (Google, GitHub, Microsoft) e os tokens de CI e de deploy também.

| Credencial | Dono | Escopo | Validade | Onde está | Última revisão | Situação |
|---|---|---|---|---|---|---|
| | | | | | | em uso / revogada em ____ |
| | | | | | | |
| | | | | | | |

Prova de que nenhuma chave está no que você entrega: a saída do scanner de segredos no seu repositório.

```
(cole aqui a saída)
```

## 2. Contrato de acesso de cada agente

Um quadro por agente. Pagamento, estorno, exclusão, credencial e envio a terceiro ficam em "nunca faz" ou "pede confirmação".

**Agente:** ______________________

| Faz sozinho | Pede confirmação | Nunca faz |
|---|---|---|
| | | |
| | | |

A ação proibida recusada no kit (comando e saída):

```
(cole aqui)
```

## 3. Correções na Loja Aurora

Escolha um dos dois caminhos.

**Com código:** a saída de `python3 sondar.py` e de `python3 -m unittest`, rodados na pasta `loja-aurora`.

```
(cole aqui as duas saídas)
```

**Pela checklist:** para cada falha que o `sondar.py` mostra, o que ela permite e o que você pediria para quem programa.

| Falha | O que ela permite | O que eu pediria |
|---|---|---|
| | | |

## 4. Regra de dados

| Pode ir para a IA | Vai mascarado | Nunca entra |
|---|---|---|
| | | |

| Conta de IA | Usa a conversa para treino? | Onde eu vi isso e em que data |
|---|---|---|
| | | |

## 5. Plano de incidente

O seu `plano-de-incidente.md` preenchido, a linha do tempo do ensaio (`cena/acoes.log`) e a saída final do `python3 ensaio.py checar` de cada fase.

## 6. O que mudou desde a ficha inicial

| Ferramenta | O que eu achava protegido, e por quê | O que eu achei | O que fiz |
|---|---|---|---|
| | | | |
| | | | |
