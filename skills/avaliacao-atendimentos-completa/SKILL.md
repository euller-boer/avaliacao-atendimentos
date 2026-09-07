---
name: avaliacao-atendimentos-completa
description: >-
  Programa ORQUESTRADOR de avaliação de atendimentos da Altocon — roda de ponta a ponta, em uma
  única execução, o agente de LEITURA de conversas e, na sequência, o agente de ANÁLISE de
  atendimentos, para a EQUIPE INTEIRA de uma unidade (Taquaritinga ou Monte Alto) em um mês. Primeiro
  lê e exporta o histórico de TODOS os colaboradores da unidade no Gestta Messenger (gerando UM ÚNICO
  arquivo de transcrição com todos os colaboradores); depois analisa essa transcrição e gera um relatório
  .docx por colaborador + o resumo geral da equipe, entregando tudo em PDF num .zip no Downloads. É
  só disparar uma vez — não precisa chamar os dois agentes separadamente. Use quando o usuário disser:
  "rodar a avaliação completa de atendimentos", "fazer a avaliação de atendimentos do mês de ponta a
  ponta", "ler e analisar os atendimentos da equipe de uma vez", "gerar os relatórios de atendimento
  da equipe do zero", "rodar leitura e análise dos atendimentos de julho", "avaliação de atendimentos
  de Taquaritinga do mês", "processar os atendimentos da equipe inteira e gerar os relatórios".
---

# Avaliação de Atendimentos — Programa Completo (Leitura + Análise)

Este é um **orquestrador**: ele não lê o Gestta nem monta os relatórios por conta própria — ele
**dispara, na ordem certa, os dois agentes que já existem** e cuida de encaixar a saída de um na
entrada do outro, cobrindo a **equipe inteira** de uma unidade em uma só execução.

```
  ┌─────────────────────────┐        ┌──────────────────────────┐        Entrega
  │  Agente de LEITURA de   │   →    │  Agente de ANÁLISE de    │   →    .zip com os PDFs
  │  Conversas (Gestta)     │        │  Atendimentos            │        no Downloads
  │  → 1 transcrição ÚNICA   │        │  → .docx por colaborador │        (1 por colaborador
  │    (todos, em seções)    │        │    + Resumo da Equipe    │         + Resumo da Equipe)
  └─────────────────────────┘        └──────────────────────────┘
```

> A leitura gera **um único arquivo** `transcricao_equipe_<unidade>_<MM-AAAA>.txt`, com uma seção
> `### COLABORADOR: <nome>` para cada um. A análise lê esse arquivo único (é o formato exato que o
> `analisar.py` espera). **Não** se gera mais um `.txt` por colaborador.

Agentes encadeados (use as versões **corrigidas/determinísticas** quando existirem):

1. **Leitura** — `agente-leitura-conversas-corrigido` (ou `agente-leitura-conversas`).
2. **Análise** — `agente-analise-atendimento-corrigido` (ou `agente-analise-atendimento`).

## O que este programa faz e o que NÃO faz

- **Faz:** roda a leitura **uma vez** para os colaboradores escolhidos da unidade (exporta o histórico
  do mês em **um único arquivo** de transcrição) e, quando essa transcrição estiver pronta, roda a
  análise e entrega os relatórios.
- **NÃO faz** nada além de orquestrar. Todas as regras de leitura (como navegar o Gestta) e de análise
  (9 critérios, pesos, evidências, notas) ficam **dentro** dos respectivos agentes. Este orquestrador
  **não** reinterpreta nem altera essas regras.
- **NÃO inventa dados.** Se a leitura de um colaborador falhar ou vier vazia, registre e siga; nunca
  preencha a análise com dados que a transcrição não sustenta.

## Unidades — uma unidade por execução (IMPORTANTE)

A Altocon tem **duas unidades, avaliadas SEPARADAMENTE**. Cada execução deste programa cobre **uma**
unidade e gera **um Resumo da Equipe próprio** — exatamente como o agente de análise já exige.

- **Taquaritinga** (lista fixa — só muda quando o usuário avisar de um novo colaborador):
  Ana Chueco, Julia Ribeiro, Leonardo Chueco, Natália Tiesi, Priscila de Pietro, Tiago Chueco.
