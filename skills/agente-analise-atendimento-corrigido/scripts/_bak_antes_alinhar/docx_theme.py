#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tema visual compartilhado dos relatórios da Altocon — navy/dourado, Arial,
fundo navy, cabeçalho/rodapé com paginação. Usado por build_report.py e
build_team_summary.py. Não é executado diretamente.
"""
from docx.shared import Pt, RGBColor, Twips, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---- Paleta ----------------------------------------------------------------
NAVY      = "0B1F3A"   # fundo da página
NAVY_DK   = "081830"   # navy mais escuro (linhas de tabela)
NAVY_CELL = "12294A"   # célula de tabela
GOLD      = "C9A24B"   # dourado (títulos, bordas, bullets)
GOLD_LT   = "E3C77A"   # dourado claro (rótulos de destaque)
WHITE     = "FFFFFF"
GREY_LT   = "C7D0DC"   # texto secundário
GREEN     = "5BBF7A"   # ✓
RED       = "E2706B"   # ✗

FONT = "Arial"


# ---- Helpers de baixo nível (OOXML) ---------------------------------------
def _set(el, **attrs):
    for k, v in attrs.items():
        el.set(qn(k), v)
    return el


def set_page_background(doc, color=NAVY):
    """Pinta a página inteira de navy (w:background + displayBackgroundShape)."""
    bg = OxmlElement("w:background")
    bg.set(qn("w:color"), color)
    # w:background tem de ser o PRIMEIRO filho de w:document
    doc.element.insert(0, bg)
    settings = doc.settings.element
    if settings.find(qn("w:displayBackgroundShape")) is None:
        dbg = OxmlElement("w:displayBackgroundShape")
        settings.append(dbg)


def shade(el, color):
    """Aplica preenchimento (shading) a uma célula ou parágrafo."""
    pr = el.get_or_add_tcPr() if el.tag.endswith("}tc") else el.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    _set(shd, **{"w:val": "clear", "w:color": "auto", "w:fill": color})
    pr.append(shd)


def cell_borders(cell, color=GOLD, sz=8, sides=("top", "bottom", "left", "right")):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in sides:
        b = OxmlElement(f"w:{side}")
        _set(b, **{"w:val": "single", "w:sz": str(sz), "w:space": "0", "w:color": color})
        borders.append(b)
    tcPr.append(borders)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr = cell._tc.get_or_add_tcPr()
    m = OxmlElement("w:tcMar")
    for side, val in (("top", top), ("bottom", bottom), ("start", left), ("end", right)):
        e = OxmlElement(f"w:{side}")
        _set(e, **{"w:w": str(val), "w:type": "dxa"})
        m.append(e)
    tcPr.append(m)


def vmerge_off(cell):
    pass


# ---- Texto -----------------------------------------------------------------
def style_run(run, color=WHITE, size=11, bold=False, italic=False, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    # garante a fonte também para scripts complexos
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    _set(rfonts, **{"w:ascii": font, "w:hAnsi": font, "w:cs": font})
    return run


def add_para(doc_or_cell, text="", color=WHITE, size=11, bold=False, italic=False,
             align=None, space_before=2, space_after=6, font=FONT):
    p = doc_or_cell.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.18
    if text:
        style_run(p.add_run(text), color=color, size=size, bold=bold, italic=italic, font=font)
    return p


def add_title(doc, text, color=GOLD, size=22):
    p = add_para(doc, text, color=color, size=size, bold=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=4)
    return p


def add_subtitle(doc, text, color=GREY_LT, size=12):
    return add_para(doc, text, color=color, size=size, bold=False,
                    align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=2)


def add_heading(doc, text, color=GOLD, size=14):
    """Cabeçalho de seção com filete dourado embaixo."""
    p = add_para(doc, text, color=color, size=size, bold=True,
                 space_before=14, space_after=2)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    _set(bottom, **{"w:val": "single", "w:sz": "10", "w:space": "4", "w:color": GOLD})
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def add_bullets(doc_or_cell, items, color=GOLD, size=11, marker="•  "):
    for it in items:
        p = doc_or_cell.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Pt(10)
        p.paragraph_format.line_spacing = 1.15
        style_run(p.add_run(marker), color=GOLD, size=size, bold=True)
        # suporta ✓/✗ coloridos no fim do item
        _emit_inline(p, str(it), default_color=color, size=size)
    return doc_or_cell


def _emit_inline(p, text, default_color=WHITE, size=11):
    """Escreve texto colorindo ✓ de verde e ✗ de vermelho."""
    buf = ""
    for ch in text:
        if ch in ("✓", "✗"):
            if buf:
                style_run(p.add_run(buf), color=default_color, size=size)
                buf = ""
            style_run(p.add_run(ch), color=(GREEN if ch == "✓" else RED), size=size, bold=True)
        else:
            buf += ch
    if buf:
        style_run(p.add_run(buf), color=default_color, size=size)


# ---- Caixa de destaque -----------------------------------------------------
def add_highlight_box(doc, label, text):
    """Caixa com borda dourada: rótulo dourado (negrito) + texto branco (negrito)."""
    if not text:
        return None
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    cell = tbl.rows[0].cells[0]
    shade(cell._tc, NAVY_CELL)
    cell_borders(cell, color=GOLD, sz=10)
    set_cell_margins(cell, top=100, bottom=100, left=160, right=160)
    cell.paragraphs[0]._element.getparent().remove(cell.paragraphs[0]._element)
    p = cell.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    if label:
        style_run(p.add_run(f"{label.upper()} — "), color=GOLD_LT, size=10.5, bold=True)
    style_run(p.add_run(text), color=WHITE, size=10.5, bold=True)
    _spacer(doc, 4)
    return tbl


def _spacer(doc, pts=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    style_run(p.add_run(""), size=pts)
    return p


# ---- Tabelas ---------------------------------------------------------------
def _clear_cell(cell):
    for para in list(cell.paragraphs):
        para._element.getparent().remove(para._element)
    return cell.add_paragraph()


def make_table(doc, headers, rows, widths=None, header_fill=GOLD, header_color=NAVY,
               body_fill=NAVY_CELL, alt_fill=NAVY_DK, body_color=WHITE,
               header_size=10.5, body_size=10.5, aligns=None):
    """Tabela temática: cabeçalho dourado, corpo navy com linhas alternadas."""
    ncols = len(headers)
    tbl = doc.add_table(rows=1, cols=ncols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = (widths is None)
    aligns = aligns or [WD_ALIGN_PARAGRAPH.LEFT] * ncols

    hdr = tbl.rows[0].cells
    for i, h in enumerate(headers):
        shade(hdr[i]._tc, header_fill)
        cell_borders(hdr[i], color=GOLD, sz=6)
        set_cell_margins(hdr[i])
        p = _clear_cell(hdr[i])
        p.alignment = aligns[i]
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(str(h)), color=header_color, size=header_size, bold=True)

    for r, row in enumerate(rows):
        cells = tbl.add_row().cells
        fill = body_fill if r % 2 == 0 else alt_fill
        for i, val in enumerate(row):
            shade(cells[i]._tc, fill)
            cell_borders(cells[i], color=GOLD, sz=4)
            set_cell_margins(cells[i])
            p = _clear_cell(cells[i])
            p.alignment = aligns[i]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.12
            _emit_inline(p, str(val), default_color=body_color, size=body_size)

    if widths:
        for row in tbl.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = w
        # reforça largura via tcW
        for row in tbl.rows:
            for i, w in enumerate(widths):
                tcPr = row.cells[i]._tc.get_or_add_tcPr()
                tcW = tcPr.find(qn("w:tcW"))
                if tcW is None:
                    tcW = OxmlElement("w:tcW")
                    tcPr.append(tcW)
                _set(tcW, **{"w:w": str(int(w.twips)), "w:type": "dxa"})
    return tbl


def add_total_row(tbl, label, value, fill=NAVY_DK, color=GOLD, size=11):
    """Linha final destacada (ex.: NOTA FINAL PONDERADA)."""
    cells = tbl.add_row().cells
    n = len(cells)
    # mescla todas menos a última para o rótulo
    if n >= 2:
        a = cells[0]
        for c in cells[1:n - 1]:
            a = a.merge(c)
        for c in (cells[0], cells[n - 1]):
            shade(c._tc, fill)
            cell_borders(c, color=GOLD, sz=8)
            set_cell_margins(c)
        p = _clear_cell(cells[0])
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(label), color=color, size=size, bold=True)
        p2 = _clear_cell(cells[n - 1])
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        style_run(p2.add_run(value), color=color, size=size, bold=True)


# ---- Bloco da NOTA FINAL ---------------------------------------------------
def add_score_block(doc, nota, label):
    """Bloco grande 'NOTA FINAL: X,X / 10' + rótulo de desempenho."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    shade(cell._tc, NAVY_CELL)
    cell_borders(cell, color=GOLD, sz=12)
    set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
    _clear_cell(cell)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    style_run(p.add_run("NOTA FINAL: "), color=WHITE, size=18, bold=True)
    style_run(p.add_run(f"{nota}"), color=GOLD, size=26, bold=True)
    style_run(p.add_run("  / 10"), color=GREY_LT, size=16, bold=True)
    if label:
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        style_run(p2.add_run(label.upper()), color=GOLD_LT, size=12, bold=True)
    _spacer(doc, 4)
    return tbl


