@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Rode o Iniciar.bat uma vez antes.
  pause
  exit /b 1
)
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup') + '\LLyrics.lnk'); $s.TargetPath='%~dp0.venv\Scripts\pythonw.exe'; $s.Arguments='main.py'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%~dp0icon.ico'; $s.Save()"
echo O app vai abrir junto com o Windows.
echo Para desfazer, apague o atalho "LLyrics" na pasta que vai abrir agora.
explorer shell:startup
pause
