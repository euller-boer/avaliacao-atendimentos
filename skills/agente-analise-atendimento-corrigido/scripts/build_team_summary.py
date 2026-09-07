#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o RESUMO DA EQUIPE (.docx) — identidade visual Altocon (fundo branco, navy/dourado, logo no topo), 6 seções.
Inclui ranking, médias por critério e GRÁFICO DE BARRAS de atendimentos por colaborador.

Uso:
    python3 scripts/build_team_summary.py resumo_equipe.json "<saida>/Resumo_Escritorio_<Cidade>_<MM-AAAA>.docx"

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


def _fixar_grid(tbl, widths):
    """Faz o LibreOffice respeitar a largura de cada coluna.

    `make_table` grava a largura em `w:tcW` (célula a célula), mas quem manda no layout fixo é o
    `w:tblGrid` da tabela — que o python-docx deixa com todas as colunas IGUAIS. Resultado: numa
    tabela de 6 colunas o cabeçalho "COLABORADOR" quebrava em "COLABORAD/OR" e os nomes saíam em
    duas linhas (visto na semana 03–09/08/2026). Aqui o grid e a largura total passam a valer as
    larguras pedidas.

    Proposital que esteja neste arquivo e não no `docx_theme`: o tema é compartilhado com os
    relatórios MENSAIS, que já foram entregues e validados com o layout atual.
    """
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    tblPr = tbl._tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:type"), "dxa")
    tblW.set(qn("w:w"), str(int(sum(w.twips for w in widths))))

    grid = tbl._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for col, w in zip(grid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(int(w.twips)))


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
    # A altura por barra (0,55") fazia o gráfico crescer sem limite: com os 24 de Monte Alto em
    # julho/2026 saía 14,2" de altura, que ao entrar com 16 cm de largura virava 27,2 cm numa
    # página útil de ~24 cm — o gráfico estourava a página e a última pessoa do ranking
    # (Graziele Anselmo) era CORTADA fora do PDF. Agora a altura tem teto, e a barra fica mais
    # fina quando a equipe é grande, para que todos caibam.
    fig_h = max(1.6, min(0.55 * n + 1.0, 8.6))
    fig, ax = plt.subplots(figsize=(8.4, fig_h), dpi=150)
    fig.patch.set_facecolor(_hexf(T.WHITE))
    ax.set_facecolor(_hexf(T.WHITE))

    y = range(len(nomes))
    bars = ax.barh(list(y), vals, color=_hexf(T.NAVY), edgecolor=_hexf(T.GOLD), height=0.62)
    ax.invert_yaxis()
    ax.set_yticks(list(y))
    ax.set_yticklabels(nomes, color=_hexf(T.NAVY), fontsize=(10 if n <= 16 else 8))
    ax.tick_params(axis="x", colors=_hexf(T.GREY_LT), labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.xaxis.grid(True, color="#D8DEE7", linewidth=0.6)
    ax.set_axisbelow(True)

    vmax = max(vals) if vals else 1
    for rect, v in zip(bars, vals):
        ax.text(rect.get_width() + vmax * 0.01, rect.get_y() + rect.get_height() / 2,
                str(v), va="center", ha="left", color=_hexf(T.NAVY), fontsize=9, fontweight="bold")
    ax.set_xlim(0, vmax * 1.12 if vmax else 1)
    ax.set_title("Atendimentos por colaborador", color=_hexf(T.NAVY),
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
    style.font.color.rgb = RGBColor.from_string(T.TEXT)

    T.set_page_background(doc)  # página branca

    periodo = data.get("periodo_label", "")
    data_ger = data.get("data_geracao", "")
    colabs = data.get("colaboradores", []) or []

    # ACOMPANHAMENTO (coordenação 08/08/2026): semana e dia saem SEM nota, média ou ranking —
    # a tabela é de indicadores, ordenada por volume de atendimentos. JSON sem `periodo_tipo`
    # (pacotes antigos) é tratado como MENSAL.
    tipo = data.get("periodo_tipo", "mes")
    acomp = tipo != "mes"
    per_nome = {"intervalo": "Semanal", "dia": "Diário"}.get(tipo, "")

    # ESCOPO POR COORDENADOR (coordenação 11/08/2026): quando o JSON traz `escopo_equipe`, o
    # documento é o da equipe de um coordenador — a LISTA é só da equipe, mas média, ranking e
    # médias por critério continuam sendo da UNIDADE inteira. JSON sem essa chave é o resumo de
    # unidade de sempre e sai exatamente como antes (pacotes já entregues não mudam).
    escopo = data.get("escopo_equipe") or {}
    coord = escopo.get("coordenador", "")
    depto = escopo.get("departamento", "")
    n_unid = escopo.get("total_colaboradores_unidade")
    unidade = escopo.get("unidade", "")

    if escopo:
        tit_doc = (f"Acompanhamento {per_nome} da Equipe — {coord}".replace("  ", " ")
                   if acomp else f"Resumo da Equipe — {coord}")
        rot_cab = f"Equipe {coord}"
    else:
        # "Escritório", não "Equipe": desde 01/09/2026 este consolidado vai junto no pacote de cada
        # coordenador, ao lado do resumo da equipe dele — dois documentos chamados "Resumo da
        # Equipe" no mesmo zip não diziam qual era qual.
        tit_doc = (f"Acompanhamento {per_nome} do Escritório — Atendimentos".replace("  ", " ")
                   if acomp else "Resumo do Escritório — Análise de Atendimentos")
        rot_cab = ("Acompanhamento do Escritório" if acomp else "Resumo do Escritório")

    T.setup_header_footer(doc, f"{rot_cab}{(' — ' + periodo) if periodo else ''}")

    T.add_logo(doc)
    T.add_title(doc, tit_doc)
    if escopo and depto:
        T.add_subtitle(doc, depto)
    if periodo:
        T.add_subtitle(doc, periodo)
    # ver nota em build_report.py: "Gerado em" era a data da TRANSCRIÇÃO, não a da emissão
    T.add_subtitle(doc, T.linha_datas(data_ger), size=9)
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
    ind_rows = []
    if escopo:
        ind_rows.append(["Coordenador", coord])
        if depto:
            ind_rows.append(["Departamento", depto])
    ind_rows += [["Colaboradores analisados", str(total_colab)],
                 ["Total de atendimentos no período", f"{total_atend:,}".replace(",", ".")]]
    if not acomp:
        if escopo:
            ind_rows.append([f"Média geral de {unidade or 'da unidade'}",
                             f"{media_geral or '—'} / 10"
                             + (f"  ({n_unid} colaboradores)" if n_unid else "")])
        else:
            ind_rows.append(["Média geral da equipe", f"{media_geral or '—'} / 10"])
    else:
        ind_rows.append(["Mensagens enviadas pela equipe",
                         f"{sum(int(c.get('mensagens') or 0) for c in colabs):,}".replace(",", ".")])
    T.make_table(doc, ["INDICADOR", "RESULTADO"], ind_rows, widths=[Cm(10.5), Cm(6.0)])
    T._spacer(doc, 2)

    # ---- 2. Notas por Colaborador / Indicadores por Colaborador -----------
    if acomp:
        T.add_heading(doc, "2. Indicadores por Colaborador")
        T.add_para(doc, "Ordenado por volume de atendimentos no período. Não é ranking de desempenho — "
                        "este acompanhamento não atribui nota.", color=T.GREY_LT, size=9)
        ordem = sorted(colabs, key=lambda c: (-int(c.get("total_atendimentos") or 0),
                                              (c.get("nome") or "").lower()))
        rows = [[c.get("nome", ""), str(c.get("total_atendimentos", "")),
                 str(c.get("sla", "—")), str(c.get("mensagens", "")),
                 str(c.get("proativos", "")), str(c.get("girias", "—"))] for c in ordem]
        if rows:
            # "PROATIVOS" (10 pt, negrito, caixa alta) não cabia em 2,4 cm menos as margens da
            # célula (0,42 cm) e quebrava em "PROATIVO / S" no cabeçalho. Corrigido em
            # 11/08/2026 alargando essa coluna para 2,8 cm, com a folga vindo da coluna de
            # nomes (que sobrava) e dos 0,2 cm livres da página. Total 16,9 cm em ~17 cm úteis.
            larg = [Cm(4.8), Cm(2.0), Cm(3.2), Cm(1.8), Cm(2.8), Cm(2.3)]
            tbl = T.make_table(doc, ["Colaborador", "Atend.", "SLA 1ª resp. (base)", "Msgs", "Proativos", "Gírias"],
                               rows, widths=larg,
                               aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                                       WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                                       WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
            _fixar_grid(tbl, larg)
            T._spacer(doc, 4)
    else:
        T.add_heading(doc, "2. Notas por Colaborador")
        if media_geral:
            if escopo:
                T.add_score_block(doc, media_geral,
                                  f"Referência de {unidade}" if unidade else "Referência da unidade",
                                  prefixo="MÉDIA DA UNIDADE: ")
            else:
                T.add_score_block(doc, media_geral, "Média Geral da Equipe")

        pos = escopo.get("posicoes") or {}
        if escopo and pos:
            T.add_para(doc, f"A coluna \"#\" é a posição de cada um no ranking de "
                            f"{unidade or 'toda a unidade'}"
                            + (f" ({n_unid} colaboradores)" if n_unid else "")
                            + " — não é a colocação dentro da equipe.",
                       color=T.GREY_LT, size=9)

        ranking = sorted(colabs, key=lambda c: (T.parse_nota(c.get("nota_final")) or -1), reverse=True)
        rows = []
        for i, c in enumerate(ranking, 1):
            nome = c.get("nome", "")
            num = f"{pos[nome]}º" if (escopo and nome in pos) else str(i)
            rows.append([num, nome,
                         str(c.get("total_atendimentos", "")),
                         str(c.get("nota_final", ""))])
        if rows:
            # "#" fica um pouco mais larga só no resumo de equipe, onde o número vem com "º"
            # (ex.: "12º"). O resumo de UNIDADE mantém 1,2 cm — layout já entregue e validado.
            larg_n = Cm(1.6) if (escopo and pos) else Cm(1.2)
            larg_nome = Cm(7.9) if (escopo and pos) else Cm(8.3)
            T.make_table(doc, ["#", "Colaborador", "Atendimentos", "Nota Final"], rows,
                         widths=[larg_n, larg_nome, Cm(3.5), Cm(3.3)],
                         aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                                 WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
            T._spacer(doc, 4)
        dm = escopo.get("depto_membro") or {}
        if dm:
            det = "; ".join(f"{c.get('nome')} — {dm[c.get('nome','').upper()]}"
                            for c in ranking if c.get("nome", "").upper() in dm)
            if det:
                T.add_para(doc, f"Departamentos da equipe: {det}.", color=T.GREY_LT, size=9)

    # gráfico de barras
    if colabs:
        try:
            tmp_png = os.path.join(tempfile.gettempdir(),
                                   f"_barras_{os.getpid()}.png")
            make_bar_chart(colabs, tmp_png)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Trava de segurança: mesmo com o teto de altura do gráfico, nunca inserir uma
            # imagem mais alta que a área útil da página — senão ela é cortada no PDF (era o
            # que acontecia com Monte Alto). Se não couber em 16 cm de largura, reduz a largura.
            LARG_MAX, ALT_MAX = 16.0, 23.0  # cm
            larg = LARG_MAX
            try:
                from PIL import Image
                with Image.open(tmp_png) as im:
                    px_w, px_h = im.size
                if px_w and px_h:
                    alt = LARG_MAX * px_h / px_w
                    if alt > ALT_MAX:
                        larg = ALT_MAX * px_w / px_h
            except Exception:
                pass  # sem PIL, mantém a largura padrão
            p.add_run().add_picture(tmp_png, width=Cm(larg))
            try:
                os.remove(tmp_png)
            except OSError:
                pass
        except Exception as e:  # gráfico é "nice to have"; não derruba o relatório
            T.add_para(doc, f"(gráfico não gerado: {e})", color=T.GREY_LT, size=9)

    # ---- 3. Médias por Critério (equipe) — só na avaliação MENSAL ---------
    n = 3
    if not acomp:
        med_unid = escopo.get("medias_criterio_unidade") or {}
        if escopo and med_unid:
            # Régua da unidade inteira, não da equipe — assim todos os coordenadores olham
            # para a mesma referência e os documentos continuam comparáveis entre si.
            T.add_heading(doc, f"3. Médias por Critério ({unidade or 'Unidade'})")
            col_med = f"Média de {unidade}" if unidade else "Média da Unidade"
            med_rows = [[nome, T.peso_pct(nome), med_unid.get(nome, "—")]
                        for nome in T.ORDEM_CRITERIOS]
        else:
            T.add_heading(doc, "3. Médias por Critério (Equipe)")
            col_med = "Média da Equipe"
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
        T.make_table(doc, ["Critério", "Peso", col_med], med_rows,
                     widths=[Cm(8.5), Cm(4.0), Cm(4.0)],
                     aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                             WD_ALIGN_PARAGRAPH.CENTER])
        T._spacer(doc, 2)
        n = 4

    # ---- Destaques da Equipe ----------------------------------------------
    T.add_heading(doc, f"{n}. Destaques da Equipe")
    dest = data.get("destaques") or []
    if dest:
        T.add_bullets(doc, dest)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- Pontos de Melhoria / de Atenção da Equipe ------------------------
    T.add_heading(doc, f"{n+1}. " + ("Pontos de Atenção da Equipe" if acomp else "Pontos de Melhoria da Equipe"))
    pm = data.get("pontos_melhoria_equipe") or []
    if pm:
        T.add_bullets(doc, pm)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- Conclusão ---------------------------------------------------------
    T.add_heading(doc, f"{n+2}. Conclusão")
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
