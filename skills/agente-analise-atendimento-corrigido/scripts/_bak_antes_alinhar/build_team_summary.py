#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o RESUMO DA EQUIPE (.docx) — tema navy/dourado, 6 seções.
Inclui ranking, médias por critério e GRÁFICO DE BARRAS de atendimentos por colaborador.

Uso:
    python3 scripts/build_team_summary.py resumo_equipe.json "<saida>/Resumo_Equipe_<MM-AAAA>.docx"

As médias por critério e o ranking são calculados aqui a partir de `colaboradores`.
"""
import json
import sys
import os
import tempfile

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docx_theme as T


def _hexf(c):
    return "#" + c


def make_bar_chart(colabs, png_path):
    """Gráfico de barras: quantidade de atendimentos por colaborador (tema navy/dourado)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nomes = [c.get("nome", "?") for c in colabs]
    vals = [int(c.get("total_atendimentos") or 0) for c in colabs]
    # ordena do maior para o menor
    pares = sorted(zip(nomes, vals), key=lambda x: x[1], reverse=True)
    nomes = [p[0] for p in pares]
    vals = [p[1] for p in pares]

    n = max(len(nomes), 1)
    fig_h = max(1.6, 0.55 * n + 1.0)
    fig, ax = plt.subplots(figsize=(8.4, fig_h), dpi=150)
    fig.patch.set_facecolor(_hexf(T.NAVY))
    ax.set_facecolor(_hexf(T.NAVY))

    y = range(len(nomes))
    bars = ax.barh(list(y), vals, color=_hexf(T.GOLD), edgecolor=_hexf(T.GOLD_LT), height=0.62)
    ax.invert_yaxis()
    ax.set_yticks(list(y))
    ax.set_yticklabels(nomes, color=_hexf(T.WHITE), fontsize=10)
    ax.tick_params(axis="x", colors=_hexf(T.GREY_LT), labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.xaxis.grid(True, color="#23416B", linewidth=0.6)
    ax.set_axisbelow(True)

    vmax = max(vals) if vals else 1
    for rect, v in zip(bars, vals):
        ax.text(rect.get_width() + vmax * 0.01, rect.get_y() + rect.get_height() / 2,
                str(v), va="center", ha="left", color=_hexf(T.WHITE), fontsize=9, fontweight="bold")
    ax.set_xlim(0, vmax * 1.12 if vmax else 1)
    ax.set_title("Atendimentos por colaborador", color=_hexf(T.GOLD),
                 fontsize=12, fontweight="bold", pad=10, loc="left")

    plt.tight_layout()
    fig.savefig(png_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return png_path


def build(data, out_path):
    doc = Document()
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

    periodo = data.get("periodo_label", "")
    data_ger = data.get("data_geracao", "")
    colabs = data.get("colaboradores", []) or []

    T.setup_header_footer(doc, f"Resumo da Equipe{(' — ' + periodo) if periodo else ''}")

    T.add_para(doc, "ALTOCON CONTABILIDADE", color=T.GREY_LT, size=11, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    T.add_title(doc, "Resumo da Equipe — Análise de Atendimentos")
    if periodo:
        T.add_subtitle(doc, periodo)
    if data_ger:
        T.add_subtitle(doc, f"Gerado em {data_ger}", size=9)
    T._spacer(doc, 4)

    # ---- 1. Resumo Executivo da Equipe ------------------------------------
    T.add_heading(doc, "1. Resumo Executivo da Equipe")
    total_colab = data.get("total_colaboradores") or len(colabs)
    total_atend = data.get("total_atendimentos")
    if total_atend is None:
        total_atend = sum(int(c.get("total_atendimentos") or 0) for c in colabs)
    notas = [T.parse_nota(c.get("nota_final")) for c in colabs]
    notas = [n for n in notas if n is not None]
    media_geral = data.get("media_geral")
    if not media_geral and notas:
        media_geral = T.fmt_nota(sum(notas) / len(notas))
    if data.get("resumo_executivo"):
        T.add_para(doc, data["resumo_executivo"])
    T.make_table(doc, ["INDICADOR", "RESULTADO"], [
        ["Colaboradores analisados", str(total_colab)],
        ["Total de atendimentos no período", f"{total_atend:,}".replace(",", ".")],
        ["Média geral da equipe", f"{media_geral or '—'} / 10"],
    ], widths=[Cm(10.5), Cm(6.0)])
    T._spacer(doc, 2)

    # ---- 2. Notas por Colaborador (média + ranking + gráfico) -------------
    T.add_heading(doc, "2. Notas por Colaborador")
    if media_geral:
        T.add_score_block(doc, media_geral, "Média Geral da Equipe")

    ranking = sorted(colabs, key=lambda c: (T.parse_nota(c.get("nota_final")) or -1), reverse=True)
    rows = []
    for i, c in enumerate(ranking, 1):
        rows.append([str(i), c.get("nome", ""),
                     str(c.get("total_atendimentos", "")),
                     str(c.get("nota_final", ""))])
    if rows:
        T.make_table(doc, ["#", "Colaborador", "Atendimentos", "Nota Final"], rows,
                     widths=[Cm(1.2), Cm(8.3), Cm(3.5), Cm(3.3)],
                     aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                             WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
        T._spacer(doc, 4)

    # gráfico de barras
    if colabs:
        try:
            tmp_png = os.path.join(tempfile.gettempdir(),
                                   f"_barras_{os.getpid()}.png")
            make_bar_chart(colabs, tmp_png)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(tmp_png, width=Cm(16.0))
            try:
                os.remove(tmp_png)
            except OSError:
                pass
        except Exception as e:  # gráfico é "nice to have"; não derruba o relatório
            T.add_para(doc, f"(gráfico não gerado: {e})", color=T.GREY_LT, size=9)

    # ---- 3. Médias por Critério (equipe) ----------------------------------
    T.add_heading(doc, "3. Médias por Critério (Equipe)")
    med_rows = []
    for nome in T.ORDEM_CRITERIOS:
        vals = []
        for c in colabs:
            cr = c.get("criterios", {}) or {}
            v = T.parse_nota(cr.get(nome))
            if v is not None:
                vals.append(v)
        if vals:
            med_rows.append([nome, T.peso_pct(nome), T.fmt_nota(sum(vals) / len(vals))])
        else:
            med_rows.append([nome, T.peso_pct(nome), "—"])
    T.make_table(doc, ["Critério", "Peso", "Média da Equipe"], med_rows,
                 widths=[Cm(8.5), Cm(4.0), Cm(4.0)],
                 aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                         WD_ALIGN_PARAGRAPH.CENTER])
    T._spacer(doc, 2)

    # ---- 4. Destaques da Equipe -------------------------------------------
    T.add_heading(doc, "4. Destaques da Equipe")
    dest = data.get("destaques") or []
    if dest:
        T.add_bullets(doc, dest)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- 5. Pontos de Melhoria da Equipe ----------------------------------
    T.add_heading(doc, "5. Pontos de Melhoria da Equipe")
    pm = data.get("pontos_melhoria_equipe") or []
    if pm:
        T.add_bullets(doc, pm)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- 6. Conclusão ------------------------------------------------------
    T.add_heading(doc, "6. Conclusão")
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
        print("Uso: build_team_summary.py <resumo_equipe.json> <saida.docx>", file=sys.stderr)
        sys.exit(1)
    json_path, out_path = sys.argv[1], sys.argv[2]
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    out = build(data, out_path)
    print(f"OK: resumo da equipe gerado -> {out}")


if __name__ == "__main__":
    main()
