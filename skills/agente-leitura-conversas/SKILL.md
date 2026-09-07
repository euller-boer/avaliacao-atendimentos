---
name: agente-leitura-conversas
description: >
  Agente de leitura de conversas. Lê e exporta TODO o histórico de atendimentos (conteúdo
  completo das conversas) dos colaboradores de uma unidade, em um período, no Gestta Messenger
  da Altocon, e gera a TRANSCRIÇÃO CONGELADA no formato exato do agente de análise — incluindo
  o carimbo de transferência da triagem usado pelo SLA. Use quando o usuário disser:
  "ler os atendimentos do mês", "ler todas as conversas de um colaborador",
  "exportar o histórico de atendimentos", "guardar as conversas do Gestta",
  "baixar os atendimentos da Natália", "preparar dados para a análise de atendimento".
tools:
  - mcp__Claude_in_Chrome__list_connected_browsers
  - mcp__Claude_in_Chrome__select_browser
  - mcp__Claude_in_Chrome__tabs_context_mcp
  - mcp__Claude_in_Chrome__navigate
  - mcp__Claude_in_Chrome__javascript_tool
  - mcp__Claude_in_Chrome__read_network_requests
---

# Agente de Leitura de Conversas — Gestta Messenger (v2, com carimbo de transferência)

Lê o conteúdo completo das conversas direto pela API do Gestta (mesmo dado do "olhinho") e
exporta a **transcrição .txt congelada** — entrada única do `agente-analise-atendimento-corrigido`.
O formato é RÍGIDO: o `analisar.py` valida o cabeçalho e ABORTA se qualquer contagem não bater.

> Novidade v2: cada atendimento traz a linha `Transferência:` com o carimbo do repasse da
> triagem. O SLA da análise INICIA nesse carimbo para atendimentos transferidos. Sem essa
> linha, o atendimento transferido é tratado como iniciado pelo cliente.

## Pré-requisitos

1. Chrome conectado (extensão Claude in Chrome). Se houver mais de um navegador, pergunte qual usar.
2. Aba aberta e logada em https://app.gestta.com.br/messenger-dashboard/#/attendance-history
   Se cair no login, peça ao usuário para logar (NUNCA digite a senha você mesmo).
3. Token: `localStorage["user-jwt"]` vem JSON-STRINGIFICADO (com aspas). Use
   `JSON.parse(localStorage.getItem('user-jwt'))` no header Authorization — usar o valor cru dá 401.

## Passo 1 — Listar TODOS os atendimentos do período (com verificação)

GET paginado: `https://api.gestta.com.br/messenger-dashboard-v2/attendances?start=<ISO>&end=<ISO>&sort=-finished_at&limit=50&page=<N>`
(ex.: start=2026-06-01T03:00:00.000Z, end=2026-07-01T02:59:59.999Z para 06/2026, fuso -03).

### Períodos aceitos: MÊS, SEMANA/INTERVALO ou DIA

O período pode ser de três tipos. Em todos, `start` = 00:00:00 do PRIMEIRO dia e `end` = 00:00:00 do
dia SEGUINTE ao último (exclusivo), convertidos de America/São_Paulo (-03) para ISO UTC:

| Tipo | Pedido | start .. end (exemplo) | `Período:` no cabeçalho | Sufixo do arquivo |
|---|---|---|---|---|
| Mês | "junho/2026" | 2026-06-01T03:00:00Z .. 2026-07-01T03:00:00Z | `06/2026` | `06-2026` |
| Semana/intervalo | "01/06 a 07/06/2026" | 2026-06-01T03:00:00Z .. 2026-06-08T03:00:00Z | `01/06/2026 a 07/06/2026` | `01-06-2026_a_07-06-2026` |
| Dia | "05/06/2026" | 2026-06-05T03:00:00Z .. 2026-06-06T03:00:00Z | `05/06/2026` | `05-06-2026` |

