@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Avaliacao de Atendimentos - Altocon
cd /d "%USERPROFILE%"

:MENU_UNIDADE
cls
echo ============================================================
echo   AVALIACAO DE ATENDIMENTOS - ALTOCON
echo   Leitura + Analise (ponta a ponta)
echo ============================================================
echo.
echo   PASSO 1 de 3 - UNIDADE
echo.
echo     [1] Taquaritinga
echo     [2] Monte Alto
echo.
echo     [X] Sair (nao faz nada)
echo.
set "UNIDADE="
set /p "OPU=  Escolha: "
if /i "%OPU%"=="X" goto SAIR
if "%OPU%"=="1" set "UNIDADE=Taquaritinga"
if "%OPU%"=="2" set "UNIDADE=Monte Alto"
if not defined UNIDADE goto MENU_UNIDADE
if "%OPU%"=="1" goto MENU_TAQUA
goto MENU_MONTE

:MENU_TAQUA
cls
echo ============================================================
echo   PASSO 2 de 3 - COLABORADORES (Taquaritinga)
echo ============================================================
echo.
echo     [1] Ana Chueco
echo     [2] Julia Ribeiro
echo     [3] Leonardo Chueco
echo     [4] Natalia Tiesi
echo     [5] Priscila de Pietro
echo     [6] Tiago Chueco
echo.
echo   Digite os numeros separados por virgula (ex: 1,3,4)
echo   ou digite  T  para TODOS.
echo.
echo     [V] Voltar     [X] Sair
echo.
set "COLABS="
set /p "SEL=  Selecao: "
if /i "%SEL%"=="X" goto SAIR
if /i "%SEL%"=="V" goto MENU_UNIDADE
if /i "%SEL%"=="T" (
  set "COLABS=Ana Chueco, Julia Ribeiro, Leonardo Chueco, Natalia Tiesi, Priscila de Pietro, Tiago Chueco"
  goto MENU_PERIODO
)
for %%N in (%SEL%) do (
  if "%%N"=="1" set "COLABS=!COLABS!, Ana Chueco"
  if "%%N"=="2" set "COLABS=!COLABS!, Julia Ribeiro"
  if "%%N"=="3" set "COLABS=!COLABS!, Leonardo Chueco"
  if "%%N"=="4" set "COLABS=!COLABS!, Natalia Tiesi"
  if "%%N"=="5" set "COLABS=!COLABS!, Priscila de Pietro"
  if "%%N"=="6" set "COLABS=!COLABS!, Tiago Chueco"
)
if defined COLABS set "COLABS=!COLABS:~2!"
if not defined COLABS goto MENU_TAQUA
goto MENU_PERIODO

:MENU_MONTE
cls
echo ============================================================
echo   PASSO 2 de 3 - COLABORADORES (Monte Alto)
echo ============================================================
echo.
echo   Monte Alto = todos os operadores que NAO sao de Taquaritinga.
echo.
echo     [1] Avaliar a EQUIPE INTEIRA de Monte Alto
echo     [2] Digitar nomes especificos
echo.
echo     [V] Voltar     [X] Sair
echo.
set "COLABS="
set /p "OPM=  Escolha: "
if /i "%OPM%"=="X" goto SAIR
if /i "%OPM%"=="V" goto MENU_UNIDADE
if "%OPM%"=="1" (
  set "COLABS=EQUIPE INTEIRA de Monte Alto (todos os operadores que nao sao de Taquaritinga)"
  goto MENU_PERIODO
)
if "%OPM%"=="2" (
  echo.
  set /p "COLABS=  Nomes separados por virgula: "
  if defined COLABS goto MENU_PERIODO
)
goto MENU_MONTE

:MENU_PERIODO
cls
echo ============================================================
echo   PASSO 3 de 3 - PERIODO
echo ============================================================
echo.
echo   Digite  V  para voltar  ou  X  para sair.
echo.
set "MES="
set "ANO="
set /p "MES=  Mes (1-12): "
if /i "%MES%"=="X" goto SAIR
if /i "%MES%"=="V" goto MENU_UNIDADE
if not defined MES goto MENU_PERIODO
set /p "ANO=  Ano (ex: 2026): "
if /i "%ANO%"=="X" goto SAIR
if /i "%ANO%"=="V" goto MENU_PERIODO
if not defined ANO goto MENU_PERIODO

:CONFIRMA
cls
echo ============================================================
echo   CONFIRMACAO
echo ============================================================
echo.
echo     Unidade......: %UNIDADE%
echo     Colaboradores: %COLABS%
echo     Periodo......: %MES%/%ANO%
echo.
echo     [S] Iniciar    [V] Recomecar    [X] Sair
echo.
set /p "OK=  Escolha: "
if /i "%OK%"=="X" goto SAIR
if /i "%OK%"=="V" goto MENU_UNIDADE
if /i not "%OK%"=="S" goto CONFIRMA

cls
echo ============================================================
echo   Iniciando... o Claude assume a partir daqui.
echo   Deixe o Gestta acessivel para a etapa de leitura.
echo ============================================================
echo.
call claude "Rode a skill avaliacao-atendimentos-completa. Unidade: %UNIDADE%. Colaboradores selecionados: %COLABS%. Periodo: mes %MES% de %ANO%. Faca a avaliacao completa (leitura + analise) APENAS dos colaboradores selecionados acima, de ponta a ponta: rode o agente de leitura de conversas UMA vez para todos os selecionados, gerando UM UNICO arquivo de transcricao (transcricao_equipe_<unidade>_<MM-AAAA>.txt, com uma secao por colaborador) - nao gere um txt por colaborador; ao terminar, rode o agente de analise de atendimentos sobre esse arquivo unico e entregue o .zip com os PDFs no Downloads. Antes de iniciar a leitura, me mostre em uma linha o resumo da selecao (unidade, colaboradores e periodo) para eu confirmar."

echo.
echo ============================================================
echo   Sessao encerrada. Pressione qualquer tecla para fechar.
echo ============================================================
pause >nul
endlocal
exit /b 0

:SAIR
cls
echo.
echo   Saindo sem executar nada. Ate logo!
echo.
timeout /t 2 >nul
endlocal
exit /b 0