# ---- Cabeçalho / rodapé com paginação --------------------------------------
def setup_header_footer(doc, header_text, footer_left="Altocon Contabilidade"):
    sec = doc.sections[0]
    # Cabeçalho
    h = sec.header
    h.is_linked_to_previous = False
    hp = h.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.paragraph_format.space_after = Pt(2)
    style_run(hp.add_run(header_text), color=GOLD, size=9, bold=True)
    _para_bottom_border(hp, GOLD)

    # Rodapé com numeração de página
    f = sec.footer
    f.is_linked_to_previous = False
    fp = f.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _para_top_border(fp, GOLD)
    style_run(fp.add_run(f"{footer_left}   •   Página "), color=GREY_LT, size=8.5)
    _add_page_field(fp)
    style_run(fp.add_run(" de "), color=GREY_LT, size=8.5)
    _add_pages_field(fp)


def _para_bottom_border(p, color):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    _set(b, **{"w:val": "single", "w:sz": "6", "w:space": "2", "w:color": color})
    pbdr.append(b)
    pPr.append(pbdr)


def _para_top_border(p, color):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    t = OxmlElement("w:top")
    _set(t, **{"w:val": "single", "w:sz": "6", "w:space": "2", "w:color": color})
    pbdr.append(t)
    pPr.append(pbdr)