- **Monte Alto:** **todos os demais** colaboradores que **não** estão na lista de Taquaritinga
  (ex.: Euller Boer e os outros operadores do Gestta), **menos os desligados**: Graziele Anselmo
  (desde 08/08/2026), Graziela dos Anjos (desde 24/08/2026) — duas pessoas diferentes, confira a
  grafia — e **Flavio Rosato** (saída em 24/08/2026). Os três são regra **"total"**: nunca
  marcar, em período nenhum, nem nos meses em que trabalharam. O Flavio era "corte" até
  **01/09/2026**, quando o usuário mudou a regra dele; rodadas antigas saíram com ele.
  A tabela completa, com as regras, está no Passo 2 do `agente-leitura-conversas-corrigido`.
  Como a lista de Monte Alto é por **exclusão**, quem saiu continua sendo puxado do Gestta
  enquanto tiver atendimento no período: tem que ser tirado na mão, na seleção da Etapa 1.

Se o usuário pedir "a equipe inteira" sem dizer a unidade, **confirme qual unidade** antes de começar
(não misture as duas num único resumo).

## Antes de começar — confirmar 3 coisas

1. **Unidade:** Taquaritinga ou Monte Alto? (uma por execução)
2. **Colaboradores:** quais avaliar? Pode ser a **equipe inteira** da unidade **ou um subconjunto
   selecionado** (o launcher/menu passa a seleção já pronta — respeite exatamente quem foi escolhido).
   Se o usuário não especificar, use a **equipe inteira** da unidade.
3. **Período:** pode ser de **três tipos** (o app/menu já manda pronto; se o usuário não disser,
   assuma o **mês anterior completo** e confirme em uma linha antes de rodar):

   | Tipo | Regime | `Período:` no cabeçalho | Sufixo dos arquivos |
   |---|---|---|---|
   | **Mês** | avaliação **formal** | `06/2026` | `06-2026` |
   | **Semana** (seg–dom) | **acompanhamento** | `01/06/2026 a 07/06/2026` | `01-06-2026_a_07-06-2026` |
   | **Dia** | **acompanhamento** | `05/06/2026` | `05-06-2026` |

   O formato do `Período:` no bloco de integridade da transcrição é **rígido** — é ele que o
   `analisar.py` lê para rotular o relatório e decidir o regime.

> **Semana e Dia = acompanhamento SEM NOTA** (regra da coordenação, 08/08/2026). A amostra é
> reduzida demais para virar nota (ex.: 2 atendimentos no dia → um único atraso derruba o SLA para
> 50%; na semana 03–09/08/2026 uma colaboradora com UM atendimento tirou 3,0 e puxou a média da
> unidade inteira). Nesses períodos o `analisar.py` gera um **levantamento**: mesmos 9 critérios,
> mesmas contagens e os mesmos exemplos reais, mas **sem nota, sem média e sem ranking** — os
> documentos saem como `Acompanhamento_<Colab>_<sufixo>`, `Acompanhamento_Equipe_<Coord>_<sufixo>`
> e `Acompanhamento_Escritorio_<Cidade>_<sufixo>`, e o
> zip como `Acompanhamento de atendimento de <Cidade> - <sufixo>`. **Nota só na avaliação mensal.**
> Nada a configurar: o script decide pelo formato do `Período:` no cabeçalho da transcrição.

Monte a **lista de colaboradores a processar**:
- Se veio uma **seleção específica** (do menu ou do pedido), processe **somente** esses nomes.
- Se for **equipe inteira**: para Taquaritinga, os 6 nomes fixos; para Monte Alto, os operadores do
  Gestta que não estão na lista de Taquaritinga (o agente de leitura ajuda a identificar quem teve
  atividade no período).

Sempre confirme em uma linha o **resumo da seleção** (unidade · colaboradores · período) antes de
iniciar a leitura.

## Fluxo de execução (ponta a ponta)

### Etapa 1 — Leitura (um único arquivo com todos os selecionados)

Rode o **agente de leitura de conversas** (`agente-leitura-conversas-corrigido`) **uma vez** para a
seleção, no período informado. Ele lê o Gestta e exporta **um único arquivo** com **todos** os
colaboradores selecionados, cada um em sua seção `### COLABORADOR: <nome>`:

```
transcricao_equipe_<unidade>_<MM-AAAA>.txt
```

Regras da Etapa 1:

- **Um arquivo só.** Não gere um `.txt` por colaborador — a leitura já entrega todos juntos, no
  formato exato que a análise espera (bloco de integridade no topo + seções por colaborador).
