# Abre um e-mail JÁ PRONTO no Thunderbird com o .zip da avaliação anexado.
# NÃO envia nada — só monta o rascunho; quem clica em "Enviar" é o usuário.
#
# Uso:
#   powershell -File enviar-avaliacao-email.ps1 -Zip "<caminho do .zip>" -Unidade "Taquaritinga" -Periodo "06/2026"
#   (opcional)  -Para "a@x.com,b@x.com"   -Regime "Avaliação mensal"

param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$Unidade = "",
    [string]$Periodo = "",
    [string]$Regime  = "Avaliação mensal",
    [string]$Para    = ""
)

$ErrorActionPreference = "Stop"

# --- destinatários: lidos de avaliacao-destinatarios.txt (por unidade, se houver) ---
$CFG = Join-Path $env:USERPROFILE ".claude\avaliacao-destinatarios.txt"
$CC  = ""
$avisoDest = ""

if (-not $Para -or $Para.Trim() -eq "") {
    $mapa = @{}
    if (Test-Path -LiteralPath $CFG) {
        foreach ($ln in (Get-Content -LiteralPath $CFG -Encoding UTF8)) {
            $t = $ln.Trim()
            if ($t -eq "" -or $t.StartsWith("#")) { continue }
            $i = $t.IndexOf("=")
            if ($i -lt 1) { continue }
            $chave = $t.Substring(0, $i).Trim().ToUpper()
            $valor = $t.Substring($i + 1).Trim()
            if ($valor) { $mapa[$chave] = $valor }
        }
    }
    $chaveUni = $Unidade.Trim().ToUpper()
    if ($chaveUni -and $mapa.ContainsKey($chaveUni)) { $Para = $mapa[$chaveUni] }   # unidade tem prioridade
    elseif ($mapa.ContainsKey("PADRAO"))             { $Para = $mapa["PADRAO"] }
    else { $Para = ""; $avisoDest = "Nenhum destinatario configurado - preencha o campo Para no Thunderbird (ou edite $CFG)." }
    if ($mapa.ContainsKey("CC")) { $CC = $mapa["CC"] }
}

if (-not (Test-Path -LiteralPath $Zip)) {
    Write-Host "ERRO: nao encontrei o arquivo: $Zip" -ForegroundColor Red
    exit 1
}
$zipItem = Get-Item -LiteralPath $Zip
$tamMB   = [math]::Round($zipItem.Length / 1MB, 1)

$tb = @("$env:ProgramFiles\Mozilla Thunderbird\thunderbird.exe",
        "${env:ProgramFiles(x86)}\Mozilla Thunderbird\thunderbird.exe",
        "$env:LOCALAPPDATA\Mozilla Thunderbird\thunderbird.exe") |
      Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $tb) {
    Write-Host "ERRO: Thunderbird nao encontrado nesta maquina." -ForegroundColor Red
    exit 1
}

$titulo  = "Avaliação de Atendimentos"
if ($Unidade) { $titulo += " - $Unidade" }
if ($Periodo) { $titulo += " - $Periodo" }

$corpo = @"
Prezados,

Segue em anexo a $($Regime.ToLower()) dos atendimentos$(if($Unidade){" da unidade $Unidade"})$(if($Periodo){", referente a $Periodo"}).

O arquivo contém um relatório individual em PDF para cada colaborador avaliado e o Resumo da Equipe.

As notas seguem os 9 critérios do Manual de Padrões Operacionais, com os pesos definidos pela coordenação, e cada critério traz exemplos reais (cliente, data e hora) extraídos das conversas do período.

Atenciosamente,
"@

# o Thunderbird espera o anexo como URL file:/// — via AbsoluteUri, que codifica os espacos
# como %20. Montada a mao, a URL saia com espacos crus e o anexo era descartado sem aviso.
$anexoUrl = ([System.Uri]$zipItem.FullName).AbsoluteUri

# valores entre aspas simples: protege virgulas dentro do texto
# (aspas duplas removidas: o bloco todo vai entre aspas duplas na linha de comando)
function Q($s) { "'" + ($s -replace "'", "" -replace '"', "") + "'" }
# attachment ANTES do body: as quebras de linha do corpo cortavam a leitura do argumento e
# tudo que vinha depois se perdia — o e-mail abria sem anexo. Corrigido em 11/08/2026.
$arg = "to=" + (Q $Para) + ",subject=" + (Q $titulo) + ",attachment=" + (Q $anexoUrl)
if ($CC) { $arg += ",cc=" + (Q $CC) }
$arg += ",body=" + (Q $corpo)

Write-Host ""
Write-Host "Abrindo o e-mail no Thunderbird..." -ForegroundColor Cyan
Write-Host "  Para....: $(if($Para){$Para}else{'(vazio - preencher no Thunderbird)'})"
if ($CC) { Write-Host "  CC......: $CC" }
Write-Host "  Unidade.: $(if($Unidade){$Unidade}else{'(nao informada)'})"
Write-Host "  Assunto.: $titulo"
Write-Host "  Anexo...: $($zipItem.Name) ($tamMB MB)"
Write-Host ""
Write-Host "  >> NADA FOI ENVIADO. Confira e clique em Enviar no Thunderbird. <<" -ForegroundColor Yellow
if ($avisoDest) { Write-Host "  >> $avisoDest" -ForegroundColor Yellow }
Write-Host ""

# UMA string com aspas duplas explicitas: com -ArgumentList @("-compose", $arg) o PowerShell
# nao poe aspas em volta e o Thunderbird recebe o comando partido nos espacos.
Start-Process -FilePath $tb -ArgumentList ('-compose "' + $arg + '"')


