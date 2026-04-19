@echo off
setlocal

set "ROOT=%~dp0"
set "ACTIVATE=%ROOT%.venv\Scripts\activate.bat"

if not exist "%ACTIVATE%" (
    echo ERRO: Virtualenv nao encontrado em .venv\
    echo Execute install.bat primeiro.
    pause
    exit /b 1
)

call "%ACTIVATE%"
python "%ROOT%run.py"
