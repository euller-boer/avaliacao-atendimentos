#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_girias_report.py — Relatório de gírias/abreviações POR COLABORADOR.

Por que existe: a coordenação precisa VER as gírias de cada colaborador (quais
termos, quantas vezes e trechos reais) — só a contagem do critério 9 fica vaga.

Uso:
    python3 scripts/build_girias_report.py <transcricao.txt> <saida.docx>

100% determinístico: reutiliza o MESMO parser e o MESMO regex de gírias do
analisar.py, então os totais deste relatório batem exatamente com os dos
relatórios individuais. Mesma transcrição -> mesmo relatório, byte a byte.
Para cada colaborador (ordem: mais ocorrências primeiro): total, termos com
frequência e até 3 trechos reais com data e nome do contato (quando a
transcrição traz a linha "Contato:"), para localizar a conversa no Histórico
de Atendimentos do Gestta.
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collections import Counter
from docx import Document
from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import docx_theme as T
from analisar import GIRIA_RE, ler_cabecalho, parse, ATT_RE, COLAB_RE

MAX_EX = 3
CONTATO_RE = re.compile(r"^Contato: (.+)$")

def trecho(texto, m, width=140):
    ini = max(0, m.start() - width // 2)
    fim = min(len(texto), m.end() + width // 2)
    s = texto[ini:fim].replace("\n", " ").strip()
    return ("…" if ini > 0 else "") + s + ("…" if fim < len(texto) else "")

def mapear_contatos(lines):
    """id do atendimento -> nome do contato (linha 'Contato:' após o cabeçalho
    do atendimento, quando a transcrição a inclui)."""
    mapa, cur_id = {}, None
    for ln in lines:
        m = ATT_RE.match(ln)
        if m:
            cur_id = m.group(3); continue
        m = CONTATO_RE.match(ln)
        if m and cur_id and cur_id not in mapa:
            mapa[cur_id] = m.group(1).strip()
    return mapa

def main():
    if len(sys.argv) < 3:
        sys.exit("Uso: python3 scripts/build_girias_report.py <transcricao.txt> <saida.docx>")
    lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
    hdr = ler_cabecalho(lines)
    colabs = parse(lines, hdr["tot_map"])
    contatos = mapear_contatos(lines)

    dados = []
    for nm, ats in colabs.items():
        termos, exemplos, total = Counter(), [], 0
        for at in ats:
            for m in sorted(at["mensagens"], key=lambda x: x["dt"]):
                if m["dir"] != "OUT" or m["interna"]:
                    continue
                hits = list(GIRIA_RE.finditer(m["texto"]))
                if not hits:
                    continue
                total += len(hits)
                for h in hits:
                    termos[h.group(0).lower()] += 1
                if len(exemplos) < MAX_EX:
                    exemplos.append({
                        "quando": m["dt"].strftime("%d/%m/%Y %H:%M"),
                        "contato": contatos.get(at["id"], "?"),
                        "girias": ", ".join(sorted({h.group(0).lower() for h in hits})),
                        "trecho": trecho(m["texto"], hits[0])})
        dados.append({"nome": nm, "total": total, "termos": termos, "exemplos": exemplos})
    dados.sort(key=lambda x: (-x["total"], x["nome"].lower()))
    tot_g = sum(x["total"] for x in dados)

    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2.0)
    sec.top_margin = Cm(1.6); sec.bottom_margin = Cm(1.8)
    T.add_logo(doc)
    T.add_title(doc, "Gírias e Abreviações por Colaborador", size=18)
    T.add_subtitle(doc, f"{hdr['periodo_label_base']}" + (f" — {hdr['unidade']}" if hdr["unidade"] else "") +
                   "  •  Critério: Coerência na Escrita, Gírias e Informalidades")
    T.add_para(doc, f"Detecção pela mesma regra do pipeline determinístico (analisar.py) — {tot_g} ocorrências na unidade. "
                    "Somente mensagens enviadas pelo analista (notas internas fora). Trechos com data e nome do contato — "
                    "localizáveis pelo filtro do Histórico de Atendimentos do Gestta.",
               color=T.GREY_LT, size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    for x in dados:
        T.add_heading(doc, f"{x['nome']} — {x['total']} ocorrência(s)", size=12)
        if x["total"] == 0:
            T.add_para(doc, "Nenhuma gíria/abreviação vetada encontrada nas mensagens do mês. ✓", size=10.5)
            continue
        freq = "  •  ".join(f'"{t}" ×{n}' for t, n in x["termos"].most_common())
        T.add_para(doc, "Termos encontrados: " + freq, size=10, color=T.GREY_LT, space_after=4)
        rows = [[f"Ex. {i+1}", f'{e["trecho"]}\n[{e["quando"]} — contato: {e["contato"]} — gíria(s): {e["girias"]}]']
                for i, e in enumerate(x["exemplos"])]
        T.make_table(doc, ["#", "Trecho da mensagem (como enviado ao cliente)"], rows,
                     widths=[Cm(1.6), Cm(14.9)], body_size=9.5, header_size=8.5)
        T._spacer(doc, 4)
    T.setup_header_footer(doc, f"Gírias por Colaborador — {hdr['periodo_label_base']}")
    doc.save(sys.argv[2])
    print(f"OK: {sys.argv[2]} | total unidade: {tot_g}")

if __name__ == "__main__":
    main()
