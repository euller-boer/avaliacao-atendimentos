Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# ----- paleta Altocon -----
$navy   = [System.Drawing.Color]::FromArgb(22, 36, 63)
$gold   = [System.Drawing.Color]::FromArgb(198, 165, 94)
$white  = [System.Drawing.Color]::White
$muted  = [System.Drawing.Color]::FromArgb(158, 168, 186)
$ink    = [System.Drawing.Color]::FromArgb(31, 37, 51)
$field  = [System.Drawing.Color]::White
$grayBt = [System.Drawing.Color]::FromArgb(231, 233, 238)

function Strip([string]$s) {
  if (-not $s) { return $s }
  ($s.Normalize([Text.NormalizationForm]::FormD) -replace '\p{Mn}', '')
}

# ----- janela -----
$form = New-Object System.Windows.Forms.Form
$form.Text = "Avaliação de Atendimentos — Altocon"
$form.ClientSize = New-Object System.Drawing.Size(480, 700)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedSingle"
$form.MaximizeBox = $false
$form.BackColor = $navy
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

# ----- cabecalho com logo -----
$header = New-Object System.Windows.Forms.Panel
$header.SetBounds(0, 0, 480, 150)
$header.BackColor = $navy
$form.Controls.Add($header)

$logoCandidatos = @(
  (Join-Path $env:USERPROFILE ".claude\assets\altocon-logo.png"),
  (Join-Path $env:USERPROFILE "Downloads\altocon-logo.png")
)
$logoFile = $logoCandidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $logoFile) {
  $c = Get-ChildItem (Join-Path $env:USERPROFILE "Downloads") -Filter *.png -ErrorAction SilentlyContinue |
       Where-Object { $_.Name -match 'alto|logo' } | Select-Object -First 1
  if ($c) { $logoFile = $c.FullName }
}

if ($logoFile) {
  $pic = New-Object System.Windows.Forms.PictureBox
  $pic.SizeMode = "Zoom"
  $pic.SetBounds(90, 16, 300, 118)
  $pic.BackColor = $navy
  try { $pic.Image = [System.Drawing.Image]::FromFile($logoFile) } catch {}
  $header.Controls.Add($pic)
} else {
  $lg = New-Object System.Windows.Forms.Label
  $lg.Text = "ALTOCON"
  $lg.ForeColor = $white
  $lg.Font = New-Object System.Drawing.Font("Segoe UI", 26, [System.Drawing.FontStyle]::Bold)
  $lg.TextAlign = "MiddleCenter"
  $lg.SetBounds(0, 30, 480, 46)
  $header.Controls.Add($lg)
  $lc = New-Object System.Windows.Forms.Label
  $lc.Text = "CONTABILIDADE"
  $lc.ForeColor = $gold
  $lc.Font = New-Object System.Drawing.Font("Segoe UI", 11)
  $lc.TextAlign = "MiddleCenter"
  $lc.SetBounds(0, 80, 480, 24)
  $header.Controls.Add($lc)
}

# faixa dourada
$rule = New-Object System.Windows.Forms.Panel
$rule.SetBounds(0, 150, 480, 3)
$rule.BackColor = $gold
$form.Controls.Add($rule)

$titulo = New-Object System.Windows.Forms.Label
$titulo.Text = "Avaliação de Atendimentos"
$titulo.ForeColor = $white
$titulo.Font = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$titulo.SetBounds(24, 162, 440, 26)
$form.Controls.Add($titulo)

$sub = New-Object System.Windows.Forms.Label
$sub.Text = "Leitura + Análise — relatórios da equipe"
$sub.ForeColor = $gold
$sub.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$sub.SetBounds(25, 189, 440, 18)
$form.Controls.Add($sub)

function Secao([string]$txt, [int]$y) {
  $l = New-Object System.Windows.Forms.Label
  $l.Text = $txt.ToUpper()
  $l.ForeColor = $muted
  $l.Font = New-Object System.Drawing.Font("Segoe UI", 8)
  $l.SetBounds(24, $y, 440, 16)
  $form.Controls.Add($l)
}

# ----- unidade -----
Secao "Unidade" 222
# painel proprio = grupo de radio independente (senao Unidade e Periodo viram um grupo so)
$panUni = New-Object System.Windows.Forms.Panel
$panUni.SetBounds(24, 238, 432, 26)
$panUni.BackColor = $navy
$form.Controls.Add($panUni)
$rbTaq = New-Object System.Windows.Forms.RadioButton
$rbTaq.Text = "Taquaritinga"
$rbTaq.ForeColor = $white
$rbTaq.SetBounds(0, 2, 140, 22)
$rbTaq.Checked = $true
$panUni.Controls.Add($rbTaq)
$rbMon = New-Object System.Windows.Forms.RadioButton
$rbMon.Text = "Monte Alto"
$rbMon.ForeColor = $white
$rbMon.SetBounds(156, 2, 140, 22)
$panUni.Controls.Add($rbMon)