> O `Período:` do cabeçalho DEVE seguir **exatamente** o formato da tabela: o `analisar.py` usa ele
> para rotular o relatório e para decidir o regime — **mês = avaliação formal**; **dia/intervalo =
> acompanhamento** (o relatório sai com aviso de amostra reduzida). Formato fora do padrão = rótulo "?/?".

REGRAS APRENDIDAS (obrigatórias):
- Buscar páginas com pool de até 4-5 workers, MAS com até 4 retentativas por página (backoff
  ~800ms) e guardando por número de página. Páginas se perdem silenciosamente em paralelo.
- Ao final, CONFERIR `soma(docs) == totalDocs` da página 1. Se não bater, rebuscar as páginas
  faltantes antes de prosseguir. NUNCA seguir com lista parcial.
- Rodadas longas de JS devem rodar em IIFE async em background gravando progresso em
  `window.__prog` (retornos síncronos longos estouram o timeout de 45s da ferramenta).

## Passo 2 — Selecionar os colaboradores

Agrupe os docs por `company_user_data._id`/`name` e apresente a lista (nome + nº de atendimentos)
para o usuário marcar quem entra (ex.: unidade Monte Alto = todos menos a lista fixa de
Taquaritinga: Ana Chueco, Julia Ribeiro, Leonardo Chueco, Natália Tiesi, Priscila de Pietro,
Tiago Chueco). ATENÇÃO: usuário com nome alterado no mês (mesmo `_id`, dois nomes — ex.
"Eduarda Borges"/"Maria Eduarda") é UM colaborador: unificar sob o nome atual e registrar a
observação no cabeçalho.

### DESLIGADOS — nunca marcar

Saíram do escritório e **não entram em avaliação nenhuma**, mesmo aparecendo como operador no
Gestta com atendimentos no período:

| Colaborador(a) | Unidade | Desligamento | Regra |
|---|---|---|---|
| Graziele Anselmo | Monte Alto | 08/08/2026 | **Total** — nunca marcar, em período nenhum |
| Graziela dos Anjos | Monte Alto | 24/08/2026 | **Total** — nunca marcar, em período nenhum |
| Flavio Rosato | Monte Alto (era da equipe da Laysa) | 24/08/2026 | **Total** — nunca marcar, em período nenhum (era "Corte" até 01/09/2026; o usuário mudou para Total nessa data) |

> **As duas regras não são a mesma coisa.** "Total" apaga a pessoa da avaliação mesmo onde ela
> ainda tinha atendimento. "Corte" preserva o que a pessoa fez até sair, e só para de trazer o
> nome em períodos que começam depois da saída. **Hoje os três da tabela são "Total"** — ninguém
> está em "Corte"; a regra fica de pé para o próximo caso.
> Na dúvida, pergunte ao usuário antes de tirar alguém de um período já trabalhado.

⚠️ São **duas pessoas diferentes**, não é o mesmo nome repetido — confira a grafia (Graziel**e**
Anselmo × Graziel**a** dos Anjos) antes de tirar alguém da lista.

A exclusão tem que ser feita **aqui, antes de gerar a transcrição**: o bloco de integridade é
montado com quem foi marcado, então `totalDocs` e `Atendimentos lidos` já saem certos. Tirar a
pessoa depois, editando a transcrição pronta, faz o `analisar.py` abortar na trava de contagem.

Efeito colateral esperado e correto: os carimbos "Atendimento transferido por X para
&lt;desligada&gt;" saem junto, então quem transferiu perde esses casos na base do critério 6.

A lista de **Monte Alto é por EXCLUSÃO** (todos que não são de Taquaritinga), então quem saiu
continua sendo puxado automaticamente enquanto tiver atendimento no período — tem que ser tirado
na mão, nesta seleção.

## Passo 3 — Ler as conversas (o "olhinho") com retentativas

