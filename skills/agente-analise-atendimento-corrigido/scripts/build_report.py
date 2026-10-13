#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o RELATÓRIO INDIVIDUAL (.docx) de análise de atendimento — identidade visual Altocon (fundo branco, navy/dourado, logo no topo).

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
    style.font.color.rgb = RGBColor.from_string(T.TEXT)

    T.set_page_background(doc)  # página branca

    colaborador = data.get("colaborador", "Colaborador")
    periodo = data.get("periodo_label", "")
    data_ger = data.get("data_geracao", "")

    # ACOMPANHAMENTO (coordenação 08/08/2026): semana e dia não recebem nota — o documento é um
    # levantamento do que os atendimentos mostram em cada critério. `periodo_tipo` vem do
    # analisar.py; JSON antigo (sem a chave) é tratado como MENSAL, para não mudar pacote já emitido.
    tipo = data.get("periodo_tipo", "mes")
    acomp = tipo != "mes"
    titulo = {"intervalo": "Acompanhamento Semanal de Atendimento",
              "dia": "Acompanhamento Diário de Atendimento"}.get(tipo, "Relatório de Análise de Atendimento")
    rotulo_cab = ("Acompanhamento" if acomp else "Análise") + f" de Atendimento — {colaborador}"

    T.setup_header_footer(doc, rotulo_cab)

    # ---- Capa/título -------------------------------------------------------
    T.add_logo(doc)
    T.add_title(doc, titulo)
    T.add_subtitle(doc, colaborador + (f"  •  {periodo}" if periodo else ""))
    # `data_geracao` vem do "Gerado em:" da TRANSCRIÇÃO (a base congelada), não da data em que
    # este relatório foi montado. Rotular só como "Gerado em" fazia o PDF parecer mais antigo do
    # que era (transcrição de 03/08 num pacote emitido em 07/08). Agora as duas datas aparecem,
    # cada uma com o nome certo. A data de emissão NÃO entra no JSON — os JSONs seguem
    # bit-a-bit idênticos entre rodadas (trava de determinismo do checklist).
    T.add_subtitle(doc, T.linha_datas(data_ger), size=9)
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

    # ---- 2. Nota Geral / Panorama do Período -------------------------------
    criterios = data.get("criterios", [])

    if acomp:
        # levantamento: nada de nota, peso, caixa de nota final ou linha de total
        T.add_heading(doc, "2. Panorama do Período")
        if data.get("panorama_texto"):
            T.add_para(doc, data["panorama_texto"])
        if criterios:
            rows = [[c.get("nome", ""), c.get("justificativa", "") or "—"] for c in criterios]
            T.make_table(
                doc, ["Critério", "O que foi observado no período"], rows,
                widths=[Cm(5.2), Cm(11.3)],
                aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
            T._spacer(doc, 2)
    else:
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
                # ✓ a partir de 9 (mesmo corte do "Boa prática" das caixas), ✗ abaixo de 8,
                # nada entre 8 e 9 — decisão do usuário em 01/10/2026: um 8,5 não é falha.
                # Critério "Não avaliado" (sem nota) fica sem marca.
                n = T.parse_nota(c.get("nota"))
                mk = "" if n is None else " ✓" if n >= 9 else " ✗" if n < 8 else ""
                rows.append([
                    c.get("nome", ""),
                    T.peso_pct(c.get("nome", ""), c.get("peso")),
                    str(c.get("nota", "")) + mk,
                    c.get("justificativa", "") or "—",
                ])
            tbl = T.make_table(
                doc, ["Critério", "Peso", "Nota", "Justificativa"], rows,
                widths=[Cm(4.0), Cm(1.6), Cm(2.0), Cm(8.9)],
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
        T.add_heading(doc, f"{sec_num}. {nome}" if acomp else f"{sec_num}. {nome} — {nota} / 10")
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
                # `marca` (✓/✗) vem do analisar.py em todos os criterios desde
                # 01/10/2026; docx_theme._emit_inline colore verde/vermelho.
                linhas.append(f"{e.get('marca','')}{pre}“{trecho}”{suf}")
            if linhas:
                rotulo = ("Exemplos (cliente · data · hora):"
                          if not (len(ev) == 1 and ev[0].get("sem_ocorrencia"))
                          else "Evidência:")
                T.add_para(doc, rotulo, color=T.GOLD_LT, size=10, bold=True, space_after=1)
                T.add_bullets(doc, linhas)
        # CRITERIO 2 — casos que o detector de compromisso de retorno absolveu
        # (correcao 2.2, 26/08/2026). Saem SEMPRE listados: o perdao e automatico, e
        # so nao vira caixa-preta porque quem revisa consegue ver o que foi perdoado.
        perd = data.get("criterio2_perdoados") or []
        if perd and nome == "Gestão de Prazos e Comunicação Assertiva":
            T.add_para(doc, "Conferir — termo vago com prazo de retorno (não contados como vagos):",
                       color=T.GOLD_LT, size=10, bold=True, space_before=6, space_after=1)
            linhas = []
            for e in perd:
                cab = " · ".join(x for x in [e.get("cliente"), e.get("data"), e.get("hora")]
                                 if x and x != "—")
                tr = " ".join((e.get("trecho") or "").split())
                if len(tr) > 300:
                    tr = tr[:300].rstrip() + "…"
                termos = e.get("termos")
                linhas.append(f"{cab} — “{tr}”" + (f"  [{termos}]" if termos else ""))
            T.add_bullets(doc, linhas)
        # CRITERIO 6 — repasses que a TRIAGEM mandou fazer (regra 3.1, 27/08/2026).
        # Mesmo padrao do perdao do criterio 2: o repasse sai da contagem, mas fica
        # listado, com a instrucao original, para conferencia na mao.
        instr = data.get("criterio6_instruidos") or []
        if instr and nome == "Postura Contínua e Soluções Definitivas":
            T.add_para(doc, "Conferir — repasses instruídos pela triagem (não contados como repasse):",
                       color=T.GOLD_LT, size=10, bold=True, space_before=6, space_after=1)
            linhas = []
            for e in instr:
                cab = " · ".join(x for x in [e.get("cliente"), e.get("data"), e.get("hora")]
                                 if x and x != "—")
                txt = " ".join((e.get("instrucao") or "").split())
                if len(txt) > 220:
                    txt = txt[:220].rstrip() + "…"
                linhas.append(f"{cab} — repassado para {e.get('destino')} conforme instrução de "
                              f"{e.get('instruido_por')}: “{txt}”")
            T.add_bullets(doc, linhas)
        # CRITERIO 6 — chamados usados para passar uma TAREFA interna a um colega
        # (regra 3.2, 27/08/2026). Sem mensagem ao cliente e com recado escrito: o
        # repasse sai da contagem e fica listado, com o recado, para conferencia.
        deleg = data.get("criterio6_delegacoes") or []
        if deleg and nome == "Postura Contínua e Soluções Definitivas":
            T.add_para(doc, "Conferir — tarefa interna passada a um colega (não contados como repasse):",
                       color=T.GOLD_LT, size=10, bold=True, space_before=6, space_after=1)
            linhas = []
            for e in deleg:
                cab = " · ".join(x for x in [e.get("cliente"), e.get("data"), e.get("hora")]
                                 if x and x != "—")
                txt = " ".join((e.get("recado") or "").split())
                if len(txt) > 220:
                    txt = txt[:220].rstrip() + "…"
                linhas.append(f"{cab} — sem mensagem ao cliente; recado interno para "
                              f"{e.get('destino')}: “{txt}”")
            T.add_bullets(doc, linhas)
        # CRITERIO 6 — chamado que a triagem mandou para a pessoa errada e ela
        # redirecionou REGISTRANDO o motivo (regra 3.3, 27/08/2026). Sem registro o
        # repasse continua contando; por isso o que sai listado aqui e o registro.
        errados = data.get("criterio6_chegou_errado") or []
        if errados and nome == "Postura Contínua e Soluções Definitivas":
            T.add_para(doc, "Conferir — chamado que chegou errado e foi redirecionado com o motivo "
                            "registrado (não contados como repasse):",
                       color=T.GOLD_LT, size=10, bold=True, space_before=6, space_after=1)
            linhas = []
            for e in errados:
                cab = " · ".join(x for x in [e.get("cliente"), e.get("data"), e.get("hora")]
                                 if x and x != "—")
                txt = " ".join((e.get("motivo") or "").split())
                if len(txt) > 220:
                    txt = txt[:220].rstrip() + "…"
                linhas.append(f"{cab} — veio de {e.get('veio_de')} e foi redirecionado para "
                              f"{e.get('destino')} em {e.get('minutos')} min; "
                              f"{e.get('onde')}: “{txt}”")
            T.add_bullets(doc, linhas)
        d = c.get("destaque")
        if d and d.get("texto"):
            T.add_highlight_box(doc, d.get("label", ""), d.get("texto", ""))
        sec_num += 1

    # ---- 12. Registros Internos do Atendimento ----------------------------
    # Secao criada em 25/08/2026 a pedido da coordenacao. Lista TODA nota interna
    # escrita pelo proprio colaborador — reconhecida ou nao pelo filtro de canal —
    # para que o atendimento feito por telefone/presencial nao fique invisivel. O
    # aviso so aparece quando o MESMO atendimento consta apontado no criterio 1.
    regs = data.get("registros_internos") or []
    if regs:
        T.add_heading(doc, "12. Registros Internos do Atendimento")
        T.add_para(doc,
                   "Notas internas escritas pelo próprio colaborador no período. Elas não são "
                   "mensagens ao cliente: não entram na contagem de mensagens enviadas nem nos "
                   "critérios de escrita. Servem para a leitura do atendimento e para conferir "
                   "os indicadores acima.")
        if data.get("registros_internos_resumo"):
            T.add_para(doc, data["registros_internos_resumo"], bold=True)
        linhas = []
        for r in regs:
            cab = " · ".join(x for x in [r.get("cliente"), r.get("data"), r.get("hora")]
                             if x and x != "—")
            txt = " ".join((r.get("texto") or "").split())
            if len(txt) > 300:
                txt = txt[:300].rstrip() + "…"
            # A tentativa de contato encerra a contagem desde 26/08/2026, mas recebe
            # marcador PROPRIO: quem revisa precisa distinguir "liguei e resolvi" de
            # "liguei e caiu na caixa postal" — as duas param o cronometro igual.
            if r.get("por_tentativa"):
                marca = "  [encerrado por tentativa de contato]"
            elif r.get("atendimento_registrado"):
                marca = "  [atendimento registrado]"
            else:
                marca = ""
            linha = f"{cab} — “{txt}”{marca}"
            if r.get("alerta"):
                linha += f"    ⚠ CONFERIR — {r['alerta']}"
            linhas.append(linha)
        T.add_para(doc, "Registros (cliente · data · hora):",
                   color=T.GOLD_LT, size=10, bold=True, space_after=1)
        T.add_bullets(doc, linhas)
        if any(r.get("alerta") for r in regs):
            T.add_highlight_box(doc, "Atenção",
                                "Os itens marcados com ⚠ CONFERIR têm registro de atendimento que o "
                                "indicador acima não considerou. Conferir antes de usar o "
                                "número como apontamento.")

    # ---- 13. Pontos Positivos ---------------------------------------------
    T.add_heading(doc, "13. Pontos Positivos")
    pos = data.get("pontos_positivos") or []
    if pos:
        T.add_bullets(doc, pos)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)

    # ---- 13. Pontos de Melhoria / de Atenção ------------------------------
    T.add_heading(doc, "14. Pontos de Atenção" if acomp else "14. Pontos de Melhoria")
    mel = data.get("pontos_melhoria") or []
    if mel:
        T.add_bullets(doc, mel)
    else:
        T.add_para(doc, "—", color=T.GREY_LT)
    md = data.get("melhoria_destaque")
    if md and md.get("texto"):
        T.add_highlight_box(doc, md.get("label", "Regra de ouro"), md.get("texto", ""))

    # ---- 14. Conclusão -----------------------------------------------------
    T.add_heading(doc, "15. Conclusão")
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
