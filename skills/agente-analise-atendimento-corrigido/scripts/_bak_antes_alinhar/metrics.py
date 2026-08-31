#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metrics.py — CALCULO DETERMINISTICO dos indicadores e dos criterios objetivos.

Por que este script existe
---------------------------
A divergencia de notas entre execucoes vinha de o MODELO contar indicadores
"de cabeca" e atribuir notas de 0 a 10 sem regua. Aqui, tudo o que e contavel e
calculado por CODIGO, a partir do JSON estruturado exportado pelo
agente-leitura-conversas. Mesma entrada -> MESMA saida, sempre.

O que calcula
-------------
1. INDICADORES objetivos (tabela "INDICADOR | RESULTADO" do relatorio):
   total de atendimentos, proativos, transferidos recebidos, mensagens enviadas,
   concluidos, SLA de 1a resposta (% em 2h + tempo medio).
2. NOTAS FIXAS de 2 criterios 100% contaveis, por tabela de mapeamento:
   - Criterio 1  (Tempo de Inicio / SLA)        -> do % de 1a resposta em 2h
   - Criterio 9  (Coerencia na Escrita / girias) -> da taxa de girias/abreviacoes
   (a nota 9 e um TETO por girias; o modelo pode baixa-la por gramatica, com
    evidencia, mas nunca subir acima deste teto.)

Os demais criterios (2,3,4,5,6,7,8) continuam com julgamento do modelo, porem
guiados pela RUBRICA ANCORADA do SKILL.md e com citacao obrigatoria da transcricao.

Uso
---
    python3 scripts/metrics.py atendimentos.json metrics.json

Schema de ENTRADA (atendimentos.json) — exportado pelo agente-leitura-conversas:
{
  "colaborador": "Natalia Tiesi",
  "periodo_label": "Maio/2026",
  "atendimentos": [
    {
      "id": "abc123",
      "contato": "Empresa X",
      "atendente": "Natalia Tiesi",
      "iniciado_por": "CLIENTE",        # "CLIENTE" ou "ANALISTA" (opcional; deduzido da 1a msg se ausente)
      "transferido_recebido": false,    # veio de transferencia? (opcional)
      "concluido": true,                # concluido no mes? (opcional, default true)
      "mensagens": [
        {"direcao":"INBOUND",  "tipo":"CHAT", "autor":"Cliente", "interna":false, "em":"2026-05-02T13:10:00.000Z", "texto":"..."},
        {"direcao":"OUTBOUND", "tipo":"CHAT", "autor":"Natalia", "interna":false, "em":"2026-05-02T13:35:00.000Z", "texto":"..."}
      ]
    }
  ]
}

