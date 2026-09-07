#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Empacota a entrega: .docx -> PDF -> .zip por coordenador, direto no Downloads.

Substitui o passo que era feito à mão seguindo o SKILL.md. Existe porque instrução escrita
esquece e código não: em 11/08/2026 dois defeitos vieram exatamente daí — os zips saíram sem a
unidade no nome (o pacote de Taquaritinga ia anexado no e-mail da diretoria de Monte Alto) e o
"Passo 3" continuou mandando gerar um zip só depois que a divisão por equipe já existia.

A divisão vem da MESMA constante `EQUIPES` que o `analisar.py` usa para montar os relatórios —
não há segunda lista para desatualizar.

Uso:
    python3 scripts/empacotar.py <dir_com_os_json>  [--saida <pasta>] [--manter-docx]

Entra: a pasta que o `analisar.py` gerou (analise_*.json + resumo_equipe*.json).
Sai:   os .zip no Downloads (ou em --saida) e um resumo do que foi feito na tela.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from analisar import EQUIPES, MESES  # noqa: E402  (mesma fonte da divisão e dos meses)

SOFFICE_CANDIDATOS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/usr/local/bin/soffice", "soffice",
]


def achar_soffice():
    for c in SOFFICE_CANDIDATOS:
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return shutil.which(c)
    sys.exit("ERRO: LibreOffice (soffice) não encontrado — sem ele não dá para gerar os PDFs.")


def safe(nome):
    return re.sub(r"[^A-Za-z0-9]+", "_", nome).strip("_")


def sufixo_de(periodo_label_base, tipo):
    """'Julho/2026' -> '07-2026' · '03/08/2026 a 09/08/2026' -> '03-08-2026_a_09-08-2026'.

    O nome do mês volta a número pela MESMA tabela `MESES` do analisar.py, para não existir
    uma segunda lista de meses que possa divergir.
    """
    p = periodo_label_base.strip()
    if tipo == "mes":
        nome_mes, _, ano = p.partition("/")
        inv = {v.lower(): k for k, v in MESES.items()}
        num = inv.get(nome_mes.strip().lower())
        if not num:
            sys.exit(f"ERRO: não reconheci o mês em '{p}'.")
        return f"{num:02d}-{ano.strip()}"
    return p.replace("/", "-").replace(" a ", "_a_")


