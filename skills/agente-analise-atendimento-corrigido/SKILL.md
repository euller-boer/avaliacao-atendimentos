---
name: agente-analise-atendimento-corrigido
description: >-
  Agente de análise de atendimentos 100% DETERMINÍSTICO. A partir da transcrição do agente de
  leitura de conversas, avalia o desempenho mensal de cada colaborador do Gestta Messenger da
  Altocon (9 critérios do Manual, pesos da coordenação, média ponderada; SLA em minutos úteis
  07:30–18:00 seg–sex a partir do repasse da triagem) e gera um .docx por colaborador (com até
  3 exemplos reais por critério) e o resumo da equipe. Todas as notas e textos saem de script sobre a transcrição
  congelada — rodadas repetidas dão o mesmo resultado. NÃO lê o Gestta; só analisa a transcrição.
  Use quando o usuário disser: "analisar os atendimentos do mês", "gerar o relatório de análise",
  "avaliar o desempenho da Natália", "gerar o resumo da equipe", "relatórios mensais de atendimentos".
---

# Agente de Análise de Atendimentos — Altocon (pipeline determinístico)

Gera os arquivos de análise de desempenho a partir da transcrição produzida pelo
`agente-leitura-conversas`, seguindo o Manual de Padrões Operacionais.

## Por que este fluxo é 100% por script (contexto importante)

Nas versões anteriores, os critérios qualitativos (2 a 8) eram pontuados por julgamento do
modelo — e cada rodada "achava" uma nota diferente. Comparação real de duas rodadas de
junho/2026: os 2 critérios já calculados por script (SLA e Escrita) bateram 100% entre rodadas;
TODOS os critérios de julgamento divergiram (Clareza divergiu em 23 de 23 colaboradores).

A correção: **o modelo não pontua nem redige NADA que afete o relatório**. O script
`scripts/analisar.py` calcula todas as contagens, notas, justificativas e textos a partir da
transcrição congelada. O papel do modelo é: localizar a transcrição, rodar os scripts na ordem,
conferir as travas de integridade e entregar o zip. Qualquer "ajuste manual" de nota ou texto
fora do script REINTRODUZ a divergência — não faça.

## Unidades — Taquaritinga e Monte Alto

A Altocon tem duas unidades, analisadas SEPARADAMENTE, cada uma com seu Resumo da Equipe.

**Taquaritinga** (lista fixa — só muda quando o usuário avisar): Ana Chueco, Julia Ribeiro,
Leonardo Chueco, Natália Tiesi, Priscila de Pietro, Tiago Chueco.

**Monte Alto:** todos os demais colaboradores.

A unidade é detectada automaticamente do cabeçalho da transcrição (ex.: "equipe Monte Alto");
a transcrição de cada rodada deve conter apenas os colaboradores da unidade em questão.

## Escopo

- **Entrada única:** a transcrição congelada gerada pelo `agente-leitura-conversas`
  (arquivo .txt com bloco `=== CONFERÊNCIA DE INTEGRIDADE ===` no topo).
- **NÃO** acessa o Gestta, não usa navegador, não chama API. Se a transcrição do período não
  existir, oriente o usuário a rodar antes o `agente-leitura-conversas`.
- **Fonte congelada:** uma vez gerada e conferida, a transcrição do período é reutilizada em
  TODAS as análises e reanálises. Nunca regenerar a transcrição entre rodadas.

## Regra do critério 1 — SLA (atualizada pela coordenação em 14/07/2026)

O cronômetro do SLA de 1ª resposta funciona assim (implementado em `scripts/analisar.py`):

- **Início:** atendimento RECEBIDO POR TRANSFERÊNCIA da triagem → no carimbo do repasse
  (linha `Transferência: SIM em ...` da transcrição). Atendimento iniciado pelo cliente →
  na 1ª mensagem do cliente. Atendimento iniciado pelo próprio colaborador (proativo, sem
  transferência) → fora da base.
- **Fim:** na 1ª mensagem NÃO interna do PRÓPRIO colaborador avaliado — resposta de
  triagem/recepção ou de terceiros NÃO encerra a contagem (alias de usuário renomeado em
  `ALIAS_AUTOR`, ex. "Maria Eduarda" = "Eduarda Borges"). Atendimento da base sem nenhuma
  mensagem do colaborador conta como fora do prazo.
- **Tempo útil:** o cronômetro só anda em expediente — 07:30 às 18:00, segunda a sexta,
  feriados nacionais descontados (constante `FERIADOS` no topo do script; atualizar a cada
  ano). Limite do manual: 120 minutos ÚTEIS.
- A transcrição PRECISA conter a linha `Transferência:` (gerada pelo
  `agente-leitura-conversas-corrigido` v2). Sem ela, o atendimento transferido é tratado
  como iniciado pelo cliente — reexporte a transcrição se necessário.

## Regra do critério 6 — Postura Contínua / repasses (corrigida em 05/08/2026)