Compatibilidade de campos (aceita variacoes da leitura):
- direcao: "direcao" | "type" | "direction"  -> normaliza p/ INBOUND/OUTBOUND
- horario: "em" | "received_at" | "created_at" | "at"
- interna: "interna" | "internal_message" | "internal"
- texto:   "texto" | "content"
"""
import json
import re
import sys
from datetime import datetime, timezone

# ----------------------------------------------------------------------------
# TABELAS DE MAPEAMENTO (a "regua" — calibre AQUI se a coordenacao quiser)
# ----------------------------------------------------------------------------

# Criterio 1 — SLA: nota a partir do % de 1a resposta dentro de 2 horas.
# Faixas fechadas (limite inferior inclusivo). Mesmo % -> sempre a mesma nota.
SLA_TABELA = [
    (98.0, 10.0),
    (95.0, 9.5),
    (90.0, 9.0),
    (85.0, 8.5),
    (80.0, 8.0),
    (75.0, 7.5),
    (70.0, 7.0),
    (60.0, 6.0),
    (50.0, 5.0),
    (40.0, 4.0),
    (0.0, 3.0),
]

# Criterio 9 — escrita: TETO de nota a partir da taxa de girias/abreviacoes
# (ocorrencias por 100 mensagens enviadas pelo analista).
GIRIAS_TABELA = [
    (0.0, 10.0),   # taxa == 0
    (0.5, 9.0),    # 0 < taxa <= 0.5
    (1.0, 8.0),
    (2.0, 7.0),
    (4.0, 6.0),
    (7.0, 5.0),
    (float("inf"), 4.0),
]

# Lista fixa de girias/abreviacoes vetadas (case-insensitive, com fronteira de
# palavra). Conta so em mensagens OUTBOUND nao internas. Edite a vontade.
GIRIAS = [
    r"vc", r"vcs", r"voce", r"pra", r"pro", r"pq", r"q",
    r"k{2,}", r"rs+", r"kk+", r"hh+", r"blz", r"vlw", r"flw",
    r"obg", r"pfv", r"pf", r"tbm", r"tb", r"qdo", r"qto", r"msg",
    r"to", r"ta", r"tava", r"neh", r"ne", r"aki", r"vamo", r"oki",
]
GIRIA_RE = re.compile(r"\b(" + "|".join(GIRIAS) + r")\b", re.IGNORECASE)

SLA_LIMITE_HORAS = 2.0

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _nota_por_tabela(valor, tabela):
    for limite, nota in tabela:
        if valor >= limite:
            return nota
    return tabela[-1][1]


def _teto_por_tabela_crescente(valor, tabela):
    for limite, nota in tabela:
        if valor <= limite:
            return nota
    return tabela[-1][1]


def fmt_nota(x):
    return f"{x:.1f}".replace(".", ",")


def fmt_pct(x):
    return f"{x:.0f}%"


def _parse_dt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _direcao(m):
    v = (m.get("direcao") or m.get("type") or m.get("direction") or "").upper()
    if v in ("OUTBOUND", "OUT", "ATENDENTE", "ANALISTA"):
        return "OUTBOUND"
    if v in ("INBOUND", "IN", "CLIENTE", "CLIENT"):
        return "INBOUND"
    return v


def _interna(m):
    return bool(m.get("interna") or m.get("internal_message") or m.get("internal"))


def _quando(m):
    return _parse_dt(m.get("em") or m.get("received_at") or m.get("created_at") or m.get("at"))


def _texto(m):
    return str(m.get("texto") or m.get("content") or "")


def _msgs_ordenadas(at):
    msgs = list(at.get("mensagens", []))
    msgs.sort(key=lambda m: (_quando(m) or datetime.min.replace(tzinfo=timezone.utc)))
    return msgs

# ----------------------------------------------------------------------------
# Calculo
# ----------------------------------------------------------------------------

def calcular(data):
    atendimentos = data.get("atendimentos", [])
    total = len(atendimentos)

    proativos = 0
    transferidos = 0
    concluidos = 0
    msgs_enviadas = 0
    girias_total = 0

    sla_consid = 0
    sla_dentro = 0
    tempos_resp_min = []

    for at in atendimentos:
        msgs = _msgs_ordenadas(at)

        if at.get("transferido_recebido"):
            transferidos += 1
        if at.get("concluido", True):
            concluidos += 1

        for m in msgs:
            if _direcao(m) == "OUTBOUND" and not _interna(m):
                msgs_enviadas += 1
                girias_total += len(GIRIA_RE.findall(_texto(m)))

        externas = [m for m in msgs if not _interna(m)]
        if not externas:
            continue
        iniciado_por = (at.get("iniciado_por") or "").upper()
        if not iniciado_por:
            iniciado_por = "ANALISTA" if _direcao(externas[0]) == "OUTBOUND" else "CLIENTE"

        if iniciado_por == "ANALISTA":
            proativos += 1
            continue

        sla_consid += 1
        t_cliente = _quando(externas[0])
        t_resp = None
        for m in externas[1:]:
            if _direcao(m) == "OUTBOUND":
                t_resp = _quando(m)
                break
        if t_cliente and t_resp and t_resp >= t_cliente:
            mins = (t_resp - t_cliente).total_seconds() / 60.0
            tempos_resp_min.append(mins)
            if mins <= SLA_LIMITE_HORAS * 60.0:
                sla_dentro += 1

    sla_pct = (sla_dentro / sla_consid * 100.0) if sla_consid else 100.0
    media_min = (sum(tempos_resp_min) / len(tempos_resp_min)) if tempos_resp_min else 0.0
    giria_taxa = (girias_total / msgs_enviadas * 100.0) if msgs_enviadas else 0.0

    nota_sla = _nota_por_tabela(sla_pct, SLA_TABELA)
    nota_escrita_teto = _teto_por_tabela_crescente(giria_taxa, GIRIAS_TABELA)

    def _tempo_label(mins):
        if mins <= 0:
            return "—"
        if mins < 60:
            return f"{mins:.0f} min"
        return f"{mins/60:.1f} h"

    indicadores = [
        ["Total de atendimentos", str(total)],
        ["1a resposta dentro de 2h (SLA)",
         f"{fmt_pct(sla_pct)} (media {_tempo_label(media_min)}, base {sla_consid} iniciados pelo cliente)"],
        ["Atendimentos iniciados pelo analista (proativos)", str(proativos)],
        ["Atendimentos transferidos (recebidos)", str(transferidos)],
        ["Mensagens enviadas pelo analista", f"{msgs_enviadas:,}".replace(",", ".")],
        ["Concluidos no mes", f"{'Sim' if concluidos == total else 'Parcial'} ({concluidos}/{total})"],
        ["Ocorrencias de girias/abreviacoes", f"{girias_total} (taxa {giria_taxa:.2f}/100 msgs)"],
    ]

    return {
        "colaborador": data.get("colaborador"),
        "periodo_label": data.get("periodo_label"),
        "indicadores": indicadores,
        "metricas_brutas": {
            "total_atendimentos": total,
            "proativos": proativos,
            "transferidos_recebidos": transferidos,
            "concluidos": concluidos,
            "mensagens_enviadas": msgs_enviadas,
            "sla_considerados": sla_consid,
            "sla_dentro_2h": sla_dentro,
            "sla_pct": round(sla_pct, 1),
            "tempo_medio_1a_resposta_min": round(media_min, 1),
            "girias_total": girias_total,
            "giria_taxa_por_100": round(giria_taxa, 3),
        },
        "notas_fixas": {
            "Tempo de Inicio do Atendimento (SLA)": fmt_nota(nota_sla),
            "Coerencia na Escrita, Girias e Informalidades (TETO por girias)": fmt_nota(nota_escrita_teto),
        },
    }


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 metrics.py <atendimentos.json> <metrics.json>", file=sys.stderr)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    out = calcular(data)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("=== INDICADORES (deterministicos) ===")
    for a, b in out["indicadores"]:
        print(f"  {a}: {b}")
    print("\n=== NOTAS FIXAS (nao dependem de julgamento) ===")
    for k, v in out["notas_fixas"].items():
        print(f"  {k}: {v}")
    print(f"\nmetrics.json salvo em: {sys.argv[2]}")


if __name__ == "__main__":
    main()