GET: `https://api.gestta.com.br/messenger-dashboard-v2/overview/attendance/<company_contact._id>/<attendance._id>/message-history`
(1º segmento = _id do CONTATO; 2º = _id do atendimento; inverter dá 400).

Pool de 6-8 workers, até 4 retentativas por atendimento, exigir 0 falhas ao final
(3.910 atendimentos ≈ 4 min). Campos por mensagem: `type` (INBOUND/OUTBOUND), `content_type`,
`content`, `author`, `internal_message`, `received_at`/`created_at`, `attendance_info`.

## Passo 4 — Detectar transferência

O atendimento foi RECEBIDO POR TRANSFERÊNCIA quando a 1ª mensagem (ordenada por data) tem
`attendance_info.type === 'TRANSFER'`. O carimbo do repasse é o `started_at` do próprio doc
(confere com o horário da 1ª mensagem). Não use os campos `transferred/transfer/origin` da
lista — não existem mais na resposta.

## Passo 5 — Gerar a transcrição congelada (formato EXATO)

Gerar DENTRO da página e disparar download (`Blob` + `<a download>`) — nunca retornar o
conteúdo pelo canal de texto. Nome: `transcricao_equipe_<unidade>_<sufixo-do-período>.txt`
(sufixo conforme a tabela do Passo 1: `06-2026`, `01-06-2026_a_07-06-2026` ou `05-06-2026`).
Datas em America/Sao_Paulo, timestamps SEMPRE com segundos e vírgula: `dd/mm/aaaa, hh:mm:ss`.

Cabeçalho (bloco de integridade — as linhas por colaborador DEVEM estar nas primeiras 60 linhas):

```
=== CONFERÊNCIA DE INTEGRIDADE ===
Histórico de atendimentos da equipe <Unidade>
Período: <MM/AAAA  |  DD/MM/AAAA  |  DD/MM/AAAA a DD/MM/AAAA>   (formato EXATO do Passo 1)
Gerado em: dd/mm/aaaa
totalDocs (API): <N>
Atendimentos lidos: <N>
Falhas após retentativas: 0
Obs.: <observações, ex. unificação de usuário duplicado>
<Nome>: <N> atendimentos, <M> mensagens      (uma linha por colaborador)
=== FIM DA CONFERÊNCIA ===
```

Corpo, por colaborador (nome da seção em MAIÚSCULAS; atendimentos ordenados por finished_at):

```
### COLABORADOR: <NOME EM MAIÚSCULAS>
=== Atendimento <i>/<N> | ID: <attendance._id> ===
Contato: <company_contact.name>
Transferência: SIM em dd/mm/aaaa, hh:mm:ss      (ou: Transferência: NÃO)
[dd/mm/aaaa, hh:mm:ss] ATENDENTE|CLIENTE (<author>) [NOTA INTERNA / <tipo-anexo>]: <conteúdo>
```

Regras de escrita:
- Mensagens ordenadas por `received_at||created_at`; direção ATENDENTE=OUTBOUND, CLIENTE=INBOUND.
- Autor sempre entre parênteses (fallback: nome do colaborador p/ OUTBOUND, contato p/ INBOUND).
- Tags entre colchetes: `NOTA INTERNA` e/ou `content_type` ≠ CHAT, unidas por " / ".
- Conteúdo multilinha: linhas de continuação que comecem com `===`, `###`, `---` ou
  `[dd/mm/aaaa, ` recebem um espaço à frente (senão quebram o parser da análise).
- `M mensagens` do cabeçalho = TOTAL de mensagens do colaborador (internas incluídas) e DEVE
  bater com o corpo — o analisar.py aborta se divergir.

## Congelamento

A transcrição do período é gerada UMA vez, conferida e reutilizada em todas as análises e
reanálises. Salvar na pasta Downloads do usuário. Nunca regenerar entre rodadas da análise;
regenerar apenas se a coordenação mudar o escopo (novo campo, outro período, outra unidade).
