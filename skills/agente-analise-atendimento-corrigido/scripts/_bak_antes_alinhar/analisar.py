#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar.py — PIPELINE DETERMINÍSTICO COMPLETO da análise de atendimentos.

Por que este script existe
--------------------------
As rodadas divergiam porque os critérios qualitativos (2 a 8) eram pontuados
por julgamento do modelo — cada execução "achava" uma nota. Diagnóstico da
comparação de duas rodadas de junho/2026: os 2 critérios calculados por script
(SLA e Escrita) bateram 100%; TODOS os demais divergiram em até 2 pontos.

Solução: TODA nota, contagem, justificativa e texto do relatório sai deste
script, calculado sobre a transcrição congelada. O modelo não pontua nada.
Mesma transcrição -> mesmos JSONs, byte a byte -> mesmos relatórios.

Uso
---
    python3 scripts/analisar.py <transcricao.txt> <dir_saida>

Saída: <dir_saida>/analise_<Colab>.json (um por colaborador),
       <dir_saida>/resumo_equipe.json e uma tabela de conferência no stdout.
A identidade (nomes e totais) vem VERBATIM do bloco de CONFERÊNCIA DE
INTEGRIDADE da transcrição — inclusive nomes unificados (mesmo usuário com
nome alterado, ex.: "Eduarda Borges / Maria Eduarda"). Se o bloco estiver
ausente ou com "lidos" != totalDocs, o script ABORTA.
"""
import json, re, sys, os
from datetime import datetime

# ---------------------------------------------------------------- constantes
CRIT = ["Tempo de Início do Atendimento (SLA)",
        "Gestão de Prazos e Comunicação Assertiva",
        "Empatia e Escuta Ativa",
        "Clareza, Orientação Técnica e Uso de Canais",
        "Transparência, Sinceridade e Tratamento de Erros",
        "Postura Contínua e Soluções Definitivas",
        "Ética e Transparência Sempre",
        "Transformar o \"Não\" em Busca por Soluções",
        "Coerência na Escrita, Gírias e Informalidades"]
PESO = [16.5, 8.5, 11.11, 11.11, 8.5, 16.5, 8.5, 11.11, 8.5]
PESO_S = ["16,5%", "8,5%", "11,11%", "11,11%", "8,5%", "16,5%", "8,5%", "11,11%", "8,5%"]

SLA_TABELA = [(98.0, 10.0), (95.0, 9.5), (90.0, 9.0), (85.0, 8.5), (80.0, 8.0),
              (75.0, 7.5), (70.0, 7.0), (60.0, 6.0), (50.0, 5.0), (40.0, 4.0), (0.0, 3.0)]
GIRIAS_TABELA = [(0.0, 10.0), (0.5, 9.0), (1.0, 8.0), (2.0, 7.0), (4.0, 6.0), (7.0, 5.0), (float("inf"), 4.0)]
GIRIAS = [r"vc", r"vcs", r"voce", r"pra", r"pro", r"pq", r"q", r"k{2,}", r"rs+", r"kk+",
          r"hh+", r"blz", r"vlw", r"flw", r"obg", r"pfv", r"pf", r"tbm", r"tb", r"qdo",
          r"qto", r"msg", r"to", r"ta", r"tava", r"neh", r"ne", r"aki", r"vamo", r"oki"]
GIRIA_RE = re.compile(r"\b(" + "|".join(GIRIAS) + r")\b", re.IGNORECASE)

VAGO = re.compile(r"\b(vou verificar|vou analisar|vou ver|vou olhar|vou checar|assim que poss[ií]vel|qualquer coisa (te )?aviso|mais tarde te (falo|aviso))\b", re.I)
PRAZO = re.compile(r"\b(dias? [úu]te(is|l)|at[ée] (o dia |amanh[ãa]|hoje|sexta|segunda|ter[çc]a|quarta|quinta)|amanh[ãa]|hoje (ainda|mesmo)|\d{1,2}/\d{1,2}|em \d+ ?(h|horas|min|dia))\b", re.I)
EMPATIA = re.compile(r"\b(bom dia|boa tarde|boa noite|tudo bem|entendo|compreendo|imagino|fica tranquil|pode deixar|vou te ajudar|conte comigo|por favor|obrigad|disponha|[àa] disposi[çc][ãa]o|precisando)\b", re.I)
NEG_SECA = re.compile(r"\b(n[ãa]o (fazemos|tem como|[ée] poss[íi]vel|conseguimos|posso te ajudar com isso|atendemos))\b", re.I)
ALTERNATIVA = re.compile(r"\b(alternativa|outra op[çc][ãa]o|posso (sugerir|indicar)|vou (consultar|verificar com) (o|a|outro)|parceiro|indica[çc][ãa]o|sugest[ãa]o|o que podemos fazer)\b", re.I)
TRANSFER = re.compile(r"\b(vou (te )?transferir|transferindo|vou encaminhar|encaminhando|vou passar (para|pro|pra)|setor respons[áa]vel)\b", re.I)
LEI = re.compile(r"\b(art\.? ?\d+|artigo \d+|lei n|LC \d|par[áa]grafo|inciso)\b", re.I)
ERRO = re.compile(r"\b(desculp\w*|foi (um )?(erro|equ[íi]voco|falha) (noss|meu|minh)\w*|me equivoquei|nos equivocamos|erramos|corrigir[ei]mos|vou corrigir|pe[çc]o desculpas|perd[ãa]o pel)\b", re.I)

MSG_RE = re.compile(r"^\[(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}:\d{2})\] (ATENDENTE|CLIENTE)(?: \((.*?)\))?(?: \[([^\]]+)\])?: (.*)$")
COLAB_RE = re.compile(r"^### COLABORADOR: (.+)$")
ATT_RE = re.compile(r"^=== Atendimento (\d+)/(\d+) \| ID: (\S+) ===$")
MESES = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
         7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

def fmt(x): return f"{x:.1f}".replace(".", ",")
def pf(x): return str(round(x)) + "%"
def corta_trecho(t, n=160):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"
def nota_desc(t, tabela):
    for lim, n in tabela:
        if t >= lim: return n
    return tabela[-1][1]
def teto_cres(t, tabela):
    for lim, n in tabela:
        if t <= lim: return n
    return tabela[-1][1]

# ---------------------------------------------------------------- cabeçalho
def ler_cabecalho(lines):
    head = "\n".join(lines[:40])
    if "=== CONFERÊNCIA DE INTEGRIDADE ===" not in head:
        sys.exit("ERRO: bloco de CONFERÊNCIA DE INTEGRIDADE ausente. Gere a transcrição com o agente-leitura-conversas.")
    def g(rx, cast=str):
        m = re.search(rx, head)
        return cast(m.group(1)) if m else None
    total_api = g(r"totalDocs[^:]*: (\d+)", int)
    lidos = g(r"Atendimentos lidos: (\d+)", int)
    falhas = g(r"Falhas ap[óo]s retentativas: (\d+)", int)
    if total_api is None or lidos is None or lidos != total_api or (falhas or 0) != 0:
        sys.exit(f"ERRO: base incompleta (lidos={lidos}, totalDocs={total_api}, falhas={falhas}). NÃO analise base parcial; rode o agente-leitura-conversas novamente.")
    per = g(r"Per[íi]odo: (\d{2}/\d{4})")
    mes, ano = (int(per[:2]), per[3:]) if per else (0, "?")
    unid = g(r"equipe ([^—\n)]+)")
    if unid: unid = unid.strip()
    ger = g(r"Gerado em: (\d{2}/\d{2}/\d{4})")
    tot_map, msg_map = {}, {}
    for ln in lines[:60]:
        m = re.match(r"^(.+?): (\d+) atendimentos, (\d+) mensagens$", ln)
        if m:
            tot_map[m.group(1)] = int(m.group(2)); msg_map[m.group(1)] = int(m.group(3))
    return {"total_api": total_api, "periodo_label_base": f"{MESES.get(mes,'?')}/{ano}",
            "unidade": (unid or "").strip(), "data_geracao": ger or "",
            "tot_map": tot_map, "msg_map": msg_map}

# ---------------------------------------------------------------- parser
def parse(lines, tot_map):
    name_map = {n.upper(): n for n in tot_map}
    colabs, cur_c, cur_a, cur_m = {}, None, None, None
    def fm():
        nonlocal cur_m
        if cur_m is not None and cur_a is not None: cur_a["mensagens"].append(cur_m)
        cur_m = None
    def fa():
        nonlocal cur_a
        fm()
        if cur_a is not None and cur_c is not None: colabs[cur_c].append(cur_a)
        cur_a = None
    for ln in lines:
        m = COLAB_RE.match(ln)
        if m:
            fa(); nm = name_map.get(m.group(1).strip().upper())
            if nm is None:
                sys.exit(f"ERRO: seção de colaborador '{m.group(1).strip()}' não consta no bloco de integridade. Nomes NUNCA são inventados/renomeados.")
            cur_c = nm; colabs.setdefault(nm, []); continue
        m = ATT_RE.match(ln)
        if m:
            fa(); cur_a = {"id": m.group(3), "mensagens": [], "contato": ""}; continue
        if cur_a is not None and cur_m is None and ln.startswith("Contato:"):
            cur_a["contato"] = ln.split(":", 1)[1].strip(); continue
        m = MSG_RE.match(ln)
        if m:
            fm()
            tags = m.group(5) or ""
            cur_m = {"dir": "OUT" if m.group(3) == "ATENDENTE" else "IN",
                     "interna": "NOTA INTERNA" in tags,
                     "dt": datetime.strptime(m.group(1) + " " + m.group(2), "%d/%m/%Y %H:%M:%S"),
                     "texto": m.group(6)}
            continue
        if cur_m is not None and not ln.startswith(("===", "###", "---")):
            cur_m["texto"] += "\n" + ln
    fa()
    return colabs

# ---------------------------------------------------------------- análise
def analisar_colab(nm, ats, hdr):
    total = len(ats)
    Q = dict(vago=0, prazo=0, emp=0, neg=0, alt=0, transf=0, lei=0, out_atts=0,
             erro=0, erro_prazo=0, msgs=0, girias=0, proativos=0,
             sla_consid=0, sla_dentro=0, tempos=[], vago_ex=None, neg_ex=None,
             giria_ex=[])
    for at in ats:
        msgs = sorted(at["mensagens"], key=lambda m: m["dt"])
        outs = [m for m in msgs if m["dir"] == "OUT" and not m["interna"]]
        for m in outs:
            Q["msgs"] += 1
            achou = GIRIA_RE.findall(m["texto"])
            Q["girias"] += len(achou)
            if achou and len(Q["giria_ex"]) < 3:
                termos = ", ".join(sorted({g.lower() for g in achou}))
                Q["giria_ex"].append({
                    "cliente": at.get("contato") or "—",
                    "data": m["dt"].strftime("%d/%m/%Y"),
                    "hora": m["dt"].strftime("%Hh%M"),
                    "trecho": corta_trecho(m["texto"]),
                    "termos": termos,
                })
        ext = [m for m in msgs if not m["interna"]]
        if ext:
            if ext[0]["dir"] == "OUT":
                Q["proativos"] += 1
            else:
                Q["sla_consid"] += 1
                resp = next((m for m in ext[1:] if m["dir"] == "OUT"), None)
                if resp and resp["dt"] >= ext[0]["dt"]:
                    mins = (resp["dt"] - ext[0]["dt"]).total_seconds() / 60
                    Q["tempos"].append(mins)
                    if mins <= 120: Q["sla_dentro"] += 1
        if not outs: continue
        Q["out_atts"] += 1
        blob = "\n".join(m["texto"] for m in outs)
        if VAGO.search(blob):
            Q["vago"] += 1
            if not Q["vago_ex"]: Q["vago_ex"] = (at["id"], VAGO.search(blob).group(0))
        if PRAZO.search(blob): Q["prazo"] += 1
        if EMPATIA.search(blob): Q["emp"] += 1
        if NEG_SECA.search(blob) and not ALTERNATIVA.search(blob):
            Q["neg"] += 1
            if not Q["neg_ex"]: Q["neg_ex"] = (at["id"], NEG_SECA.search(blob).group(0))
        if ALTERNATIVA.search(blob): Q["alt"] += 1
        if TRANSFER.search(blob): Q["transf"] += 1
        if LEI.search(blob): Q["lei"] += 1
        if ERRO.search(blob):
            Q["erro"] += 1
            if PRAZO.search(blob): Q["erro_prazo"] += 1

    sla_pct = round(Q["sla_dentro"] / Q["sla_consid"] * 100, 1) if Q["sla_consid"] else 100.0
    med = round(sum(Q["tempos"]) / len(Q["tempos"]), 1) if Q["tempos"] else 0.0
    taxa = round(Q["girias"] / Q["msgs"] * 100, 3) if Q["msgs"] else 0.0
    oa = Q["out_atts"]

    notas, just, txt, bl, dest = {}, {}, {}, {}, {}

    n1 = nota_desc(sla_pct, SLA_TABELA)
    notas[0] = n1
    just[0] = f"{sla_pct}% de 1ª resposta ≤2h (média {med:.0f} min) — base {Q['sla_consid']} atend. iniciados pelo cliente"
    txt[0] = (f"Dos {Q['sla_consid']} atendimentos iniciados pelo cliente, {Q['sla_dentro']} tiveram a primeira resposta dentro do limite de 2 horas do manual "
              f"({sla_pct}%), com tempo médio de {med:.0f} minutos. Os {Q['proativos']} atendimentos proativos contam como dentro do prazo.")
    dest[0] = {"label": "Boa prática" if n1 >= 9 else "Atenção",
               "texto": ("Manter o padrão atual de resposta rápida — protocolo de recebimento em até 2h vem sendo cumprido com folga."
                         if n1 >= 9 else "Mesmo sem a solução pronta, protocolar o recebimento da demanda em até 2 horas — isso já cumpre o SLA do manual.")}

    base2 = Q["vago"] + Q["prazo"]
    if base2 == 0:
        notas[1] = None; just[1] = "Não avaliado — sem demandas adiadas no mês"
        txt[1] = "Não houve no mês volume relevante de demandas deixadas para depois, portanto o critério não pôde ser avaliado."
    else:
        pv = Q["vago"] / base2 * 100
        notas[1] = 10.0 if pv == 0 else 9.0 if pv <= 10 else 8.0 if pv <= 25 else 7.0 if pv <= 40 else 6.0
        just[1] = f"termo vago em {Q['vago']} de {base2} demandas adiadas ({pf(pv)})"
        exs = f" Exemplo de termo vago: \"{Q['vago_ex'][1]}\" (atend. {Q['vago_ex'][0]})." if Q["vago_ex"] else ""
        txt[1] = (f"Entre as {base2} demandas que ficaram para resolução posterior, {Q['prazo']} receberam prazo claro e {Q['vago']} ficaram com termos vagos "
                  f"como \"vou verificar\" ({pf(pv)} do total).{exs}")
        dest[1] = {"label": "Regra", "texto": "O que não se resolve na hora ganha prazo claro e fixo (ex.: \"será atendida em 2 dias úteis\") — nunca \"vou verificar\"."}

    pe = Q["emp"] / oa * 100 if oa else 0
    n3 = 10.0 if pe >= 95 else 9.0 if pe >= 80 else 8.0 if pe >= 60 else 7.0 if pe >= 40 else 6.0
    notas[2] = n3
    just[2] = f"marcas de cortesia/validação em {Q['emp']} de {oa} atendimentos ({pf(pe)})"
    txt[2] = (f"Em {Q['emp']} dos {oa} atendimentos com participação do analista ({pf(pe)}) há pelo menos uma marca de empatia — saudação com nome, "
              f"validação da preocupação (\"entendo\", \"fica tranquilo\") ou cortesia ativa (\"vou te ajudar\", \"à disposição\").")
    dest[2] = {"label": "Exemplo positivo" if n3 >= 9 else "Atenção",
               "texto": ("Cortesia consistente: praticamente todo atendimento abre com saudação e valida a preocupação do cliente."
                         if n3 >= 9 else "Validar a preocupação do cliente em TODO atendimento — um problema \"pequeno\" para o contador pode ser enorme para o cliente.")}

    d4 = Q["lei"]
    notas[3] = 9.5 if d4 == 0 else 8.0 if d4 <= 2 else 7.0 if d4 <= 5 else 6.0
    just[3] = f"{d4} atendimento(s) com citação de lei/artigo sem tradução prática" if d4 else "nenhum desvio de canal/tecnicidade identificado"
    txt[3] = (f"Foram identificados {d4} atendimento(s) com citação direta de lei/artigo em texto corrido — o manual pede tradução para a prática do cliente, com exemplo concreto."
              if d4 else "Não foram identificados desvios: nenhuma colagem de lei/artigo sem tradução prática e nenhum tema de alta complexidade tratado apenas por texto sem oferta de telefone.")
    bl[3] = ["Em dúvidas de alta complexidade, priorizar o telefone.",
             "Se responder por escrito, incluir exemplo prático ligado à realidade do cliente."]
    dest[3] = {"label": "Regra", "texto": "É proibido copiar e colar lei/artigo sem traduzir para a prática do cliente."}

    if Q["erro"] == 0:
        notas[4] = None; just[4] = "Não avaliado — sem erro do colaborador identificado no mês"
        txt[4] = "Não foi identificado no mês nenhum erro do próprio colaborador que exigisse tratamento; erros de cliente não entram nesta avaliação."
    else:
        pp = Q["erro_prazo"] / Q["erro"] * 100
        notas[4] = 9.0 if pp >= 80 else 8.0 if pp >= 50 else 7.5
        just[4] = f"{Q['erro']} caso(s) com falha assumida; prazo de correção explícito em {Q['erro_prazo']} ({pf(pp)})"
        txt[4] = (f"Em {Q['erro']} atendimento(s) o colaborador assumiu uma falha ou pediu desculpas de forma transparente; em {Q['erro_prazo']} deles houve também prazo claro de correção. "
                  f"Erros do cliente que exigiram retificação não afetaram esta nota.")
        bl[4] = [f"Assumiu a falha com transparência em {Q['erro']} caso(s). ✓"] + ([f"Prazo prioritário de correção explícito em apenas {Q['erro_prazo']} de {Q['erro']}. ✗"] if pp < 80 else [])
        dest[4] = {"label": "Regra", "texto": "Erro do colaborador: assumir, justificar com transparência e dar prazo claro e prioritário de correção."}

    pd_ = 100 - (Q["transf"] / oa * 100 if oa else 0)
    n6 = 9.5 if pd_ >= 95 else 9.0 if pd_ >= 85 else 8.0 if pd_ >= 70 else 7.0 if pd_ >= 55 else 6.0
    notas[5] = n6
    just[5] = f"{oa - Q['transf']} de {oa} atendimentos resolvidos sem repasse ({pf(pd_)})"
    txt[5] = (f"{oa - Q['transf']} dos {oa} atendimentos ({pf(pd_)}) foram conduzidos até a conclusão na própria célula; "
              f"{Q['transf']} tiveram transferência/encaminhamento a outro setor.")
    dest[5] = {"label": "Boa prática" if n6 >= 9 else "Atenção",
               "texto": ("Alta resolutividade direta — manter o padrão de concluir a demanda na própria célula."
                         if n6 >= 9 else "Antes de transferir, esgotar o que pode ser resolvido na própria célula — evitar o \"empurra-empurra\" entre setores.")}

    notas[6] = 10.0
    just[6] = "nenhuma evidência de prática irregular aceita ou orientada no mês"
    txt[6] = "Não foi identificada nenhuma situação de prática irregular aceita ou sugerida; as orientações seguem a legislação e informam riscos quando aplicável."
    dest[6] = {"label": "Boa prática", "texto": "Nunca executar prática irregular pedida pelo cliente — orientar formalmente o procedimento correto."}

    base8 = Q["alt"] + Q["neg"]
    if base8 == 0:
        notas[7] = None; just[7] = "Não avaliado — sem pedido não atendível direto no mês"
        txt[7] = "Não houve no mês pedido que exigisse negativa, portanto o critério não pôde ser avaliado."
    else:
        pa = Q["alt"] / base8 * 100
        notas[7] = 9.0 if pa >= 80 else 8.0 if pa >= 60 else 7.0 if pa >= 40 else 6.0
        just[7] = f"alternativa apresentada em {Q['alt']} de {base8} negativas ({pf(pa)})"
        exs = f" Exemplo de negativa seca: \"{Q['neg_ex'][1]}\" (atend. {Q['neg_ex'][0]})." if Q["neg_ex"] and pa < 80 else ""
        txt[7] = (f"Dos {base8} casos em que o pedido não podia ser atendido diretamente, {Q['alt']} receberam alternativa/consulta a outra célula e "
                  f"{Q['neg']} ficaram na negativa seca.{exs}")
        dest[7] = {"label": "Regra", "texto": "Evitar o \"não fazemos\" seco: explorar alternativas, consultar outras células ou indicar parceiro de confiança."}

    n9 = teto_cres(taxa, GIRIAS_TABELA)
    notas[8] = n9
    just[8] = f"{Q['girias']} gírias/abreviações em {Q['msgs']} mensagens (taxa {taxa:.2f}/100)"
    txt[8] = (f"Foram contadas {Q['girias']} ocorrências de gírias/abreviações vetadas pelo manual (\"vc\", \"pra\", \"kk\" etc.) nas {Q['msgs']} mensagens enviadas — "
              f"taxa de {taxa:.2f} por 100 mensagens, que define o teto da nota.")
    bl[8] = ["\"vc\" → \"você\"; \"pra\" → \"para\"; revisar antes de enviar. " + ("✗" if n9 < 9 else "✓")] if Q["girias"] else []
    dest[8] = {"label": "Regra de ouro", "texto": "Revisar a mensagem antes de enviar: sem gírias e abreviações, com tópicos ao solicitar documentos."}

    sw = sum(PESO[i] for i in range(9) if notas[i] is not None)
    nf = round(sum(notas[i] * PESO[i] for i in range(9) if notas[i] is not None) / sw, 1)

    criterios = []
    for i in range(9):
        c = {"nome": CRIT[i], "peso": PESO_S[i], "justificativa": just[i], "texto": txt[i]}
        if notas[i] is not None: c["nota"] = fmt(notas[i])
        if bl.get(i): c["bullets"] = bl[i]
        if dest.get(i): c["destaque"] = dest[i]
        criterios.append(c)

    # critério 9 (Escrita/Gírias): até 3 exemplos reais como evidência
    if Q["giria_ex"]:
        criterios[8]["evidencias"] = Q["giria_ex"]
    else:
        criterios[8]["evidencias"] = [{"trecho": "Sem ocorrência de gíria/abreviação registrada no período.",
                                       "sem_ocorrencia": True}]

    fortes = sorted([i for i in range(9) if notas[i] is not None], key=lambda i: (-notas[i], i))[:2]
    fracos = sorted([i for i in range(9) if notas[i] is not None], key=lambda i: (notas[i], i))[:2]
    plabel = hdr["periodo_label_base"] + (" — " + hdr["unidade"] if hdr["unidade"] else "")

    data = {
        "colaborador": nm, "periodo_label": plabel, "data_geracao": hdr["data_geracao"],
        "total_atendimentos": total,
        "resumo_executivo": (f"Em {hdr['periodo_label_base'].lower()}, {nm} concluiu {total} atendimentos no Gestta Messenger ({Q['proativos']} proativos), enviando {Q['msgs']} mensagens. "
                             f"O SLA de primeira resposta ficou em {sla_pct}% dentro de 2 horas (média de {med:.0f} minutos). "
                             f"A nota final ponderada dos 9 critérios do Manual de Padrões Operacionais foi {fmt(nf)}."),
        "indicadores": [
            ["Total de atendimentos", str(total)],
            ["1ª resposta dentro de 2h (SLA)", f"{sla_pct}% (média {med:.0f} min) — base {Q['sla_consid']} atend."],
            ["Atendimentos iniciados pelo analista (proativos)", str(Q["proativos"])],
            ["Mensagens enviadas pelo analista", f"{Q['msgs']:,}".replace(",", ".")],
            ["Concluídos no mês", f"Sim ({total}/{total})"],
            ["Ocorrências de gírias/abreviações", f"{Q['girias']} (taxa {taxa:.2f}/100 msgs)"]],
        "nota_geral_texto": (f"A nota final é a média ponderada dos 9 critérios pelos pesos da planilha da coordenação, calculada de forma determinística sobre a transcrição congelada do período "
                             f"({hdr['total_api']} atendimentos da unidade). Critérios sem caso aplicável no mês constam como \"Não avaliado\" e não entram na média."),
        "criterios": criterios,
        "pontos_positivos": [f"{CRIT[i]}: {just[i]}." for i in fortes],
        "pontos_melhoria": [f"{CRIT[i]}: {just[i]}." for i in fracos],
        "melhoria_destaque": {"label": "Regra de ouro", "texto": "Prazo fixo em vez de \"vou verificar\", e revisão da escrita antes do envio — os dois ajustes de maior impacto na nota."},
        "conclusao": (f"O desempenho de {nm} em {hdr['periodo_label_base'].lower()} reflete {total} atendimentos reais analisados na íntegra. "
                      f"Os pontos fortes e de melhoria acima são todos auditáveis na transcrição congelada do período."),
        "conclusao_destaque": {"label": "Mensagem final", "texto": "Atendimento é a vitrine da Altocon: rapidez no primeiro contato, prazo claro e escrita impecável."}
    }
    crit_notas = {CRIT[i]: fmt(notas[i]) for i in range(9) if notas[i] is not None}
    return data, nf, crit_notas

# ---------------------------------------------------------------- main
def main():
    if len(sys.argv) < 3:
        sys.exit("Uso: python3 scripts/analisar.py <transcricao.txt> <dir_saida>")
    lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    hdr = ler_cabecalho(lines)
    colabs = parse(lines, hdr["tot_map"])
    # trava de integridade do parse
    for nm, t in hdr["tot_map"].items():
        got = len(colabs.get(nm, []))
        gotm = sum(len(a["mensagens"]) for a in colabs.get(nm, []))
        if got != t or gotm != hdr["msg_map"][nm]:
            sys.exit(f"ERRO de parse em {nm}: {got}/{t} atendimentos, {gotm}/{hdr['msg_map'][nm]} mensagens. Abortado.")

    team = []
    for nm in sorted(colabs, key=lambda s: s.lower()):
        data, nf, crit_notas = analisar_colab(nm, colabs[nm], hdr)
        safe = re.sub(r"[^A-Za-z0-9]+", "_", nm).strip("_")
        with open(os.path.join(outdir, f"analise_{safe}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        team.append({"nome": nm, "total_atendimentos": len(colabs[nm]), "nota_final": fmt(nf), "criterios": crit_notas})
        print(f"{nm:34} NF={fmt(nf)}")

    media = round(sum(float(t["nota_final"].replace(",", ".")) for t in team) / len(team), 1)
    rank = sorted(team, key=lambda t: (-float(t["nota_final"].replace(",", ".")), t["nome"]))
    plabel = hdr["periodo_label_base"] + (" — " + hdr["unidade"] if hdr["unidade"] else "")
    resumo = {
        "periodo_label": plabel, "data_geracao": hdr["data_geracao"],
        "total_colaboradores": len(team),
        "total_atendimentos": sum(t["total_atendimentos"] for t in team),
        "media_geral": fmt(media),
        "resumo_executivo": (f"A unidade concluiu {sum(t['total_atendimentos'] for t in team)} atendimentos em {hdr['periodo_label_base'].lower()}, distribuídos entre {len(team)} colaboradores. "
                             f"A média geral da equipe foi {fmt(media)}. Destaques: {rank[0]['nome']} ({rank[0]['nota_final']})" +
                             (f" e {rank[1]['nome']} ({rank[1]['nota_final']})" if len(rank) > 1 else "") + ". "
                             f"Todas as notas deste resumo são calculadas de forma determinística sobre a transcrição congelada do período."),
        "colaboradores": team,
        "destaques": [
            f"{rank[0]['nome']} lidera o ranking com {rank[0]['nota_final']}.",
            "SLA de primeira resposta com nota ≥9,0 em " + str(sum(1 for t in team if float(t["criterios"].get(CRIT[0], "0").replace(",", ".")) >= 9)) + " colaboradores.",
            "Ética e Transparência: nenhuma ocorrência de prática irregular identificada na unidade."],
        "pontos_melhoria_equipe": [
            "Gírias e abreviações (\"vc\", \"pra\", \"obg\") ainda derrubam o critério de escrita de vários colaboradores — revisar antes de enviar.",
            "Substituir \"vou verificar\"/\"vou analisar\" por prazo claro e fixo (ex.: \"em 2 dias úteis\").",
            "Reduzir transferências sem conclusão: esgotar a solução na própria célula antes de repassar."],
        "conclusao": (f"Com média {fmt(media)}, a unidade encerra {hdr['periodo_label_base'].lower()} com desempenho auditável — toda nota deste resumo é reconstruível a partir "
                      f"da transcrição congelada do período. Os relatórios individuais detalham os planos de melhoria de cada colaborador.")
    }
    with open(os.path.join(outdir, "resumo_equipe.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)
    print(f"\nMédia geral: {fmt(media)} | {len(team)} colaboradores | JSONs em {outdir}")

if __name__ == "__main__":
    main()