# ----- colaboradores -----
Secao "Colaboradores" 272

# painel Taquaritinga (lista com caixinhas)
$panTaq = New-Object System.Windows.Forms.Panel
$panTaq.SetBounds(24, 290, 432, 168)
$panTaq.BackColor = $navy
$form.Controls.Add($panTaq)

$chkTodos = New-Object System.Windows.Forms.CheckBox
$chkTodos.Text = "Selecionar todos"
$chkTodos.ForeColor = $gold
$chkTodos.Checked = $true
$chkTodos.SetBounds(2, 0, 200, 22)
$panTaq.Controls.Add($chkTodos)

$clb = New-Object System.Windows.Forms.CheckedListBox
$clb.SetBounds(2, 26, 428, 138)
$clb.BackColor = $field
$clb.ForeColor = $ink
$clb.CheckOnClick = $true
$clb.BorderStyle = "FixedSingle"
$clb.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$nomesTaq = @("Ana Chueco", "Julia Ribeiro", "Leonardo Chueco", "Natália Tiesi", "Priscila de Pietro", "Tiago Chueco")
foreach ($n in $nomesTaq) { [void]$clb.Items.Add($n, $true) }
$panTaq.Controls.Add($clb)

$syncing = $false
$chkTodos.Add_CheckedChanged({
  if ($syncing) { return }
  $script:syncing = $true
  for ($i = 0; $i -lt $clb.Items.Count; $i++) { $clb.SetItemChecked($i, $chkTodos.Checked) }
  $script:syncing = $false
})
$clb.Add_ItemCheck({
  if ($syncing) { return }
  $script:syncing = $true
  $chk = 0
  for ($i = 0; $i -lt $clb.Items.Count; $i++) {
    $st = if ($i -eq $_.Index) { $_.NewValue } else { $clb.GetItemCheckState($i) }
    if ($st -eq [System.Windows.Forms.CheckState]::Checked) { $chk++ }
  }
  $chkTodos.Checked = ($chk -eq $clb.Items.Count)
  $script:syncing = $false
})

# painel Monte Alto (equipe inteira / digitar nomes)
$panMon = New-Object System.Windows.Forms.Panel
$panMon.SetBounds(24, 290, 432, 168)
$panMon.BackColor = $navy
$panMon.Visible = $false
$form.Controls.Add($panMon)

$mHint = New-Object System.Windows.Forms.Label
$mHint.Text = "Monte Alto = todos os operadores que não são de Taquaritinga."
$mHint.ForeColor = $muted
$mHint.SetBounds(2, 0, 428, 18)
$panMon.Controls.Add($mHint)

$rbEquipe = New-Object System.Windows.Forms.RadioButton
$rbEquipe.Text = "Avaliar a equipe inteira de Monte Alto"
$rbEquipe.ForeColor = $white
$rbEquipe.Checked = $true
$rbEquipe.SetBounds(2, 24, 420, 24)
$panMon.Controls.Add($rbEquipe)

$rbDigitar = New-Object System.Windows.Forms.RadioButton
$rbDigitar.Text = "Digitar nomes específicos:"
$rbDigitar.ForeColor = $white
$rbDigitar.SetBounds(2, 52, 420, 24)
$panMon.Controls.Add($rbDigitar)

$txtNomes = New-Object System.Windows.Forms.TextBox
$txtNomes.SetBounds(2, 80, 428, 80)
$txtNomes.Multiline = $true
$txtNomes.BackColor = $field
$txtNomes.ForeColor = $ink
$txtNomes.Enabled = $false
$txtNomes.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$panMon.Controls.Add($txtNomes)
$rbDigitar.Add_CheckedChanged({ $txtNomes.Enabled = $rbDigitar.Checked })

$rbTaq.Add_CheckedChanged({
  $panTaq.Visible = $rbTaq.Checked
  $panMon.Visible = -not $rbTaq.Checked
})

# ----- periodo (3 modos: Mes / Semana / Dia) -----
Secao "Período" 470
$hoje = Get-Date
$mesAnterior = $hoje.AddMonths(-1)