def rodar(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERRO ao rodar {' '.join(args[:3])}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description="Empacota a entrega da avaliação de atendimentos.")
    ap.add_argument("dir_json", help="pasta gerada pelo analisar.py")
    ap.add_argument("--saida", default=None, help="onde gravar os .zip (padrão: Downloads)")
    ap.add_argument("--manter-docx", action="store_true",
                    help="não apagar a pasta temporária com os .docx/.pdf")
    a = ap.parse_args()

    dj = a.dir_json
    resumo_path = os.path.join(dj, "resumo_equipe.json")
    if not os.path.exists(resumo_path):
        sys.exit(f"ERRO: não achei {resumo_path}. Rode o analisar.py antes.")
    resumo = json.load(open(resumo_path, encoding="utf-8"))

    tipo = resumo.get("periodo_tipo", "mes")
    mensal = (tipo == "mes")
    label = resumo.get("periodo_label", "")
    base, _, unidade = label.partition("—")
    unidade = unidade.strip()
    if not unidade:
        sys.exit(f"ERRO: não consegui ler a unidade de '{label}'.")
    suf = sufixo_de(base, tipo)

    prefixo = "Análise de atendimento" if mensal else "Acompanhamento de atendimento"
    pref_ind = "Relatorio" if mensal else "Acompanhamento"
    pref_eq = "Resumo_Equipe" if mensal else "Acompanhamento_Equipe"
    # O consolidado do escritorio tem nome proprio: desde 01/09/2026 ele vai TAMBEM no pacote de
    # cada coordenador, e "Resumo_Equipe_<mes>" ao lado de "Resumo_Equipe_<coord>_<mes>" nao dizia
    # qual era qual na hora de abrir o zip.
    pref_esc = "Resumo_Escritorio" if mensal else "Acompanhamento_Escritorio"

    saida = a.saida or os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(saida, exist_ok=True)

    print(f"Unidade..: {unidade}")
    print(f"Período..: {base.strip()}  (sufixo dos arquivos: {suf})")
    print(f"Regime...: {'AVALIAÇÃO MENSAL (com nota)' if mensal else 'ACOMPANHAMENTO (sem nota)'}")
    print(f"Saída....: {saida}\n")

    tmp = tempfile.mkdtemp(prefix="altocon_pack_")
    try:
        # ---- 1. .docx individuais ------------------------------------------
        individuais = {}
        for j in sorted(glob.glob(os.path.join(dj, "analise_*.json"))):
            nome = json.load(open(j, encoding="utf-8"))["colaborador"]
            d = os.path.join(tmp, f"{pref_ind}_{safe(nome)}_{suf}.docx")
            rodar(sys.executable, os.path.join(AQUI, "build_report.py"), j, d)
            individuais[nome.upper()] = d
        if not individuais:
            sys.exit("ERRO: nenhum analise_*.json na pasta indicada.")

        # ---- 2. resumo da unidade + resumos por coordenador ----------------
        resumo_unidade = os.path.join(tmp, f"{pref_esc}_{safe(unidade)}_{suf}.docx")
        rodar(sys.executable, os.path.join(AQUI, "build_team_summary.py"), resumo_path, resumo_unidade)

        equipes = {}
        for j in sorted(glob.glob(os.path.join(dj, "resumo_equipe_*.json"))):
            d0 = json.load(open(j, encoding="utf-8"))
            esc = d0.get("escopo_equipe") or {}
            coord = esc.get("coordenador")
            if not coord:
                sys.exit(f"ERRO: {j} não tem escopo_equipe.coordenador.")
            d = os.path.join(tmp, f"{pref_eq}_{safe(coord)}_{suf}.docx")
            rodar(sys.executable, os.path.join(AQUI, "build_team_summary.py"), j, d)
            equipes[coord.upper()] = {
                "coordenador": coord,
                "departamento": esc.get("departamento", ""),
                "docx": d,
                "membros": [c["nome"].upper() for c in d0.get("colaboradores", [])],
            }

        # ---- 3. PDF (uma chamada só) ---------------------------------------
        docs = sorted(glob.glob(os.path.join(tmp, "*.docx")))
        rodar(achar_soffice(), "--headless", "--convert-to", "pdf", *docs, "--outdir", tmp)
        pdf = lambda d: os.path.splitext(d)[0] + ".pdf"
        faltando = [os.path.basename(d) for d in docs if not os.path.exists(pdf(d))]
        if faltando:
            sys.exit(f"ERRO: PDF não gerado para: {', '.join(faltando)}")
        print(f"{len(docs)} documentos convertidos em PDF\n")

        # ---- 4. zips --------------------------------------------------------
        # A unidade SEMPRE entra no nome: é por ela que o script de e-mail separa os pacotes
        # quando as duas unidades rodam no mesmo período e os zips convivem no Downloads.
        gerados = []

        def zipar(nome_zip, docx_list):
            alvo = os.path.join(saida, nome_zip)
            with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
                for d in docx_list:
                    z.write(pdf(d), os.path.basename(pdf(d)))
            gerados.append(alvo)
            return alvo

        if equipes:
            div = EQUIPES.get(unidade, [])
            declarados = set()
            for e in div:
                info = equipes.get(e["coordenador"])
                if not info:
                    print(f"  AVISO: equipe de {e['coordenador']} declarada em EQUIPES mas sem "
                          f"resumo gerado — ninguém dela apareceu no período.")
                    continue
                docs_eq = [individuais[m] for m in info["membros"] if m in individuais]
                declarados.update(info["membros"])
                # o resumo do escritorio vai junto para o gestor comparar a equipe dele com a
                # media da unidade sem precisar pedir o pacote da diretoria
                alvo = zipar(f"{prefixo} de {unidade} - {info['coordenador']} - {suf}.zip",
                             docs_eq + [info["docx"], resumo_unidade])
                print(f"  {info['coordenador']:24} {info['departamento']:34} "
                      f"{len(docs_eq)} relatório(s) + resumo da equipe + resumo do escritório")
            # diretoria: todos os individuais + resumo da unidade + os resumos de equipe
            todos = list(individuais.values()) + [resumo_unidade] + [i["docx"] for i in equipes.values()]
            zipar(f"{prefixo} de {unidade} (Diretoria) - {suf}.zip", todos)
            print(f"  {unidade + ' (Diretoria)':24} {'consolidado':34} "
                  f"{len(individuais)} relatório(s) + {1 + len(equipes)} resumos")
            fora = [n for n in individuais if n not in declarados]
            if fora:
                print(f"\n  Sem equipe declarada (entram SÓ no pacote da diretoria): "
                      f"{', '.join(sorted(fora))}")
        else:
            zipar(f"{prefixo} de {unidade} - {suf}.zip",
                  list(individuais.values()) + [resumo_unidade])
            print(f"  {unidade:24} {'pacote único (sem divisão)':34} "
                  f"{len(individuais)} relatório(s) + resumo")

        # ---- 5. conferência -------------------------------------------------
        print("\nConferência:")
        esperados = len(resumo.get("colaboradores", []))
        ok = (esperados == len(individuais))
        print(f"  {'OK ' if ok else '*** '}relatórios individuais: {len(individuais)} "
              f"(resumo da unidade lista {esperados})")
        if not ok:
            sys.exit("ERRO: número de relatórios não bate com o resumo da unidade.")
        for g in gerados:
            n = len(zipfile.ZipFile(g).namelist())
            print(f"  OK  {os.path.basename(g)}  ({n} PDFs)")
        print(f"\n{len(gerados)} pacote(s) em {saida}")
    finally:
        if a.manter_docx:
            print(f"\n(.docx/.pdf mantidos em {tmp})")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