- Se veio uma **seleção específica**, a transcrição deve conter **apenas** esses colaboradores.
- Se um colaborador **não tiver histórico** no mês, ele simplesmente não aparece / fica sem
  atendimentos; a análise o trata como "Não avaliado" (fora do cálculo e do ranking).
- **Só avance para a Etapa 2 com a transcrição única pronta e conferida** (o bloco de integridade tem
  de fechar: `Atendimentos lidos == totalDocs`, `Falhas == 0`). Sem isso, não há o que analisar.
- Confirme rapidamente ao usuário a cobertura (colaborador → nº de atendimentos, lido do cabeçalho)
  antes da análise.

### Etapa 2 — Análise dos colaboradores selecionados

Com a **transcrição única** pronta, rode o **agente de análise de atendimentos**
(`agente-analise-atendimento-corrigido`) passando **esse arquivo** como entrada. Se a execução cobriu
apenas um subconjunto, o **Resumo da Equipe**
agrega **somente os colaboradores selecionados** (deixe isso claro no `periodo_label`, ex.:
"Junho/2026 — Taquaritinga (seleção)"). Ele vai:

- gerar **um .docx por colaborador** (tema navy/dourado, 9 critérios, tabela de indicadores, uma
  caixa de evidência por critério). **Mensal:** `Relatorio_<Colab>_<MM-AAAA>.docx`, com nota final
  por média ponderada. **Semana/dia:** `Acompanhamento_<Colab>_<sufixo>.docx`, **sem nota** —
  levantamento do que foi observado em cada critério (ver o quadro no SKILL.md do agente de análise);
- gerar **o documento da equipe** só com os colaboradores daquela unidade, identificando a unidade
  no `periodo_label` (ex.: "Junho/2026 — Taquaritinga"). **Mensal:**
  `Resumo_Escritorio_<Cidade>_<MM-AAAA>.docx` com média e ranking da unidade inteira, mais um
  `Resumo_Equipe_<Coord>_<MM-AAAA>.docx` por coordenador. **Semana/dia:**
  `Acompanhamento_Escritorio_<Cidade>_<sufixo>.docx` (+ um por coordenador), com a tabela de
  indicadores por colaborador ordenada por volume de atendimentos — sem média e sem ranking;

  O **resumo do escritório entra no pacote de TODOS os coordenadores**, não só no da diretoria
  (decisão do Euller em 01/09/2026): o gestor precisa da média da unidade para comparar com a
  equipe dele sem ter de pedir o pacote da diretoria.
- **empacotar com um comando** (não montar zip à mão):

```
python3 scripts/empacotar.py <dir_dos_json>
```

O `empacotar.py` (na skill `agente-analise-atendimento-corrigido`) gera os `.docx`, converte
para PDF, monta os `.zip` com o nome padronizado e grava no Downloads. Ele lê a **mesma
constante `EQUIPES`** que o `analisar.py` usa, então a divisão por coordenador não tem como
sair diferente da que está nos relatórios. Detecta sozinho o regime (mensal x acompanhamento)
e se a unidade tem divisão.

| Unidade | O que sai |
|---|---|
| **Monte Alto** | 5 zips: um por coordenador (com o PDF do próprio coordenador junto) + o `(Diretoria)`, que leva TODOS os individuais, o resumo da unidade e os resumos de equipe |
| **Taquaritinga** | 1 zip: todos os individuais + Resumo da Equipe (não tem divisão) |

O nome sempre traz a unidade — `Análise de atendimento de <Unidade> - <Coordenador> - <sufixo>`
no mensal, `Acompanhamento de atendimento ...` na semana/dia. É por ela que o script de e-mail
separa os pacotes quando as duas unidades rodam no mesmo período e os zips convivem no
Downloads. Só PDFs no zip, nunca `.docx`.

Quem está na transcrição sem equipe declarada entra **só** no zip da diretoria, e o script
avisa quem foi — nunca encaixar a pessoa numa equipe por conta própria.

### Etapa 3 — Entrega e conferência

Apresente ao usuário:

- o caminho de **cada .zip** entregue no Downloads (em Monte Alto são 5 — um por coordenador
  mais o da diretoria);
- a **contagem por pacote**: nº de colaboradores + o Resumo da Equipe correspondente;
- quem ficou **"Não avaliado"** (sem histórico no mês), se houver;
- os **AVISOS de equipe** que o `analisar.py` imprimiu: quem estava na transcrição sem equipe
  declarada e quem foi declarado mas não apareceu no período.