# painel proprio = grupo de radio independente do da Unidade
$panModo = New-Object System.Windows.Forms.Panel
$panModo.SetBounds(24, 486, 432, 26)
$panModo.BackColor = $navy
$form.Controls.Add($panModo)
$rbMes = New-Object System.Windows.Forms.RadioButton
$rbMes.Text = "Mês"
$rbMes.ForeColor = $white
$rbMes.Checked = $true
$rbMes.SetBounds(0, 2, 70, 22)
$panModo.Controls.Add($rbMes)
$rbPer = New-Object System.Windows.Forms.RadioButton
$rbPer.Text = "Período"
$rbPer.ForeColor = $white
$rbPer.SetBounds(80, 2, 90, 22)
$panModo.Controls.Add($rbPer)
$rbDia = New-Object System.Windows.Forms.RadioButton
$rbDia.Text = "Dia"
$rbDia.ForeColor = $white
$rbDia.SetBounds(180, 2, 70, 22)
$panModo.Controls.Add($rbDia)

# --- painel Mês
$panMes = New-Object System.Windows.Forms.Panel
$panMes.SetBounds(24, 516, 432, 62)
$panMes.BackColor = $navy
$form.Controls.Add($panMes)
$mesLbl = New-Object System.Windows.Forms.Label
$mesLbl.Text = "Mês"; $mesLbl.ForeColor = $muted; $mesLbl.SetBounds(0, 0, 60, 18)
$panMes.Controls.Add($mesLbl)
$cbMes = New-Object System.Windows.Forms.ComboBox
$cbMes.DropDownStyle = "DropDownList"
$cbMes.SetBounds(0, 20, 200, 26)
$cbMes.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$meses = @("Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro")
foreach ($m in $meses) { [void]$cbMes.Items.Add($m) }
$cbMes.SelectedIndex = $mesAnterior.Month - 1
$panMes.Controls.Add($cbMes)
$anoLbl = New-Object System.Windows.Forms.Label
$anoLbl.Text = "Ano"; $anoLbl.ForeColor = $muted; $anoLbl.SetBounds(224, 0, 60, 18)
$panMes.Controls.Add($anoLbl)
$cbAno = New-Object System.Windows.Forms.ComboBox
$cbAno.DropDownStyle = "DropDownList"
$cbAno.SetBounds(224, 20, 120, 26)
$cbAno.Font = New-Object System.Drawing.Font("Segoe UI", 10)
foreach ($a in ($hoje.Year - 2)..($hoje.Year + 1)) { [void]$cbAno.Items.Add("$a") }
$cbAno.SelectedItem = "$($mesAnterior.Year)"
$panMes.Controls.Add($cbAno)

# --- painel Periodo (intervalo livre de datas)
$panPer = New-Object System.Windows.Forms.Panel
$panPer.SetBounds(24, 516, 432, 62)
$panPer.BackColor = $navy
$panPer.Visible = $false
$form.Controls.Add($panPer)
$deLbl = New-Object System.Windows.Forms.Label
$deLbl.Text = "De"
$deLbl.ForeColor = $muted; $deLbl.SetBounds(0, 0, 60, 18)
$panPer.Controls.Add($deLbl)
$dtIni = New-Object System.Windows.Forms.DateTimePicker
$dtIni.Format = "Short"
$dtIni.SetBounds(0, 20, 140, 26)
$dtIni.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$dtIni.Value = $hoje.AddDays(-7)
$panPer.Controls.Add($dtIni)
$ateLbl = New-Object System.Windows.Forms.Label
$ateLbl.Text = "Até"
$ateLbl.ForeColor = $muted; $ateLbl.SetBounds(152, 0, 60, 18)
$panPer.Controls.Add($ateLbl)
$dtFim = New-Object System.Windows.Forms.DateTimePicker
$dtFim.Format = "Short"
$dtFim.SetBounds(152, 20, 140, 26)
$dtFim.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$dtFim.Value = $hoje.AddDays(-1)
$panPer.Controls.Add($dtFim)
$perInfo = New-Object System.Windows.Forms.Label
$perInfo.ForeColor = $gold
$perInfo.Font = New-Object System.Drawing.Font("Segoe UI", 8, [System.Drawing.FontStyle]::Bold)
$perInfo.SetBounds(300, 22, 132, 22)
$panPer.Controls.Add($perInfo)

