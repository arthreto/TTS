#!/usr/bin/env bash
# Installation du mode Réaliste (Chatterbox) - environ 3 Go à télécharger.
set -e
cd "$(dirname "$0")"
./installer-base.sh
UV="$PWD/outils/uv"
if [ "$(uname)" = "Darwin" ]; then
    "$UV" pip install --python .venv/bin/python torch==2.7.1 torchaudio==2.7.1
else
    "$UV" pip install --python .venv/bin/python torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128
fi
"$UV" pip install --python .venv/bin/python -r requirements-realiste.txt
"$UV" pip install --python .venv/bin/python chatterbox-tts==0.1.7 --no-deps
.venv/bin/python -c "import torch; print('Carte graphique :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'aucune (le mode Réaliste sera lent)')"
echo "Terminé ! Relancez ./lancer-mac-linux.sh et choisissez le mode Réaliste."
