' Lancador silencioso do app Avaliacao de Atendimentos (Altocon)
' Abre a janela WinForms sem mostrar o console do PowerShell.
Dim sh, home, ps
Set sh = CreateObject("WScript.Shell")
home = sh.ExpandEnvironmentStrings("%USERPROFILE%")
ps = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Sta -File """ & home & "\.claude\avaliacao-atendimentos-app.ps1"""
sh.Run ps, 0, False
