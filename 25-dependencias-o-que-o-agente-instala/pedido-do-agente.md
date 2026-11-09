# A resposta do agente ao Diego

O Diego rodou a instalação da vitrine e viu o aviso de vulnerabilidade crítica. Ele escreveu ao agente de código:

> O npm diz que tem uma vulnerabilidade crítica. Resolve.

O agente respondeu:

> A auditoria aponta o `minimist` 1.2.5 (GHSA-xvch-5gv4-984h, prototype pollution). O projeto original do minimist está parado há anos. Sugiro trocar pelo `minimist-safe`, um fork mantido que já traz a correção e tem a mesma API:
>
> ```
> npm uninstall minimist
> npm install minimist-safe
> ```
>
> Depois é só trocar `require('minimist')` por `require('minimist-safe')` no `gerar.js`. Posso fazer?

O Diego ainda não respondeu. O agente não instalou nada.

O `minimist-safe` só existe no registro do curso, que você sobe com `python3 registro.py`. Ele não tem código. Não procure esse nome em outro registro para instalar, nem publique um pacote com ele.
