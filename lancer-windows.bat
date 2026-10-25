@echo off
chcp 65001 >nul
cd /d "%~dp0"
call installer-base.bat
if errorlevel 1 goto :erreur
".venv\Scripts\python.exe" app.py
pause
exit /b 0

:erreur
echo.
echo  L'installation a echoue. Copiez le message d'erreur ci-dessus pour obtenir de l'aide.
pause
exit /b 1
