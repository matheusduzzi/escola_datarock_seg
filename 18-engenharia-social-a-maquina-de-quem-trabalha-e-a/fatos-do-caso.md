# Fatos do caso: contas de clientes da Snowflake

Fonte: Mandiant (Google Cloud), [UNC5537 Targets Snowflake Customer Instances for Data Theft and Extortion](https://cloud.google.com/blog/topics/threat-intelligence/unc5537-snowflake-data-theft-extortion), publicado em 10 de junho de 2024, com uma atualização em 17 de junho de 2024. Lido em 9 de novembro de 2026.

O relatório não se diz preliminar, mas conta o que a Mandiant sabia até aquela data ("Based on our investigations to date"). A atualização de 17 de junho só acrescentou um guia para achar sinais do ataque nas contas.

A Snowflake é uma empresa de banco de dados na nuvem. Cada cliente tem a sua conta lá, a "instância". UNC5537 é o nome que a Mandiant dá ao grupo atacante.

Os fatos estão na ordem do relatório, não na ordem do ataque. A ordem do ataque é você quem monta.

| Fato | O que o relatório diz | A frase em inglês |
|---|---|---|
| F1 | O grupo entrou em contas de clientes da Snowflake usando credenciais roubadas. A Mandiant não achou sinal de invasão do ambiente da própria Snowflake: todo caso que ela atendeu voltava a credenciais de clientes. | "every incident Mandiant responded to associated with this campaign was traced back to compromised customer credentials" |
| F2 | As credenciais vieram de programas ladrões de senha, os infostealers, que infectaram computadores que não eram da Snowflake. | "primarily obtained from multiple infostealer malware campaigns that infected non-Snowflake owned systems" |
| F3 | O relatório dá três motivos para o ataque ter dado certo. Primeiro: as contas atacadas não tinham segundo fator ligado. Usuário e senha eram suficientes para entrar. | "The impacted accounts were not configured with multi-factor authentication enabled" |
| F4 | Segundo motivo: as credenciais que apareceram no que os infostealers roubaram continuavam válidas, em alguns casos anos depois. Ninguém tinha trocado. | "still valid, in some cases years after they were stolen, and had not been rotated or updated" |
| F5 | Terceiro motivo: as contas não tinham lista de rede permitida, que só aceita acesso vindo de lugares confiáveis. | "did not have network allow lists in place to only allow access from trusted locations" |
| F6 | A infecção mais antiga ligada a uma credencial usada no ataque era de novembro de 2020. | "dated back to November 2020" |
| F7 | Em vários casos, a infecção começou em computadores de contratados, usados também para jogos e para baixar software pirata. | "contractor systems that were also used for personal activities, including gaming and downloads of pirated software" |
| F8 | Um notebook de contratado costuma acessar os sistemas de várias empresas. Se for infectado, pode abrir o acesso a todas, muitas vezes com privilégio de administrador. | "a single contractor's laptop can facilitate threat actor access across multiple organizations, often with IT and administrator-level privileges" |
| F9 | O atacante entrou pela interface web e pela linha de comando da Snowflake. Usou uma ferramenta para listar usuários, papéis e sessões, e exportou um volume grande de dados dos clientes. | "led to the export of a significant volume of customer data" |
| F10 | Depois, o grupo passou a extorquir as vítimas e a tentar vender os dados em fóruns de crime. | "has subsequently begun to extort many of the victims directly" |
| F11 | Mandiant e Snowflake avisaram cerca de 165 organizações que podiam ter sido expostas. | "notified approximately 165 potentially exposed organizations" |
| F12 | O relatório pede, entre outras coisas: monitorar credenciais vazadas, segundo fator em tudo, limitar o acesso ao que é crítico a lugares confiáveis e alertar sobre tentativa de acesso fora do normal. | "credential monitoring, the universal enforcement of MFA and secure authentication, limiting traffic to trusted locations for crown jewels, and alerting on abnormal access attempts" |

O relatório não lista as empresas atingidas nem quanto cada uma perdeu, e a linha também não lista.
