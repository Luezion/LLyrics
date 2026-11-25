@echo off
chcp 65001 >nul
cd /d "%~dp0"
title LLyrics

set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (
  echo Python nao encontrado.
  echo Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/
  echo IMPORTANTE: marque "Add python.exe to PATH" na instalacao.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\pythonw.exe" (
  echo Primeira vez: preparando o app, isso leva 1-2 minutos...
  %PY% -m venv .venv || (echo Falha ao criar o ambiente. & pause & exit /b 1)
  ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Falha ao instalar as dependencias. & pause & exit /b 1)
)

start "" ".venv\Scripts\pythonw.exe" main.py
