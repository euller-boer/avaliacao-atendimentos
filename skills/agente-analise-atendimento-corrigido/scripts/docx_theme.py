#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tema visual compartilhado dos relatórios da Altocon — identidade do modelo
"Matriz de Responsabilidades": página BRANCA, navy #1B2A44 e dourado #C2A35A,
logo Altocon centralizado no topo com filete dourado, tabelas com cabeçalho
navy (texto dourado), primeira coluna navy (texto branco) e linhas zebradas
brancas/#EEF1F5. Usado por build_report.py e build_team_summary.py.
"""
import os
from docx.shared import Pt, Cm, RGBColor, Twips, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---- Paleta (extraída do PDF modelo) ---------------------------------------
NAVY      = "1B2A44"   # navy principal (títulos, cabeçalhos, células-rótulo)
NAVY_DK   = "0D2436"   # navy do logo (blocos de destaque)
NAVY_CELL = "1B2A44"   # células-rótulo de tabela
GOLD      = "C2A35A"   # dourado (filetes, texto do cabeçalho de tabela)
GOLD_LT   = "E8DCB5"   # dourado claro (células/caixas de destaque)
WHITE     = "FFFFFF"
TEXT      = "1B2A44"   # texto do corpo (navy)
GREY_LT   = "6B7686"   # texto secundário (cinza)
ROW_ALT   = "EEF1F5"   # linha zebrada
BORDER    = "D8DEE7"   # bordas sutis
GREEN     = "2F8F5B"   # ✓
RED       = "C0504D"   # ✗

FONT = "Arial"

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "assets", "logo_altocon.png")


def linha_datas(data_transcricao=""):
    """Linha de datas da capa: base congelada + data de emissão do PDF.

    `data_transcricao` é o "Gerado em:" da transcrição (a base analisada). A data de emissão
    é a de hoje, e fica SÓ no .docx — nunca nos JSONs — para não quebrar a trava de
    determinismo (mesma transcrição -> JSONs idênticos). Para reproduzir um pacote antigo,
    fixe a emissão em ALTOCON_DATA_EMISSAO (formato DD/MM/AAAA).
    """
    from datetime import date
    emissao = (os.environ.get("ALTOCON_DATA_EMISSAO") or "").strip() \
        or date.today().strftime("%d/%m/%Y")
    if data_transcricao:
        return f"Base: transcrição congelada de {data_transcricao}  •  Relatório emitido em {emissao}"
    return f"Relatório emitido em {emissao}"


# ---- Helpers de baixo nível (OOXML) ---------------------------------------
def _set(el, **attrs):
    for k, v in attrs.items():
        el.set(qn(k), v)
    return el


def set_page_background(doc, color=WHITE):
    """Página branca (identidade do modelo). Mantido por compatibilidade."""
    return None


def shade(el, color):
    """Aplica preenchimento (shading) a uma célula ou parágrafo."""
    pr = el.get_or_add_tcPr() if el.tag.endswith("}tc") else el.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    _set(shd, **{"w:val": "clear", "w:color": "auto", "w:fill": color})
    pr.append(shd)


def cell_borders(cell, color=BORDER, sz=4, sides=("top", "bottom", "left", "right")):
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
def style_run(run, color=TEXT, size=11, bold=False, italic=False, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    _set(rfonts, **{"w:ascii": font, "w:hAnsi": font, "w:cs": font})
    return run


def add_para(doc_or_cell, text="", color=TEXT, size=11, bold=False, italic=False,
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


def add_logo(doc, width_cm=4.6):
    """Logo Altocon centralizado no topo + filete dourado (como no modelo)."""
    if os.path.exists(LOGO_PATH):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run()
        run.add_picture(LOGO_PATH, width=Cm(width_cm))
    # filete dourado horizontal
    rule = doc.add_paragraph()
    rule.paragraph_format.space_before = Pt(0)
    rule.paragraph_format.space_after = Pt(10)
    pPr = rule._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    _set(bottom, **{"w:val": "single", "w:sz": "12", "w:space": "1", "w:color": GOLD})
    pbdr.append(bottom)
    pPr.append(pbdr)
    return rule


def add_title(doc, text, color=NAVY, size=20):
    p = add_para(doc, text, color=color, size=size, bold=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=4)
    return p


def add_subtitle(doc, text, color=GOLD, size=12):
    return add_para(doc, text, color=color, size=size, bold=False,
                    align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=2)


def add_heading(doc, text, color=NAVY, size=14):
    """Cabeçalho de seção navy com filete dourado embaixo."""
    p = add_para(doc, text, color=color, size=size, bold=True,
                 space_before=14, space_after=2)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    _set(bottom, **{"w:val": "single", "w:sz": "8", "w:space": "4", "w:color": GOLD})
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def add_bullets(doc_or_cell, items, color=TEXT, size=11, marker="•  "):
    for it in items:
        p = doc_or_cell.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Pt(10)
        p.paragraph_format.line_spacing = 1.15
        style_run(p.add_run(marker), color=GOLD, size=size, bold=True)
        _emit_inline(p, str(it), default_color=color, size=size)
    return doc_or_cell


def _emit_inline(p, text, default_color=TEXT, size=11, bold=False):
    """Escreve texto colorindo ✓ de verde e ✗ de vermelho."""
    buf = ""
    for ch in text:
        if ch in ("✓", "✗"):
            if buf:
                style_run(p.add_run(buf), color=default_color, size=size, bold=bold)
                buf = ""
            style_run(p.add_run(ch), color=(GREEN if ch == "✓" else RED), size=size, bold=True)
        else:
            buf += ch
    if buf:
        style_run(p.add_run(buf), color=default_color, size=size, bold=bold)


# ---- Caixa de destaque -----------------------------------------------------
def add_highlight_box(doc, label, text):
    """Caixa dourada clara (como as células de destaque do modelo): rótulo navy
    em negrito + texto navy."""
    if not text:
        return None
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    cell = tbl.rows[0].cells[0]
    shade(cell._tc, GOLD_LT)
    cell_borders(cell, color=GOLD, sz=8)
    set_cell_margins(cell, top=100, bottom=100, left=160, right=160)
    cell.paragraphs[0]._element.getparent().remove(cell.paragraphs[0]._element)
    p = cell.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    if label:
        style_run(p.add_run(f"{label.upper()} — "), color=NAVY, size=10.5, bold=True)
    style_run(p.add_run(text), color=NAVY, size=10.5, bold=True)
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


def make_table(doc, headers, rows, widths=None, header_fill=NAVY, header_color=GOLD,
               body_fill=WHITE, alt_fill=ROW_ALT, body_color=TEXT,
               header_size=10, body_size=10.5, aligns=None, first_col_dark=True):
    """Tabela do modelo: cabeçalho navy com texto dourado em caixa alta,
    primeira coluna navy com texto branco em negrito, corpo com linhas
    zebradas branco/#EEF1F5 e bordas sutis."""
    ncols = len(headers)
    tbl = doc.add_table(rows=1, cols=ncols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = (widths is None)
    aligns = aligns or [WD_ALIGN_PARAGRAPH.LEFT] * ncols

    hdr = tbl.rows[0].cells
    for i, h in enumerate(headers):
        shade(hdr[i]._tc, header_fill)
        cell_borders(hdr[i], color=header_fill, sz=4)
        set_cell_margins(hdr[i])
        p = _clear_cell(hdr[i])
        p.alignment = aligns[i]
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(str(h).upper()), color=header_color, size=header_size, bold=True)

    for r, row in enumerate(rows):
        cells = tbl.add_row().cells
        fill = body_fill if r % 2 == 0 else alt_fill
        for i, val in enumerate(row):
            dark = first_col_dark and i == 0
            shade(cells[i]._tc, NAVY_CELL if dark else fill)
            cell_borders(cells[i], color=(NAVY_CELL if dark else BORDER), sz=4)
            set_cell_margins(cells[i])
            p = _clear_cell(cells[i])
            p.alignment = aligns[i]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.12
            if dark:
                _emit_inline(p, str(val), default_color=WHITE, size=body_size, bold=True)
            else:
                _emit_inline(p, str(val), default_color=body_color, size=body_size)

    if widths:
        for row in tbl.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = w
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
    """Linha final destacada (ex.: NOTA FINAL PONDERADA): navy escuro + dourado."""
    cells = tbl.add_row().cells
    n = len(cells)
    if n >= 2:
        a = cells[0]
        for c in cells[1:n - 1]:
            a = a.merge(c)
        for c in (cells[0], cells[n - 1]):
            shade(c._tc, fill)
            cell_borders(c, color=fill, sz=8)
            set_cell_margins(c)
        p = _clear_cell(cells[0])
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(label), color=color, size=size, bold=True)
        p2 = _clear_cell(cells[n - 1])
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        style_run(p2.add_run(value), color=color, size=size, bold=True)


