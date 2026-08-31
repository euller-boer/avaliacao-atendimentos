# Avaliação de Atendimentos — Altocon Contabilidade

Sistema do Departamento Pessoal da Altocon (unidades **Taquaritinga** e **Monte Alto**) que lê
os atendimentos do **Gestta Messenger**, avalia o desempenho mensal de cada colaborador pelos
**9 critérios do Manual** e entrega um relatório por pessoa mais o resumo da equipe.

> ⚠️ **Repositório privado.** O código traz nomes reais de colaboradores e de clientes nos
> comentários que explicam cada regra. Não tornar público sem antes anonimizar tudo.

## Como está organizado

| Pasta | O que é |
|---|---|
| `skills/avaliacao-atendimentos-completa` | **Orquestrador.** Roda leitura + análise de ponta a ponta para a equipe inteira, numa execução só. É por aqui que se começa. |
| `skills/agente-leitura-conversas-corrigido` | Lê o Gestta e gera a **transcrição congelada** (inclui o carimbo de transferência da triagem, que o SLA usa). |
| `skills/agente-leitura-conversas` | Versão anterior da leitura, mantida como referência. |
| `skills/agente-analise-atendimento-corrigido` | **O coração.** `analisar.py` aplica as réguas dos 9 critérios sobre a transcrição; `build_report.py` desenha o .docx; `build_team_summary.py` faz o resumo da equipe. |
| `app/` | O app de janela da Área de Trabalho (`.ps1` + `.vbs`) e os scripts de envio dos rascunhos de e-mail. |
| `docs/` | Documentação completa do sistema e o contexto permanente usado pelo Claude. |
| `assets/` | Logo e identidade visual (navy `#16243F`, dourado `#C6A55C`). |

## Regras que valem para qualquer mudança aqui

1. **Nunca inventar dado.** Toda nota, exemplo, data e trecho citado num relatório precisa ter
   respaldo na transcrição real. Sem dado, registrar "sem ocorrência" — nunca supor. Esses
   documentos avaliam **pessoas**.
2. **A análise é determinística.** Rodar duas vezes sobre a mesma transcrição tem que dar
   exatamente o mesmo resultado. Nota sai de script, não de julgamento.
3. **Testar de verdade antes de dizer que funciona** — rodar sobre uma transcrição real e mostrar
   a evidência.
4. **Toda mudança de régua** precisa ser registrada no arquivo de decisões (OneDrive) junto com
   o motivo e a data.
5. **O e-mail nunca é enviado sozinho.** O sistema só deixa o rascunho pronto; clicar em "Enviar"
   é sempre do usuário.

## Armadilhas do ambiente Windows

- `.ps1` precisa ser salvo em **UTF-8 COM BOM** (senão o PowerShell 5.1 quebra os acentos).
- `.bat` / `.cmd` precisam ser **UTF-8 SEM BOM** (com BOM o `cmd` engasga na primeira linha).
- O token JWT do Gestta é lido do navegador na hora, **nunca fica salvo em arquivo** — e o prefixo
  do header `Authorization` já mudou sozinho antes; ao tomar 401, testar os prefixos antes de
  culpar a sessão.
- Conferir PDF **pela imagem**, não por texto extraído: os símbolos ✓ ✗ ⚠ aparecem na página mas
  somem no `pdftotext`.

## Onde isso roda de verdade

O app da Área de Trabalho usa a cópia em `C:\Users\atend\.claude\`. Este repositório é o espelho
versionado dela: para restaurar, é só copiar `skills/` e `app/` de volta para lá.