def _add_field(paragraph, instr, color=GREY_LT, size=8.5):
    run = paragraph.add_run()
    style_run(run, color=color, size=size)
    r = run._r
    fc1 = OxmlElement("w:fldChar"); fc1.set(qn("w:fldCharType"), "begin"); r.append(fc1)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r.append(it)
    fc2 = OxmlElement("w:fldChar"); fc2.set(qn("w:fldCharType"), "end"); r.append(fc2)


def _add_page_field(paragraph):
    _add_field(paragraph, " PAGE ")


def _add_pages_field(paragraph):
    _add_field(paragraph, " NUMPAGES ")


# ---- Utilitários de nota ----------------------------------------------------
def parse_nota(val):
    """'8,4' / '8.4' / 8.4 -> float; retorna None se vazio."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_nota(x):
    """float -> '8,4' (1 casa, vírgula decimal)."""
    return f"{x:.1f}".replace(".", ",")


def desempenho_from_nota(x):
    if x is None:
        return ""
    if x >= 9.0:
        return "Desempenho Excelente"
    if x >= 8.0:
        return "Desempenho Muito Bom"
    if x >= 7.0:
        return "Desempenho Bom"
    if x >= 6.0:
        return "Desempenho Regular"
    return "Desempenho Abaixo do Esperado"


# Manual de Padrões Operacionais (vigência Junho/2026) + planilha de pesos da
# coordenação: 9 critérios (o antigo "Dupla Confirmação" foi removido), com
# PESOS DIFERENCIADOS e nota final por MÉDIA PONDERADA (normalizada pela soma
# dos pesos). Pesos conforme Tabela_de_Critério.xlsx.
ORDEM_CRITERIOS = [
    "Tempo de Início do Atendimento (SLA)",
    "Gestão de Prazos e Comunicação Assertiva",
    "Empatia e Escuta Ativa",
    "Clareza, Orientação Técnica e Uso de Canais",
    "Transparência, Sinceridade e Tratamento de Erros",
    "Postura Contínua e Soluções Definitivas",
    "Ética e Transparência Sempre",
    'Transformar o "Não" em Busca por Soluções',
    "Coerência na Escrita, Gírias e Informalidades",
]
PESOS_PADRAO = {
    "Tempo de Início do Atendimento (SLA)": 0.165,
    "Gestão de Prazos e Comunicação Assertiva": 0.085,
    "Empatia e Escuta Ativa": 1.0 / 9.0,
    "Clareza, Orientação Técnica e Uso de Canais": 1.0 / 9.0,
    "Transparência, Sinceridade e Tratamento de Erros": 0.085,
    "Postura Contínua e Soluções Definitivas": 0.165,
    "Ética e Transparência Sempre": 0.085,
    'Transformar o "Não" em Busca por Soluções': 1.0 / 9.0,
    "Coerência na Escrita, Gírias e Informalidades": 0.085,
}


def peso_pct(nome, peso_str=None):
    """Formata o peso como porcentagem (ex.: '16,5%', '8,5%', '11,11%')."""
    if peso_str:
        return str(peso_str)
    p = PESOS_PADRAO.get(nome)
    if p is None:
        return ""
    pct = p * 100.0
    if abs(pct - round(pct)) < 0.05:
        return f"{int(round(pct))}%"
    s = f"{pct:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",") + "%"
