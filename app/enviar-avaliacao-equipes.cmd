@echo off
chcp 65001>nul
title Enviar Avaliacao por Equipe - Altocon
rem %* repassa argumentos: permite -Simular / -Sufixo "03-08-2026_a_09-08-2026" sem editar o atalho
powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\.claude\enviar-avaliacao-equipes.ps1" %*
echo.
pause
