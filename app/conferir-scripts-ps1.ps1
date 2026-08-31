# Confere os scripts .ps1 da avaliacao de atendimentos:
#   1) sintaxe valida
#   2) UTF-8 COM BOM (sem o BOM o PowerShell 5.1 quebra os acentos)
#   3) toda funcao e DEFINIDA antes da primeira linha que a chama
#
# O item 3 existe por causa de um erro real (11/08/2026): a funcao Select-Opcao ficou
# definida depois da linha que a usava, e o script so quebrava no clique do usuario —
# o modo -Simular saia antes e dava tudo certo.
#
# Uso: powershell -File conferir-scripts-ps1.ps1

$ErrorActionPreference = "Stop"
$alvos = @("enviar-avaliacao-equipes.ps1", "enviar-avaliacao-email.ps1", "avaliacao-atendimentos-app.ps1")
$falhas = 0

foreach ($nome in $alvos) {
    $p = Join-Path $env:USERPROFILE ".claude\$nome"
    if (-not (Test-Path -LiteralPath $p)) { Write-Host "[PULADO] $nome (nao existe)" -ForegroundColor DarkGray; continue }
    Write-Host "`n=== $nome ===" -ForegroundColor Cyan

    $b = [IO.File]::ReadAllBytes($p)
    $temBom = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
    if ($temBom) { Write-Host "  BOM UTF-8........: OK" -ForegroundColor Green }
    else { Write-Host "  BOM UTF-8........: FALTANDO (acentos vao quebrar)" -ForegroundColor Red; $falhas++ }

    $txt = Get-Content -LiteralPath $p -Raw
    $erros = $null
    $tokens = [System.Management.Automation.PSParser]::Tokenize($txt, [ref]$erros)
    if ($erros -and $erros.Count -gt 0) {
        Write-Host "  Sintaxe..........: $($erros.Count) erro(s)" -ForegroundColor Red
        $erros | ForEach-Object { Write-Host "     linha $($_.Token.StartLine): $($_.Message)" -ForegroundColor Red }
        $falhas++
        continue
    }
    Write-Host "  Sintaxe..........: OK" -ForegroundColor Green

    # funcoes definidas: token "function" seguido do nome
    $defs = @{}
    for ($i = 0; $i -lt $tokens.Count - 1; $i++) {
        if ($tokens[$i].Type -eq "Keyword" -and $tokens[$i].Content -eq "function") {
            $n = $tokens[$i + 1].Content
            if ($n -and -not $defs.ContainsKey($n)) { $defs[$n] = $tokens[$i].StartLine }
        }
    }
    if ($defs.Count -eq 0) { Write-Host "  Ordem de funcoes.: (nenhuma funcao)" -ForegroundColor DarkGray; continue }

    $problemas = @()
    foreach ($n in $defs.Keys) {
        $usos = @($tokens | Where-Object { $_.Type -eq "Command" -and $_.Content -eq $n } |
                  Sort-Object StartLine | Select-Object -First 1)
        if ($usos.Count -gt 0 -and $usos[0].StartLine -lt $defs[$n]) {
            $problemas += "$n : usada na linha $($usos[0].StartLine), definida so na $($defs[$n])"
        }
    }
    if ($problemas.Count -gt 0) {
        Write-Host "  Ordem de funcoes.: PROBLEMA" -ForegroundColor Red
        $problemas | ForEach-Object { Write-Host "     $_" -ForegroundColor Red }
        $falhas++
    } else {
        Write-Host "  Ordem de funcoes.: OK ($($defs.Count) funcao(oes), todas definidas antes do uso)" -ForegroundColor Green
    }
}

Write-Host ""
if ($falhas -eq 0) { Write-Host "Tudo certo." -ForegroundColor Green }
else { Write-Host "$falhas problema(s) encontrado(s)." -ForegroundColor Red; exit 1 }
