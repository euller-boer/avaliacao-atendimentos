# -*- coding: utf-8 -*-
"""Confere (sem copiar) se CLI e app desktop estao com os mesmos arquivos."""
import os, hashlib

CLI = r"C:\Users\atend\.claude\skills"
DESK = ("\\\\?\\C:\\Users\\atend\\AppData\\Local\\Packages\\Claude_pzs8sxrjxfjjc\\LocalCache"
        "\\Roaming\\Claude\\local-agent-mode-sessions\\skills-plugin"
        "\\29b22f3e-77c6-4955-8623-579c35f9ee6d\\e12d3bd3-a6b1-4d16-9b7e-6d878ed5e6ee\\skills")

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
