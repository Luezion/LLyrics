@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Gerar LLyrics.exe
if not exist ".venv\Scripts\python.exe" (
  echo Rode o Iniciar.bat uma vez antes, para instalar tudo.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name LLyrics --icon icon.ico --add-data "fonts;fonts" --add-data "icon.png;." --collect-submodules winrt main.py
if errorlevel 1 (echo Falhou ao gerar o exe. & pause & exit /b 1)
echo.
echo Pronto! O app esta em: dist\LLyrics\LLyrics.exe
echo Voce pode copiar a pasta dist\LLyrics para onde quiser.
explorer dist\LLyrics
pause
