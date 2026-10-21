# -*- coding: utf-8 -*-
"""Confere (sem copiar) se CLI e app desktop estao com os mesmos arquivos."""
import os, sys, glob, hashlib

# Os caminhos eram fixos em C:\Users\atend ate 21/10/2026. Depois da formatacao o usuario do
# Windows passou a ser outro e o app desktop gerou novos IDs de sessao no caminho - por isso
# agora os dois lados sao descobertos na hora, em vez de escritos aqui.
HOME = os.path.expanduser("~")
CLI = os.path.join(HOME, ".claude", "skills")

def achar_desktop():
    # A busca vai sem o prefixo \\?\ (os.listdir em ...\Packages falha com ele - WinError 123);
    # as pastas ate "skills" cabem no limite de 260. O prefixo entra so na leitura dos arquivos,
    # porque scripts\analisar.py passa de 260 caracteres.
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages")
    achados = glob.glob(os.path.join(base, "Claude_*", "LocalCache", "Roaming", "Claude",
                                     "local-agent-mode-sessions", "skills-plugin", "*", "*", "skills"))
    achados = [p for p in achados if os.path.isdir(os.path.join(p, ALVOS[0][0]))] or achados
    if not achados:
        sys.exit("Pasta de skills do app desktop NAO encontrada - as skills ainda nao foram "
                 "instaladas no app desktop do Claude (ou ele ainda nao abriu uma sessao).")
    if len(achados) > 1:
        print("AVISO: mais de uma pasta de skills no app desktop; usando a mais recente:")
        for p in achados:
            print("   ", p)
    return "\\\\?\\" + max(achados, key=os.path.getmtime)

ALVOS = [
    ("agente-analise-atendimento-corrigido", "scripts/analisar.py"),
    ("agente-analise-atendimento-corrigido", "scripts/build_team_summary.py"),
    # empacotar.py faltava aqui ate 07/09/2026 - e por isso a conferencia dizia "tudo
    # identico" enquanto o desktop estava parado na versao de 11/08, sem o resumo do
    # escritorio no pacote de cada coordenador. Ao criar script novo, incluir na lista.
    ("agente-analise-atendimento-corrigido", "scripts/empacotar.py"),
    ("agente-analise-atendimento-corrigido", "scripts/build_report.py"),
    ("agente-analise-atendimento-corrigido", "scripts/docx_theme.py"),
    ("agente-analise-atendimento-corrigido", "SKILL.md"),
    ("avaliacao-atendimentos-completa", "SKILL.md"),
    ("agente-leitura-conversas-corrigido", "SKILL.md"),
]

def h(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]

DESK = achar_desktop()
print(f"CLI....: {CLI}\nDESKTOP: {DESK[4:]}\n")
print(f"{'arquivo':58} {'CLI':>17} {'DESKTOP':>17}  situacao")
print("-" * 116)
divergentes = []
for skill, rel in ALVOS:
    src = os.path.join(CLI, skill, rel.replace("/", os.sep))
    dst = os.path.join(DESK, skill, rel.replace("/", "\\"))
    rotulo = f"{skill}/{rel}"
    if not os.path.exists(src):
        print(f"{rotulo:58} {'(nao existe)':>17} {'-':>17}  so no desktop?")
        continue
    if not os.path.exists(dst):
        print(f"{rotulo:58} {h(src):>17} {'(ausente)':>17}  SO NO CLI")
        continue
    a, b = h(src), h(dst)
    ok = "IDENTICO" if a == b else "*** DIVERGENTE ***"
    if a != b:
        divergentes.append(rotulo)
    print(f"{rotulo:58} {a:>17} {b:>17}  {ok}")

print()
if divergentes:
    print("PRECISAM SER SINCRONIZADOS:")
    for d in divergentes:
        print("  -", d)
else:
    print("Tudo que existe nas duas copias esta identico.")