function Conta-DiasUteis([datetime]$ini, [datetime]$fim) {
  $n = 0
  for ($d = $ini.Date; $d -le $fim.Date; $d = $d.AddDays(1)) {
    if ($d.DayOfWeek -ne [DayOfWeek]::Saturday -and $d.DayOfWeek -ne [DayOfWeek]::Sunday) { $n++ }
  }
  return $n
}
function Atualiza-Periodo {
  # a data final nunca pode ser anterior a inicial
  if ($dtFim.Value.Date -lt $dtIni.Value.Date) { $dtFim.Value = $dtIni.Value.Date }
  $tot = ($dtFim.Value.Date - $dtIni.Value.Date).Days + 1
  $ut  = Conta-DiasUteis $dtIni.Value $dtFim.Value
  $pd  = if ($tot -eq 1) { "1 dia" } else { "$tot dias" }
  $pu  = if ($ut -eq 1) { "1 útil" } else { "$ut úteis" }
  $perInfo.Text = "$pd ($pu)"
}
$dtIni.Add_ValueChanged({ Atualiza-Periodo })
$dtFim.Add_ValueChanged({ Atualiza-Periodo })
Atualiza-Periodo

# --- painel Dia
$panDia = New-Object System.Windows.Forms.Panel
$panDia.SetBounds(24, 516, 432, 62)
$panDia.BackColor = $navy
$panDia.Visible = $false
$form.Controls.Add($panDia)
$diaLbl = New-Object System.Windows.Forms.Label
$diaLbl.Text = "Data"
$diaLbl.ForeColor = $muted; $diaLbl.SetBounds(0, 0, 60, 18)
$panDia.Controls.Add($diaLbl)
$dtDia = New-Object System.Windows.Forms.DateTimePicker
$dtDia.Format = "Short"
$dtDia.SetBounds(0, 20, 140, 26)
$dtDia.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$dtDia.Value = $hoje.AddDays(-1)
$panDia.Controls.Add($dtDia)

$avisoAcomp = New-Object System.Windows.Forms.Label
$avisoAcomp.Text = "Período/Dia = acompanhamento (amostra reduzida), não avaliação formal."
$avisoAcomp.ForeColor = $gold
$avisoAcomp.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$avisoAcomp.SetBounds(24, 580, 432, 16)
$avisoAcomp.Visible = $false
$form.Controls.Add($avisoAcomp)

$AtualizaModo = {
  $panMes.Visible = $rbMes.Checked
  $panPer.Visible = $rbPer.Checked
  $panDia.Visible = $rbDia.Checked
  $avisoAcomp.Visible = (-not $rbMes.Checked)
}
$rbMes.Add_CheckedChanged($AtualizaModo)
$rbPer.Add_CheckedChanged($AtualizaModo)
$rbDia.Add_CheckedChanged($AtualizaModo)

# ----- botoes -----
$btnGo = New-Object System.Windows.Forms.Button
$btnGo.Text = "Iniciar avaliação"
$btnGo.SetBounds(24, 604, 300, 46)
$btnGo.FlatStyle = "Flat"
$btnGo.FlatAppearance.BorderSize = 0
$btnGo.BackColor = $gold
$btnGo.ForeColor = $navy
$btnGo.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$btnGo.Cursor = "Hand"
$form.Controls.Add($btnGo)

$btnQuit = New-Object System.Windows.Forms.Button
$btnQuit.Text = "Sair"
$btnQuit.SetBounds(336, 604, 120, 46)
$btnQuit.FlatStyle = "Flat"
$btnQuit.FlatAppearance.BorderSize = 0
$btnQuit.BackColor = $grayBt
$btnQuit.ForeColor = $ink
$btnQuit.Cursor = "Hand"
$form.Controls.Add($btnQuit)
$btnQuit.Add_Click({ $form.Close() })

$rodape = New-Object System.Windows.Forms.Label
$rodape.Text = "O resultado é entregue em PDF (.zip) na pasta Downloads."
$rodape.ForeColor = $muted
$rodape.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$rodape.TextAlign = "MiddleCenter"
$rodape.SetBounds(24, 660, 432, 18)
$form.Controls.Add($rodape)

