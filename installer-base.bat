@echo off
rem Prepare l'environnement de l'appli dans son propre dossier :
rem  - telecharge "uv" (outils\uv.exe), un petit installeur Python ;
rem  - uv telecharge un Python 3.12 prive (outils\python), sans toucher aux Pythons du PC ;
rem  - installe Piper et Flask dans .venv.
rem Le fichier .venv\installe.ok n'est cree qu'apres une installation reussie :
rem une installation ratee est effacee et refaite au lancement suivant.
set "UV=%~dp0outils\uv.exe"
set "UV_PYTHON_INSTALL_DIR=%~dp0outils\python"
if exist ".venv\installe.ok" exit /b 0
if exist ".venv" (
    echo  Suppression de l'ancienne installation incomplete...
    rmdir /s /q ".venv"
)
if not exist "%UV%" (
    echo  Telechargement de l'installeur uv...
    if not exist "%~dp0outils" mkdir "%~dp0outils"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile '%~dp0outils\uv.zip'; Expand-Archive -Force '%~dp0outils\uv.zip' '%~dp0outils'; Remove-Item '%~dp0outils\uv.zip'"
)
if not exist "%UV%" (
    echo  Impossible de telecharger uv. Verifiez votre connexion Internet.
    exit /b 1
)
echo  Premiere installation : telechargement de Python 3.12 et de Piper, patientez une minute...
"%UV%" venv --python 3.12 --python-preference only-managed --seed ".venv"
if not exist ".venv\Scripts\python.exe" exit /b 1
"%UV%" pip install --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 exit /b 1
echo ok> ".venv\installe.ok"
exit /b 0
