#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o RELATÓRIO INDIVIDUAL (.docx) de análise de atendimento — tema navy/dourado.

Uso:
    python3 scripts/build_report.py analise.json "<saida>/Relatorio_<Colab>_<MM-AAAA>.docx"

Lê o schema descrito no SKILL.md (analise.json). Campos opcionais ausentes
degradam com elegância. Nunca monte o docx na mão: preencha o JSON e rode isto.
"""
import json
import sys
import os

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx_theme as T


def final_score(criterios):
    """Calcula a MÉDIA PONDERADA das notas; retorna float ou None.

    Peso de cada critério: campo `peso` do JSON (ex.: "16,5%") ou, na ausência,
    o peso padrão de docx_theme.PESOS_PADRAO. A média é normalizada pela soma
    dos pesos presentes, então funciona mesmo que os pesos não somem 100%
    e ignora critérios sem nota (regra "Não avaliado").
    """
    num = den = 0.0
    for c in criterios:
        nota = T.parse_nota(c.get("nota"))
        if nota is None:
            continue
        peso = None
        peso_str = c.get("peso")
        if peso_str:
            try:
                peso = float(str(peso_str).replace("%", "").replace(",", ".")) / 100.0
            except ValueError:
                peso = None
        if peso is None:
            peso = T.PESOS_PADRAO.get(c.get("nome"))
        if peso is None:
            continue
        num += nota * peso
        den += peso
    if den == 0:
        return None
    return num / den


def build(data, out_path):
    doc = Document()
    # margens e fonte base
    for sec in doc.sections:
        sec.top_margin = Cm(1.8)
        sec.bottom_margin = Cm(1.6)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)
    style = doc.styles["Normal"]
    style.font.name = T.FONT
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor.from_string(T.WHITE)

    T.set_page_background(doc, T.NAVY)

    colaborador = data.get("colaborador", "Colaborador")
    periodo = data.get("periodo_label", "")
    data_ger = data.get("data_geracao", "")

    T.setup_header_footer(doc, f"Análise de Atendimento — {colaborador}")

    # ---- Capa/título -------------------------------------------------------
    T.add_para(doc, "ALTOCON CONTABILIDADE", color=T.GREY_LT, size=11, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    T.add_title(doc, "Relatório de Análise de Atendimento")
    T.add_subtitle(doc, colaborador + (f"  •  {periodo}" if periodo else ""))
    if data_ger:
        T.add_subtitle(doc, f"Gerado em {data_ger}", size=9)
    T._spacer(doc, 4)

    # ---- 1. Resumo Executivo ----------------------------------------------
    T.add_heading(doc, "1. Resumo Executivo")
    if data.get("resumo_executivo"):
        T.add_para(doc, data["resumo_executivo"])
    indic = data.get("indicadores")
    if indic:
        rows = [[str(a), str(b)] for a, b in indic]
        T.make_table(doc, ["INDICADOR", "RESULTADO"], rows,
                     widths=[Cm(10.5), Cm(6.0)],
                     aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
        T._spacer(doc, 2)

    # ---- 2. Nota Geral do Atendimento -------------------------------------
    criterios = data.get("criterios", [])
    calc = final_score(criterios)
    nota_final = T.fmt_nota(calc) if calc is not None else "—"  # sempre recalculado (patch anti-divergencia)
    nota_f = T.parse_nota(nota_final)
    label = data.get("desempenho_label") or T.desempenho_from_nota(nota_f if nota_f is not None else calc)

    T.add_heading(doc, "2. Nota Geral do Atendimento")
    T.add_score_block(doc, nota_final, label)
    if data.get("nota_geral_texto"):
        T.add_para(doc, data["nota_geral_texto"])

    # tabela de critérios
    if criterios:
        rows = []
        for c in criterios:
            rows.append([
                c.get("nome", ""),
                T.peso_pct(c.get("nome", ""), c.get("peso")),
                str(c.get("nota", "")),
                c.get("justificativa", "") or "—",
            ])
        tbl = T.make_table(
            doc, ["Critério", "Peso", "Nota", "Justificativa"], rows,
            widths=[Cm(4.0), Cm(1.6), Cm(1.6), Cm(9.3)],
            aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                    WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT])
        T.add_total_row(tbl, "NOTA FINAL PONDERADA (9 critérios)", str(nota_final))
        T._spacer(doc, 2)

    # ---- 3..11 Critérios (1 seção cada, 9 critérios) ----------------------
    sec_num = 3
    by_name = {c.get("nome"): c for c in criterios}
    for nome in T.ORDEM_CRITERIOS:
        c = by_name.get(nome)
        if not c:
            sec_num += 1
            continue
        nota = c.get("nota", "")
        T.add_heading(doc, f"{sec_num}. {nome} — {nota} / 10")
        if c.get("texto"):
            T.add_para(doc, c["texto"])
        if c.get("bullets"):
            T.add_bullets(doc, c["bullets"])
        ev = c.get("evidencias")
        if ev:
            linhas = []
            for e in ev:
                trecho = (e.get("trecho") or "").strip()
                if not trecho:
                    continue
                if e.get("sem_ocorrencia"):
                    linhas.append(trecho)
                    continue
                cab = " · ".join(x for x in [e.get("cliente"), e.get("data"), e.get("hora")]
                                 if x and x != "—")
                termos = e.get("termos")
                pre = f"{cab} — " if cab else ""
                suf = f"  [{termos}]" if termos else ""
                linhas.append(f"{pre}“{trecho}”{suf}")
            if linhas:
                T.add_para(doc, "Exemplos de gírias/informalidades no período:",
                           color=T.GOLD_LT, size=10, bold=True, space_after=1)
                T.add_bullets(doc, linhas)
        d = c.get("destaque")
        if d and d.get("texto"):
            T.add_highlight_box(doc, d.get("label", ""), d.get("texto", ""))
        sec_num += 1

    # ---- 12. Pontos Positivos ---------------------------------------------
    T.add_heading(doc, "12. Pontos Positivos")
    pos = data.get("pontos_positivos") or []
    if pos:
        T.add_bullets(doc, pos)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- 13. Pontos de Melhoria -------------------------------------------
    T.add_heading(doc, "13. Pontos de Melhoria")
    mel = data.get("pontos_melhoria") or []
    if mel:
        T.add_bullets(doc, mel)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)
    md = data.get("melhoria_destaque")
    if md and md.get("texto"):
        T.add_highlight_box(doc, md.get("label", "Regra de ouro"), md.get("texto", ""))

    # ---- 14. Conclusão -----------------------------------------------------
    T.add_heading(doc, "14. Conclusão")
    if data.get("conclusao"):
        T.add_para(doc, data["conclusao"])
    cd = data.get("conclusao_destaque")
    if cd and cd.get("texto"):
        T.add_highlight_box(doc, cd.get("label", "Mensagem final"), cd.get("texto", ""))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    doc.save(out_path)
    return out_path


def main():
    if len(sys.argv) < 3:
        print("Uso: build_report.py <analise.json> <saida.docx>", file=sys.stderr)
        sys.exit(1)
    json_path, out_path = sys.argv[1], sys.argv[2]
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = build(data, out_path)
    print(f"OK: relatório gerado -> {out}")


if __name__ == "__main__":
    main()
