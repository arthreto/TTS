#!/usr/bin/env bash
# Prépare l'environnement de l'appli dans son propre dossier :
#  - télécharge "uv" (outils/uv), un petit installeur Python ;
#  - uv télécharge un Python 3.12 privé (outils/python), sans toucher aux Pythons du système ;
#  - installe Piper et Flask dans .venv.
set -e
cd "$(dirname "$0")"
export UV_PYTHON_INSTALL_DIR="$PWD/outils/python"
UV="$PWD/outils/uv"
[ -f .venv/installe.ok ] && exit 0
rm -rf .venv
if [ ! -x "$UV" ]; then
    echo "Téléchargement de l'installeur uv..."
    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) target=aarch64-apple-darwin ;;
        Darwin-*) target=x86_64-apple-darwin ;;
        Linux-aarch64) target=aarch64-unknown-linux-gnu ;;
        *) target=x86_64-unknown-linux-gnu ;;
    esac
    mkdir -p outils
    curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-$target.tar.gz" | tar xz -C outils --strip-components=1
fi
echo "Première installation : téléchargement de Python 3.12 et de Piper, patientez une minute..."
"$UV" venv --python 3.12 --python-preference only-managed --seed .venv
"$UV" pip install --python .venv/bin/python -r requirements.txt
touch .venv/installe.ok
