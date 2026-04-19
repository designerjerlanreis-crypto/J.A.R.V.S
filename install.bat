@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo  =============================================
echo   J.A.R.V.I.S. - Instalador Windows
echo  =============================================
echo.

:: ── Diretório raiz do projeto (onde este .bat está) ──────────────────────────
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "VENV=%ROOT%\.venv"
set "PYTHON_EXE=%VENV%\Scripts\python.exe"
set "PIP_EXE=%VENV%\Scripts\pip.exe"

:: ── Verificar Python 3.10+ ────────────────────────────────────────────────────
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado no PATH.
    echo Instale o Python 3.10+ em python.org e adicione ao PATH.
    goto :fail
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! LSS 3 (
    echo ERRO: Python !PY_VER! detectado. Requer Python 3.10+.
    goto :fail
)
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 10 (
    echo ERRO: Python !PY_VER! detectado. Requer Python 3.10+.
    goto :fail
)
echo    OK - Python !PY_VER!

:: ── Criar virtualenv ──────────────────────────────────────────────────────────
echo.
echo [2/5] Criando ambiente virtual em .venv...
if exist "%VENV%" (
    echo    Ambiente virtual ja existe — reutilizando.
) else (
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo ERRO: Falha ao criar o ambiente virtual.
        goto :fail
    )
    echo    OK
)

:: ── Atualizar pip ─────────────────────────────────────────────────────────────
echo.
echo [3/5] Atualizando pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo AVISO: Nao foi possivel atualizar o pip. Continuando...
)
echo    OK

:: ── Instalar dependências ─────────────────────────────────────────────────────
echo.
echo [4/5] Instalando dependencias (pode demorar alguns minutos)...
"%PIP_EXE%" install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias.
    echo Verifique sua conexao com a internet e tente novamente.
    goto :fail
)
echo    OK

:: ── Criar .env se não existir ─────────────────────────────────────────────────
if not exist "%ROOT%\.env" (
    copy "%ROOT%\.env.example" "%ROOT%\.env" >nul
    echo    .env criado a partir de .env.example — preencha suas chaves antes de rodar.
)

:: ── Criar atalho na Área de Trabalho ─────────────────────────────────────────
echo.
echo [5/5] Criando atalho na Area de Trabalho...

set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\JARVIS.lnk"

:: Gera um script PowerShell temporário para criar o atalho
set "PS_TMP=%TEMP%\jarvis_shortcut.ps1"
(
    echo $wsh = New-Object -ComObject WScript.Shell
    echo $lnk = $wsh.CreateShortcut('%SHORTCUT%'^)
    echo $lnk.TargetPath = '%PYTHON_EXE%'
    echo $lnk.Arguments = '-m jarvis.main'
    echo $lnk.WorkingDirectory = '%ROOT%'
    echo $lnk.Description = 'J.A.R.V.I.S. Voice Assistant'
    echo $lnk.IconLocation = '%SystemRoot%\System32\shell32.dll,13'
    echo $lnk.WindowStyle = 1
    echo $lnk.Save(^)
) > "%PS_TMP%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TMP%" >nul 2>&1
del "%PS_TMP%" >nul 2>&1

if exist "%SHORTCUT%" (
    echo    OK - Atalho criado em: %SHORTCUT%
) else (
    echo    AVISO: Nao foi possivel criar o atalho automaticamente.
    echo    Para rodar manualmente:
    echo      %PYTHON_EXE% -m jarvis.main
)

:: ── Concluído ─────────────────────────────────────────────────────────────────
echo.
echo  =============================================
echo   Instalacao concluida com sucesso!
echo  =============================================
echo.
echo  Proximos passos:
echo    1. Abra "%ROOT%\.env" e preencha:
echo         ANTHROPIC_API_KEY=sk-ant-...
echo         PICOVOICE_KEY=...  (opcional)
echo    2. Clique no atalho "JARVIS" na Area de Trabalho
echo       ou execute: %PYTHON_EXE% -m jarvis.main
echo.
pause
exit /b 0

:fail
echo.
echo  Instalacao falhou. Corrija os erros acima e tente novamente.
echo.
pause
exit /b 1
