# Contexto permanente — Altocon Contabilidade

## Quem é o usuário e como falar

- Trabalha no **Departamento Pessoal / RH da Altocon Contabilidade** (unidades **Taquaritinga** e
  **Monte Alto**). Não é da área técnica.
- **Responda sempre em português (pt-BR)**, em linguagem simples. Explique o "porquê" das coisas
  técnicas sem jargão; se algo não for possível, diga com franqueza e ofereça a alternativa real.

## Regras inegociáveis

- **Nunca inventar dado.** Em qualquer relatório, análise ou documento: toda nota, número, exemplo,
  data, nome de cliente ou trecho precisa ter respaldo na fonte real (transcrição, PDF, sistema).
  Se não houver o dado, registrar "sem ocorrência" / "não avaliado" — jamais preencher por
  suposição. Isso vale especialmente porque esses documentos avaliam **pessoas**.
- **Testar antes de dizer que funciona.** Rodar o script/app de verdade e mostrar a evidência.
  Nada de "deve funcionar".

## Convenções de entrega

- Arquivos finais vão para a pasta **Downloads**.
- Documentos que saem para cliente/coordenação: entregar em **PDF** (o `.docx` é intermediário).
- Identidade visual Altocon: **navy `#16243F`** e **dourado `#C6A55C`**; logo em
  `~/.claude/assets/altocon-logo.png`.

## Sistemas que já existem (usar, não reimplementar)

Antes de construir algo novo, verifique as skills instaladas em `~/.claude/skills/`:

- **Avaliação de Atendimentos** (`avaliacao-atendimentos-completa` + `agente-leitura-conversas*` +
  `agente-analise-atendimento-corrigido`) — lê o Gestta e gera os relatórios da equipe.
  App de janela: `~/.claude/avaliacao-atendimentos-app.ps1` (ícone na Área de Trabalho).
  Documentação completa: `OneDrive\Documentos\Avaliacao de Atendimentos - Backup\`.
- **Gerador de CCT** (`gerador-documentos-cct`) — informativo e resumo executivo de convenção coletiva.

> **A análise de atendimentos existe em DUAS cópias que divergem:** a do CLI
> (`~/.claude/skills/...`, usada pelo app da Área de Trabalho) e a do app desktop do Claude
> (`%APPDATA%\Roaming\Claude\local-agent-mode-sessions\skills-plugin\<ids>\skills\...`).
> **Toda alteração precisa ser aplicada nas DUAS** e testada rodando o script sobre uma transcrição
> real — senão a mudança "não fica salva" quando o usuário roda pelo outro caminho.

## Armadilhas deste ambiente Windows (já custaram tempo)

- **`.ps1`** precisa ser salvo em **UTF-8 COM BOM** (senão o PowerShell 5.1 quebra os acentos).
- **`.bat` / `.cmd`** precisam ser **UTF-8 SEM BOM** (com BOM o `cmd` engasga na primeira linha).
- **`%APPDATA%\Roaming\Claude` é um junction** para `%LOCALAPPDATA%\Packages\Claude_...`. Não usar
  `cd` do bash nesse caminho — passar o caminho absoluto direto ao Python.
- **Windows Terminal:** não passar `--title` com espaços via `Start-Process` (quebra o comando); o
  título vem do `title` dentro do próprio `.cmd`.
- **WinForms:** radio buttons no mesmo container viram **um grupo só** — grupos diferentes precisam
  de painéis separados.
- Testar menu de terminal alimentando `stdin` **não funciona** (`chcp 65001` quebra a leitura) —
  testar a lógica isolada, não o menu inteiro.
