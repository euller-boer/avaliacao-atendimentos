# Sistema de Avaliação de Atendimentos — Altocon Contabilidade

Documentação do sistema que lê os atendimentos do **Gestta Messenger** e gera os relatórios de
desempenho da equipe. Atualizado em **15/07/2026**.

---

## 1. Visão geral

O sistema é um **pipeline de dois agentes de IA**, disparado por um aplicativo de janela no Windows:

```
  App (janela)  →  Agente de LEITURA  →  Agente de ANÁLISE  →  .zip com PDFs
   unidade          lê o Gestta e         lê a transcrição      1 relatório por
   colaboradores    exporta 1 arquivo     e calcula as notas    colaborador +
   período          de transcrição        por script            Resumo da Equipe
```

**Ponto essencial:** o app é só a "casca". Quem lê as conversas e julga os critérios é a **IA
(Claude Code)** — não existe executável que faça isso sozinho. O terminal que abre ao clicar em
"Iniciar" é o Claude trabalhando (e onde se confirma a seleção, faz login no Gestta e acompanha).

---

## 2. As duas unidades

Analisadas **SEPARADAMENTE** — uma por execução, cada uma com seu Resumo da Equipe.

- **Taquaritinga** (lista fixa): Ana Chueco, Julia Ribeiro, Leonardo Chueco, Natália Tiesi,
  Priscila de Pietro, Tiago Chueco.
- **Monte Alto**: todos os demais operadores do Gestta.

---

## 3. A transcrição (saída da leitura)

Um **único arquivo** por execução, com todos os colaboradores selecionados:
`transcricao_equipe_<unidade>_<sufixo-do-período>.txt`

Estrutura obrigatória (formato rígido — o `analisar.py` aborta se não bater):

```
=== CONFERÊNCIA DE INTEGRIDADE ===
Histórico de atendimentos da equipe <Unidade>
Período: <MM/AAAA | DD/MM/AAAA | DD/MM/AAAA a DD/MM/AAAA>
Gerado em: dd/mm/aaaa
totalDocs (API): <N>
Atendimentos lidos: <N>        <- tem de ser IGUAL ao totalDocs
Falhas após retentativas: 0
<Nome>: <N> atendimentos, <M> mensagens      (uma linha por colaborador)
=== FIM DA CONFERÊNCIA ===

### COLABORADOR: <NOME EM MAIÚSCULAS>
=== Atendimento <i>/<N> | ID: <id> ===
Contato: <cliente>
Transferência: SIM em dd/mm/aaaa, hh:mm:ss   (ou NÃO)
[dd/mm/aaaa, hh:mm:ss] ATENDENTE|CLIENTE (<autor>) [NOTA INTERNA / anexo]: <conteúdo>
```

**Fonte congelada:** gerada uma vez, conferida e reutilizada em todas as análises do período. Nunca
regenerar entre rodadas — era isso que fazia o nº de atendimentos mudar de uma rodada para outra.

---

## 4. Os três períodos

| Tipo | Regime | `Período:` no cabeçalho | Sufixo dos arquivos |
|---|---|---|---|
| **Mês** | avaliação **FORMAL** | `06/2026` | `06-2026` |
| **Semana** (seg–dom) | **acompanhamento** | `01/06/2026 a 07/06/2026` | `01-06-2026_a_07-06-2026` |
| **Dia** | **acompanhamento** | `05/06/2026` | `05-06-2026` |

> **Semana/Dia não são avaliação formal.** A amostra é pequena e as notas oscilam demais (2
> atendimentos no dia → um atraso derruba o SLA para 50%). O `analisar.py` insere sozinho um aviso
> de amostra reduzida nesses relatórios. Decisão pendente: se um dia virarem avaliação formal, basta
> remover o aviso.

---

## 5. A análise é 100% determinística

**O modelo não pontua nem redige nada que afete o relatório.** Todas as notas, contagens,
justificativas e textos saem do `scripts/analisar.py`, calculado sobre a transcrição congelada.
Mesma transcrição → JSONs idênticos → relatórios idênticos.

Motivo: nas versões antigas os critérios qualitativos eram julgados pelo modelo e **cada rodada dava
uma nota diferente** (Clareza divergiu em 23 de 23 colaboradores entre duas rodadas de junho/2026).
Qualquer "ajuste manual" de nota fora do script reintroduz a divergência.