### Etapa 4 — Abrir o e-mail para a diretoria (rascunho, NÃO enviar)

Depois de entregar o `.zip` **e só depois de a conferência passar**, abra o e-mail já montado:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\enviar-avaliacao-email.ps1" -Zip "<caminho do .zip>" -Unidade "<Taquaritinga|Monte Alto>" -Periodo "<06/2026 | 05/06/2026 | 01/06/2026 a 07/06/2026>" -Regime "<Avaliação mensal|Acompanhamento (amostra reduzida)>"
```

> **Monte Alto (11/08/2026): NÃO use este script.** Ele foi feito para um zip por unidade. Para
> Monte Alto existe o **`~/.claude/enviar-avaliacao-equipes.ps1`**, que abre um rascunho por
> coordenador (com o zip da equipe dele) mais o da diretoria (consolidado + os 5 zips). O usuário
> dispara pelo ícone **"Enviar Avaliacao por Equipe"** na Área de Trabalho, **quando ele quiser** —
> decisão dele de 11/08/2026 foi ícone separado, não automático no fim da rodada. **Não abra os
> e-mails por conta própria**; ao terminar os zips, apenas lembre que o ícone existe.
>
> **Taquaritinga também usa o mesmo ícone** (11/08/2026): o pacote é um só e sai em **um único
> rascunho**, com Tiago Chueco (`diretoriataq`) e Leonardo Chueco (`rhtaq`) juntos no campo
> "Para". Taquaritinga recebe **somente** os arquivos de Taquaritinga. Se houver pacotes das
> duas unidades no mesmo período, o script pergunta para qual delas abrir os e-mails.
>
> Destinatários por coordenador ficam em `~/.claude/avaliacao-destinatarios.txt`. Se estiver em
> branco, o rascunho abre com "Para" vazio e um aviso — **nunca inventar endereço**.

Regras (inegociáveis):

- **NUNCA enviar o e-mail.** O script só ABRE o rascunho no Thunderbird; quem confere e clica em
  "Enviar" é sempre o usuário. Não automatize o clique, não use SMTP, não manipule senha de e-mail.
- **A unidade e o período do e-mail são os da rodada** — nunca outros. Se a execução cobriu só um
  subconjunto de colaboradores, diga isso ao usuário antes, porque o e-mail vai para a diretoria.
- **Semana/Dia:** passe `-Regime "Acompanhamento (amostra reduzida)"` para o texto deixar claro que
  não é a avaliação formal do colaborador.
- **Destinatários:** o script lê `~/.claude/avaliacao-destinatarios.txt` (específico por unidade tem
  prioridade sobre `PADRAO`). Se estiver vazio, o rascunho abre com o campo "Para" em branco e um
  aviso — **não invente endereço**.
- Se o usuário não quiser enviar naquela rodada, é só não abrir o rascunho — pergunte se ele quer.

Rode a checklist de verificação do próprio agente de análise (um .docx por colaborador + Resumo;
notas batem com a média ponderada; totais batem com os cabeçalhos das transcrições; evidências reais
por critério; arquivos abrem sem erro).

## Regras de robustez do orquestrador

- **Mesmo período em todas as etapas.** Nunca leia um colaborador em um mês e analise em outro.
- **Uma unidade por execução.** Para avaliar as duas unidades, rode o programa duas vezes (um .zip
  para Taquaritinga e outro para Monte Alto).
- **Se a leitura falhar** (Gestta indisponível, login, páginas perdidas), a própria leitura tem
  retentativas e uma trava de integridade; não avance para a análise com base parcial. Avise o usuário
  com os números exatos e refaça a leitura.
- **Não duplique trabalho:** se a transcrição única do período (`transcricao_equipe_<unidade>_<MM-AAAA>.txt`)
  **já existir** e estiver conferida, reuse-a em vez de reler o Gestta (confirme com o usuário se deve
  reprocessar). A transcrição é a **fonte congelada** — não regenere entre rodadas da análise.
- **Sem invenção de dados** em nenhuma etapa: toda nota, indicador e evidência da análise vem da
  transcrição real; toda transcrição vem do Gestta real.

## Resumo em uma linha

Um comando → leitura da equipe da unidade em **um único arquivo** de transcrição → análise → um .zip de
PDFs no Downloads (relatórios individuais + Resumo da Equipe), sem você precisar disparar os dois
agentes separadamente.
