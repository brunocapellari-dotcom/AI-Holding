@echo off
setlocal
if not exist "%~dp0MISSOES-PARA-NUVEM.md" (
 echo PACOTE INCOMPLETO OU ABERTO DENTRO DO ZIP. Use Extrair Tudo antes de executar.
 if not defined AI_HOLDING_NO_PAUSE pause
 exit /b 2
)
start "" "https://chatgpt.com/codex"
start "" "https://claude.ai/code"
start "" "%~dp0MISSOES-PARA-NUVEM.md"
exit /b 0