### Os 9 critérios e pesos (planilha da coordenação)

| # | Critério | Peso |
|---|---|---|
| 1 | Tempo de Início do Atendimento (SLA) | 16,5% |
| 2 | Gestão de Prazos e Comunicação Assertiva | 8,5% |
| 3 | Empatia e Escuta Ativa | 11,11% |
| 4 | Clareza, Orientação Técnica e Uso de Canais | 11,11% |
| 5 | Transparência, Sinceridade e Tratamento de Erros | 8,5% |
| 6 | Postura Contínua e Soluções Definitivas | 16,5% |
| 7 | Ética e Transparência Sempre | 8,5% |
| 8 | Transformar o "Não" em Busca por Soluções | 11,11% |
| 9 | Coerência na Escrita, Gírias e Informalidades | 8,5% |

Nota final = **média ponderada normalizada** pela soma dos pesos (critérios "Não avaliado" ficam
fora). Faixas: 9,0+ Excelente · 8,0–8,9 Muito Bom · 7,0–7,9 Bom · 6,0–6,9 Regular · <6,0 Abaixo.

### Regras específicas
- **SLA (coordenação, 14/07/2026):** conta **minutos úteis** (07:30–18:00, seg–sex, feriados
  nacionais descontados); limite 120 min úteis. O cronômetro só para na 1ª mensagem **do próprio
  colaborador** — resposta da triagem não encerra a contagem.
- **Critério 9 (gírias):** o relatório traz **até 3 exemplos reais** — cliente · data · hora — com o
  trecho da mensagem e o termo detectado. Sem gírias no período: "Sem ocorrência registrada".
- **Amostra insuficiente:** colaborador sem mensagens no período = "Não avaliado", fora da média e
  do ranking (não é punido).
- **Veracidade:** nenhuma nota, exemplo ou feedback é inventado — tudo auditável na transcrição.

---

## 6. Entrega

- 1 relatório `.docx` por colaborador + 1 Resumo da Equipe;
- convertidos para **PDF** (LibreOffice);
- entregues em **um `.zip` na pasta Downloads**: `Análise de atendimento de <Cidade> - <MM-AAAA>`;
- só os PDFs entram no zip (os `.docx` são intermediários).

---

## 7. Onde cada peça vive (no PC)

| Peça | Caminho |
|---|---|
| Ícone | `Área de Trabalho\Avaliacao de Atendimentos.lnk` |
| App (janela) | `%USERPROFILE%\.claude\avaliacao-atendimentos-app.ps1` (+ `.vbs` que o abre sem console) |
| Logo | `%USERPROFILE%\.claude\assets\altocon-logo.png` |
| Skills | `%USERPROFILE%\.claude\skills\` (orquestrador, leitura, análise + scripts Python) |
| Resultado | `Downloads\` (o `.zip` de PDFs) |

---

## 8. Armadilhas conhecidas (aprendidas na prática)

1. **A análise existe em DUAS cópias** (CLI e app desktop do Claude) e elas **divergem**. Toda
   alteração precisa ser aplicada nas duas — foi o que causou o "a mudança não ficou salva".
2. **`%APPDATA%\Roaming\Claude` é um junction** para `%LOCALAPPDATA%\Packages\Claude_...`. Não use
   `cd` do bash nesse caminho; passe o caminho absoluto direto ao Python.
3. **WinForms:** radio buttons no mesmo container viram **um grupo só**. Unidade e Período precisam
   de painéis separados — senão marcar "Semana" desmarca "Taquaritinga".
4. **PowerShell 5.1:** o `.ps1` precisa ser salvo em **UTF-8 COM BOM**, senão os acentos quebram.
5. **`.cmd`/`.bat`:** salvar em UTF-8 **SEM** BOM (com BOM o cmd engasga na 1ª linha).
6. **Windows Terminal:** não passe `--title` com espaços via `Start-Process` — ele quebra o comando.
   O título vem do `title` dentro do próprio `.cmd`.
7. **Não é um executável.** Compartilhar exige instalar o pacote na outra máquina + Claude Code
   logado + Python + LibreOffice + extensão do Chrome + acesso ao Gestta.