# ----- acao Iniciar -----
$btnGo.Add_Click({
  if ($rbTaq.Checked) {
    $unidade = "Taquaritinga"
    $sel = @($clb.CheckedItems | ForEach-Object { $_ })
    if ($sel.Count -eq 0) {
      [System.Windows.Forms.MessageBox]::Show("Selecione ao menos um colaborador.", "Avaliação de Atendimentos", "OK", "Warning") | Out-Null
      return
    }
    $colabs = (($sel | ForEach-Object { Strip $_ }) -join ", ")
  } else {
    $unidade = "Monte Alto"
    if ($rbDigitar.Checked) {
      $nm = $txtNomes.Text.Trim()
      if (-not $nm) {
        [System.Windows.Forms.MessageBox]::Show("Digite os nomes dos colaboradores de Monte Alto.", "Avaliação de Atendimentos", "OK", "Warning") | Out-Null
        return
      }
      $colabs = (Strip $nm)
    } else {
      $colabs = "EQUIPE INTEIRA de Monte Alto (todos os operadores que nao sao de Taquaritinga)"
    }
  }
  # monta o periodo conforme o modo escolhido
  if ($rbMes.Checked) {
    $mesNum = $cbMes.SelectedIndex + 1
    $ano = [int]$cbAno.SelectedItem
    $ini = Get-Date -Year $ano -Month $mesNum -Day 1
    $fim = $ini.AddMonths(1).AddDays(-1)
    $mm = "{0:00}" -f $mesNum
    $periodoDesc = "MES de $mm/$ano"
    $cabecalho = "$mm/$ano"
    $sufixo = "$mm-$ano"
    $regime = "avaliacao MENSAL formal"
  } elseif ($rbPer.Checked) {
    $ini = $dtIni.Value.Date; $fim = $dtFim.Value.Date
    if ($fim -lt $ini) {
      [System.Windows.Forms.MessageBox]::Show("A data final não pode ser anterior à data inicial.", "Avaliação de Atendimentos", "OK", "Warning") | Out-Null
      return
    }
    $periodoDesc = "PERIODO de " + $ini.ToString("dd/MM/yyyy") + " a " + $fim.ToString("dd/MM/yyyy")
    $cabecalho = $ini.ToString("dd/MM/yyyy") + " a " + $fim.ToString("dd/MM/yyyy")
    $sufixo = $ini.ToString("dd-MM-yyyy") + "_a_" + $fim.ToString("dd-MM-yyyy")
    $regime = "ACOMPANHAMENTO (amostra reduzida, nao e avaliacao formal)"
  } else {
    $ini = $dtDia.Value.Date; $fim = $ini
    $periodoDesc = "DIA " + $ini.ToString("dd/MM/yyyy")
    $cabecalho = $ini.ToString("dd/MM/yyyy")
    $sufixo = $ini.ToString("dd-MM-yyyy")
    $regime = "ACOMPANHAMENTO (amostra reduzida, nao e avaliacao formal)"
  }
  $iniS = $ini.ToString("dd/MM/yyyy"); $fimS = $fim.ToString("dd/MM/yyyy")

  $prompt = "Rode a skill avaliacao-atendimentos-completa. Unidade: $unidade. Colaboradores selecionados: $colabs. Periodo: $periodoDesc — intervalo de $iniS ate $fimS (inclusive). Regime: $regime. Faca a avaliacao completa (leitura + analise) APENAS dos colaboradores selecionados, de ponta a ponta: 1) rode o agente de leitura de conversas UMA vez para todos os selecionados nesse intervalo, gerando UM UNICO arquivo de transcricao chamado transcricao_equipe_<unidade>_$sufixo.txt (uma secao por colaborador) - nao gere um txt por colaborador; no bloco de CONFERENCIA DE INTEGRIDADE a linha do periodo deve ser exatamente 'Período: $cabecalho'. 2) ao terminar, rode o agente de analise de atendimentos sobre esse arquivo unico e entregue os .zip com os PDFs no Downloads, usando $sufixo no nome dos arquivos e seguindo a divisao por coordenador definida na skill (Monte Alto sai em varios zips - um por coordenador mais o da diretoria; Taquaritinga sai em um zip so). Antes de iniciar a leitura, me mostre em uma linha o resumo da selecao (unidade, colaboradores, periodo e regime) para eu confirmar."

  # roteiro temporario com o comando (evita problemas de aspas ao passar o prompt)
  $runner = Join-Path $env:TEMP 'avaliacao_atendimentos_run.cmd'
  $body = "@echo off`r`nchcp 65001>nul`r`ntitle Avaliacao de Atendimentos - Altocon`r`ncd /d `"%USERPROFILE%`"`r`nclaude `"$prompt`"`r`n"
  [System.IO.File]::WriteAllText($runner, $body, (New-Object System.Text.UTF8Encoding($false)))

  # abre no Windows Terminal (mais bonito); se nao houver, cai no cmd
  $wt = Get-Command wt.exe -ErrorAction SilentlyContinue
  if ($wt) {
    # o titulo da aba vem do comando "title" dentro do runner (evita quebrar em espacos)
    Start-Process -FilePath 'wt.exe' -ArgumentList @('cmd', '/k', $runner)
  } else {
    Start-Process -FilePath 'cmd.exe' -ArgumentList ('/k "' + $runner + '"') -WorkingDirectory $env:USERPROFILE
  }
  $form.Close()
})

[void]$form.ShowDialog()



