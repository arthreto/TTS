@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  Installation du mode Realiste (Chatterbox) - environ 3 Go a telecharger.
echo.
call installer-base.bat
if errorlevel 1 goto :erreur
echo.
echo  [1/3] PyTorch avec prise en charge des cartes NVIDIA...
"%UV%" pip install --python ".venv\Scripts\python.exe" torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128 || goto :erreur
echo.
echo  [2/3] Dependances...
"%UV%" pip install --python ".venv\Scripts\python.exe" -r requirements-realiste.txt || goto :erreur
echo.
echo  [3/3] Chatterbox...
"%UV%" pip install --python ".venv\Scripts\python.exe" chatterbox-tts==0.1.7 --no-deps || goto :erreur
echo.
".venv\Scripts\python.exe" -c "import torch; print('  Carte graphique detectee :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'AUCUNE (mettez a jour le pilote NVIDIA)')"
echo.
echo  Termine ! Lancez maintenant lancer-windows.bat et choisissez le mode Realiste.
echo  Au premier lancement, le modele (environ 3 Go) se telecharge automatiquement.
pause
exit /b 0

:erreur
echo.
echo  L'installation a echoue. Copiez le message d'erreur ci-dessus pour obtenir de l'aide.
pause
exit /b 1