# ---- Bloco da NOTA FINAL ---------------------------------------------------
def add_score_block(doc, nota, label, prefixo="NOTA FINAL: "):
    """Bloco grande 'NOTA FINAL: X,X / 10' — caixa navy (como o bloco do logo),
    nota em dourado.

    `prefixo` existe por causa do resumo por coordenador (11/08/2026): ali o número é a MÉDIA
    DA UNIDADE, e a palavra "NOTA FINAL" logo acima do nome do coordenador dava a impressão de
    ser a nota dele. O padrão é o texto de sempre — relatório individual e resumo de unidade
    não mudam."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    shade(cell._tc, NAVY_DK)
    cell_borders(cell, color=GOLD, sz=12)
    set_cell_margins(cell, top=140, bottom=140, left=160, right=160)
    _clear_cell(cell)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    style_run(p.add_run(prefixo), color=WHITE, size=18, bold=True)
    style_run(p.add_run(f"{nota}"), color=GOLD, size=26, bold=True)
    style_run(p.add_run("  / 10"), color="C7D0DC", size=16, bold=True)
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
    # Cabeçalho: texto navy pequeno com filete dourado (páginas seguintes)
    h = sec.header
    h.is_linked_to_previous = False
    hp = h.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.paragraph_format.space_after = Pt(2)
    style_run(hp.add_run(header_text), color=NAVY, size=9, bold=True)
    _para_bottom_border(hp, GOLD)

    # Rodapé cinza centralizado, como no modelo
    f = sec.footer
    f.is_linked_to_previous = False
    fp = f.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(fp.add_run(f"{footer_left}   •   {header_text}   •   Página "),
              color=GREY_LT, size=8.5)
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
