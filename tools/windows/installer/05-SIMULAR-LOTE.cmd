@echo off
setlocal
if not exist "%~dp0scripts\Trabalhar-Local.ps1" goto incompleto
if not exist "%~dp0scripts\Comum.ps1" goto incompleto
if not exist "%~dp0projetos.json" goto incompleto
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Trabalhar-Local.ps1" -Simular %*
set "rc=%errorlevel%"
if "%rc%"=="0" (echo Etapa concluida. Consulte README e relatorio.) else (echo Etapa falhou ou possui pendencias. Codigo: %rc%)
if not defined AI_HOLDING_NO_PAUSE pause
exit /b %rc%
:incompleto
echo PACOTE INCOMPLETO OU ABERTO DENTRO DO ZIP.
echo Feche esta janela. No ZIP, clique com o botao direito e escolha Extrair Tudo.
echo Abra a pasta extraida AI-HOLDING-INSTALADOR e execute o CMD novamente.
echo Mantenha scripts e projetos.json junto dos arquivos CMD.
if not defined AI_HOLDING_NO_PAUSE pause
exit /b 2