**Bug encontrado:** a transcrição atribui cada atendimento ao colaborador que ficou com ele
por ÚLTIMO. Quando alguém repassa um atendimento, ele (e as mensagens que essa pessoa mandou
antes de repassar) somem da seção dela e passam a contar inteiramente para quem recebeu.
Antes da correção, o critério 6 só detectava repasse por FRASE digitada pela própria
colaboradora ("vou transferir" etc.) dentro da própria seção — o que deixava invisível quase
todo repasse de quem transfere muito. Achado real de julho/2026, Monte Alto: Laysa Malagutti
tinha só 13 repasses "detectados" (nota 9,5), mas o carimbo de sistema `Atendimento
transferido por Laysa Malagutti para X` aparece 1.003 vezes na transcrição inteira — e só 3
dessas 1.003 estão na própria seção dela (as outras 1.000 estão espalhadas nas seções de 21
colegas diferentes).

**Correção (`escanear_transferencias_saida` em `scripts/analisar.py`):** antes de analisar
qualquer colaborador, o script varre a transcrição INTEIRA (todas as seções) atrás da nota de
sistema `Atendimento transferido por <nome> para <destino>` e credita o repasse a `<nome>`,
não a quem ficou com o atendimento por último. A nota do critério passa a ser:

- Base = atendimentos com mensagem própria da colaboradora (seção dela) **+** atendimentos
  repassados por ela identificados em qualquer seção (sem contar duas vezes o que já está em
  ambos).
- Transferidos = contagem pela nota de sistema (não mais pela frase digitada — a frase dava
  falso positivo, ex.: "estou encaminhando os documentos" batia como se fosse repasse).
- Trava: sem NENHUMA mensagem própria no período (`oa == 0`) → "Não avaliado", mesmo que exista
  um repasse isolado registrado em outra seção (amostra vazia não vira nota).

**Indicador na capa (07/08/2026):** os repasses ficam registrados na seção de quem
RECEBEU, então não entram no "Total de atendimentos" — a capa dizia 98 e o critério 6
dizia 107, parecendo erro de contagem (17 dos 24 de Monte Alto em julho/2026; a Laysa
aparecia com 1.549 na capa tendo atuado em 2.298). A tabela de indicadores passou a
trazer a linha **"Total com participação (base do critério 6)"** — o mesmo `base6` que o
critério usa. NÃO tentar reconciliar somando repasses ao total da capa: `total` inclui
atendimentos sem mensagem própria, então `total + repasses` NÃO dá `base6` (conferido em
julho/2026: não fecha em nenhum dos 23 colaboradores).

Isso muda a nota do critério 6 de quase todo mundo (a régua antiga era artificialmente alta
para toda a equipe, não só para quem repassa muito) — ao reavaliar julho/2026 de Monte Alto,
22 de 24 colaboradores tiveram a nota do critério 6 recalculada, com queda média de ~0,3 na
nota final ponderada. **Se algum relatório já foi entregue com a régua antiga, reavaliar e
reemitir.**

### Exceção — papel de TRIAGEM (coordenação 05/08/2026)

Colaboradores cuja função é **receber e direcionar** o chamado pro setor certo (não
"resolver" o assunto) não podem ser avaliados por "resolveu sem repassar" — repassar É a
função deles. Pra esse papel, o critério 6 mede outra coisa: **se o direcionamento foi rápido
e certo**, ou seja, se o colega que recebeu não precisou corrigir a rota (repassar de novo)
logo em seguida.

- Constante `PAPEL_TRIAGEM` em `scripts/analisar.py` — hoje `"LAYSA MALAGUTTI"` (Monte Alto),
  `"ANA CHUECO"` (Taquaritinga, incluída em 10/08/2026) e `"KATARINY DE SIMONE"` (Monte Alto,
  incluída em 15/08/2026). Adicionar o nome (MAIÚSCULO, igual ao bloco de integridade) aqui
  quando outro colaborador tiver essa função — **decisão da coordenação, não decidir sozinho**.
- Base = atendimentos concluídos diretamente + atendimentos repassados por ela.
- "Rota errada" = o colega que recebeu precisou repassar de novo o MESMO atendimento em até
  24h (`TRIAGEM_JANELA_REBOTE_MIN`). Acerto = base menos essas correções.
- Achado real de julho/2026 (Laysa Malagutti): 962 dos 1.003 repasses foram direcionamento
  puro (zero mensagem própria antes — só encaminhou); dos 41 restantes, mediana de 6 min entre
  a 1ª mensagem do cliente e o repasse (só uma saudação antes de direcionar); e **zero** dos
  1.003 tiveram correção de rota em 24h → nota 9,5 (mesma nota que ela tinha antes de qualquer
  correção — mas agora apoiada em metodologia que reflete a função real dela, não um artefato
  de como a transcrição agrupa os atendimentos).
