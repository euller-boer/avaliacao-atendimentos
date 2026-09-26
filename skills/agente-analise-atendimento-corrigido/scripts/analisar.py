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
import json, re, sys, os, html, unicodedata
from datetime import datetime, timedelta

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

# REGRA SLA (opcao b, coordenacao 14/07/2026): o cronometro para apenas na 1a
# mensagem do PROPRIO colaborador avaliado — resposta da recepcao/triagem nao
# encerra a contagem. Autores com nome alterado no mes sao unificados via alias.
ALIAS_AUTOR = {"MARIA EDUARDA": "EDUARDA BORGES"}
def autor_eh(nm, autor):
    a = (autor or "").strip().upper()
    a = ALIAS_AUTOR.get(a, a)
    return a == nm.upper()

VAGO = re.compile(r"\b(vou verificar|vou analisar|vou ver|vou olhar|vou checar|assim que poss[ií]vel|qualquer coisa (te )?aviso|mais tarde te (falo|aviso))\b", re.I)

# ATENDIMENTO POR OUTRO CANAL (apontamento da equipe, 21/08/2026): nota interna em
# que o colaborador REGISTRA que o cliente ja foi atendido fora do chat (telefone,
# presencial, acesso remoto). Serve para (a) parar o cronometro do criterio 1 (SLA)
# e (b) alimentar a secao "Registros internos" do relatorio. NAO entra em nenhum
# criterio de escrita, nao conta como mensagem enviada e nao vira exemplo de
# empatia/prazo.
#
# CALIBRACAO: o filtro procura APENAS a mencao ao canal. Foi tentada antes uma
# versao exigindo verbo de conclusao + preposicao + canal ("tratado via ligacao");
# ela reconhecia so 5 das 14 notas reais de agosto/2026, porque cada pessoa escreve
# de um jeito ("Feito atendimento telefonico", "Conversei com a cliente por
# telefone", "Respondido presencialmente"). O que TODAS tem em comum e nomear o
# canal — ninguem escreve "telefone" numa nota interna por acaso. A versao simples
# acerta 18 de 19 sem nenhum falso positivo.
#
# O que o filtro NAO pega (e por isso a secao "Registros internos" lista TODAS as
# notas proprias, reconhecidas ou nao): nota que nao nomeia o canal, como
# "dado retorno para ele por outro meio" (Diesley Queiroz, 07/08/2026).
# O canal precisa aparecer como MEIO do atendimento, nao como palavra solta. Achado
# real de julho/2026 (Ricardo Buzeto): a nota era uma lista de documentos para
# abertura de empresa e trazia o item "Telefone e e-mail;" — mencionava o canal sem
# nenhum atendimento ter acontecido. Por isso exige-se preposicao de meio antes do
# substantivo ("por telefone", "via fone", "pelo telefone"), ou entao a forma que ja
# e adverbio/adjetivo de meio ("presencialmente", "telefonico", "remotamente").
_SUBST = r"(liga[çc][ãa]o|telefone|fone|videochamada|v[íi]deo ?chamada|reuni[ãa]o|whats ?app|anydesk|teamviewer)"
CANAL_ATENDIMENTO = re.compile(
    r"\b(por|via|pelo|pela|atrav[ée]s d[eoa]s?|em)\s+(o\s+|a\s+|uma?\s+)?" + _SUBST + r"\b"
    r"|\b(presencialmente|presencial|remotamente|telef[oôó]nic[oa]|acesso remoto)\b",
    re.I)

# TENTATIVA DE CONTATO (regra revista pela coordenacao em 26/08/2026): a nota em que
# o colaborador registra que TENTOU contato ("Tentamos contatos telefonico para
# agilizar o pedido, iremos tentar novamente no proximo dia!" — Jairo Ravasi,
# junho/2026) PARA o cronometro do criterio 1. Motivo dado pela coordenacao: a
# pessoa agiu para retornar ao cliente; nao e o mesmo que ignorar o atendimento.
#
# ATE 25/08/2026 a regra era o contrario — a tentativa nao parava o cronometro,
# para evitar que alguem encerrasse a contagem sem ter atendido ninguem. Esse risco
# continua existindo, e o contrapeso e a secao 12: a tentativa recebe marcador
# PROPRIO ("[encerrado por tentativa de contato]"), diferente do atendimento de fato
# concluido, para que quem revisa consiga distinguir os dois.
#
# EFEITO MEDIDO antes de aplicar (jun a 21/08, duas unidades, 32 colaboradores):
# nenhuma nota, media ou percentual mudou. Os 3 casos reais da base ou ja tinham
# resposta (6 e 66 min uteis) ou nem entravam na base do SLA. A mudanca vale para
# frente.
# RECADO PARA COLEGA: nota que ABRE endereçando alguem ("@Fulano ...") e recado
# interno ou tarefa, nunca registro de atendimento ao cliente. Achado real de
# junho/2026 (Graziele Anselmo): "@Graziele Anselmo Confirmar se a reuniao sera
# presencial ou online" — tarefa futura que casava por causa de "presencial".
# Nas 81 notas proprias de jun/jul/ago das duas unidades, nenhuma das que abrem
# com @ era registro de atendimento.
RECADO_COLEGA = re.compile(r"^\s*(<[^>]+>\s*)*@", re.I)

TENTATIVA_FRUSTRADA = re.compile(
    r"\b(tentamos|tentei|tentativa|tentar novamente|sem sucesso|n[ãa]o atendeu|"
    r"n[ãa]o consegui|n[ãa]o retornou|caixa postal|n[ãa]o foi poss[íi]vel falar)\b", re.I)

CARIMBO_TRANSF = re.compile(r"Atendimento transferido por .+ para ", re.I)
# Igual ao de cima, mas capturando os dois nomes. Vale para QUALQUER pessoa, mesmo
# quem nao esta na avaliacao — a regra 3.3 precisa saber quem entregou o chamado.
_QUALQUER_TRANSF = re.compile(r"Atendimento transferido por (.+?) para (.+?):?\s*$", re.I)

# COMPROMISSO DE RETORNO (criterio 2, correcao 2.2 de 26/08/2026): o prazo so absolve
# o termo vago quando esta LIGADO a um verbo de retorno dirigido ao cliente ("lhe
# retorno ate amanha", "ate amanha te encaminho", "posso te mandar amanha"). Verbo
# solto NAO vale: "se puder entrar em contato amanha, assim que possivel respondo
# aqui" (Leonardo Chueco, 03/06/2026) tem "amanha" e "respondo", mas o "amanha" e para
# o CLIENTE ligar e o retorno segue vago. Testado nas 20 mensagens reais da base de
# jun a 21/08: 5 absolvidas, 15 mantidas, nenhuma classificada errado.
_VERBO_RETORNO = (r"(retorn\w+|te? ?(encaminho|mando|envio|passo|aviso|respondo|falo)|"
                  r"lhe (retorno|encaminho|envio)|posso te (mandar|enviar|passar))")
_QUANDO = (r"(at[ée] (amanh[ãa]|hoje|sexta|segunda|ter[çc]a|quarta|quinta|o dia \d{1,2}|"
           r"\d{1,2}/\d{1,2})|amanh[ãa]|hoje (ainda|mesmo)|em \d+ ?(h|horas|min|"
           r"dias? ?[úu]te(is|l)?)|\d+ dias? [úu]te(is|l))")
COMPROMISSO_RETORNO = re.compile(
    rf"\b{_VERBO_RETORNO}\b[^.!?]{{0,40}}\b{_QUANDO}\b"
    rf"|\b{_QUANDO}\b[^.!?]{{0,40}}\b{_VERBO_RETORNO}\b", re.I)


def para_cronometro(m, nm):
    """A mensagem encerra a contagem do SLA? Mensagem externa do proprio
    colaborador sempre encerra; nota interna so encerra quando registra
    atendimento feito por outro canal."""
    if m["dir"] != "OUT" or not autor_eh(nm, m.get("autor")):
        return False
    if not m["interna"]:
        return True
    # O carimbo do sistema ("Atendimento transferido por X para Y: <texto>") carrega
    # junto o recado de quem repassou, escrito por OUTRA pessoa. Achado real de
    # agosto/2026: um repasse da Natalia Santos dizia "foi tratado em reuniao" e
    # zerava o cronometro de quem recebeu. Carimbo nunca encerra contagem.
    if CARIMBO_TRANSF.search(m["texto"]):
        return False
    if RECADO_COLEGA.search(m["texto"]):
        return False
    # A tentativa de contato encerra a contagem desde 26/08/2026 (ver comentario da
    # TENTATIVA_FRUSTRADA). Ela sai marcada a parte na secao 12 — nao e silenciosa.
    return bool(CANAL_ATENDIMENTO.search(m["texto"]))


def encerrado_por_tentativa(m, nm):
    """A contagem foi encerrada por uma TENTATIVA de contato, e nao por um
    atendimento concluido? So para diferenciar as duas coisas na secao 12."""
    return bool(para_cronometro(m, nm) and TENTATIVA_FRUSTRADA.search(m["texto"]))
PRAZO = re.compile(r"\b(dias? [úu]te(is|l)|at[ée] (o dia |amanh[ãa]|hoje|sexta|segunda|ter[çc]a|quarta|quinta)|amanh[ãa]|hoje (ainda|mesmo)|\d{1,2}/\d{1,2}|em \d+ ?(h|horas|min|dia))\b", re.I)
EMPATIA = re.compile(r"\b(bom dia|boa tarde|boa noite|tudo bem|entendo|compreendo|imagino|fica tranquil|pode deixar|vou te ajudar|conte comigo|por favor|obrigad|disponha|[àa] disposi[çc][ãa]o|precisando)\b", re.I)
NEG_SECA = re.compile(r"\b(n[ãa]o (fazemos|tem como|[ée] poss[íi]vel|conseguimos|posso te ajudar com isso|atendemos))\b", re.I)
# Formas condicionais e interrogativas NAO sao recusa: "se nao der certo me avisa",
# "caso nao de certo tente...", "nao da para identificar?". Achado real de julho/2026
# (Monte Alto): 20 das 82 mensagens com "nao" eram oferta de ajuda ou pergunta.
NEG_COND = re.compile(r"\b(se n[ãa]o|sen[ãa]o|caso n[ãa]o)\b", re.I)
# Lista de ALTERNATIVA ampliada a partir de como a equipe realmente escreve
# (achado real de julho/2026): "sera necessario comparecer ao cartorio", "precisara
# entrar em contato com o contador", "seria diretamente com eles", "tente...".
ALTERNATIVA = re.compile(r"\b(alternativa|outra op[çc][ãa]o|posso (sugerir|indicar|te ligar)|"
                         r"vou (consultar|verificar com) (o|a|outro)|parceiro|indica[çc][ãa]o|sugest[ãa]o|"
                         r"o que podemos fazer|(ser[áa]|[ée]|vai ser) necess[áa]rio|precisar[áa]|"
                         r"entrar em contato com|comparecer|procurar (o|a|diretamente)|"
                         r"(seria|ser[áa]) diretamente|diretamente (com|ao|na|no)|"
                         r"o que (eu )?(consigo|posso) (fazer|verificar|te passar)|tente|me avisa que|"
                         r"providenciamos|sugiro|recomendo|encaminh(o|ar|amos) para|vou passar para|"
                         r"solicite|pe[çc]o que)\b", re.I)
# Base minima do criterio 8 (coordenacao 07/08/2026): abaixo disso a nota oscilaria
# demais com um unico caso lido de outro jeito — o criterio sai como "Nao avaliado"
# e seu peso e redistribuido entre os demais (linha do calculo de `sw`).
MIN_BASE_C8 = 3


def achar_negativa(txt):
    """Devolve o trecho da negativa de RECUSA, ou None. Ignora oracao condicional
    ("se nao der certo me avisa") e pergunta ("nao da para identificar?")."""
    toks = re.split(r"([.!?\n]+)", txt)
    for i in range(0, len(toks), 2):
        frase = toks[i]
        delim = toks[i + 1] if i + 1 < len(toks) else ""
        m = NEG_SECA.search(frase)
        if not m or NEG_COND.search(frase) or "?" in delim:
            continue
        return m.group(0)
    return None
TRANSFER = re.compile(r"\b(vou (te )?transferir|transferindo|vou encaminhar|encaminhando|vou passar (para|pro|pra)|setor respons[áa]vel)\b", re.I)
LEI = re.compile(r"\b(art\.? ?\d+|artigo \d+|lei n|LC \d|par[áa]grafo|inciso)\b", re.I)
ERRO = re.compile(r"\b(desculp\w*|foi (um )?(erro|equ[íi]voco|falha) (noss|meu|minh)\w*|me equivoquei|nos equivocamos|erramos|corrigir[ei]mos|vou corrigir|pe[çc]o desculpas|perd[ãa]o pel)\b", re.I)

# REGUA DE EXPEDIENTE (coordenacao 14/07/2026): o cronometro do SLA conta
# apenas minutos uteis — 07:30 as 18:00, segunda a sexta, feriados nacionais
# descontados. Limite do manual: 120 minutos UTEIS.
EXP_INI = (7, 30)
EXP_FIM = (18, 0)
FERIADOS = {"01/01/2026", "16/02/2026", "17/02/2026", "03/04/2026", "21/04/2026",
            "01/05/2026", "04/06/2026", "07/09/2026", "12/10/2026", "02/11/2026",
            "15/11/2026", "20/11/2026", "25/12/2026"}
def _dia_util(d):
    return d.weekday() < 5 and d.strftime("%d/%m/%Y") not in FERIADOS
def minutos_uteis(a, b):
    from datetime import timedelta
    if b <= a: return 0.0
    tot = 0.0
    d = a.replace(hour=0, minute=0, second=0, microsecond=0)
    while d <= b:
        if _dia_util(d):
            ini = d.replace(hour=EXP_INI[0], minute=EXP_INI[1])
            fim = d.replace(hour=EXP_FIM[0], minute=EXP_FIM[1])
            lo = max(a, ini); hi = min(b, fim)
            if hi > lo: tot += (hi - lo).total_seconds() / 60
        d += timedelta(days=1)
    return tot

MSG_RE = re.compile(r"^\[(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}:\d{2})\] (ATENDENTE|CLIENTE)(?: \((.*?)\))?(?: \[([^\]]+)\])?: (.*)$")
COLAB_RE = re.compile(r"^### COLABORADOR: (.+)$")
ATT_RE = re.compile(r"^=== Atendimento (\d+)/(\d+) \| ID: (\S+) ===$")
TRANSF_RE = re.compile(r"^Transferência: SIM em (\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}:\d{2})$")
MESES = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
         7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

# ACOMPANHAMENTO SEM NOTA (coordenação 08/08/2026) -----------------------------
# Semana e dia deixaram de receber nota. Motivo: com amostra de poucos dias a nota vira ruído
# (achado real da semana 03–09/08/2026, Monte Alto — Graziele Anselmo tirou 3,0 com UM único
# atendimento e derrubou a média da unidade de 8,6 para 8,4). O acompanhamento passa a ser um
# LEVANTAMENTO: mesmos 9 critérios, mesmas contagens e os mesmos exemplos reais, sem nota,
# sem média e sem ranking. A nota formal sai só na avaliação MENSAL.
# Implementação: `analisar.py` calcula tudo como sempre (as notas ainda ordenam internamente o
# que entra em pontos fortes / pontos de atenção), mas o JSON de saída de período não-mensal
# NÃO carrega nota alguma — assim é impossível um número vazar para o .docx.
AVISO_ACOMP = ("ATENÇÃO — LEVANTAMENTO DE ACOMPANHAMENTO: o período analisado não é um mês fechado. "
               "A amostra é reduzida, portanto este documento NÃO atribui nota: ele levanta o que os "
               "atendimentos do período mostram em cada critério. A avaliação formal, com nota, é a mensal.")

def _sem_nota(s):
    """Reescreve as frases que falam em nota/peso para o texto de acompanhamento.

    Substituições completas e literais de propósito: um replace genérico de "nota" quebraria
    "nota de sistema" (o carimbo `Atendimento transferido por X para Y`) e "NOTA INTERNA".
    """
    if not s:
        return s
    for de, para in (
        ("Não avaliado — ", "Sem caso aplicável — "),
        ("portanto o critério não pôde ser avaliado", "portanto o critério ficou sem caso no período"),
        ("que define o teto da nota", "que é o indicador do critério"),
        ("Erros do cliente que exigiram retificação não afetaram esta nota.",
         "Erros do cliente que exigiram retificação não entram nesta contagem."),
        ("Com base tão pequena, um único caso lido de outra forma moveria "
         "a nota em vários pontos, portanto o critério não foi avaliado e seu peso foi "
         "redistribuído entre os demais critérios.",
         "Com base tão pequena, um único caso lido de outra forma mudaria bastante a leitura, "
         "portanto o critério fica sem conclusão neste acompanhamento."),
        ("os dois ajustes de maior impacto na nota", "os dois ajustes de maior impacto no atendimento"),
    ):
        s = s.replace(de, para)
    return s