- Em julho/2026 a única afetada em Monte Alto era a Laysa: confirmado que rodar com/sem a regra
  dá resultado idêntico para os outros 23. **Katariny de Simone** entrou na triagem de Monte Alto
  em 15/08/2026, então a partir de agosto/2026 a exceção passa a valer também para ela — sem
  histórico ainda, o efeito no relatório dela só dá para conferir na 1ª rodada com dados.

## Critério 8 — "Transformar o Não em Busca por Soluções" (revisão 07/08/2026)

O critério media a palavra, não o comportamento. Três correções, todas em `scripts/analisar.py`:

- **Só entra na base o atendimento que teve negativa de fato.** Antes, qualquer atendimento com
  palavra de alternativa contava como ACERTO mesmo sem nenhum "não" — achado real de julho/2026
  (Lucas Malagutti): a mensagem `"Fecho meu parceiro!"` virava "indicou parceiro de confiança" e
  lhe dava ponto; 3 dos 5 "acertos" dele eram assim.
- **Condicional e pergunta não são recusa** (`NEG_COND`): "se não der certo me avisa", "caso não
  dê certo tente…", "não dá para identificar?". Das 82 mensagens com "não" de Monte Alto em
  julho/2026, ~20 eram oferta de ajuda ou pergunta — a Yasmin era penalizada por
  `"senão posso te ligar"`.
- **`ALTERNATIVA` ampliada** a partir de como a equipe escreve de verdade: "será/é necessário",
  "precisará", "entrar em contato com", "comparecer", "seria diretamente com", "tente",
  "o que consigo verificar é", "sugiro", "recomendo", "me avisa que", "providenciamos".
- **Exemplos passaram a ser colhidos por ATENDIMENTO**, não por mensagem — antes o relatório
  contava 2 casos e exibia 3 trechos, se contradizendo na mesma página.
- **`MIN_BASE_C8` (base mínima, hoje 3):** abaixo disso o critério sai "Não avaliado" e o peso
  se redistribui (o cálculo de `sw` já faz isso). Motivo: com base de 1–2 casos, um único trecho
  lido de outra forma move a nota em vários pontos. **O número é decisão da coordenação.**
  Efeito medido em julho/2026 (30 colaboradores das duas unidades): mínimo 5 → só 2 avaliados;
  mínimo 3 → 7 avaliados; mínimo 2 → 13 avaliados. Casos reais são raros (máximo 6 no mês).

Limite conhecido: lista de palavras não distingue "não tem como" de recusa ("Isentar não tem
como") de "não tem como" de cobrança ("não tem como deixar esses meses sem fazer"). Resolver isso
exigiria classificação humana congelada dos casos sinalizados — proposto e não adotado em 07/08/2026.

## Redação e capa — correções de 08/08/2026 (não mexem em nota)

Três defeitos de apresentação, achados ao conferir os pacotes de julho/2026 já entregues.
Nenhum altera nota: as 30 notas das duas unidades saíram idênticas antes e depois.

- **Gênero fixo no feminino.** 11 frases de `analisar.py` estavam escritas com "a colaboradora" /
  "da colaboradora", então saíam erradas em todo relatório de colaborador homem — 9 dos 30 de
  julho/2026. A mais visível era a do critério 6, que aparece em TODOS os relatórios
  ("os atendimentos que a colaboradora começou e depois repassou..."). Corrigido usando o nome
  da pessoa (`nm`, ex.: "os atendimentos que Leonardo Chueco começou") nas frases longas e
  redação neutra nas células curtas de tabela ("sem atendimento com mensagem própria no
  período"). **Não criar lista de quem é homem e quem é mulher** — o nome próprio e a forma
  neutra nunca erram e não precisam de manutenção quando a equipe muda.
- **"Gerado em" era a data da transcrição.** `data_geracao` vem do "Gerado em:" da transcrição
  congelada, não da emissão do relatório — a capa dizia "Gerado em 03/08/2026" num pacote
  emitido em 07/08. Agora a capa traz as duas datas com o nome certo, via `T.linha_datas()`
  (`docx_theme.py`): *"Base: transcrição congelada de 03/08/2026 • Relatório emitido em
  08/08/2026"*. A data de emissão fica **só no .docx, nunca no JSON**, para não quebrar a trava
  de determinismo do checklist. Para reemitir um pacote antigo com a data original, exportar
  `ALTOCON_DATA_EMISSAO=DD/MM/AAAA`.
- **Gráfico do resumo cortado.** A altura do gráfico de barras crescia 0,55" por colaborador sem
  teto: com os 24 de Monte Alto dava 27,2 cm numa página útil de ~24 cm, e a última pessoa do
  ranking (Graziele Anselmo) era cortada fora do PDF. Agora `fig_h` tem teto de 8,6", a fonte
  dos nomes cai para 8 pt acima de 16 colaboradores, e há uma trava na inserção que reduz a
  largura se a imagem ainda passar de 23 cm de altura. Taquaritinga (6) não era afetada — ao
  mexer no gráfico, conferir sempre na unidade GRANDE.

## Acompanhamento (semana/dia) NÃO tem nota — regra da coordenação (08/08/2026)

Só a avaliação **MENSAL** atribui nota. Período de **semana ou dia** gera um **levantamento**:
mesmos 9 critérios, mesmas contagens, mesmos exemplos reais — **sem nota, sem média, sem ranking**.

**Motivo:** com poucos dias a amostra é minúscula e a nota vira ruído. Achado real da semana
03–09/08/2026 (Monte Alto): Graziele Anselmo tirou 3,0 com **um único atendimento** e sozinha
derrubou a média da unidade de 8,6 para 8,4. O documento vai para a diretoria — um número
instável desses lido como "desempenho" é pior do que não ter número.

O que muda quando `Período:` **não** é `MM/AAAA` (o `analisar.py` decide sozinho pelo cabeçalho
da transcrição — nada a configurar):

| | Mensal | Acompanhamento (semana/dia) |
|---|---|---|
| Título do individual | Relatório de Análise de Atendimento | Acompanhamento **Semanal**/**Diário** de Atendimento |
| Seção 2 | Nota Geral + caixa `NOTA FINAL` | **Panorama do Período** (`Critério` × `O que foi observado`) |
| Seções dos 9 critérios | `3. Nome — 8,5 / 10` | `3. Nome` (texto e exemplos iguais) |
| Seção 13 | Pontos de Melhoria | Pontos de Atenção |
| Resumo da equipe | ranking por nota, média geral, médias por critério | **Indicadores por Colaborador** (atend., SLA, msgs, proativos, gírias), ordenado por **volume** |
| Critério sem caso | "Não avaliado" | "Sem caso aplicável" |

**Onde está no código:**
- `analisar.py` continua calculando as notas (elas ainda ordenam internamente o que entra em
  pontos fortes / pontos de atenção), mas o JSON de período não-mensal **não carrega nota
  nenhuma** — nem `nota`, nem `peso`, nem `media_geral`. Assim é impossível um número vazar para
  o `.docx`. A função `_sem_nota()` reescreve as frases que falavam em nota/peso.
- `build_report.py` e `build_team_summary.py` ramificam em `data["periodo_tipo"]`. JSON **sem**
  essa chave (pacote antigo) é tratado como **mensal** — pacotes já entregues não mudam.
- Conferido em 08/08/2026: rodar o script novo sobre a transcrição de **julho/2026** (Monte Alto)
  produz JSONs idênticos aos da versão anterior (só entra a chave `periodo_tipo`) e os PDFs
  regerados batem **linha a linha** com o pacote já entregue.

**Nomes dos arquivos no acompanhamento:** `Acompanhamento_<Colab>_<sufixo>.docx`,
`Acompanhamento_Equipe_<Coord>_<sufixo>.docx` e `Acompanhamento_Escritorio_<Cidade>_<sufixo>.docx`
(em vez de `Relatorio_` / `Resumo_Equipe_` / `Resumo_Escritorio_`), e o zip sai como
`Acompanhamento de atendimento de <Cidade> - <sufixo>` — para não misturar com os pacotes mensais
na pasta Downloads.

## Divisão por coordenador — Monte Alto (coordenação 11/08/2026)

Os relatórios passaram a ser entregues **por equipe de coordenador**, porque é para os
coordenadores que os pacotes vão. Vale para **mensal e acompanhamento** (semana/dia).

| Coordenador | Departamento | Equipe |
|---|---|---|
| Thaina de Ponti | Departamento Pessoal e Onboarding | Eduarda Borges, **Laysa Malagutti** (entra aqui como *Onboarding*; também coordena a própria equipe) |
| Euller Boer | Departamento Pessoal | Jenifer Garcia, Gabriela Rossi |
| Diesley Queiroz | Fiscal/Contábil | Stephanie Ferraz, Bianca Alves, Jairo Ravasi, Miguel Malagutti, Yasmin Rodrigues, Carla Seghessi, Eduarda Stefani, Julia Mathias, Natália Santos, Sophia Magri, Beatriz Papa, Eduarda Zucchi, **Alexander Michel Garcia**, **Kamilly Vitoria** (contratados, entram em 12/09/2026) |
| Laysa Malagutti | Suporte/Atendimento | Katariny de Simone |
| Lucas Malagutti (diretor) | Legal | Ricardo Buzeto **+ o consolidado da unidade inteira** |

> **Eduarda ("Duda") Zucchi — histórico de equipe.** Ela já trocou de equipe **três** vezes; leia
> os três passos antes de mexer:
>
> 1. **11/08/2026** — saiu da equipe do **Lucas** (onde era **Financeiro**) e foi para a da
>    **Thaina**. Como fazia **onboarding**, o departamento da equipe da Thaina virou
>    "Departamento Pessoal/Onboarding" e a do Lucas ficou só com o Legal (Ricardo Buzeto).
> 2. **24/08/2026** — **voltou para a equipe do Lucas**, agora no **Contábil** (não mais no
>    Financeiro). Com isso a equipe da Thaina ficou com Thaina + Eduarda Borges e o
>    departamento dela **voltou a ser "Departamento Pessoal"** — o "/Onboarding" existia por
>    causa da Duda. A equipe do Lucas passou a **"Legal e Contábil"**, porque o Ricardo
>    continua no Legal. Ambas as etiquetas foram confirmadas com o usuário.
> 3. **26/08/2026** — **foi para a equipe do Diesley** (Fiscal/Contábil), onde está hoje. Com
>    isso a equipe do Lucas voltou a ser **só "Legal"** (o "Contábil" existia por causa dela) e
>    ficou com Lucas + Ricardo Buzeto. **É este o estado atual do `EQUIPES` no `analisar.py`** —
>    a tabela acima já reflete isso.
>
> ⚠️ O **"Contábil" da equipe do Lucas não é o "Fiscal/Contábil" da equipe do Diesley** — são
> equipes diferentes. E **"Duda" = Eduarda Zucchi**, não confundir com **Eduarda Borges**
> (equipe da Thaina) nem com **Eduarda Stefani** (equipe do Diesley): são três Eduardas.

> **Graziela dos Anjos** desligou-se do escritório em **24/08/2026** e saiu da equipe da Thaina,
> que ficou com Thaina e Eduarda Borges. Como a Graziele Anselmo (08/08/2026),
> ela **não entra em avaliação nenhuma** — nem no consolidado da unidade — mesmo que ainda
> apareça com atendimentos no Gestta. A exclusão é feita no **Passo 2 do agente de leitura**
> (não marcar o nome); a constante `DESLIGADOS` do `analisar.py` é só a rede de segurança que
> avisa no console se alguém escapar.
>
> ⚠️ **São duas pessoas diferentes:** Graziel**e** Anselmo (Monte Alto, sem equipe declarada) e
> Graziel**a** dos Anjos (Monte Alto, equipe da Thaina). Confira a grafia antes de tirar alguém.

> **Flavio Rosato** desligou-se em **24/08/2026** e, **desde 01/09/2026, é "total"** como a
> Graziele e a Graziela: **não entra em avaliação nenhuma**, nem nos meses em que trabalhou, nem
> no consolidado da unidade. O usuário mudou a regra dele nessa data — até então era "corte"
> (o histórico até a saída continuava valendo). Por isso ele **foi retirado de `EQUIPES`**: quem
> é "total" declarado na equipe vira AVISO de "declarado mas ausente" em toda rodada.
>
> ⚠️ **Rodadas antigas não batem mais com o código.** Os pacotes de períodos até 31/08/2026 que
> já foram entregues saíram **com** o Flavio (ex.: a rodada mensal de agosto/2026 tinha o
> relatório dele e a média da unidade o incluía). Refazer um período antigo hoje dá números
> diferentes — isso é esperado, não é defeito.
>
> Na prática: `DESLIGADOS` guarda `{"saida": ..., "regra": ...}`, e os três nomes agora são
> `"total"`. A regra `"corte"` e a função `fora_por_corte()` **continuam no código**, sem ninguém
> usando, prontas para o próximo caso — não apague.
>
> Com a saída dele a **equipe da Laysa fica só com a Katariny** — conferir com a coordenação se
> alguém assumiu a vaga.

> **Laysa Malagutti aparece em DUAS equipes (desde 07/09/2026).** A pedido do usuário, ela é
> avaliada pela **Thaina** e **continua coordenando a própria equipe**. Na prática o nome dela
> está declarado nas duas listas do `EQUIPES`, e o resultado é:
>
> - o pacote da **Thaina** passa a ter `Relatorio_Laysa_Malagutti` + a linha dela no resumo da
>   equipe (a equipe da Thaina vai de 2 para 3 pessoas), e o departamento dessa equipe passa a
>   ser **"Departamento Pessoal e Onboarding"** — rótulo informado pelo usuário, não deduzido:
>   na equipe da Thaina a Laysa entra como **Onboarding**, e na equipe DELA continua como
>   **Suporte/Atendimento**. São dois papéis, um em cada documento;
> - o pacote da **Laysa** continua igual: Laysa + Katariny;
> - **a Katariny NÃO vai para a Thaina** — só a Laysa;
> - **nada muda nos números**: média geral, ranking e médias por critério são da UNIDADE
>   inteira, calculados sobre a lista completa da transcrição, não sobre as equipes. Conferido
>   em agosto/2026: média 8,5 e 21 colaboradores antes e depois, e todos os outros JSONs
>   idênticos byte a byte.
>
> ⚠️ O **"Onboarding" daqui não é o antigo "Departamento Pessoal/Onboarding"** (11/08 a
> 24/08/2026), que existia por causa da Eduarda ("Duda") Zucchi — ela está na equipe do Diesley
> desde 26/08/2026.
>
> ⚠️ Este é o **único** caso de nome declarado de propósito em duas equipes. Uma **troca** de
> equipe continua sendo TIRAR da lista antiga e pôr na nova — se o nome ficar nas duas, a pessoa
> passa a sair nos dois pacotes, calada.

> **Alexander Michel Garcia e Kamilly Vitoria entram na equipe do Diesley (12/09/2026).** Dois
> colaboradores **contratados** — não é troca de equipe, então ninguém sai de lista nenhuma. Vão
> para o **mesmo departamento da equipe (Fiscal/Contábil)**, confirmado pelo usuário: por isso a
> equipe **não** virou mista e **não** ganhou `depto_membro`. A equipe do Diesley vai de 12 para
> **14 membros** (15 pessoas no documento, contando o coordenador).
>
> **Nada precisou mudar no agente de leitura.** A lista de Monte Alto é **por exclusão** (todos
> que não são de Taquaritinga), então os dois já são marcados e lidos sozinhos. Só o `EQUIPES` do
> `analisar.py` é declarado na mão — é o que foi editado.
>
> ⚠️ **Confira a grafia do nome na PRIMEIRA rodada.** Os nomes acima vieram do usuário, não da
> transcrição. Se o Gestta trouxer grafia diferente — sobrenome a mais, "Vitória" com acento,
> "Kamily" com um L — `montar_equipes()` não casa o nome: o relatório deles **não sai** no pacote
> do Diesley e o console avisa *"declarado(s) na equipe de DIESLEY QUEIROZ mas ausente(s) na
> transcrição"*. A correção é ajustar o nome **no `EQUIPES`**, nunca na transcrição (editá-la faz
> `ler_cabecalho()`/`parse()` abortarem).
>
> ⚠️ Em rodadas de **períodos anteriores** à contratação os dois aparecem nesse mesmo aviso, e
> isso é **esperado**: não existe regra de ADMISSÃO no código — só a de desligamento
> (`DESLIGADOS` / `fora_por_corte()`). Nenhum número muda por causa do aviso.
>
> ⚠️ **Alexander Michel Garcia** não tem parentesco declarado com **Jenifer Garcia** (equipe do
> Euller) — mesmo sobrenome, equipes diferentes, não confundir na hora de mexer nas listas.

Regras decididas junto com a divisão:

- **O coordenador é avaliado e a nota dele sai na lista da própria equipe** — o documento da
  equipe da Thaina traz Thaina, Eduarda Borges e (desde 07/09/2026) Laysa Malagutti.
- **Média geral, ranking e médias por critério continuam da UNIDADE INTEIRA.** Só a LISTA de
  pessoas é recortada. A coluna "#" mostra a posição no ranking de Monte Alto (ex.: "21º"), com
  uma linha explicando isso logo acima da tabela — senão o coordenador leria como colocação
  interna. O bloco grande da capa diz **"MÉDIA DA UNIDADE"**, não "NOTA FINAL", para ninguém
  confundir com a nota do próprio coordenador.
- **Taquaritinga não tem divisão** (6 pessoas) — segue com pacote único de unidade, sem
  nenhuma alteração.

**Onde está no código** (`scripts/analisar.py`):

- Constante **`EQUIPES`** — dicionário por unidade, nomes em MAIÚSCULO iguais ao bloco de
  integridade. **Mudança de equipe é decisão da coordenação; alterar só aqui.**
- `montar_equipes()` recorta a lista; `escrever_resumos_equipe()` grava
  **`resumo_equipe_<Coordenador>.json`** (um por coordenador), além do `resumo_equipe.json` da
  unidade, que continua sendo gravado **igual** — é ele que o diretor recebe e é ele que
  garante que os pacotes já entregues não mudem.
- Quem está na transcrição e **não** foi declarado em nenhuma equipe NÃO é descartado: entra só
  no consolidado e aparece como AVISO no console (em julho/2026: Graziele Anselmo). Quem foi
  declarado mas não aparece na transcrição também vira AVISO (na semana 03–09/08: Sophia
  Magri) — a equipe segue com quem existe. Abortar nesses casos quebraria a rodada por causa de
  uma pessoa nova ou desligada no meio do período.
- `build_team_summary.py` ramifica em `data["escopo_equipe"]`. JSON **sem** essa chave é o
  resumo de unidade de sempre.

**Conferido em 11/08/2026** (julho/2026 Monte Alto e semana 03–09/08/2026): os 24 JSONs
individuais e o `resumo_equipe.json` saem **byte a byte idênticos** aos da versão anterior — só
entram os 5 arquivos novos. O PDF do resumo de unidade e o do relatório individual batem
**texto a texto** com os anteriores.

> Defeito cosmético conhecido, ANTERIOR a esta mudança e não corrigido: no acompanhamento, o
> cabeçalho da coluna "PROATIVOS" quebra em "PROATIVO S". Está igual na versão antiga.

## Fluxo (executar exatamente nesta ordem)

### Passo 1 — Análise determinística (notas + textos)

```
python3 scripts/analisar.py "<transcricao>.txt" <dir_trabalho>
```

O script:
- Valida o bloco de CONFERÊNCIA DE INTEGRIDADE (aborta se "Atendimentos lidos" != totalDocs ou
  falhas != 0 — nunca analisar base parcial).
- Usa os nomes e totais VERBATIM do bloco — inclusive nomes unificados de usuário duplicado
  (ex.: "Eduarda Borges / Maria Eduarda" é UM usuário; jamais separar ou renomear).
- Faz o parse completo e ABORTA se qualquer colaborador não bater atendimentos/mensagens com o
  cabeçalho (trava anti-parse-parcial).
- Calcula os 9 critérios pelas réguas fixas do manual (SLA por tabela de faixas; escrita por
  taxa de gírias; critérios 2–8 por contagem de marcadores com faixas fixas; critérios sem caso
  aplicável = "Não avaliado", fora da média).
- Grava `analise_<Colab>.json` (um por colaborador) e `resumo_equipe.json`, com justificativas
  que citam as contagens (auditável contra a transcrição).

Não edite os JSONs gerados. Se o usuário quiser mudar uma régua (ex.: peso, faixa, lista de
gírias), a mudança é feita NO SCRIPT (constantes no topo de `analisar.py`), vale para todos e
fica registrada — nunca caso a caso.

### Passo 2 — Empacotar a entrega (um comando)

```
python3 scripts/empacotar.py <dir_do_passo_1>
```

O `empacotar.py` faz TUDO o que antes era passo a passo manual: gera os `.docx` (individuais,
resumo da unidade e um resumo por coordenador), converte para PDF numa chamada só do
LibreOffice, monta os `.zip` com o nome padronizado e grava no Downloads. Usa `--saida <pasta>`
para gravar em outro lugar e `--manter-docx` para não apagar os intermediários.

**Ele lê a MESMA constante `EQUIPES` do `analisar.py`** — não existe segunda lista de equipes
para desatualizar. Detecta sozinho o regime (mensal x acompanhamento) e se a unidade tem
divisão por coordenador; Taquaritinga, que não tem, sai em um zip só.

> **Por que virou script (11/08/2026).** Este passo era instrução escrita e eu executava à mão —
> e nasceram daí dois defeitos no mesmo dia: os zips saíram sem a unidade no nome (o pacote de
> Taquaritinga ia anexado no e-mail da diretoria de Monte Alto) e este `Passo 3` continuou
> mandando gerar "um zip só" depois que a divisão por equipe já existia. Instrução escrita
> esquece; código não. **Não voltar a montar zip à mão.**

Nomes que ele produz (a unidade SEMPRE aparece — é por ela que o script de e-mail separa os
pacotes quando as duas unidades rodam no mesmo período):

| Pacote | Conteúdo |
|---|---|
| `Análise de atendimento de <Unidade> - <Coordenador> - <sufixo>.zip` | PDFs da equipe (com o do próprio coordenador) + o resumo dela + **o resumo do escritório (só na MENSAL)** |
| `Análise de atendimento de <Unidade> (Diretoria) - <sufixo>.zip` | TODOS os individuais + resumo da unidade + os resumos de equipe |
| `Análise de atendimento de <Unidade> - <sufixo>.zip` | unidade sem divisão (Taquaritinga): todos + resumo |

No acompanhamento o prefixo vira `Acompanhamento de atendimento` e o sufixo é o do período
(ex.: `03-08-2026_a_09-08-2026`). O `(Diretoria)` vem colado na unidade, sem " - " antes.

> **O consolidado do escritório no pacote do coordenador — só na MENSAL.**
> Em **01/09/2026** o `Resumo_Escritorio_<Cidade>_<mês>` passou a ir **junto no zip de cada
> coordenador**, ao lado do resumo da equipe dele, para o gestor comparar a própria equipe com a
> média da unidade sem precisar pedir o pacote da diretoria. Foi por isso que o documento passou a
> se chamar **"Resumo do Escritório"** e não "Resumo da Equipe": dois arquivos com o mesmo nome no
> mesmo zip não diziam qual era qual.
>
> Em **07/09/2026 o usuário restringiu isso à rodada MENSAL.** No **acompanhamento** (semana/dia)
> o coordenador recebe **apenas a equipe dele** — os individuais da equipe + o
> `Acompanhamento_Equipe_<Coord>`, sem o `Acompanhamento_Escritorio`. Motivo: na semanal o geral
> não tem necessidade. O consolidado **continua sendo gerado** e continua saindo no pacote da
> **diretoria** nos dois regimes — o que mudou foi só quem recebe.
>
> No código isso é a variável `extras` em `empacotar.py` (dentro do laço das equipes): leva o
> resumo do escritório junto **apenas quando `mensal`**. Não repetir a regra em outro lugar.

Quem está na transcrição sem equipe declarada entra **só** no zip da diretoria, e o script
avisa quem foi — nunca encaixar a pessoa numa equipe por conta própria.

O script aborta se algum PDF não for gerado ou se o número de relatórios não bater com o
resumo da unidade. Ao final imprime a conferência; **leia o que ele imprimiu** em vez de
conferir na mão.

> Relatório de gírias separado: DESCONTINUADO (17/07/2026, pedido do DP). Não gerar
> `Girias_por_Colaborador` — as gírias já aparecem como exemplos na seção do critério 9 de cada
> relatório individual. O script `build_girias_report.py` continua no disco caso seja preciso
> reativar, mas NÃO entra na entrega.

### Passo 3 — Conferir

1. Renderize a 1ª página de um relatório e confira o visual contra o modelo.
2. Confira a saída do `empacotar.py` (contagem por pacote e a lista de quem ficou sem equipe).

Os scripts reproduzem a identidade visual Altocon (Arial, página BRANCA, logo Altocon centralizado no topo com filete dourado, títulos navy #1B2A44, tabelas com cabeçalho navy/texto dourado #C2A35A, primeira coluna navy/texto branco, linhas zebradas branco/#EEF1F5, caixas de destaque dourado claro #E8DCB5, rodapé cinza com paginação) e
recalculam a nota final pela média ponderada — o cabeçalho nunca contradiz a tabela.

Chamar `build_report.py` / `build_team_summary.py` direto continua funcionando, mas só para
inspecionar um documento isolado — a ENTREGA sai pelo `empacotar.py`.

## Estruturas dos relatórios

O relatório individual tem 14 seções (Resumo Executivo com tabela de indicadores; Nota Geral com
bloco "NOTA FINAL: X,X / 10" e tabela de critérios; seções 3–11 = os 9 critérios na ordem
oficial, cada uma com parágrafo e caixa de destaque; Pontos Positivos; Pontos de Melhoria;
Conclusão). O resumo da equipe tem 6 seções (Resumo Executivo; Notas por Colaborador com ranking
e gráfico de atendimentos; Médias por Critério; Destaques; Pontos de Melhoria; Conclusão).
Tudo isso já é montado pelos scripts a partir dos JSONs — não montar docx na mão.

Os 9 critérios e pesos (planilha da coordenação): SLA 16,5% · Prazos 8,5% · Empatia 11,11% ·
Clareza/Canais 11,11% · Erros 8,5% · Soluções Definitivas 16,5% · Ética 8,5% ·
Transformar o "Não" 11,11% · Escrita 8,5%. A média é normalizada pela soma dos pesos.

Faixas de desempenho: 9,0+ Excelente · 8,0–8,9 Muito Bom · 7,0–7,9 Bom · 6,0–6,9 Regular · <6,0 Abaixo do Esperado.
## Exemplos reais em TODOS os critérios (obrigatório)

O relatório individual traz, na seção de **cada um dos 9 critérios**, **até 3 exemplos reais** — cada
um com **cliente, data, hora** e o trecho da mensagem. Prioriza o caso que **puxou a nota para baixo**
(ex.: no SLA, os atendimentos que estouraram o prazo primeiro; em Prazos, os termos vagos; em Gírias,
as gírias detectadas). Gerado pelo `analisar.py` (campo `evidencias` de cada critério, coletado em
`EX[i]`) e desenhado pelo `build_report.py`. Regras:

- **Nunca inventar:** critério sem ocorrência registra "Sem ocorrência específica registrada no
  período"; critério "Não avaliado" não recebe caixa.
- **SLA (crit. 1):** o exemplo mostra cliente, dia, hora da 1ª mensagem → hora da 1ª resposta do
  colaborador e o tempo em minutos úteis (com marca "acima do limite de 2h" / "dentro do prazo").
- **Ética (crit. 7):** é baseline fixo em 10 (sem detecção automática) → mostra nota de baseline, não
  um exemplo. Se a coordenação quiser que avalie de fato, definir a evidência objetiva a detectar.
- **Não altera nenhuma nota:** os exemplos são só evidência; as notas continuam calculadas igual
  (verificado: mesma transcrição → notas idênticas).


## Verificação antes de entregar (checklist)

- `analisar.py` rodou sem erro (travas de integridade e de parse passaram)?
- Todos os nomes vieram do bloco de integridade (nenhum criado, separado ou renomeado)?
- O `empacotar.py` rodou sem erro e a **conferência final que ele imprime** passou (contagem de
  relatórios batendo com o resumo da unidade, e um "OK" por pacote)?
- Os zips foram montados **pelo script** — nenhum zip feito à mão?
- O **logo Altocon** aparece no topo da 1ª página? (arquivo `scripts/../assets/logo_altocon.png` presente)
- O visual da 1ª página confere com o modelo (página branca, navy/dourado)?
- Nenhuma nota ou texto foi alterado fora dos scripts?
- Rodar `analisar.py` de novo sobre a mesma transcrição produz JSONs idênticos (`diff -r` limpo)?