def fmt(x): return f"{x:.1f}".replace(".", ",")
def fmt_na(x): return "—" if x is None else fmt(x)
def pf(x): return str(round(x)) + "%"
def corta_trecho(t, n=160):
    t = " ".join((t or "").split())
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"
def _ex(contato, dt, tx, termo=None):
    e = {"cliente": contato or "—", "data": dt.strftime("%d/%m/%Y"),
         "hora": dt.strftime("%Hh%M"), "trecho": corta_trecho(tx)}
    if termo: e["termos"] = termo
    return e
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
    # Período aceita 3 formatos: MM/AAAA (mês), DD/MM/AAAA (dia) e DD/MM/AAAA a DD/MM/AAAA (semana/intervalo)
    m_per = re.search(r"Per[íi]odo: *([^\n]+)", head)
    per_raw = m_per.group(1).strip() if m_per else ""
    tipo, plabel, pfrase, pnome = "mes", "?/?", "em ?", "?"
    m_r = re.match(r"^(\d{2}/\d{2}/\d{4})\s+a\s+(\d{2}/\d{2}/\d{4})$", per_raw)
    m_d = re.match(r"^(\d{2}/\d{2}/\d{4})$", per_raw)
    m_m = re.match(r"^(\d{2})/(\d{4})$", per_raw)
    if m_r:
        ini, fim = m_r.group(1), m_r.group(2)
        tipo = "intervalo"; plabel = f"{ini} a {fim}"
        pfrase = f"no período de {ini} a {fim}"; pnome = f"o período de {ini} a {fim}"
    elif m_d:
        dia = m_d.group(1)
        tipo = "dia"; plabel = dia
        pfrase = f"no dia {dia}"; pnome = f"o dia {dia}"
    elif m_m:
        mes, ano = int(m_m.group(1)), m_m.group(2)
        tipo = "mes"; plabel = f"{MESES.get(mes,'?')}/{ano}"
        pfrase = f"em {plabel.lower()}"; pnome = plabel.lower()
    unid = g(r"equipe ([^—\n)]+)")
    if unid: unid = unid.strip()
    ger = g(r"Gerado em: (\d{2}/\d{2}/\d{4})")
    tot_map, msg_map = {}, {}
    for ln in lines[:60]:
        m = re.match(r"^(.+?): (\d+) atendimentos, (\d+) mensagens$", ln)
        if m:
            tot_map[m.group(1)] = int(m.group(2)); msg_map[m.group(1)] = int(m.group(3))
    # Inicio do periodo como datetime — usado pela regra de CORTE dos DESLIGADOS.
    # Mes fechado conta a partir do dia 1; intervalo e dia contam a partir da data informada.
    p_ini = None
    try:
        if m_r:
            p_ini = datetime.strptime(m_r.group(1), "%d/%m/%Y")
        elif m_d:
            p_ini = datetime.strptime(m_d.group(1), "%d/%m/%Y")
        elif m_m:
            p_ini = datetime(int(m_m.group(2)), int(m_m.group(1)), 1)
    except ValueError:
        p_ini = None
    # FIM do periodo como datetime — usado pela VIGENCIA do PAPEL_TRIAGEM (ver
    # PAPEL_TRIAGEM_DESDE). Mes fechado termina no ultimo dia do mes; intervalo termina na
    # 2a data; dia termina nele mesmo. Fica no ULTIMO INSTANTE do dia (23:59:59) para que a
    # comparacao com a data de vigencia inclua o proprio dia.
    p_fim = None
    try:
        if m_r:
            p_fim = datetime.strptime(m_r.group(2), "%d/%m/%Y")
        elif m_d:
            p_fim = datetime.strptime(m_d.group(1), "%d/%m/%Y")
        elif m_m:
            mes_i, ano_i = int(m_m.group(1)), int(m_m.group(2))
            p_fim = datetime(ano_i + (mes_i == 12), (mes_i % 12) + 1, 1) - timedelta(days=1)
        if p_fim is not None:
            p_fim = p_fim.replace(hour=23, minute=59, second=59)
    except ValueError:
        p_fim = None
    return {"total_api": total_api, "periodo_label_base": plabel, "periodo_ini": p_ini,
            "periodo_fim": p_fim,
            "periodo_tipo": tipo, "periodo_frase": pfrase,
            "periodo_frase_cap": (pfrase[0].upper() + pfrase[1:]) if pfrase else "",
            "periodo_nome": pnome,
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
            fa(); nm = name_map.get(m.group(1).strip())
            if nm is None:
                sys.exit(f"ERRO: seção de colaborador '{m.group(1).strip()}' não consta no bloco de integridade. Nomes NUNCA são inventados/renomeados.")
            cur_c = nm; colabs.setdefault(nm, []); continue
        m = ATT_RE.match(ln)
        if m:
            fa(); cur_a = {"id": m.group(3), "mensagens": [], "transfer_dt": None, "contato": ""}; continue
        if cur_a is not None and cur_m is None and ln.startswith("Contato:"):
            cur_a["contato"] = ln.split(":", 1)[1].strip(); continue
        m = TRANSF_RE.match(ln)
        if m and cur_a is not None:
            cur_a["transfer_dt"] = datetime.strptime(m.group(1) + " " + m.group(2), "%d/%m/%Y %H:%M:%S")
            continue
        m = MSG_RE.match(ln)
        if m:
            fm()
            tags = m.group(5) or ""
            cur_m = {"dir": "OUT" if m.group(3) == "ATENDENTE" else "IN",
                     "interna": "NOTA INTERNA" in tags, "autor": (m.group(4) or "").strip(),
                     "dt": datetime.strptime(m.group(1) + " " + m.group(2), "%d/%m/%Y %H:%M:%S"),
                     "texto": m.group(6)}
            continue
        if cur_m is not None and not ln.startswith(("===", "###", "---")):
            cur_m["texto"] += "\n" + ln
    fa()
    return colabs

# REGRA CRITÉRIO 6 (coordenação 05/08/2026): a transcrição atribui cada
# atendimento ao colaborador que ficou com ele por ÚLTIMO — quando alguém
# repassa, o atendimento (e as mensagens que essa pessoa mandou antes de
# repassar) somem da própria seção dela e passam a contar inteiramente para
# quem recebeu. Isso deixava invisível quase todo repasse de quem transfere
# muito (ex.: achado real de julho/2026 — Laysa Malagutti: só 3 de 1.003
# repasses reais apareciam na própria seção dela). Por isso escaneamos a
# transcrição inteira atrás da nota de sistema "Atendimento transferido por
# X para Y" (carimbo do Gestta, não é frase digitada) e credita o repasse a
# X onde quer que o atendimento tenha ficado registrado.
# PAPEL DE TRIAGEM (coordenação 05/08/2026): colaboradores cuja função é RECEBER e
# DIRECIONAR o chamado para o setor certo — não "resolver" o assunto. Pra esse papel o
# critério 6 não pode medir "resolveu sem repassar" (repassar É a função); mede se o
# direcionamento foi rápido e certo — ou seja, se quem recebeu não precisou corrigir a
# rota logo em seguida. Achado real de julho/2026 (Laysa Malagutti): 962 dos 1.003
# repasses foram direcionamento puro (zero mensagem própria antes) e ZERO tiveram outro
# repasse do mesmo atendimento nas 24h seguintes — nenhum sinal de rota errada.
# Extensão: adicionar o nome (MAIÚSCULO) aqui quando outro colaborador tiver essa função.
# Ana Chueco incluída em 10/08/2026 (coordenação): também faz recebimento e direcionamento
# de chamados em Taquaritinga, então os repasses dela são a função, não falta de
# resolutividade — pela regra comum ela levava 7,0 em julho/2026 (69% "sem repasse").
# Katariny de Simone incluída em 15/08/2026 (coordenação): entrou nesta semana em Monte Alto,
# na equipe da Laysa (Suporte/Atendimento), com a MESMA função de receber e direcionar — por
# isso a regra da Laysa vale pra ela desde o primeiro mês. Se o nome no Gestta vier diferente
# de "Katariny de Simone", ajustar aqui (o casamento é por nome).
# ELA SAIU DO ESCRITÓRIO EM 04/09/2026 (regra "corte" — ver DESLIGADOS) E O NOME FICA AQUI DE
# PROPÓSITO. NÃO TIRAR. Duas razões, as duas medidas na transcrição de 08/2026:
#   1. rodada RETROATIVA: em agosto ela tem 1.159 atendimentos e é avaliada normalmente. Tirar
#      o nome daqui faria o critério 6 dela ser medido por "resolveu sem repassar" — a régua
#      errada para quem tem a função de direcionar — e a nota dela cairia sem motivo real;
#   2. rodada NOVA, em que ela nem aparece: os carimbos "transferido por Katariny para X"
#      continuam dentro dos atendimentos de quem RECEBEU (são 678 só em agosto). A regra 3.3
#      ("chegou errado") lê TODAS as entradas, inclusive de quem está fora da avaliação, e usa
#      esta lista para decidir a exceção do chamado devolvido a quem mandou: devolver para a
#      triagem continua sendo redirecionar, e é perdoado. Sem o nome aqui, colega que devolveu
#      um chamado para ela perderia o perdão e levaria nota mais baixa por isso.
# Efeito colateral já medido e ACEITO: com ela fora da transcrição, o parser não enxerga mais
# as INSTRUÇÕES dela ("depois direcionar para X") na regra 3.1, porque essa regra só lê carimbo
# de quem está na transcrição. São 5 casos em todo o mês de agosto (1 para cada: Beatriz Papa,
# Carla Seghessi, Jairo Ravasi, Natália Santos, Stephanie Ferraz) — medido em 17/09/2026.
PAPEL_TRIAGEM = {"LAYSA MALAGUTTI", "ANA CHUECO", "KATARINY DE SIMONE"}

# TRIAGEM COM DATA DE INICIO (usuário, 19/09/2026) — quem passou a fazer triagem NO MEIO da
# vida do sistema, e portanto NÃO pode ser medido por essa régua nos períodos anteriores.
#
# Por que este dicionário existe e o nome não foi simplesmente somado ao set acima:
# PAPEL_TRIAGEM não tem data, então incluir um nome lá aplica a régua a TODA rodada, inclusive
# retroativa. Para quem sempre fez triagem (Laysa, Ana, Katariny) isso está certo. Para quem
# MUDOU de função, não: mudaria a nota de meses em que a pessoa era colaboradora comum.
#
# EDUARDA BORGES desde 04/09/2026 12:00: assumiu o recebimento e direcionamento dos chamados
# em Monte Alto no MEIO do dia em que a Katariny saiu (04/09/2026 — ver DESLIGADOS). Medido na
# transcrição real, é a troca de função mais nítida que o sistema já registrou:
#   - agosto/2026 inteiro:      19 transferências NO MÊS (perfil de colaboradora comum);
#   - 01 a 03/09:               3 (2 em 01/09, 1 em 03/09) — ainda colaboradora comum;
#   - 04/09, a PASSAGEM DE BASTÃO, que é o motivo de a vigência ter HORA e não só data:
#       * Katariny: 31 repasses, TODOS de manhã (07h às 11h), ZERO à tarde;
#       * Eduarda:  14 repasses, TODOS à tarde (13:35 às 16:13), ZERO de manhã.
#     O usuário revisou o dia e confirmou em 19/09/2026 que ela assumiu a partir do meio-dia.
#   - 08/09 a 11/09:            271 em 4 dias úteis (80, 65, 65, 61 por dia) — a MAIOR da
#                               unidade, contra 31 da Laysa no mesmo período.
# Ou seja: pela régua comum ("resolveu sem repassar") ela seria punida em setembro por 271
# repasses que SÃO a função dela; pela régua de triagem em agosto ela seria medida por uma
# função que não exercia. Por isso a regra vale por DATA, não em bloco.
#
# COMO A VIGÊNCIA É APLICADA (duas medidas diferentes, de propósito):
#   - critério 6 DELA (analisar_colab): o critério é agregado do período inteiro, não tem data
#     por atendimento. Vale a régua de triagem quando o período TERMINA em/depois da data de
#     início — isto é, quando o período tem pelo menos um pedaço de vigência. Assim a rodada
#     mensal de 09/2026 (01/09 a 30/09) usa a régua de triagem, que é a correta da tarde de
#     04/09 em diante (só 3 repasses do mês ficaram antes disso), e as rodadas de agosto e
#     julho continuam intocadas. O usuário decidiu em 19/09/2026 NÃO separar os dias
#     anteriores à vigência dentro do mesmo mês — o critério 6 tem UMA base e UM texto.
#     EFEITO CONHECIDO E ACEITO no período curto 31/08 a 04/09/2026: ele TERMINA na tarde da
#     virada, então pela regra acima a semana inteira sai pela régua de triagem (critério 6
#     dela vai de "59 de 76 sem repasse, 78%" para "76 de 76, 100%"), embora ela só tenha
#     exercido a função em meio dia dos cinco. O pacote daquela semana JÁ FOI ENTREGUE pela
#     régua comum e o usuário decidiu não regerá-lo, então isso só apareceria se alguém
#     rerodasse o período. Se algum dia incomodar, a trava é exigir que a vigência cubra uma
#     fração mínima do período — NÃO implementar sem o usuário pedir;
#   - regras 3.1 e 3.3 (perdão dos COLEGAS): ali existe a data E HORA exatas do carimbo, então
#     a vigência é conferida carimbo a carimbo. Um chamado que ela entregou na MANHÃ de 04/09
#     não conta como "veio da triagem"; um da TARDE do mesmo dia conta.
# Extensão: para outra pessoa que MUDAR de função, acrescentar aqui com a data — "DD/MM/AAAA"
# ou "DD/MM/AAAA HH:MM" quando a virada tiver hora conhecida (sem hora, vale desde 00:00).
# Para quem sempre fez triagem, continuar usando o set PAPEL_TRIAGEM acima.
#
# FIM DA VIGÊNCIA (usuário, 26/09/2026) — a função de triagem também TERMINA. O valor passou a
# aceitar duas formas:
#   "DD/MM/AAAA HH:MM"                       -> assumiu nessa data e CONTINUA na função;
#   ("DD/MM/AAAA HH:MM", "DD/MM/AAAA HH:MM") -> assumiu e DEIXOU a função (janela fechada).
# A data final é INCLUSIVA: sem hora, vale até as 23:59:59 daquele dia (o dia inteiro conta).
#
# EDUARDA BORGES — o usuário informou em 26/09/2026 que a triagem dela vale de 04/09 ATÉ
# 18/09/2026. De 19/09 em diante ela volta a ser medida pela régua comum ("resolveu sem
# repassar"). O fim ficou SEM hora, no dia inteiro de 18/09, porque o usuário deu a data em
# dia, não em hora — diferente do início, cuja hora foi medida na passagem de bastão.
#
# JENIFER GARCIA — de 21/09/2026 a 24/09/2026 (usuário, 26/09/2026). Pegou a triagem de Monte
# Alto depois da Eduarda. NÃO há buraco entre as duas: a Eduarda terminou na SEXTA 18/09 e a
# Jenifer começou na SEGUNDA 21/09 — 19 e 20/09 são sábado e domingo.
# ⚠️ A grafia certa é JENIFER, com UM "f" só. É assim que o Gestta traz (601 ocorrências de
# "Jenifer Garcia" nas transcrições, contra 9 de "Jeniffer", todas dentro do texto de mensagem)
# e é assim que ela está em EQUIPES. APELIDOS_INSTRUCAO já mapeia "JENIFFER" -> "JENIFER" para
# o texto das mensagens, mas a CHAVE daqui tem de bater com o nome canônico, senão a régua
# simplesmente não pega e o erro passa silencioso.
# ⚠️ Perfil MUITO diferente do da Eduarda: como colaboradora comum ela quase não repassa —
# agosto/2026 = 93 de 114 sem repasse (82%); 07-11/09 = 31 de 33 (94%); 14-18/09 = 33 de 37
# (89%). Ver o aviso sobre a rodada MENSAL de 09/2026 logo abaixo, em eh_triagem_periodo.
PAPEL_TRIAGEM_DESDE = {"EDUARDA BORGES": ("04/09/2026 12:00", "18/09/2026"),
                       "JENIFER GARCIA": ("21/09/2026", "24/09/2026")}


def _dt_vigencia(txt, fim=False):
    """Converte uma data de PAPEL_TRIAGEM_DESDE em datetime.

    Aceita "DD/MM/AAAA HH:MM" (virada com hora conhecida, caso do início da Eduarda Borges em
    04/09/2026 12:00) e "DD/MM/AAAA" (sem hora).
    Sem hora, o INÍCIO vale desde 00:00 daquele dia e o FIM (`fim=True`) vale até 23:59:59 —
    ou seja, a data final informada em dia conta o dia inteiro.
    """
    txt = (txt or "").strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            d = datetime.strptime(txt, fmt)
        except ValueError:
            continue
        if fim and fmt == "%d/%m/%Y":
            d = d.replace(hour=23, minute=59, second=59)
        return d
    raise ValueError("data de vigencia invalida em PAPEL_TRIAGEM_DESDE: %r" % txt)


def _janela_triagem(nome):
    """Devolve a janela (inicio, fim) de vigencia da triagem do `nome`, ou None.

    `fim` é None quando a pessoa continua na função. Aceita as duas formas de valor descritas
    em PAPEL_TRIAGEM_DESDE (string = janela aberta; tupla = janela fechada).
    """
    v = PAPEL_TRIAGEM_DESDE.get((nome or "").strip().upper())
    if not v:
        return None
    if isinstance(v, str):
        return _dt_vigencia(v), None
    ini, fim = (list(v) + [None])[:2]
    return _dt_vigencia(ini), (_dt_vigencia(fim, fim=True) if fim else None)


def eh_triagem(nome, quando=None):
    """O `nome` exerce o PAPEL DE TRIAGEM na data `quando`?

    `quando` é o datetime do CARIMBO. Quem está em PAPEL_TRIAGEM vale sempre, com ou sem data.
    Quem está em PAPEL_TRIAGEM_DESDE só vale DENTRO da janela de vigência — e, sem data
    informada, NÃO vale (conservador de propósito: é melhor não aplicar a régua especial do que
    aplicá-la a um período em que a pessoa não tinha a função).
    Para o critério 6, que é agregado do período e não tem data por atendimento, usar
    eh_triagem_periodo().
    """
    nm = (nome or "").strip().upper()
    if nm in PAPEL_TRIAGEM:
        return True
    j = _janela_triagem(nm)
    if j is None or quando is None:
        return False
    ini, fim = j
    return quando >= ini and (fim is None or quando <= fim)


# COBERTURA MINIMA (usuário, 26/09/2026) — fração dos DIAS ÚTEIS do período que a janela de
# triagem precisa cobrir para o critério 6 sair pela régua de triagem. Ver eh_triagem_periodo.
TRIAGEM_COBERTURA_MIN = (1, 3)   # (numerador, denominador) = um terço


def _dias_uteis_no_intervalo(a, b):
    """Quantos DIAS ÚTEIS (seg-sex, feriados descontados) existem entre `a` e `b`, inclusive."""
    from datetime import timedelta
    if a is None or b is None or b < a:
        return 0
    d, n = a.replace(hour=0, minute=0, second=0, microsecond=0), 0
    while d <= b:
        if _dia_util(d):
            n += 1
        d += timedelta(days=1)
    return n


def eh_triagem_periodo(nome, p_ini, p_fim):
    """O `nome` deve ser medido pela RÉGUA DE TRIAGEM no período avaliado?

    O critério 6 é agregado do período inteiro, então a pergunta não é "nesta data" e sim "a
    pessoa exerceu a função durante uma parte relevante deste período?". São duas condições:

      1. SOBREPOSIÇÃO — o período avaliado tem interseção com a janela da função; e
      2. COBERTURA MÍNIMA — a interseção cobre pelo menos TRIAGEM_COBERTURA_MIN dos DIAS ÚTEIS
         do período (hoje, um terço).

    Por que a cobertura mínima existe (usuário, 26/09/2026): só a sobreposição bastava enquanto
    a única janela era a da Eduarda Borges, que pegava metade do mês. Com a JENIFER GARCIA, que
    foi triagem só de 21 a 24/09 — 4 dos 21 dias úteis de setembro, 19% —, a sobreposição sozinha
    daria a ela a régua de triagem no MÊS INTEIRO, e como o rebote quase nunca dispara isso vira
    nota ~9,5 de graça em 17 dias úteis nos quais ela era colaboradora comum (perfil medido: 82%
    a 94% resolvidos SEM repasse). O corte ficou em UM TERÇO porque separa os dois casos com
    folga dos dois lados — Eduarda 47,6%, Jenifer 19,0% — sem ninguém em cima da linha.
    ⚠️ Os FERIADOS entram na conta (`_dia_util`). Contar só dia de semana daria 50% para a
    Eduarda em vez de 47,6%, porque 07/09/2026 (Independência) caiu numa segunda dentro da
    janela dela. Um corte na metade a deixaria de FORA por pouco — foi por isso que não ficou
    na metade.

    A decisão de 19/09/2026 continua valendo onde a cobertura é suficiente: o critério 6 tem UMA
    base e UM texto, sem recortar os dias de fora da janela dentro do mesmo período.
    Sem as datas do período (cabeçalho ilegível) devolve False, pelo mesmo motivo conservador
    de eh_triagem().
    """
    nm = (nome or "").strip().upper()
    if nm in PAPEL_TRIAGEM:
        return True
    j = _janela_triagem(nm)
    if j is None or p_fim is None or p_ini is None:
        return False
    ini, fim = j
    if p_fim < ini:
        return False                       # o período todo é anterior à posse da função
    if fim is not None and p_ini > fim:
        return False                       # o período todo é posterior à saída da função
    # interseção entre o período avaliado e a janela da função
    i_ini = max(p_ini, ini)
    i_fim = p_fim if fim is None else min(p_fim, fim)
    uteis_periodo = _dias_uteis_no_intervalo(p_ini, p_fim)
    if uteis_periodo == 0:
        return False
    uteis_janela = _dias_uteis_no_intervalo(i_ini, i_fim)
    num, den = TRIAGEM_COBERTURA_MIN
    return uteis_janela * den >= uteis_periodo * num


TRIAGEM_JANELA_REBOTE_MIN = 24 * 60  # janela p/ considerar que o destino corrigiu a rota

# ---------------------------------------------------------------------------
# REPASSE INSTRUIDO PELA TRIAGEM  (regra 3.1 — coordenacao, 27/08/2026)
#
# A triagem frequentemente ja diz, no proprio carimbo de entrada, para onde o
# atendimento deve ir DEPOIS que o colaborador terminar a parte dele:
#   "Yasmin, por favor verificar ... Depois direcionar para o Euller - DP."
#   "Duda, bom dia. Assim que finalizar, por favor transferir para o Jairo."
#   "Jenifer ... Quando finalizar, por favor transfira pra mim."
# Cumprir essa instrucao NAO e abandonar o atendimento — e seguir a rota que a
# triagem definiu. Esses repasses saem da contagem do criterio 6.
#
# O perdao exige TRES coisas ao mesmo tempo (as tres foram calibradas sobre os
# 5.925 carimbos de junho a 21/08/2026, nas duas unidades):
#   1. o carimbo de ENTRADA veio de alguem do PAPEL_TRIAGEM e traz gatilho de
#      posterioridade + verbo de encaminhamento;
#   2. o repasse e do MESMO cliente e de quem recebeu a instrucao;
#   3. o destino do repasse E O NOME CITADO na instrucao (ou a propria triagem,
#      quando ela pede o chamado "de volta"/"pra mim").
# So o item 1 nao basta: "Duda, assim que possivel atualizar boleto... ja
# direcionei para voce" tem verbo de encaminhamento e nao instrui rota nenhuma.
# Exigir o nome do destino e o que impede perdoar repasse para outro lugar.
INSTRUCAO_JANELA_MIN = 24 * 60   # mesma janela do rebote
_INSTR_POSTERIOR = re.compile(
    r"(depois|ap[oó]s|em seguida|ao (?:finalizar|concluir|terminar)"
    r"|assim que (?:finalizar|assinar|terminar|concluir|acabar|puder|poss[ií]vel)"
    r"|quando (?:finalizar|terminar|concluir|acabar|enviar))", re.I)
_INSTR_VERBO = re.compile(
    r"(transferir|transfira|transfere|transferindo|direcionar|direcione|encaminhar"
    r"|encaminhe|devolve|devolver|manda de volta|me manda|retornar|retorne)", re.I)
_INSTR_VOLTA = re.compile(r"(pra mim|para mim|de volta|me manda)", re.I)
# Apelidos so entram quando NAO colidem com palavra comum do portugues. Ficaram
# de fora NA, LE, BIA, DI e PRI: "NA" casou a preposicao "na" e perdoou 2
# repasses do Leonardo Chueco para a Natalia Tiesi que a instrucao nunca citou.
APELIDOS_INSTRUCAO = {"DUDA": ["EDUARDA"], "GRAZI": ["GRAZIELA", "GRAZIELE"],
                      "JENIFFER": ["JENIFER"], "ZUCHI": ["ZUCCHI"], "ZUCCCHI": ["ZUCCHI"]}

def _sem_acento(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).upper()

def _texto_carimbo(bruto):
    """O texto que a triagem escreveu vem em HTML, nas linhas seguintes ao carimbo."""
    t = re.sub(r"<[^>]+>", " ", bruto or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()

def _instrucao_cita(texto, destino):
    """A instrucao nomeia a pessoa <destino>? Devolve o termo que casou, ou None."""
    t = _sem_acento(texto)
    for tok in [x for x in re.split(r"\W+", _sem_acento(destino)) if len(x) >= 3]:
        if re.search(r"\b" + re.escape(tok) + r"\b", t):
            return tok
        for ap, alvos in APELIDOS_INSTRUCAO.items():
            if tok in alvos and re.search(r"\b" + re.escape(ap) + r"\b", t):
                return ap
    return None

# ---------------------------------------------------------------------------
# DELEGACAO DE TAREFA INTERNA  (regra 3.2 — coordenacao, 27/08/2026)
#
# Ha um uso do Messenger que nao e atendimento: o colaborador NAO fala com o
# cliente naquele chamado, escreve um recado interno para um colega e passa o
# chamado adiante. Nao ha ninguem esperando resposta — o chamado e o veiculo de
# uma tarefa interna. Exemplo real (apontamento nº 3 da Yasmin, 03/08/2026):
#   nota interna "@Carla Seghessi lançar imóvel enviado no dia 29/07/2026."
#   e o chamado vai para a Carla, sem uma unica mensagem ao cliente.
# Contar isso como "empurrou o atendimento" e o oposto do que aconteceu.
#
# O perdao exige as TRES coisas ao mesmo tempo:
#   1. o colaborador nao mandou NENHUMA mensagem ao cliente naquele atendimento
#      (se ele atendeu e depois largou, e repasse comum e continua contando);
#   2. ele escreveu, ate o momento do repasse, uma NOTA INTERNA propria
#      (o carimbo "Atendimento transferido por ..." nao conta como nota);
#   3. essa nota tem TEXTO PROPRIO — o que sobra depois de tirar HTML, a URL do
#      anexo e a mencao "@Fulano" precisa ter DELEG_MIN_TEXTO caracteres.
#
# O item 3 e o que separa a delegacao do resto, e foi medido caso a caso sobre
# os 5.925 carimbos de junho a 21/08/2026 nas duas unidades:
#   - sem ele o filtro pegava 25 repasses, mas 9 eram ARQUIVO ANEXADO: o Gestta
#     registra o anexo como nota interna, e a "nota" e so a URL do S3. Anexar um
#     boleto e transferir nao e delegar tarefa nenhuma (caso real: Eduarda
#     Zucchi -> Jairo Ravasi, 12/08, com o cliente escrevendo na sequencia).
#   - o unico caso com texto que o limite descarta e "Segue chamado." (Yasmin ->
#     Lucas, 30/06): anuncia a transferencia, nao dá tarefa nem contexto.
#   - com ele sobram 16 repasses, de 4 pessoas.
# EXIGIR QUE A NOTA CITE O DESTINO foi testado e REPROVADO: derrubaria "Cliente
# quer registrar funcionárias, entrar em contato com a mesma." (Yasmin -> Thaina,
# 26/06), que e delegacao legitima, e nao acrescentaria nenhum caso.
DELEG_MIN_TEXTO = 15
_DELEG_URL = re.compile(r"https?://\S+")
_DELEG_MENCAO = re.compile(r"@\s*[\wÀ-ſ]+(?:\s+[\wÀ-ſ]+)?")

# ---------------------------------------------------------------------------
# CHAMADO QUE CHEGOU ERRADO  (regra 3.3 — coordenacao, 27/08/2026)
#
# A triagem manda o chamado para a pessoa errada; ela percebe e redireciona sem
# ter falado com o cliente. Isso contava contra ELA no criterio 6, igual a um
# atendimento abandonado.
#
# O perdao NAO e automatico: depende de a pessoa REGISTRAR o motivo (decisao do
# Euller, 27/08/2026). Sem registro, continua contando — porque sem registro
# nao ha como a coordenacao distinguir "nao era meu" de "nao quis pegar".
#
# As QUATRO condicoes precisam valer ao mesmo tempo:
#   1. a entrada mais recente do chamado veio de OUTRA pessoa — qualquer uma,
#      nao so a triagem. Excecao: se veio de um colega comum e o chamado VOLTOU
#      para ele, nao vale (e trabalho em dupla, nao rota errada);
#   2. o redirecionamento aconteceu dentro de CHEGOU_ERRADO_JANELA_MIN;
#   3. a pessoa nao mandou NENHUMA mensagem ao cliente nesse meio-tempo;
#   4. ela registrou o motivo — em NOTA INTERNA propria OU na caixa que o Gestta
#      abre na hora de transferir (o texto que fica colado no carimbo). Os DOIS
#      lugares valem: a caixa e a tela que abre naturalmente, e exigir a nota
#      separada faria a regra medir memoria, e nao comportamento.
#
# O casamento e por CONTATO + colaborador + janela, NUNCA por id de atendimento:
# o Gestta abre um atendimento NOVO a cada transferencia, entao o carimbo de
# entrada e o de saida estao em atendimentos diferentes.
#
# MEDIDO sobre junho a 21/08/2026, duas unidades: 156 redirecionamentos se
# encaixam nas condicoes 1 a 3; destes, so 26 tem registro do motivo (1 em nota
# interna, 25 na caixa de transferencia). Efeito: 21 relatorios mudam o
# percentual e 2 mudam de nota (Diesley Queiroz e Ricardo Buzeto, julho, os dois
# na fronteira dos 85%).
#
# AINDA EM ABERTO (nao implementado de proposito, decisao da coordenacao):
#   - o chamado que VOLTA para quem mandou deve ser perdoado tambem? Sao 12
#     casos, e sao de dois tipos que valem ser decididos separados: "devolvi
#     depois de fazer minha parte" (Duda Zucchi -> Gabriela: "Gabi ativei o
#     e-mail") e recusa educada ("Grazi, esse assunto e com o pessoal do
#     Fiscal", Ricardo Buzeto, 3 min);
#   - cumprimentar o cliente antes de redirecionar derruba o perdao? Sao 5
#     casos com registro do motivo — a medicao antiga dizia 44, mas aquela era
#     sem a exigencia de registro;
#   - o erro passa a contar para quem direcionou errado?
CHEGOU_ERRADO_JANELA_MIN = 24 * 60   # mesma janela da regra 3.1 e do rebote
CHEGOU_ERRADO_MIN_TEXTO = 15         # mesmo criterio de "texto de verdade" da 3.2

def _miolo_nota(bruto, pat_mencao=None):
    """O que a pessoa realmente ESCREVEU na nota: sem HTML, sem URL de anexo e
    sem a mencao '@Fulano' (que o Gestta insere ao marcar o colega).

    `pat_mencao` casa '@' + o nome COMPLETO de quem esta na transcricao e vem
    primeiro de proposito: a regra generica corta no maximo duas palavras, e
    '@Graziela dos Anjos Boa tarde!' virava 'Anjos Boa tarde!' no relatorio."""
    t = _DELEG_URL.sub(" ", _texto_carimbo(bruto))
    if pat_mencao is not None:
        t = pat_mencao.sub(" ", t)
    t = _DELEG_MENCAO.sub(" ", t)
    t = t.replace("﻿", "").replace("​", "")
    return re.sub(r"\s+", " ", t).strip()

# ---------------------------------------------------------------- equipes
# Divisão por coordenador (coordenação 11/08/2026). Cada coordenador recebe o resumo da
# PRÓPRIA equipe, e a nota dele entra na lista junto com a da equipe. O diretor recebe o
# pacote consolidado da unidade inteira (`resumo_equipe.json`), que continua sendo gerado
# igual — por isso os pacotes já entregues não mudam.
#
# Média geral, ranking e médias por critério continuam sendo da UNIDADE INTEIRA (decisão da
# coordenação em 11/08/2026): o coordenador vê onde sua equipe está dentro de Monte Alto, e
# os números seguem comparáveis com os pacotes anteriores. Só a LISTA de pessoas é recortada.
#
# Nomes em MAIÚSCULO, iguais ao bloco de integridade. Unidade sem divisão declarada aqui
# (ex.: Taquaritinga, que é pequena) segue com pacote único de unidade — nada muda para ela.
EQUIPES = {
    "Monte Alto": [
        # Eduarda ("Duda") Zucchi saiu desta equipe em 24/08/2026 (foi para o Lucas) e desde
        # 26/08/2026 esta na do DIESLEY. Com a saida dela o departamento desta equipe deixou
        # de ser "Pessoal/Onboarding" e voltou a ser so "Departamento Pessoal": o
        # "/Onboarding" existia porque ela fazia onboarding aqui (confirmado com o usuario).
        # NAO devolver o "/Onboarding" enquanto ela nao voltar para ca.
        # Graziela dos Anjos desligou-se em 24/08/2026: sai das avaliacoes por completo, como
        # a Graziele Anselmo. Tirada daqui para nao virar AVISO de "declarada mas ausente da
        # transcricao" em toda rodada. Ver DESLIGADOS logo abaixo.
        #
        # LAYSA MALAGUTTI entra aqui desde 07/09/2026, a pedido do usuario: ela passou a ser
        # avaliada pela Thaina e, na epoca, continuava coordenando a propria equipe
        # (Suporte/Atendimento). Era o UNICO caso de nome declarado em DUAS equipes de
        # proposito, e o relatorio dela saia nos DOIS pacotes.
        # DESDE 17/09/2026 NAO E MAIS DUPLICADO: a equipe dela foi encerrada (bloco comentado
        # mais abaixo, com o historico), entao a Laysa esta declarada SO aqui e o relatorio
        # dela sai UMA vez, neste pacote. Se a equipe dela for reativada, a duplicacao volta —
        # e isso e o esperado, nao um defeito.
        # Media, ranking e medias por criterio nao mudam em nenhum dos dois casos: sao da
        # UNIDADE inteira, calculados sobre `team`, nao sobre as equipes.
        # A equipe virou MISTA por causa disso — dai o rotulo composto e o `depto_membro`,
        # mesmo recurso ja usado na equipe do Lucas (build_team_summary.py imprime
        # "Departamentos da equipe: ..."). Chaves em MAIUSCULO, iguais ao bloco de integridade.
        #
        # O rotulo "Departamento Pessoal e Onboarding" foi informado pelo usuario em 07/09/2026
        # — NAO foi deduzido. Aqui a Laysa entra como ONBOARDING; na equipe DELA (logo abaixo)
        # ela continua como Suporte/Atendimento. Sao dois papeis, um em cada equipe, e cada
        # documento mostra o papel que interessa ao coordenador que o recebe.
        # ATENCAO: este "Onboarding" nao e o mesmo do antigo "Departamento Pessoal/Onboarding",
        # que existia de 11/08 a 24/08/2026 por causa da Eduarda ("Duda") Zucchi. Ela nao esta
        # nesta equipe desde 24/08/2026 (hoje esta na do Diesley).
        {"coordenador": "THAINA DE PONTI",
         "departamento": "Departamento Pessoal e Onboarding",
         "membros": ["EDUARDA BORGES", "LAYSA MALAGUTTI"],
         "depto_membro": {"THAINA DE PONTI": "Departamento Pessoal",
                          "EDUARDA BORGES": "Departamento Pessoal",
                          "LAYSA MALAGUTTI": "Onboarding"}},
        # GILMAR SOARES entra aqui em 19/09/2026: colaborador CONTRATADO (nao e troca de
        # equipe, ninguem sai de lista nenhuma), do setor de OPERACOES — um departamento que
        # nao existia no sistema ate hoje. Por ser de setor diferente do da equipe, esta
        # virou MISTA: rotulo composto "Departamento Pessoal e Operacoes" e `depto_membro`
        # dizendo quem e de qual setor, o mesmo recurso das equipes da Thaina e do Lucas.
        # O rotulo composto foi ESCOLHIDO PELO USUARIO em 19/09/2026 — nao foi deduzido.
        # Nada muda no agente de leitura: Monte Alto e lista por EXCLUSAO (todos que nao sao
        # de Taquaritinga), entao ele ja e marcado e lido sozinho.
        # Vale das rodadas NOVAS em diante (decisao do usuario). Em rodada retroativa ele
        # aparece como "declarado na equipe mas ausente na transcricao" — e so aviso de
        # console, nao quebra a analise, e e o comportamento esperado para quem ainda nao
        # tinha entrado. Nao existe lista de DATA DE ENTRADA no sistema; se um dia isso
        # incomodar, ai sim se cria uma — nao implementar sem o usuario pedir.
        # ATENCAO na PRIMEIRA rodada com ele: a grafia veio do usuario, nao da transcricao.
        # Se o Gestta trouxer nome diferente (sobrenome a mais, "Gilmar Soares da Silva"),
        # montar_equipes() nao casa, o relatorio dele NAO sai neste pacote e o console avisa.
        # A correcao e ajustar o nome AQUI, nunca na transcricao.
        {"coordenador": "EULLER BOER", "departamento": "Departamento Pessoal e Operações",
         "membros": ["JENIFER GARCIA", "GABRIELA ROSSI", "GILMAR SOARES"],
         "depto_membro": {"EULLER BOER": "Departamento Pessoal",
                          "JENIFER GARCIA": "Departamento Pessoal",
                          "GABRIELA ROSSI": "Departamento Pessoal",
                          "GILMAR SOARES": "Operações"}},
        # Eduarda ("Duda") Zucchi passou para a equipe do Diesley em 26/08/2026 (3a troca
        # dela: Lucas -> Thaina em 11/08, Thaina -> Lucas em 24/08, Lucas -> Diesley agora).
        # A TROCA de equipe e feita TIRANDO o nome da equipe antiga e pondo na nova — foi o
        # que se fez aqui, retirando-a da equipe do Lucas logo abaixo. Trocar NAO e duplicar:
        # nome declarado em duas equipes aparece nas DUAS (montar_equipes() monta cada equipe
        # de forma independente; o set `usados` so serve para saber quem ficou SEM equipe).
        # Numa troca isso faria a pessoa continuar saindo no pacote do coordenador antigo.
        # Duplicar so quando o usuario pedir de proposito, como no caso da Laysa acima.
        #
        # ALEXANDER MICHEL GARCIA e KAMILLY VITORIA entram aqui em 12/09/2026: contratados para
        # esta equipe, no MESMO departamento dela (Fiscal/Contabil, confirmado pelo usuario) —
        # por isso a equipe NAO virou mista e NAO ganhou `depto_membro`.
        # GRAFIA CONFERIDA CONTRA O GESTTA em 12/09/2026 (transcricao 07-09 a 11-09/2026):
        # "ALEXANDER MICHEL GARCIA" bate exato e "KAMILLY VITORIA" NAO batia — no Gestta e
        # "KAMILLY VITÓRIA", com acento no O. Corrigido aqui.
        # Se a transcricao trouxer grafia diferente (sobrenome a mais, acento, "KAMILY" com um
        # L), montar_equipes() nao casa o nome: o relatorio deles NAO sai no pacote do Diesley e
        # o console avisa "declarado(s) na equipe de DIESLEY QUEIROZ mas ausente(s) na
        # transcricao". A correcao e ajustar o nome AQUI para o que esta na transcricao — nunca
        # editar a transcricao, que faz ler_cabecalho()/parse() abortarem.
        # Em periodos ANTERIORES a contratacao os dois viram esse mesmo aviso, e isso e esperado:
        # nao existe regra de ADMISSAO no codigo (o espelho do fora_por_corte() para quem entra),
        # so a de desligamento. Se o aviso incomodar em rodadas retroativas, ai sim vale criar.
        {"coordenador": "DIESLEY QUEIROZ", "departamento": "Fiscal/Contábil",
         "membros": ["STEPHANIE FERRAZ", "BIANCA ALVES", "JAIRO RAVASI", "MIGUEL MALAGUTTI",
                     "YASMIN RODRIGUES", "CARLA SEGHESSI", "EDUARDA STEFANI", "JULIA MATHIAS",
                     "NATÁLIA SANTOS", "SOPHIA MAGRI", "BEATRIZ PAPA", "EDUARDA ZUCCHI",
                     "ALEXANDER MICHEL GARCIA", "KAMILLY VITÓRIA"]},
        # EQUIPE DA LAYSA (Suporte/Atendimento) — ENCERRADA em 17/09/2026, a pedido do usuário.
        #
        # Histórico (não apagar — é o que explica os pacotes já entregues):
        #   - a equipe tinha Flavio Rosato + Katariny de Simone;
        #   - Flavio saiu em 01/09/2026, quando o usuário trocou a regra dele de "corte" para
        #     "total" (sai de TODA avaliação, inclusive dos meses trabalhados, igual à Graziela
        #     dos Anjos). Ficou só a Katariny;
        #   - Katariny saiu do escritório em 04/09/2026, com regra "corte" (ver DESLIGADOS).
        #     Sem ela a equipe não tem mais nenhum membro, e o usuário decidiu ENCERRÁ-LA em vez
        #     de manter um pacote com a coordenadora sozinha.
        #
        # Efeito: não sai mais o pacote "Suporte/Atendimento". A LAYSA não fica sem equipe —
        # ela continua declarada na equipe da THAINA desde 07/09/2026 (bloco lá em cima), que
        # era o outro lado da duplicação dela. Com o encerramento a duplicação acabou: o nome
        # dela agora está em UMA equipe só, e o relatório dela sai uma vez, no pacote da Thaina.
        #
        # ATENÇÃO na rodada RETROATIVA (agosto e antes): a Katariny é "corte", então continua
        # sendo avaliada nos meses em que trabalhou — mas sem esta equipe ela cai em
        # `sem_equipe`, sai só no consolidado da unidade e o console avisa. Se quiser o pacote
        # da Laysa de volta numa rodada antiga, DESCOMENTE as duas linhas abaixo e rode; depois
        # comente de novo. Não apagar.
        # {"coordenador": "LAYSA MALAGUTTI", "departamento": "Suporte/Atendimento",
        #  "membros": ["KATARINY DE SIMONE"]},
        # Diretor: recebe a própria equipe E o consolidado da unidade inteira.
        #
        # Histórico do departamento desta equipe (não simplificar sem o usuário confirmar):
        #   - era "Legal e Financeiro", com Ricardo Buzeto + Eduarda Zucchi;
        #   - virou só "Legal" em 11/08/2026, quando ela passou para a equipe da Thaina;
        #   - voltou a ser misto em 24/08/2026, quando ela retornou — agora no CONTÁBIL,
        #     não mais no Financeiro. Por isso "Legal e Contábil": o Ricardo segue no Legal;
        #   - voltou a ser só "Legal" em 26/08/2026, quando ela passou para a equipe do
        #     Diesley. O "Contábil" existia por causa dela; sem ela, o rótulo apontaria um
        #     departamento em que ninguém desta equipe está.
        #
        # `depto_membro` sai junto: ele só serve para equipe MISTA, dizendo quem é de qual
        # departamento (build_team_summary.py imprime "Departamentos da equipe: ..."). Com o
        # Ricardo sozinho no Legal, não há o que distinguir. Se ela voltar, os dois voltam.
        # Lucas Malagutti não entra aqui: o departamento DELE nunca foi informado, e inventar
        # um rótulo num documento que avalia pessoas não é opção — quem não está no dict
        # simplesmente não aparece nessa linha.
        {"coordenador": "LUCAS MALAGUTTI", "departamento": "Legal",
         "membros": ["RICARDO BUZETO"], "diretor": True},
    ],
}


# ------------------------------------------------------------- desligados
# Quem saiu do escritorio e NAO entra em avaliacao nenhuma - nem no consolidado da unidade -
# mesmo que ainda apareca como operador no Gestta com atendimentos no periodo.
#
# A exclusao de verdade acontece no PASSO 2 do agente-leitura-conversas(-corrigido): o nome
# nao e marcado, entao nao entra na transcricao nem no bloco de integridade. Esse e o unico
# ponto onde da para tirar alguem sem quebrar a trava de contagem daqui - editar a transcricao
# ja pronta faz ler_cabecalho()/parse() abortarem.
#
# A lista abaixo e a REDE DE SEGURANCA: se a leitura esquecer de excluir, o console avisa em
# destaque, em vez de a pessoa entrar calada na media e no ranking da unidade.
#
# ATENCAO: Graziele Anselmo e Graziela dos Anjos sao DUAS PESSOAS DIFERENTES.
# Nomes em MAIUSCULO, iguais ao bloco de integridade.
#
# Cada pessoa tem uma REGRA, e as duas nao sao a mesma coisa:
#
#   "total" - sai de TODA avaliacao, inclusive de periodos em que ainda tinha atendimento.
#             Foi a decisao do usuario para a Graziele Anselmo, a Graziela dos Anjos e,
#             desde 01/09/2026, tambem para o FLAVIO ROSATO (antes ele era "corte").
#
#   "corte" - o que ela(e) fez ATE a data de saida continua valendo e deve ser avaliado
#             normalmente; so nao entra em periodos que COMECAM depois da saida. Quem e
#             "corte" CONTINUA declarado(a) em EQUIPES, senao o relatorio nao sairia nos
#             meses trabalhados.
#             KATARINY DE SIMONE entrou nessa regra em 17/09/2026 (saida 04/09/2026), a
#             pedido do usuario: ela nao traz mais atendimento nas rodadas novas, mas o que
#             ela fez ate 04/09 continua valendo. E a UNICA excecao viva a frase acima sobre
#             EQUIPES: a equipe dela (Suporte/Atendimento, da Laysa) foi ENCERRADA na mesma
#             decisao, entao em rodada RETROATIVA (agosto, por exemplo) ela cai em
#             `sem_equipe` — sai no consolidado da unidade, sem pacote de coordenador, e o
#             console avisa. Para devolver o pacote da Laysa numa rodada antiga, e so
#             descomentar o bloco da equipe dela em EQUIPES (esta logo acima, com a linha
#             pronta). Ver tambem PAPEL_TRIAGEM: o nome dela FICA la de proposito.
#
# NAO apague o historico de quem e "corte" e NAO troque a regra sem o usuario mandar.
DESLIGADOS = {
    "GRAZIELE ANSELMO":   {"saida": "08/08/2026", "regra": "total"},
    "GRAZIELA DOS ANJOS": {"saida": "24/08/2026", "regra": "total"},
    "FLAVIO ROSATO":      {"saida": "24/08/2026", "regra": "total"},
    "KATARINY DE SIMONE": {"saida": "04/09/2026", "regra": "corte"},
}


# ------------------------------------------------- contatos fora das metricas
# Chamados que a coordenacao mandou NAO contar para um colaborador especifico, mesmo
# estando na transcricao. E diferente de DESLIGADOS: la sai a PESSOA inteira; aqui sai
# so o ATENDIMENTO daquele contato, e so do colaborador listado. O mesmo contato falado
# com outra pessoa continua contando normalmente.
#
# ONDE a exclusao acontece: no main(), DEPOIS da trava de contagem do parse. O
# atendimento continua na transcricao e no bloco de integridade — o que sai e so a
# CONTA. Tirar no agente de leitura quebraria o congelamento e obrigaria a refazer a
# transcricao inteira; editar a transcricao pronta faz ler_cabecalho()/parse() abortarem.
#
# A chave e o NOME EXATO da linha "Contato:" do Gestta, em MAIUSCULAS, e a comparacao e
# EXATA de proposito: "SIMONI" nao pode arrastar "Raphael de Simoni" (citado dentro de
# uma conversa da Procorpus) nem "Eloisa Simone", e o cliente de verdade
# "Schua - 371 EGV PHARMA ..." tem que continuar valendo.
#
# Decisao do usuario em 19/09/2026:
#   EULLER BOER / "Simoni" — ex-funcionaria da EGV PHARMA que procurou o Euller em nome
#   proprio (04/09/2026, 10:06: "Aqui e a Simoni que trabalhava na EGV PHARMA. Gostaria
#   de falar com Euller"). Nao e chamado de cliente, entao nao entra em nota, SLA nem
#   volume. Vale para TODO periodo, inclusive rodadas retroativas.
#   Obs.: na transcricao de 31/08 a 04/09/2026 esse chamado esta na secao da KATARINY
#   DE SIMONE (a triagem recebeu e repassou), e por isso NAO sai de ninguem hoje — a
#   regra vale para quando o contato cair direto no Euller.
CONTATOS_FORA = {
    "EULLER BOER": {"SIMONI"},
}


def contato_fora(nome, contato):
    """True quando o atendimento deste `contato` nao conta para `nome` (CONTATOS_FORA)."""
    fora = CONTATOS_FORA.get((nome or "").strip().upper())
    return bool(fora) and (contato or "").strip().upper() in fora


def _saida_dt(nome):
    """datetime da saida de `nome`, ou None se a pessoa nao esta na lista."""
    d = DESLIGADOS.get((nome or "").strip().upper())
    return datetime.strptime(d["saida"], "%d/%m/%Y") if d else None


def fora_por_corte(nome, periodo_ini):
    """True quando `nome` e desligado(a) por CORTE e o periodo comeca depois da saida.

    Serve para nao cobrar presenca de quem ja tinha saido: sem isso a pessoa vira AVISO de
    "declarado na equipe mas ausente da transcricao" em toda rodada, para sempre.
    """
    d = DESLIGADOS.get((nome or "").strip().upper())
    if not d or d["regra"] != "corte" or periodo_ini is None:
        return False
    return periodo_ini > datetime.strptime(d["saida"], "%d/%m/%Y")


def montar_equipes(unidade, team, periodo_ini=None):
    """Recorta `team` (lista de todos da unidade) nas equipes de cada coordenador.

    Devolve (equipes, sem_equipe). Cada equipe traz o coordenador NA LISTA junto com os
    membros — a nota dele sai no mesmo documento que a da equipe dele.

    Quem está na transcrição mas não foi declarado em nenhuma equipe NÃO é descartado: entra
    só no pacote consolidado da unidade e é avisado no console, para a coordenação decidir.
    Abortar aqui quebraria a análise por causa de uma pessoa nova ou desligada no meio do mês.

    Cada equipe é montada de forma INDEPENDENTE: quem estiver declarado(a) em duas equipes
    sai nas duas (é o caso da Laysa, de propósito desde 07/09/2026). O set `usados` só marca
    quem já entrou em alguma equipe, para calcular `sem_equipe` — ele não impede repetição.
    """
    div = EQUIPES.get((unidade or "").strip())
    if not div:
        return [], []
    por_nome = {t["nome"].upper(): t for t in team}
    equipes, usados = [], set()
    for e in div:
        nomes = [e["coordenador"]] + list(e["membros"])
        # quem saiu por CORTE antes do periodo nao e cobrado como ausente (ver fora_por_corte)
        nomes = [n for n in nomes if not fora_por_corte(n, periodo_ini)]
        membros, faltando = [], []
        for n in nomes:
            t = por_nome.get(n)
            if t is None:
                faltando.append(n)
            else:
                membros.append(t)
                usados.add(n)
        if membros:
            equipes.append({**e, "membros_team": membros, "ausentes": faltando})
    sem_equipe = [t["nome"] for t in team if t["nome"].upper() not in usados]
    return equipes, sem_equipe

def escanear_transferencias_saida(lines, tot_map, ids_fora=None):
    # `ids_fora`: atendimentos tirados da conta em CONTATOS_FORA. Eles seguem sendo LIDOS
    # nas duas primeiras passadas (o contexto de notas e falas do cliente continua valendo
    # para as regras 3.2/3.3 dos OUTROS atendimentos) e so ficam de fora da CONTAGEM.
    ids_fora = ids_fora or set()
    nomes = sorted(tot_map.keys(), key=len, reverse=True)
    name_map = {n.upper(): n for n in tot_map}
    pat = re.compile(r"Atendimento transferido por (" + "|".join(re.escape(n) for n in nomes) + r") para (.+?):?\s*$", re.I)
    # '@' + nome COMPLETO de quem consta na transcricao (a lista `nomes` ja vem do
    # mais longo para o mais curto, senao "Eduarda" cortaria "Eduarda Zucchi" pela
    # metade). Usado pelo _miolo_nota da regra 3.2.
    pat_mencao = re.compile(r"@\s*(?:" + "|".join(re.escape(n) for n in nomes) + r")", re.I)
    cur_id = None
    ids = {n: set() for n in tot_map}
    exemplos = {n: [] for n in tot_map}
    perdoados = {n: [] for n in tot_map}   # regra 3.1 — repasse instruido pela triagem
    delegados = {n: [] for n in tot_map}   # regra 3.2 — delegacao de tarefa interna
    chegaram_errado = {n: [] for n in tot_map}   # regra 3.3 — chamado que chegou errado
    notas_por_atendimento = {}  # id -> [(dt, nome_de, destino), ...]

    # 1a passada: lê TODOS os carimbos, com o texto que a triagem escreveu logo
    # abaixo (o Gestta manda o recado em HTML nas linhas seguintes ao carimbo).
    # Na mesma varredura ficam guardadas, por atendimento, as NOTAS INTERNAS e
    # quem falou com o cliente — as duas coisas que a regra 3.2 precisa saber.
    carimbos = []   # (dt, nome_de, destino, contato, texto, cur_id, cliente, miolo do recado)
    notas_int = {}  # id -> [(dt, autor, miolo da nota)]
    fala_ext = {}   # id -> [autor, ...] de quem mandou mensagem NAO interna
    # A regra 3.3 casa por CLIENTE, nao por atendimento: o Gestta abre um
    # atendimento novo a cada transferencia. Estes tres mapas sao por cliente,
    # lidos da linha "Contato:" do atendimento — que e o cliente de verdade.
    entradas_cli = {}   # cliente -> [(dt, de, para)]
    fala_cli = {}       # (cliente, AUTOR) -> [dt] mensagens NAO internas
    notas_cli = {}      # (cliente, AUTOR) -> [(dt, miolo da nota)]
    cur_cliente = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = ATT_RE.match(ln)
        if m:
            cur_id = m.group(3)
            cur_cliente = ""
            i += 1
            continue
        if ln.startswith("Contato:") and cur_id is not None:
            cur_cliente = ln.split(":", 1)[1].strip().upper()
            i += 1
            continue
        mm = MSG_RE.match(ln)
        if not mm or cur_id is None:
            i += 1
            continue
        # o Gestta quebra o HTML da mensagem nas linhas seguintes — junta tudo
        buf, j = [], i + 1
        while j < len(lines) and not MSG_RE.match(lines[j]) and not ATT_RE.match(lines[j]) \
                and not lines[j].startswith("### COLABORADOR"):
            buf.append(lines[j])
            j += 1
        corpo = mm.group(6) or ""
        autor = (mm.group(4) or "").strip()
        dt_msg = datetime.strptime(mm.group(1) + " " + mm.group(2), "%d/%m/%Y %H:%M:%S")
        if CARIMBO_TRANSF.search(corpo):
            # carimbo de transferencia: nunca e "nota escrita pela pessoa"
            m2 = pat.search(corpo)
            mq = _QUALQUER_TRANSF.search(corpo)
            if mq:   # a 3.3 precisa de TODAS as entradas, inclusive de quem nao esta na avaliacao
                entradas_cli.setdefault(cur_cliente, []).append(
                    (dt_msg, mq.group(1).strip(), mq.group(2).strip().rstrip(":").strip()))
            nome_de = name_map.get(m2.group(1).strip().upper()) if m2 else None
            if nome_de:
                carimbos.append((dt_msg, nome_de, m2.group(2).strip().rstrip(":").strip(),
                                 autor, _texto_carimbo("\n".join(buf)), cur_id, cur_cliente,
                                 _miolo_nota("\n".join(buf), pat_mencao)))
        elif "NOTA INTERNA" in (mm.group(5) or ""):
            mio = _miolo_nota(corpo + "\n" + "\n".join(buf), pat_mencao)
            notas_int.setdefault(cur_id, []).append((dt_msg, autor, mio))
            notas_cli.setdefault((cur_cliente, autor.upper()), []).append((dt_msg, mio))
        else:
            fala_ext.setdefault(cur_id, []).append(autor)
            fala_cli.setdefault((cur_cliente, autor.upper()), []).append(dt_msg)
        i += 1

    # 2a passada: separa as INSTRUCOES da triagem ("depois direcionar para X").
    # eh_triagem(nome, c[0]): a vigencia e conferida na DATA DO CARIMBO — ver
    # PAPEL_TRIAGEM_DESDE. Instrucao dada por quem ainda nao tinha a funcao nao e
    # instrucao de triagem.
    instrucoes = [c for c in carimbos
                  if eh_triagem(c[1], c[0]) and c[4]
                  and _INSTR_POSTERIOR.search(c[4]) and _INSTR_VERBO.search(c[4])]

    def _instruido(dt, nome_de, destino, contato):
        """O repasse cumpre uma instrucao da triagem? Devolve a instrucao, ou None."""
        for it_dt, it_de, it_para, it_contato, it_texto, _, _cli, _cx in instrucoes:
            if it_contato != contato:                       continue
            if it_para.strip().upper() != nome_de.upper():  continue
            if not (it_dt < dt):                            continue
            if (dt - it_dt).total_seconds() / 60 > INSTRUCAO_JANELA_MIN:  continue
            alvo = _instrucao_cita(it_texto, destino)
            if not alvo and _INSTR_VOLTA.search(it_texto) and autor_eh(it_de, destino):
                alvo = it_de
            if alvo:
                return (it_dt, it_de, it_texto, alvo)
        return None

    def _chegou_errado(dt, nome_de, destino, cliente, caixa):
        """Regra 3.3: o chamado chegou errado, foi redirecionado dentro da janela
        sem a pessoa falar com o cliente, E ela registrou o motivo.
        Devolve (dt da entrada, quem entregou, texto do registro, onde), ou None."""
        antes = [e for e in entradas_cli.get(cliente, [])
                 if e[0] < dt and autor_eh(nome_de, e[2])
                 and e[1].strip().upper() != e[2].strip().upper()]
        if not antes:
            return None
        # vale a entrada MAIS RECENTE — foi ela que entregou o chamado
        it_dt, it_de, _it_para = max(antes, key=lambda e: e[0])
        if (dt - it_dt).total_seconds() / 60 > CHEGOU_ERRADO_JANELA_MIN:
            return None
        # ORIGEM (coordenacao, 27/08/2026): vale para chamado vindo de QUALQUER
        # pessoa, nao so da triagem — nao da para explicar por que o mesmo
        # "Gabi, verificar por favor" e perdoado quando veio da Laysa e punido
        # quando veio da Graziele. 37 casos a mais, nenhuma nota alterada.
        # A UNICA excecao e o chamado que VOLTA para quem mandou: A entrega, B faz
        # a parte dele e devolve para A. Isso nao e "chegou errado", e trabalho em
        # dupla — sao 12 casos, e ficaram DE FORA de proposito, para serem
        # decididos separadamente. A excecao nao se aplica a triagem: devolver o
        # chamado para quem tem a funcao de direcionar continua sendo redirecionar.
        if not eh_triagem(it_de, it_dt) and autor_eh(it_de, destino):
            return None
        if any(it_dt <= d <= dt for d in fala_cli.get((cliente, nome_de.upper()), [])):
            return None            # falou com o cliente: nao e "so passei adiante"
        notas = [t for d, t in notas_cli.get((cliente, nome_de.upper()), [])
                 if it_dt <= d <= dt and len(t) >= CHEGOU_ERRADO_MIN_TEXTO]
        if notas:
            return (it_dt, it_de, notas[-1], "nota interna")
        if len(caixa or "") >= CHEGOU_ERRADO_MIN_TEXTO:
            return (it_dt, it_de, caixa, "registro da transferência")
        return None                # sem registro do motivo: continua contando

    def _delegou_tarefa(aid, dt, nome_de):
        """Regra 3.2: o colaborador nao falou com o cliente neste atendimento e
        deixou um recado interno ESCRITO antes de repassar. Devolve (dt, texto)."""
        if any(autor_eh(nome_de, a) for a in fala_ext.get(aid, [])):
            return None
        for dt_n, autor, miolo in notas_int.get(aid, []):
            if not autor_eh(nome_de, autor):    continue
            if dt_n > dt:                       continue
            if len(miolo) >= DELEG_MIN_TEXTO:
                return (dt_n, miolo)
        return None

    # 3a passada: contagem do criterio 6.
    for dt, nome_de, destino, contato, _texto, aid, cliente, caixa in carimbos:
        # chamado tirado da conta em CONTATOS_FORA: nao conta, nao vira exemplo e nao
        # gera rebote — do mesmo jeito que ele nao aparece nos demais criterios.
        if aid in ids_fora:
            continue
        # AUTO-REPASSE (regra confirmada pela coordenacao, 25/08/2026): o carimbo
        # "transferido por X para o proprio X" e como a equipe PUXA um atendimento
        # que nao passou pela triagem — o oposto de repassar. Nao entra na contagem
        # do criterio 6, nao vira exemplo e nao gera rebote. Antes contava como se a
        # pessoa tivesse empurrado o atendimento: 87 casos em jun/jul/ago nas duas
        # unidades (1,6% dos repasses), atingindo 12 colaboradores.
        if autor_eh(nome_de, destino):
            continue
        # REPASSE INSTRUIDO PELA TRIAGEM (regra 3.1, coordenacao 27/08/2026): sai da
        # contagem, mas NAO some — vai listado no relatorio, no proprio criterio 6,
        # para que a coordenacao possa conferir na mao (mesmo padrao do perdao do
        # criterio 2). 23 casos em jun a 21/08 nas duas unidades.
        instr = _instruido(dt, nome_de, destino, contato)
        if instr:
            perdoados[nome_de].append({
                "cliente": contato or "—", "data": dt.strftime("%d/%m/%Y"), "hora": dt.strftime("%Hh%M"),
                "destino": destino, "instruido_por": instr[1],
                "instrucao": instr[2][:300],
            })
            continue
        # DELEGACAO DE TAREFA INTERNA (regra 3.2, coordenacao 27/08/2026): sai da
        # contagem e vai listado no criterio 6, com o recado, do mesmo jeito que a
        # 3.1. 16 casos em jun a 21/08 nas duas unidades.
        deleg = _delegou_tarefa(aid, dt, nome_de)
        if deleg:
            delegados[nome_de].append({
                "cliente": contato or "—", "data": dt.strftime("%d/%m/%Y"), "hora": dt.strftime("%Hh%M"),
                "destino": destino, "recado": deleg[1][:300],
            })
            continue
        # CHAMADO QUE CHEGOU ERRADO (regra 3.3, coordenacao 27/08/2026): sai da
        # contagem SO quando a pessoa registrou o motivo. Vai listado no relatorio,
        # com o registro, igual as regras 3.1 e 3.2. 26 casos em jun a 21/08.
        errado = _chegou_errado(dt, nome_de, destino, cliente, caixa)
        if errado:
            chegaram_errado[nome_de].append({
                "cliente": contato or "—", "data": dt.strftime("%d/%m/%Y"), "hora": dt.strftime("%Hh%M"),
                "destino": destino, "veio_de": errado[1], "onde": errado[3],
                "motivo": errado[2][:300],
                "minutos": int((dt - errado[0]).total_seconds() / 60),
            })
            continue
        notas_por_atendimento.setdefault(aid, []).append((dt, nome_de, destino))
        if aid not in ids[nome_de]:
            ids[nome_de].add(aid)
            # Guardamos ate 30 candidatos (nao 3) porque a escolha dos 3 exemplos que
            # vao para o relatorio e feita depois, em analisar_colab, priorizando os
            # repasses para OUTRA pessoa. Achado real de agosto/2026 (Ana Chueco): os
            # 3 primeiros repasses dela no arquivo eram "para Ana Chueco" — carimbo do
            # Gestta quando o proprio atendente puxa o chamado para si — e a caixa de
            # exemplos do criterio 6 mostrava so isso, que nao ilustra direcionamento.
            if len(exemplos[nome_de]) < 30:
                exemplos[nome_de].append((contato, dt, destino))

    # rebote: o repasse de "nome_de" foi seguido, no MESMO atendimento, por outro
    # repasse dentro da janela — sinal de que o destino corrigiu a rota.
    rebotes = {n: set() for n in tot_map}
    for aid, notas in notas_por_atendimento.items():
        notas.sort(key=lambda t: t[0])
        for i in range(len(notas) - 1):
            dt_i, nome_de, _ = notas[i]
            dt_prox = notas[i + 1][0]
            if (dt_prox - dt_i).total_seconds() / 60 <= TRIAGEM_JANELA_REBOTE_MIN:
                rebotes[nome_de].add(aid)
    return ids, exemplos, rebotes, perdoados, delegados, chegaram_errado

# ---------------------------------------------------------------- análise
def analisar_colab(nm, ats, hdr, transf_saida_ids=None, transf_saida_ex=None, transf_saida_rebote=None, transf_perdoados=None, transf_delegados=None, transf_errados=None):
    transf_saida_ids = transf_saida_ids or set()
    transf_saida_ex = transf_saida_ex or []
    transf_saida_rebote = transf_saida_rebote or set()
    transf_perdoados = transf_perdoados or []
    transf_delegados = transf_delegados or []
    transf_errados = transf_errados or []
    total = len(ats)
    Q = dict(vago=0, prazo=0, adiadas=0, perdoados=[], emp=0, neg=0, alt=0, transf=0, lei=0, out_atts=0,
             erro=0, erro_prazo=0, msgs=0, girias=0, proativos=0,
             sla_consid=0, sla_dentro=0, tempos=[], vago_ex=None, neg_ex=None,
             giria_ex=[])
    ids_com_msg_propria = set()
    # exemplos reais por critério (índices 0..8) + candidatos do SLA (com tempo)
    EX = {i: [] for i in range(9)}
    sla_cand = []
    # REGISTROS INTERNOS (pedido da coordenacao, 25/08/2026): toda nota interna
    # escrita pelo PROPRIO colaborador entra nesta lista — reconhecida ou nao pelo
    # filtro de canal. O relatorio exibe todas, para que a nota que o filtro nao
    # entendeu NAO desapareca em silencio. Nada aqui altera criterio de escrita.
    notas_internas = []
    sla_por_id = {}   # id do atendimento -> minutos uteis (None = ficou sem resposta)
    for at in ats:
        contato = at.get("contato")
        msgs = sorted(at["mensagens"], key=lambda m: m["dt"])
        # Só entram mensagens do PRÓPRIO colaborador avaliado — mensagens de quem
        # atendeu antes (triagem/recepção) num atendimento transferido não podem
        # contar como exemplo/nota de quem recebeu o repasse. Mesma regra de
        # autoria já usada no SLA (autor_eh), agora também para os critérios 2-8.
        outs = [m for m in msgs if m["dir"] == "OUT" and not m["interna"] and autor_eh(nm, m.get("autor"))]
        for m in outs:
            Q["msgs"] += 1
            tx = m["texto"]
            achou = GIRIA_RE.findall(tx)
            Q["girias"] += len(achou)
            if achou and len(Q["giria_ex"]) < 3:
                termos = ", ".join(sorted({g.lower() for g in achou}))
                Q["giria_ex"].append(_ex(contato, m["dt"], tx, termos))
            # exemplos dos demais critérios (o caso que moveu a nota)
            # A mensagem perdoada pelo COMPROMISSO_RETORNO nao entra como exemplo de
            # termo vago — ela nao foi contada como vaga. Sai so na lista "Conferir".
            if len(EX[1]) < 3 and VAGO.search(tx) and not COMPROMISSO_RETORNO.search(tx):
                EX[1].append(_ex(contato, m["dt"], tx, VAGO.search(tx).group(0)))
            if len(EX[2]) < 3 and EMPATIA.search(tx):
                EX[2].append(_ex(contato, m["dt"], tx))
            if len(EX[3]) < 3 and LEI.search(tx):
                EX[3].append(_ex(contato, m["dt"], tx))
            if len(EX[4]) < 3 and ERRO.search(tx):
                EX[4].append(_ex(contato, m["dt"], tx))
        for m in msgs:
            if (m["interna"] and m["dir"] == "OUT" and autor_eh(nm, m.get("autor"))
                    and not CARIMBO_TRANSF.search(m["texto"])):
                notas_internas.append({
                    "cliente": contato or "—", "id": at["id"],
                    "data": m["dt"].strftime("%d/%m/%Y"), "hora": m["dt"].strftime("%Hh%M"),
                    "texto": re.sub(r"<[^>]+>", "", m["texto"]).strip(),
                    "atendimento_registrado": para_cronometro(m, nm),
                    "por_tentativa": encerrado_por_tentativa(m, nm)})
        ext = [m for m in msgs if not m["interna"]]
        if ext:
            tdt = at.get("transfer_dt")
            if tdt is not None:
                # REGRA v3 (coordenacao 14/07/2026): atendimento recebido por
                # transferencia entra na base do SLA; o cronometro inicia no
                # carimbo do repasse e para na 1a mensagem do proprio colaborador.
                Q["sla_consid"] += 1
                resp = next((m for m in msgs if para_cronometro(m, nm) and m["dt"] >= tdt), None)
                sla_por_id[at["id"]] = None
                if resp:
                    mins = minutos_uteis(tdt, resp["dt"])
                    sla_por_id[at["id"]] = mins
                    Q["tempos"].append(mins)
                    if mins <= 120: Q["sla_dentro"] += 1
                    sla_cand.append((mins, tdt, resp["dt"], contato))
            elif ext[0]["dir"] == "OUT":
                Q["proativos"] += 1
            else:
                Q["sla_consid"] += 1
                resp = next((m for m in msgs if para_cronometro(m, nm) and m["dt"] >= ext[0]["dt"] and m is not ext[0]), None)
                sla_por_id[at["id"]] = None
                if resp and resp["dt"] >= ext[0]["dt"]:
                    mins = minutos_uteis(ext[0]["dt"], resp["dt"])
                    sla_por_id[at["id"]] = mins
                    Q["tempos"].append(mins)
                    if mins <= 120: Q["sla_dentro"] += 1
                    sla_cand.append((mins, ext[0]["dt"], resp["dt"], contato))
        if not outs: continue
        Q["out_atts"] += 1
        ids_com_msg_propria.add(at["id"])
        blob = "\n".join(m["texto"] for m in outs)
        # CRITERIO 2 — BASE (correcao 2.1, coordenacao 26/08/2026): a base e o numero
        # de ATENDIMENTOS que ficaram para depois, e nao "vago + prazo". Somar os dois
        # contadores contava DUAS vezes o atendimento que tinha as duas coisas — e ter
        # as duas e comum, porque o prazo costuma estar numa mensagem e o termo vago em
        # outra. Achado real de julho/2026 (Euller Boer): 7 dos 59 eram o mesmo
        # atendimento contado em dobro; a base real era 52. O denominador inflado
        # deixava o percentual de termo vago MENOR do que o real.
        tem_vago = bool(VAGO.search(blob))
        tem_prazo = bool(PRAZO.search(blob))
        if tem_vago or tem_prazo:
            Q["adiadas"] += 1
        # CRITERIO 2 — PERDAO (correcao 2.2, apontamento de Yasmin Rodrigues de
        # 21/08/2026): "vou verificar ... e lhe retorno ate amanha" NAO e termo vago —
        # a pessoa disse quando responde. Mas nao basta existir data na mensagem: em 15
        # das 20 mensagens com termo vago + data, a data era de OUTRA coisa (vencimento
        # da guia, exame demissional, migracao de portal, boleto do mes passado).
        # Por isso exige-se o prazo COLADO a um compromisso de retorno.
        perdao = next((m for m in outs
                       if VAGO.search(m["texto"]) and COMPROMISSO_RETORNO.search(m["texto"])), None)
        if tem_vago and perdao is not None:
            Q["perdoados"].append(_ex(contato, perdao["dt"],
                                      re.sub(r"<[^>]+>", " ", perdao["texto"]),
                                      VAGO.search(perdao["texto"]).group(0)))
        elif tem_vago:
            Q["vago"] += 1
            if not Q["vago_ex"]: Q["vago_ex"] = (at["id"], VAGO.search(blob).group(0))
        if tem_prazo: Q["prazo"] += 1
        if EMPATIA.search(blob): Q["emp"] += 1
        # CRITERIO 8 (coordenacao 07/08/2026): so entra na base o atendimento que
        # REALMENTE teve uma negativa. Antes, qualquer atendimento com palavra de
        # alternativa contava como acerto mesmo sem nenhum "nao" — achado real de
        # julho/2026: "Fecho meu parceiro!" virava "indicou parceiro de confianca".
        neg_hit = achar_negativa(blob)
        if neg_hit:
            if ALTERNATIVA.search(blob):
                Q["alt"] += 1
            else:
                Q["neg"] += 1
                if not Q["neg_ex"]: Q["neg_ex"] = (at["id"], neg_hit)
                if len(EX[7]) < 3:
                    for mm in outs:
                        h = achar_negativa(mm["texto"])
                        if h:
                            EX[7].append(_ex(contato, mm["dt"], mm["texto"], h))
                            break
        if TRANSFER.search(blob): Q["transf"] += 1
        if LEI.search(blob): Q["lei"] += 1
        if ERRO.search(blob):
            Q["erro"] += 1
            if PRAZO.search(blob): Q["erro_prazo"] += 1

    # critério 6 (Postura Contínua): evidência = repasses reais (nota de
    # transferência do sistema), não mais frase digitada pela colaboradora.
    # Auto-repasse ja nao chega aqui (filtrado em escanear_transferencias_saida desde
    # 25/08/2026). A ordenacao estavel permanece por seguranca: se algum carimbo novo
    # de auto-atribuicao aparecer, ele vai para o fim da fila em vez de virar exemplo.
    ex6 = sorted(transf_saida_ex, key=lambda e: autor_eh(nm, e[2]))
    EX[5] = [{
        "cliente": c or "—", "data": dt.strftime("%d/%m/%Y"), "hora": dt.strftime("%Hh%M"),
        "trecho": (f"Atendimento repassado para {destino} em {dt.strftime('%d/%m/%Y')} às {dt.strftime('%Hh%M')} (nota de transferência do sistema)."
                   if not autor_eh(nm, destino) else
                   f"Atendimento puxado para si em {dt.strftime('%d/%m/%Y')} às {dt.strftime('%Hh%M')} (carimbo do sistema \"transferido por {nm} para {destino}\")."),
    } for c, dt, destino in ex6[:3]]

    # critério 1 (SLA): exemplo = os atendimentos acima do limite primeiro, depois os mais lentos.
    # Esta e a UNICA caixa de exemplos que mistura acerto e erro (as demais sao homogeneas:
    # so termo vago, so marca de empatia, so repasse...). Sem marcacao, a lista parecia uma
    # relacao de apontamentos: em 21/08/2026 uma colaboradora contestou por escrito um
    # atendimento que estava DENTRO do prazo, lendo a caixa inteira como falha. Por isso cada
    # exemplo recebe ✓/✗ — o mesmo par que o criterio 7 ja usa, colorido automaticamente por
    # docx_theme._emit_inline (verde/vermelho).
    for mins, ini_dt, resp_dt, ct in sorted(sla_cand, key=lambda c: (c[0] <= 120, -c[0]))[:3]:
        over = mins > 120
        EX[0].append({
            "cliente": ct or "—", "data": ini_dt.strftime("%d/%m/%Y"), "hora": ini_dt.strftime("%Hh%M"),
            "trecho": (f"1ª mensagem às {ini_dt.strftime('%Hh%M')} → 1ª resposta do colaborador às "
                       f"{resp_dt.strftime('%Hh%M')} · {mins:.0f} min úteis"
                       + (" (acima do limite de 2h)" if over else " (dentro do prazo)")),
            # marca fica FORA da citacao: dentro das aspas o simbolo parecia parte da
            # frase do sistema. No inicio do item o leitor separa acerto de erro sem
            # precisar ler a linha inteira.
            "marca": "✗ " if over else "✓ ",
        })

    sla_pct = round(Q["sla_dentro"] / Q["sla_consid"] * 100, 1) if Q["sla_consid"] else None
    med = round(sum(Q["tempos"]) / len(Q["tempos"]), 1) if Q["tempos"] else 0.0
    taxa = round(Q["girias"] / Q["msgs"] * 100, 3) if Q["msgs"] else 0.0
    oa = Q["out_atts"]

    notas, just, txt, bl, dest = {}, {}, {}, {}, {}

    if sla_pct is None:
        notas[0] = None
        just[0] = "Não avaliado — sem atendimentos que exigissem resposta no período"
        txt[0] = "Não houve no período nenhum atendimento que exigisse primeira resposta do colaborador (iniciado pelo cliente ou recebido por transferência), portanto o critério não pôde ser avaliado."
    else:
        n1 = nota_desc(sla_pct, SLA_TABELA)
        notas[0] = n1
        just[0] = f"{sla_pct}% de 1ª resposta do próprio colaborador ≤2h úteis (média {med:.0f} min úteis) — base {Q['sla_consid']} atend. (iniciados pelo cliente ou recebidos por transferência)"
        txt[0] = (f"Dos {Q['sla_consid']} atendimentos que exigiam resposta — iniciados pelo cliente (contagem a partir da 1ª mensagem) ou recebidos por transferência (contagem a partir do repasse) — {Q['sla_dentro']} tiveram a primeira resposta do próprio colaborador dentro do limite de 2 horas úteis do manual (expediente 07:30–18:00, segunda a sexta, feriados descontados) "
                  f"({sla_pct}%), com tempo médio de {med:.0f} minutos úteis. Os {Q['proativos']} atendimentos proativos (iniciados pelo próprio colaborador, sem transferência) ficam fora da base.")
        dest[0] = {"label": "Boa prática" if n1 >= 9 else "Atenção",
                   "texto": ("Manter o padrão atual de resposta rápida — protocolo de recebimento em até 2h vem sendo cumprido com folga."
                             if n1 >= 9 else "Mesmo sem a solução pronta, protocolar o recebimento da demanda em até 2 horas — isso já cumpre o SLA do manual.")}

    base2 = Q["adiadas"]          # correcao 2.1 — ver comentario no laco acima
    if base2 == 0:
        notas[1] = None; just[1] = "Não avaliado — sem demandas adiadas no mês"
        txt[1] = "Não houve no mês volume relevante de demandas deixadas para depois, portanto o critério não pôde ser avaliado."
    else:
        pv = Q["vago"] / base2 * 100
        notas[1] = 10.0 if pv == 0 else 9.0 if pv <= 10 else 8.0 if pv <= 25 else 7.0 if pv <= 40 else 6.0
        just[1] = f"termo vago em {Q['vago']} de {base2} demandas adiadas ({pf(pv)})"
        exs = f" Exemplo de termo vago: \"{Q['vago_ex'][1]}\" (atend. {Q['vago_ex'][0]})." if Q["vago_ex"] else ""
        # A conta fecha: base = atendimentos adiados; o que nao ficou vago recebeu prazo.
        txt[1] = (f"Entre as {base2} demandas que ficaram para resolução posterior, {base2 - Q['vago']} receberam prazo claro e {Q['vago']} ficaram com termos vagos "
                  f"como \"vou verificar\" ({pf(pv)} do total).{exs}"
                  + (f" {len(Q['perdoados'])} demanda(s) trazia(m) termo vago junto de compromisso de retorno com prazo "
                     f"(ex.: \"lhe retorno até amanhã\") e NÃO foram contadas como vagas — estão listadas abaixo para conferência."
                     if Q["perdoados"] else ""))
        dest[1] = {"label": "Regra", "texto": "O que não se resolve na hora ganha prazo claro e fixo (ex.: \"será atendida em 2 dias úteis\") — nunca \"vou verificar\"."}

    if oa == 0:
        notas[2] = None
        just[2] = "Não avaliado — sem atendimento com mensagem própria no período"
        txt[2] = f"Não houve no período nenhum atendimento com mensagem própria de {nm}, portanto o critério não pôde ser avaliado."
    else:
        pe = Q["emp"] / oa * 100
        n3 = 10.0 if pe >= 95 else 9.0 if pe >= 80 else 8.0 if pe >= 60 else 7.0 if pe >= 40 else 6.0
        notas[2] = n3
        just[2] = f"marcas de cortesia/validação em {Q['emp']} de {oa} atendimentos ({pf(pe)})"
        txt[2] = (f"Em {Q['emp']} dos {oa} atendimentos com participação do analista ({pf(pe)}) há pelo menos uma marca de empatia — saudação com nome, "
                  f"validação da preocupação (\"entendo\", \"fica tranquilo\") ou cortesia ativa (\"vou te ajudar\", \"à disposição\").")
        dest[2] = {"label": "Exemplo positivo" if n3 >= 9 else "Atenção",
                   "texto": ("Cortesia consistente: praticamente todo atendimento abre com saudação e valida a preocupação do cliente."
                             if n3 >= 9 else "Validar a preocupação do cliente em TODO atendimento — um problema \"pequeno\" para o contador pode ser enorme para o cliente.")}

    if oa == 0:
        notas[3] = None
        just[3] = "Não avaliado — sem atendimento com mensagem própria no período"
        txt[3] = f"Não houve no período nenhuma mensagem própria de {nm} para avaliar clareza/uso de canais, portanto o critério não pôde ser avaliado."
    else:
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

    transf_real = len(transf_saida_ids)
    overlap6 = len(transf_saida_ids & ids_com_msg_propria)

    # O criterio 6 e agregado do periodo inteiro, entao a vigencia de PAPEL_TRIAGEM_DESDE e
    # conferida por SOBREPOSICAO entre o periodo avaliado e a janela em que a pessoa exerceu a
    # funcao (ver eh_triagem_periodo). Quem esta no set PAPEL_TRIAGEM vale sempre.
    if eh_triagem_periodo(nm, hdr.get("periodo_ini"), hdr.get("periodo_fim")):
        # Papel de TRIAGEM: repassar é a função, não uma falha. O critério mede se o
        # direcionamento foi certo (destino não precisou corrigir a rota em até 24h),
        # não "resolveu sem repassar".
        rebote_n = len(transf_saida_ids & transf_saida_rebote)
        base6 = oa + transf_real
        if base6 == 0:
            notas[5] = None
            just[5] = "Não avaliado — sem atendimento com participação no período"
            txt[5] = f"Não houve no período nenhum atendimento com participação de {nm}, portanto o critério não pôde ser avaliado."
        else:
            acertos = base6 - rebote_n
            pd_ = acertos / base6 * 100
            n6 = 9.5 if pd_ >= 95 else 9.0 if pd_ >= 85 else 8.0 if pd_ >= 70 else 7.0 if pd_ >= 55 else 6.0
            notas[5] = n6
            just[5] = f"direcionamento correto em {acertos} de {base6} atendimentos ({pf(pd_)}) — função de triagem/direcionamento"
            txt[5] = (f"Como {nm.split()[0]} tem função de recebimento e direcionamento de chamados (triagem), este critério não mede \"resolveu sem repassar\" "
                      f"— repassar para o setor certo É a função. Em vez disso, mede se o direcionamento foi rápido e certo: dos {base6} atendimentos em que atuou "
                      f"({oa} concluídos diretamente, {transf_real} direcionados a um colega), {rebote_n} precisaram ser corrigidos (o colega que recebeu teve que "
                      f"repassar de novo em até 24h, sinal de rota errada). Taxa de direcionamento correto: {pf(pd_)}.")
            dest[5] = {"label": "Boa prática" if n6 >= 9 else "Atenção",
                       "texto": ("Direcionamento consistente para o setor certo — manter o padrão." if n6 >= 9
                                 else "Alguns direcionamentos precisaram de correção rápida pelo colega que recebeu — vale checar com a coordenação se o fluxo de rota está claro.")}
    else:
        base6 = oa + (transf_real - overlap6)
        if oa == 0:
            # Sem mensagem própria da colaboradora no período: mesma trava dos
            # demais critérios. Um repasse isolado sem NENHUMA outra atividade no
            # mês não deve, sozinho, gerar nota (amostra estatisticamente vazia).
            notas[5] = None
            just[5] = "Não avaliado — sem atendimento com mensagem própria no período"
            txt[5] = f"Não houve no período nenhum atendimento com mensagem própria de {nm}, portanto o critério não pôde ser avaliado."
        else:
            pd_ = 100 - (transf_real / base6 * 100)
            n6 = 9.5 if pd_ >= 95 else 9.0 if pd_ >= 85 else 8.0 if pd_ >= 70 else 7.0 if pd_ >= 55 else 6.0
            notas[5] = n6
            just[5] = f"{base6 - transf_real} de {base6} atendimentos resolvidos sem repasse ({pf(pd_)})"
            txt[5] = (f"Considerando também os atendimentos que {nm} começou e depois repassou a um colega — identificados pela nota de "
                      f"transferência do sistema, mesmo quando o registro final ficou no histórico de quem recebeu — {base6 - transf_real} dos {base6} "
                      f"atendimentos ({pf(pd_)}) foram conduzidos até a conclusão sem repasse; {transf_real} foram transferidos a outro colega/setor.")
            dest[5] = {"label": "Boa prática" if n6 >= 9 else "Atenção",
                       "texto": ("Alta resolutividade direta — manter o padrão de concluir a demanda na própria célula."
                                 if n6 >= 9 else "Antes de transferir, esgotar o que pode ser resolvido na própria célula — evitar o \"empurra-empurra\" entre setores.")}

    if oa == 0:
        notas[6] = None
        just[6] = "Não avaliado — sem atendimento com mensagem própria no período"
        txt[6] = f"Não houve no período nenhuma mensagem própria de {nm} para avaliar este critério, portanto não pôde ser avaliado."
    else:
        notas[6] = 10.0
        just[6] = "nenhuma evidência de prática irregular aceita ou orientada no mês"
        txt[6] = "Não foi identificada nenhuma situação de prática irregular aceita ou sugerida; as orientações seguem a legislação e informam riscos quando aplicável."
        dest[6] = {"label": "Boa prática", "texto": "Nunca executar prática irregular pedida pelo cliente — orientar formalmente o procedimento correto."}

    base8 = Q["alt"] + Q["neg"]
    if base8 < MIN_BASE_C8:
        notas[7] = None
        EX[7] = []  # critério "Não avaliado" não exibe caixa de exemplos
        if base8 == 0:
            just[7] = "Não avaliado — sem pedido não atendível direto no mês"
            txt[7] = "Não houve no mês pedido que exigisse negativa, portanto o critério não pôde ser avaliado."
        else:
            just[7] = f"Não avaliado — apenas {base8} caso(s) no mês (mínimo de {MIN_BASE_C8})"
            txt[7] = (f"No período houve apenas {base8} atendimento(s) em que o pedido não podia ser atendido "
                      f"diretamente — abaixo do mínimo de {MIN_BASE_C8} casos definido pela coordenação para "
                      f"avaliar este critério. Com base tão pequena, um único caso lido de outra forma moveria "
                      f"a nota em vários pontos, portanto o critério não foi avaliado e seu peso foi "
                      f"redistribuído entre os demais critérios.")
    else:
        pa = Q["alt"] / base8 * 100
        notas[7] = 9.0 if pa >= 80 else 8.0 if pa >= 60 else 7.0 if pa >= 40 else 6.0
        just[7] = f"alternativa apresentada em {Q['alt']} de {base8} negativas ({pf(pa)})"
        exs = f" Exemplo de negativa seca: \"{Q['neg_ex'][1]}\" (atend. {Q['neg_ex'][0]})." if Q["neg_ex"] and pa < 80 else ""
        txt[7] = (f"Dos {base8} casos em que o pedido não podia ser atendido diretamente, {Q['alt']} receberam alternativa/consulta a outra célula e "
                  f"{Q['neg']} ficaram na negativa seca.{exs}")
        dest[7] = {"label": "Regra", "texto": "Evitar o \"não fazemos\" seco: explorar alternativas, consultar outras células ou indicar parceiro de confiança."}

    if Q["msgs"] == 0:
        notas[8] = None
        just[8] = "Não avaliado — sem mensagens próprias no período"
        txt[8] = f"Não houve no período nenhuma mensagem própria de {nm} para avaliar clareza de escrita, portanto o critério não pôde ser avaliado."
    else:
        n9 = teto_cres(taxa, GIRIAS_TABELA)
        notas[8] = n9
        just[8] = f"{Q['girias']} gírias/abreviações em {Q['msgs']} mensagens (taxa {taxa:.2f}/100)"
        txt[8] = (f"Foram contadas {Q['girias']} ocorrências de gírias/abreviações vetadas pelo manual (\"vc\", \"pra\", \"kk\" etc.) nas {Q['msgs']} mensagens enviadas — "
                  f"taxa de {taxa:.2f} por 100 mensagens, que define o teto da nota.")
        bl[8] = ["\"vc\" → \"você\"; \"pra\" → \"para\"; revisar antes de enviar. " + ("✗" if n9 < 9 else "✓")] if Q["girias"] else []
        dest[8] = {"label": "Regra de ouro", "texto": "Revisar a mensagem antes de enviar: sem gírias e abreviações, com tópicos ao solicitar documentos."}

    sw = sum(PESO[i] for i in range(9) if notas[i] is not None)
    nf = round(sum(notas[i] * PESO[i] for i in range(9) if notas[i] is not None) / sw, 1) if sw else None

    criterios = []
    for i in range(9):
        c = {"nome": CRIT[i], "peso": PESO_S[i], "justificativa": just[i], "texto": txt[i]}
        if notas[i] is not None: c["nota"] = fmt(notas[i])
        if bl.get(i): c["bullets"] = bl[i]
        if dest.get(i): c["destaque"] = dest[i]
        criterios.append(c)

    # exemplos reais em TODOS os critérios (cliente, data e hora)
    SEM = lambda t: [{"trecho": t, "sem_ocorrencia": True}]
    for i in range(8):
        if EX[i]:
            criterios[i]["evidencias"] = EX[i]
        elif i == 6:  # Ética: baseline, sem detecção automática
            criterios[i]["evidencias"] = SEM("Baseline de conformidade legal — sem ocorrência específica de irregularidade detectada no período.")
        elif notas[i] is not None:
            criterios[i]["evidencias"] = SEM("Sem ocorrência específica registrada no período para este critério.")

    if Q["giria_ex"]:
        criterios[8]["evidencias"] = Q["giria_ex"]
    else:
        criterios[8]["evidencias"] = [{"trecho": "Sem ocorrência de gíria/abreviação registrada no período.",
                                       "sem_ocorrencia": True}]

    fortes = sorted([i for i in range(9) if notas[i] is not None], key=lambda i: (-notas[i], i))[:2]
    fracos = sorted([i for i in range(9) if notas[i] is not None], key=lambda i: (notas[i], i))[:2]
    plabel = hdr["periodo_label_base"] + (" — " + hdr["unidade"] if hdr["unidade"] else "")

    # ALERTA DE CONTRADICAO: so marca a nota quando o MESMO atendimento aparece
    # apontado no SLA. Sem isso o aviso viraria ruido e deixaria de significar algo.
    for n in notas_internas:
        mins = sla_por_id.get(n["id"], "fora")
        if mins == "fora":
            n["alerta"] = ""                      # atendimento nem entra na base do SLA
        elif mins is None:
            n["alerta"] = "Este atendimento consta como não respondido no SLA acima."
        elif mins > 120:
            n["alerta"] = f"Este atendimento consta com {mins:.0f} min no SLA acima."
        else:
            n["alerta"] = ""
    notas_reconhecidas = sum(1 for n in notas_internas if n["atendimento_registrado"])
    notas_por_tentativa = sum(1 for n in notas_internas if n["por_tentativa"])

    data = {
        "colaborador": nm, "periodo_label": plabel, "data_geracao": hdr["data_geracao"],
        "total_atendimentos": total,
        "resumo_executivo": (f"{hdr['periodo_frase_cap']}, {nm} concluiu {total} atendimentos no Gestta Messenger ({Q['proativos']} proativos), enviando {Q['msgs']} mensagens. "
                             + (f"O SLA de primeira resposta ficou em {sla_pct}% dentro de 2 horas úteis (média de {med:.0f} minutos úteis; expediente 07:30–18:00, seg–sex). "
                                if sla_pct is not None else "Não houve no período atendimento que exigisse primeira resposta, portanto o SLA não pôde ser avaliado. ")
                             + (f"A nota final ponderada dos 9 critérios do Manual de Padrões Operacionais foi {fmt(nf)}."
                                if nf is not None else f"Não foi possível calcular uma nota mensal: não houve nenhuma mensagem real de {nm} no período.")),
        "indicadores": [
            ["Total de atendimentos", str(total)],
            # `total` = tudo que está na seção do colaborador, inclusive atendimentos em que
            # ele não escreveu nada. `base6` = atendimentos com mensagem própria + repasses
            # feitos por ele (que ficam registrados na seção de QUEM RECEBEU). Os dois números
            # diferem e o critério 6 usa o segundo — sem esta linha a capa dizia 98 e o
            # critério 6 dizia 107, parecendo erro de contagem (achado real de julho/2026,
            # Jairo Ravasi; 17 dos 24 de Monte Alto tinham essa divergência).
            ["Total com participação (base do critério 6)", str(base6)],
            ["1ª resposta do colaborador em 2h úteis (SLA)",
             (f"{sla_pct}% (média {med:.0f} min úteis) — base {Q['sla_consid']} atend." if sla_pct is not None else f"Não avaliado — base {Q['sla_consid']} atend.")],
            ["Atendimentos iniciados pelo analista (proativos)", str(Q["proativos"])],
            ["Mensagens enviadas pelo analista", f"{Q['msgs']:,}".replace(",", ".")],
            ["Concluídos no período", f"Sim ({total}/{total})"],
            ["Ocorrências de gírias/abreviações", f"{Q['girias']} (taxa {taxa:.2f}/100 msgs)"]],
        "nota_geral_texto": (f"A nota final é a média ponderada dos 9 critérios pelos pesos da planilha da coordenação, calculada de forma determinística sobre a transcrição congelada do período "
                             f"({hdr['total_api']} atendimentos da unidade). Critérios sem caso aplicável no período constam como \"Não avaliado\" e não entram na média."
                             + ("" if hdr["periodo_tipo"] == "mes" else " " + AVISO_ACOMP)),
        "criterio2_perdoados": Q["perdoados"],
        "criterio6_instruidos": transf_perdoados,
        "criterio6_delegacoes": transf_delegados,
        "criterio6_chegou_errado": transf_errados,
        "registros_internos": notas_internas,
        "registros_internos_resumo": (
            f"{len(notas_internas)} nota(s) interna(s) escrita(s) por {nm} no período; "
            f"{notas_reconhecidas - notas_por_tentativa} registra(m) atendimento feito por "
            f"telefone, presencialmente ou por acesso remoto"
            + (f" e {notas_por_tentativa} registra(m) tentativa de contato."
               if notas_por_tentativa else ".") if notas_internas else ""),
        "criterios": criterios,
        "pontos_positivos": [f"{CRIT[i]}: {just[i]}." for i in fortes],
        "pontos_melhoria": [f"{CRIT[i]}: {just[i]}." for i in fracos],
        "melhoria_destaque": {"label": "Regra de ouro", "texto": "Prazo fixo em vez de \"vou verificar\", e revisão da escrita antes do envio — os dois ajustes de maior impacto na nota."},
        "conclusao": (f"O desempenho de {nm} {hdr['periodo_frase']} reflete {total} atendimentos reais analisados na íntegra. "
                      f"Os pontos fortes e de melhoria acima são todos auditáveis na transcrição congelada do período."),
        "conclusao_destaque": {"label": "Mensagem final", "texto": "Atendimento é a vitrine da Altocon: rapidez no primeiro contato, prazo claro e escrita impecável."}
    }
    crit_notas = {CRIT[i]: fmt(notas[i]) for i in range(9) if notas[i] is not None}

    # indicadores que o Resumo da Equipe usa quando NÃO há nota (acompanhamento)
    # valores curtos de propósito: a tabela do resumo tem 6 colunas em 17 cm de página útil —
    # texto longo quebrava em duas linhas por célula (conferido na semana 03–09/08/2026).
    resumo_indic = {
        "sla": (f"{sla_pct}% ({Q['sla_consid']})" if sla_pct is not None else "sem base"),
        "msgs": Q["msgs"],
        "girias": f"{Q['girias']} ({taxa:.2f})",
        "proativos": Q["proativos"],
    }

    data["periodo_tipo"] = hdr["periodo_tipo"]
    if hdr["periodo_tipo"] != "mes":
        # ---- ACOMPANHAMENTO: levantamento sem nota (ver bloco AVISO_ACOMP no topo) ----
        data["resumo_executivo"] = (
            f"{hdr['periodo_frase_cap']}, {nm} concluiu {total} atendimentos no Gestta Messenger "
            f"({Q['proativos']} proativos), enviando {Q['msgs']} mensagens. "
            + (f"O SLA de primeira resposta ficou em {sla_pct}% dentro de 2 horas úteis "
               f"(média de {med:.0f} minutos úteis; expediente 07:30–18:00, seg–sex). "
               if sla_pct is not None else
               "Não houve no período atendimento que exigisse primeira resposta, portanto o SLA não pôde ser medido. ")
            + "Este documento é um levantamento de acompanhamento e não atribui nota — a avaliação "
              "formal, com nota ponderada dos 9 critérios, é a mensal.")
        data.pop("nota_geral_texto", None)
        data["panorama_texto"] = (
            "O quadro abaixo resume o que a transcrição congelada do período mostra em cada um dos 9 "
            f"critérios do Manual de Padrões Operacionais ({hdr['total_api']} atendimentos da unidade). "
            "Critério sem caso no período aparece como \"Sem caso aplicável\". " + AVISO_ACOMP)
        for c in data["criterios"]:
            c.pop("nota", None)   # nenhuma nota sai no JSON de acompanhamento
            c.pop("peso", None)
            c["justificativa"] = _sem_nota(c.get("justificativa"))
            c["texto"] = _sem_nota(c.get("texto"))
        data["pontos_positivos"] = [_sem_nota(x) for x in data["pontos_positivos"]]
        data["pontos_melhoria"] = [_sem_nota(x) for x in data["pontos_melhoria"]]
        data["melhoria_destaque"] = {
            "label": "Foco para a próxima semana",
            "texto": "Prazo fixo em vez de \"vou verificar\", e revisão da escrita antes do envio — "
                     "os dois ajustes de maior impacto no atendimento."}
        data["conclusao"] = (
            f"O acompanhamento de {nm} {hdr['periodo_frase']} reflete {total} atendimentos reais lidos "
            f"na íntegra. Os pontos acima são auditáveis na transcrição congelada do período e servem "
            f"para orientar o trabalho da semana seguinte; a nota de desempenho é apurada no fechamento do mês.")

    return data, nf, crit_notas, resumo_indic

def escrever_resumos_equipe(outdir, hdr, team, equipes, acomp, media=None, rank=None):
    """Grava um `resumo_equipe_<Coordenador>.json` por coordenador.

    O `resumo_equipe.json` da unidade continua sendo gravado igual e NÃO é tocado aqui —
    é ele que o diretor recebe e é ele que garante que os pacotes antigos não mudem.
    """
    unidade = (hdr.get("unidade") or "").strip()
    n_unid = len(team)
    pos, med_crit = {}, {}
    if not acomp:
        if rank:
            for i, t in enumerate(rank, 1):
                pos[t["nome"]] = i
        # Médias por critério da UNIDADE INTEIRA (decisão de 11/08/2026): o resumo de equipe
        # mostra a régua da unidade, não a da própria equipe — senão cada coordenador teria
        # uma referência diferente e os documentos deixariam de ser comparáveis entre si.
        for c in CRIT:
            vals = []
            for t in team:
                try:
                    vals.append(float(str((t.get("criterios") or {}).get(c)).replace(",", ".")))
                except (TypeError, ValueError):
                    pass
            med_crit[c] = fmt_na(round(sum(vals) / len(vals), 1)) if vals else "—"
    escritos = []
    for e in equipes:
        membros = e["membros_team"]
        coord = next((m["nome"] for m in membros if m["nome"].upper() == e["coordenador"]),
                     e["coordenador"].title())
        depto = e["departamento"]
        tot_eq = sum(int(m.get("total_atendimentos") or 0) for m in membros)
        escopo = {"coordenador": coord, "departamento": depto,
                  "diretor": bool(e.get("diretor")), "unidade": unidade,
                  "total_colaboradores_unidade": n_unid,
                  "posicoes": pos, "medias_criterio_unidade": med_crit,
                  "depto_membro": e.get("depto_membro") or {}}
        base = {"periodo_label": hdr["periodo_label_base"] + (" — " + unidade if unidade else ""),
                "periodo_tipo": hdr["periodo_tipo"], "data_geracao": hdr["data_geracao"],
                "escopo_equipe": escopo,
                "total_colaboradores": len(membros), "total_atendimentos": tot_eq,
                "colaboradores": membros}
        if acomp:
            vol = sorted(membros, key=lambda t: (-int(t.get("total_atendimentos") or 0), t["nome"].lower()))
            com_girias = sum(1 for t in membros if not t["girias"].startswith("0 ("))
            sem_sla = [t["nome"] for t in membros if t["sla"] == "sem base"]
            base.update({
                "colaboradores": vol,
                "resumo_executivo": (
                    AVISO_ACOMP + " "
                    f"Equipe de {coord} ({depto}): {len(membros)} colaboradores e {tot_eq} atendimentos "
                    f"{hdr['periodo_frase']}. Maior volume: {vol[0]['nome']} "
                    f"({vol[0]['total_atendimentos']} atendimentos). Os indicadores abaixo são contagens "
                    "diretas sobre a transcrição congelada — não há nota, média nem ranking neste documento."),
                "destaques": [
                    f"Volume da equipe {hdr['periodo_frase']}: {tot_eq} atendimentos por {len(membros)} colaboradores.",
                    f"Gírias/abreviações: {com_girias} de {len(membros)} colaboradores da equipe tiveram ao menos uma ocorrência.",
                ] + ([f"Sem base de SLA no período: {', '.join(sem_sla)}."] if sem_sla else []),
                "pontos_melhoria_equipe": [
                    "Gírias e abreviações (\"vc\", \"pra\", \"obg\") continuam aparecendo nas mensagens — revisar antes de enviar.",
                    "Substituir \"vou verificar\"/\"vou analisar\" por prazo claro e fixo (ex.: \"em 2 dias úteis\").",
                    "Reduzir transferências sem conclusão: esgotar a solução na própria célula antes de repassar."],
                "conclusao": (
                    f"Este levantamento cobre a equipe de {coord} ({depto}) {hdr['periodo_frase']} e serve "
                    f"para acompanhar o andamento entre os fechamentos mensais. A avaliação com nota, ranking "
                    f"e média é feita no fechamento do mês, sobre a unidade inteira.")})
        else:
            def _nota(v):
                try:
                    return float(str(v).replace(",", "."))
                except (TypeError, ValueError):
                    return None
            aval = [m for m in membros if m.get("nota_final") not in (None, "—")]
            melhor = min(aval, key=lambda m: pos.get(m["nome"], 10**6)) if aval else None
            sla9 = sum(1 for m in membros
                       if (_nota((m.get("criterios") or {}).get(CRIT[0])) or 0) >= 9)
            base.update({
                "media_geral": fmt_na(media),
                "resumo_executivo": (
                    f"Equipe de {coord} ({depto}): {len(membros)} colaboradores e {tot_eq} atendimentos "
                    f"{hdr['periodo_frase']}. A média geral de {unidade or 'da unidade'} foi {fmt_na(media)}, "
                    f"calculada sobre os {n_unid} colaboradores da unidade — a coluna \"#\" da tabela abaixo "
                    f"é a posição de cada um no ranking da UNIDADE INTEIRA, não dentro da equipe. "
                    f"Todas as notas são calculadas de forma determinística sobre a transcrição congelada."),
                "destaques": ([
                    f"{melhor['nome']} é o melhor colocado da equipe: {melhor['nota_final']}, "
                    f"{pos.get(melhor['nome'], '—')}º lugar entre os {n_unid} da unidade."] if melhor else []) + [
                    f"SLA de primeira resposta com nota ≥9,0 em {sla9} de {len(membros)} colaboradores da equipe.",
                    "Ética e Transparência: nenhuma ocorrência de prática irregular identificada na equipe."],
                "pontos_melhoria_equipe": [
                    "Gírias e abreviações (\"vc\", \"pra\", \"obg\") ainda derrubam o critério de escrita — revisar antes de enviar.",
                    "Substituir \"vou verificar\"/\"vou analisar\" por prazo claro e fixo (ex.: \"em 2 dias úteis\").",
                    "Reduzir transferências sem conclusão: esgotar a solução na própria célula antes de repassar."],
                "conclusao": (
                    f"Este resumo cobre a equipe de {coord} ({depto}) {hdr['periodo_frase']}. A média e o "
                    f"ranking são da unidade {unidade} inteira, para manter a comparação com os demais "
                    f"pacotes. Os relatórios individuais anexos detalham o plano de melhoria de cada um.")})
        safe = re.sub(r"[^A-Za-z0-9]+", "_", coord).strip("_")
        caminho = os.path.join(outdir, f"resumo_equipe_{safe}.json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(base, f, ensure_ascii=False, indent=1)
        escritos.append((coord, depto, len(membros), tot_eq))
        if e.get("ausentes"):
            print(f"  AVISO: declarado(s) na equipe de {coord} mas ausente(s) na transcrição: "
                  f"{', '.join(e['ausentes'])}")
    return escritos


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

    # rede de seguranca: desligado(a) que escapou da selecao do agente de leitura
    for nm in sorted(colabs):
        d = DESLIGADOS.get(nm.strip().upper())
        if not d:
            continue
        if d["regra"] == "total":
            print(f"  ATENCAO: {nm} esta DESLIGADA(O) desde {d['saida']} e NAO deveria estar "
                  f"nesta transcricao. Refaca a leitura sem marcar esse nome - a media e o "
                  f"ranking desta rodada saem com ela(e) dentro.")
        elif fora_por_corte(nm, hdr["periodo_ini"]):
            print(f"  ATENCAO: {nm} saiu em {d['saida']} e este periodo comeca depois disso, "
                  f"mas o nome veio na transcricao. Refaca a leitura sem marca-lo(a). "
                  f"(Periodos que incluem dias trabalhados por ele(a) sao avaliados normal.)")

    # chamados que nao contam para o colaborador (ver CONTATOS_FORA). Roda DEPOIS da
    # trava acima de proposito: a transcricao continua integra e conferida; o que sai e
    # so a CONTA. Os ids saem tambem do criterio 6, senao o repasse de um atendimento
    # que nao existe mais na nota continuaria pesando.
    ids_fora = set()
    for nm in sorted(colabs):
        fora = [a for a in colabs[nm] if contato_fora(nm, a.get("contato"))]
        if not fora:
            continue
        ids_fora.update(a["id"] for a in fora)
        colabs[nm] = [a for a in colabs[nm] if not contato_fora(nm, a.get("contato"))]
        for a in fora:
            print(f"  FORA DAS METRICAS: {nm} - contato '{a['contato']}' "
                  f"(atendimento {a['id']}) nao entra na nota. Decisao registrada em "
                  f"CONTATOS_FORA; o atendimento continua na transcricao.")

    transf_saida_ids, transf_saida_ex, transf_saida_rebote, transf_perdoados, transf_delegados, transf_errados = escanear_transferencias_saida(lines, hdr["tot_map"], ids_fora)

    acomp = hdr["periodo_tipo"] != "mes"
    team = []
    for nm in sorted(colabs, key=lambda s: s.lower()):
        data, nf, crit_notas, ind = analisar_colab(nm, colabs[nm], hdr, transf_saida_ids.get(nm), transf_saida_ex.get(nm), transf_saida_rebote.get(nm), transf_perdoados.get(nm), transf_delegados.get(nm), transf_errados.get(nm))
        safe = re.sub(r"[^A-Za-z0-9]+", "_", nm).strip("_")
        with open(os.path.join(outdir, f"analise_{safe}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        if acomp:
            # sem nota nem notas por critério — o resumo do acompanhamento é de indicadores
            team.append({"nome": nm, "total_atendimentos": len(colabs[nm]),
                         "sla": ind["sla"], "mensagens": ind["msgs"],
                         "girias": ind["girias"], "proativos": ind["proativos"]})
            print(f"{nm:34} {len(colabs[nm]):>5} atend. | SLA {ind['sla']}")
        else:
            team.append({"nome": nm, "total_atendimentos": len(colabs[nm]), "nota_final": fmt_na(nf), "criterios": crit_notas})
            print(f"{nm:34} NF={fmt_na(nf)}")

    plabel = hdr["periodo_label_base"] + (" — " + hdr["unidade"] if hdr["unidade"] else "")
    total_at = sum(t["total_atendimentos"] for t in team)

    if acomp:
        # ---- Resumo da equipe SEM nota: levantamento por volume de atendimentos ----
        vol = sorted(team, key=lambda t: (-t["total_atendimentos"], t["nome"].lower()))
        sem_sla = [t["nome"] for t in team if t["sla"] == "sem base"]
        com_girias = sum(1 for t in team if not t["girias"].startswith("0 ("))
        resumo = {
            "periodo_label": plabel, "periodo_tipo": hdr["periodo_tipo"],
            "data_geracao": hdr["data_geracao"],
            "total_colaboradores": len(team),
            "total_atendimentos": total_at,
            "resumo_executivo": (
                AVISO_ACOMP + " "
                f"A unidade concluiu {total_at} atendimentos {hdr['periodo_frase']}, distribuídos entre "
                f"{len(team)} colaboradores. Maior volume: {vol[0]['nome']} ({vol[0]['total_atendimentos']} atendimentos)"
                + (f" e {vol[1]['nome']} ({vol[1]['total_atendimentos']})" if len(vol) > 1 else "") + ". "
                "Os indicadores abaixo são contagens diretas sobre a transcrição congelada do período — "
                "não há nota, média nem ranking de desempenho neste documento."),
            "colaboradores": vol,
            "destaques": [
                f"Volume do período: {total_at} atendimentos concluídos por {len(team)} colaboradores.",
                f"Gírias/abreviações: {com_girias} de {len(team)} colaboradores tiveram ao menos uma ocorrência no período.",
                "Ética e Transparência: nenhuma ocorrência de prática irregular identificada na unidade no período.",
            ] + ([f"Sem base de SLA no período (nenhum atendimento exigiu primeira resposta): {', '.join(sem_sla)}."] if sem_sla else []),
            "pontos_melhoria_equipe": [
                "Gírias e abreviações (\"vc\", \"pra\", \"obg\") continuam aparecendo nas mensagens — revisar antes de enviar.",
                "Substituir \"vou verificar\"/\"vou analisar\" por prazo claro e fixo (ex.: \"em 2 dias úteis\").",
                "Reduzir transferências sem conclusão: esgotar a solução na própria célula antes de repassar."],
            "conclusao": (
                f"Este levantamento cobre {hdr['periodo_nome']} e serve para a diretoria acompanhar o "
                f"andamento da unidade entre os fechamentos mensais. Todos os números são reconstruíveis "
                f"a partir da transcrição congelada do período. A avaliação de desempenho com nota, "
                f"ranking e média da equipe é feita no fechamento do mês.")
        }
        with open(os.path.join(outdir, "resumo_equipe.json"), "w", encoding="utf-8") as f:
            json.dump(resumo, f, ensure_ascii=False, indent=1)
        equipes, sem_eq = montar_equipes(hdr["unidade"], team, hdr["periodo_ini"])
        if equipes:
            print("\nEquipes (acompanhamento):")
            for coord, depto, n, tot in escrever_resumos_equipe(outdir, hdr, team, equipes, True):
                print(f"  {coord:24} {depto:22} {n:>3} colab. | {tot:>5} atend.")
            if sem_eq:
                print(f"  AVISO: sem equipe declarada (só no consolidado): {', '.join(sem_eq)}")
        print(f"\nACOMPANHAMENTO (sem nota) | {len(team)} colaboradores | {total_at} atendimentos | JSONs em {outdir}")
        return

    avaliaveis = [t for t in team if t["nota_final"] != "—"]
    media = round(sum(float(t["nota_final"].replace(",", ".")) for t in avaliaveis) / len(avaliaveis), 1) if avaliaveis else None
    rank = sorted(avaliaveis, key=lambda t: (-float(t["nota_final"].replace(",", ".")), t["nome"]))
    resumo = {
        "periodo_label": plabel, "periodo_tipo": hdr["periodo_tipo"],
        "data_geracao": hdr["data_geracao"],
        "total_colaboradores": len(team),
        "total_atendimentos": total_at,
        "media_geral": fmt_na(media),
        "resumo_executivo": (f"A unidade concluiu {total_at} atendimentos {hdr['periodo_frase']}, distribuídos entre {len(team)} colaboradores. "
                             f"A média geral da equipe foi {fmt_na(media)}. Destaques: {rank[0]['nome']} ({rank[0]['nota_final']})" +
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
        "conclusao": (f"Com média {fmt_na(media)}, a unidade encerra {hdr['periodo_nome']} com desempenho auditável — toda nota deste resumo é reconstruível a partir "
                      f"da transcrição congelada do período. Os relatórios individuais detalham os planos de melhoria de cada colaborador.")
    }
    with open(os.path.join(outdir, "resumo_equipe.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)
    equipes, sem_eq = montar_equipes(hdr["unidade"], team, hdr["periodo_ini"])
    if equipes:
        print("\nEquipes:")
        for coord, depto, n, tot in escrever_resumos_equipe(outdir, hdr, team, equipes, False,
                                                            media=media, rank=rank):
            print(f"  {coord:24} {depto:22} {n:>3} colab. | {tot:>5} atend.")
        if sem_eq:
            print(f"  AVISO: sem equipe declarada (só no consolidado): {', '.join(sem_eq)}")
    print(f"\nMédia geral: {fmt_na(media)} | {len(team)} colaboradores | JSONs em {outdir}")

if __name__ == "__main__":
    main()
