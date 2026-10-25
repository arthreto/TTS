"""Voix IA — synthèse vocale 100 % locale et gratuite (français / anglais).

Deux moteurs :
- « Rapide »   : Piper (https://github.com/rhasspy/piper), léger, tourne partout.
- « Réaliste » : Chatterbox Multilingual (voir realiste.py), très naturel,
                 nécessite une carte graphique NVIDIA pour être rapide.

Les voix Piper sont téléchargées une seule fois depuis Hugging Face puis
stockées dans le dossier ./voices.

Lancement :  python app.py   puis ouvrir http://127.0.0.1:5050
"""

import io
import json
import os
import re
import threading
import time
import urllib.request
import wave
import webbrowser
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_file, send_from_directory
from piper import PiperVoice, SynthesisConfig

from realiste import RealisticEngine

BASE_DIR = Path(__file__).resolve().parent
VOICES_DIR = Path(os.environ.get("VOIX_IA_VOICES_DIR", BASE_DIR / "voices"))
REFS_DIR = VOICES_DIR / "references"
CUSTOM_DIR = VOICES_DIR / "mes-voix"
HF_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{family}/{lang}/{name}/{quality}/{model}{ext}?download=true"
PORT = int(os.environ.get("VOIX_IA_PORT", "5050"))
MAX_CHARS = 20_000
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Catalogue des voix proposées. "model" = nom du modèle Piper,
# "speaker" = nom du locuteur pour les modèles à plusieurs voix.
CATALOG = [
    # --- Français ---
    {"id": "fr-siwis", "lang": "fr", "label": "Siwis", "gender": "Femme", "accent": "France", "model": "fr_FR-siwis-medium"},
    {"id": "fr-tom", "lang": "fr", "label": "Tom", "gender": "Homme", "accent": "France", "model": "fr_FR-tom-medium"},
    {"id": "fr-jessica", "lang": "fr", "label": "Jessica", "gender": "Femme", "accent": "France", "model": "fr_FR-upmc-medium", "speaker": "jessica"},
    {"id": "fr-pierre", "lang": "fr", "label": "Pierre", "gender": "Homme", "accent": "France", "model": "fr_FR-upmc-medium", "speaker": "pierre"},
    {"id": "fr-gilles", "lang": "fr", "label": "Gilles", "gender": "Homme", "accent": "France", "model": "fr_FR-gilles-low"},
    # --- Anglais ---
    {"id": "en-lessac", "lang": "en", "label": "Lessac", "gender": "Femme", "accent": "US", "model": "en_US-lessac-high"},
    {"id": "en-amy", "lang": "en", "label": "Amy", "gender": "Femme", "accent": "US", "model": "en_US-amy-medium"},
    {"id": "en-kristin", "lang": "en", "label": "Kristin", "gender": "Femme", "accent": "US", "model": "en_US-kristin-medium"},
    {"id": "en-ryan", "lang": "en", "label": "Ryan", "gender": "Homme", "accent": "US", "model": "en_US-ryan-high"},
    {"id": "en-joe", "lang": "en", "label": "Joe", "gender": "Homme", "accent": "US", "model": "en_US-joe-medium"},
    {"id": "en-norman", "lang": "en", "label": "Norman", "gender": "Homme", "accent": "US", "model": "en_US-norman-medium"},
    {"id": "en-cori", "lang": "en", "label": "Cori", "gender": "Femme", "accent": "UK", "model": "en_GB-cori-high"},
    {"id": "en-jenny", "lang": "en", "label": "Jenny", "gender": "Femme", "accent": "UK", "model": "en_GB-jenny_dioco-medium"},
    {"id": "en-alba", "lang": "en", "label": "Alba", "gender": "Femme", "accent": "Écosse", "model": "en_GB-alba-medium"},
    {"id": "en-alan", "lang": "en", "label": "Alan", "gender": "Homme", "accent": "UK", "model": "en_GB-alan-medium"},
    {"id": "en-northern", "lang": "en", "label": "Oliver", "gender": "Homme", "accent": "Nord de l'Angleterre", "model": "en_GB-northern_english_male-medium"},
]
CATALOG_BY_ID = {v["id"]: v for v in CATALOG}
BUILTIN_ID = "builtin"  # voix intégrée à Chatterbox (anglais, mode réaliste uniquement)

# Texte lu par Piper pour fabriquer la voix de référence du mode réaliste.
# Il doit être dans la bonne langue, sinon Chatterbox reprend l'accent de la référence.
REFERENCE_TEXT = {
    "fr": "Bonjour à tous. Aujourd'hui, je vais vous raconter une petite histoire. "
          "Il était une fois, dans un village au bord de la mer, une famille qui tenait une boulangerie.",
    "en": "Hello everyone. Today, I'm going to tell you a short story. "
          "Once upon a time, in a small village by the sea, there was a family who ran a bakery.",
}

app = Flask(__name__, static_folder=str(BASE_DIR / "static"))
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
realistic = RealisticEngine()

_loaded: dict[str, PiperVoice] = {}
_load_lock = threading.Lock()
_downloads: dict[str, dict] = {}  # model -> {"done": int, "total": int, "error": str | None}
_downloads_lock = threading.Lock()
_custom_lock = threading.Lock()


# --------------------------------------------------------------------------- Piper


def model_paths(model: str) -> tuple[Path, Path]:
    onnx = VOICES_DIR / f"{model}.onnx"
    return onnx, VOICES_DIR / f"{model}.onnx.json"


def is_installed(model: str) -> bool:
    onnx, cfg = model_paths(model)
    return onnx.exists() and cfg.exists() and onnx.stat().st_size > 0


def model_url(model: str, ext: str) -> str:
    lang, name, quality = model.split("-", 2)
    return HF_URL.format(family=lang.split("_")[0], lang=lang, name=name, quality=quality, model=model, ext=ext)


def _fetch(url: str, dest: Path, state: dict | None = None) -> None:
    """Télécharge dans un fichier temporaire puis renomme (pas de fichier corrompu si coupure)."""
    tmp = dest.with_name(dest.name + ".part")
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
        if state is not None:
            state["total"] = int(resp.headers.get("Content-Length") or 0)
        while chunk := resp.read(256 * 1024):
            out.write(chunk)
            if state is not None:
                state["done"] += len(chunk)
    tmp.replace(dest)


def _download_worker(model: str) -> None:
    state = _downloads[model]
    onnx, cfg = model_paths(model)
    try:
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        _fetch(model_url(model, ".onnx.json"), cfg)
        _fetch(model_url(model, ".onnx"), onnx, state)
        with _downloads_lock:
            del _downloads[model]
    except Exception as exc:  # noqa: BLE001 - l'erreur est renvoyée à l'interface
        state["error"] = f"Échec du téléchargement : {exc}"


def start_download(model: str) -> None:
    with _downloads_lock:
        if is_installed(model):
            return
        current = _downloads.get(model)
        if current and not current["error"]:
            return  # déjà en cours
        _downloads[model] = {"done": 0, "total": 0, "error": None}
    threading.Thread(target=_download_worker, args=(model,), daemon=True).start()


def get_voice(model: str) -> PiperVoice:
    with _load_lock:
        if model not in _loaded:
            onnx, cfg = model_paths(model)
            _loaded[model] = PiperVoice.load(onnx, config_path=cfg)
        return _loaded[model]


def piper_wav(voice: dict, text: str, speed: float = 1.0) -> bytes:
    piper_voice = get_voice(voice["model"])
    speaker_id = None
    if voice.get("speaker"):
        speaker_id = piper_voice.config.speaker_id_map.get(voice["speaker"])
    cfg = SynthesisConfig(speaker_id=speaker_id, length_scale=1.0 / speed)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        piper_voice.synthesize_wav(text, wav, syn_config=cfg)
    return buf.getvalue()


def float_to_wav(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


# --------------------------------------------------------------------------- Mes voix


def custom_index_path() -> Path:
    return CUSTOM_DIR / "index.json"


def load_custom() -> list[dict]:
    try:
        return json.loads(custom_index_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_custom(voices: list[dict]) -> None:
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    custom_index_path().write_text(json.dumps(voices, ensure_ascii=False, indent=2), encoding="utf-8")


def reference_for(voice_id: str) -> tuple[str | None, str | None]:
    """Renvoie (chemin du WAV de référence, message d'erreur) pour le mode réaliste."""
    if voice_id == BUILTIN_ID:
        return None, None
    for v in load_custom():
        if v["id"] == voice_id:
            return str(CUSTOM_DIR / v["file"]), None
    voice = CATALOG_BY_ID.get(voice_id)
    if not voice:
        return None, "Voix inconnue."
    ref = REFS_DIR / f"{voice_id}.wav"
    if not ref.exists():
        if not is_installed(voice["model"]):
            return None, "Cette voix n'est pas encore téléchargée."
        REFS_DIR.mkdir(parents=True, exist_ok=True)
        ref.write_bytes(piper_wav(voice, REFERENCE_TEXT[voice["lang"]], speed=0.95))
    return str(ref), None


# --------------------------------------------------------------------------- API


def voice_status(v: dict) -> dict:
    model = v["model"]
    info = {k: v[k] for k in ("id", "lang", "label", "gender", "accent")}
    info["quality"] = model.rsplit("-", 1)[1]
    info["installed"] = is_installed(model)
    dl = _downloads.get(model)
    if dl and not info["installed"]:
        info["download"] = dict(dl)
    return info


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/voices")
def api_voices():
    return jsonify(catalog=[voice_status(v) for v in CATALOG], custom=load_custom())


@app.post("/api/download")
def api_download():
    voice = CATALOG_BY_ID.get((request.get_json(silent=True) or {}).get("voice", ""))
    if not voice:
        return jsonify(error="Voix inconnue."), 404
    start_download(voice["model"])
    return jsonify(voice_status(voice))


@app.get("/api/realistic")
def api_realistic_status():
    return jsonify(realistic.status())


@app.post("/api/realistic/load")
def api_realistic_load():
    realistic.start_loading()
    return jsonify(realistic.status())


@app.post("/api/custom")
def api_custom_add():
    file = request.files.get("file")
    name = (request.form.get("name") or "").strip()[:40]
    lang = request.form.get("lang")
    if not file or not name or lang not in ("fr", "en"):
        return jsonify(error="Il faut un nom, une langue et un fichier audio."), 400
    data = file.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return jsonify(error="Le fichier doit être converti en WAV par la page avant l'envoi."), 400
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "voix"
    voice_id = f"custom-{slug}-{int(time.time())}"
    with _custom_lock:
        CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
        (CUSTOM_DIR / f"{voice_id}.wav").write_bytes(data)
        voices = load_custom()
        entry = {"id": voice_id, "label": name, "lang": lang, "file": f"{voice_id}.wav"}
        voices.append(entry)
        save_custom(voices)
    return jsonify(entry)


@app.delete("/api/custom/<voice_id>")
def api_custom_delete(voice_id: str):
    with _custom_lock:
        voices = load_custom()
        keep = [v for v in voices if v["id"] != voice_id]
        if len(keep) == len(voices):
            return jsonify(error="Voix inconnue."), 404
        (CUSTOM_DIR / f"{voice_id}.wav").unlink(missing_ok=True)
        save_custom(keep)
    return jsonify(ok=True)


@app.post("/api/tts")
def api_tts():
    data = request.get_json(silent=True) or {}
    voice_id = data.get("voice", "")
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="Le texte est vide."), 400
    if len(text) > MAX_CHARS:
        return jsonify(error=f"Texte trop long (maximum {MAX_CHARS} caractères)."), 400

    if data.get("engine") == "realiste":
        lang = data.get("lang")
        if lang not in ("fr", "en"):
            return jsonify(error="Langue inconnue."), 400
        if realistic.state != "ready":
            return jsonify(error="Le modèle réaliste n'est pas encore chargé."), 409
        try:
            exaggeration = min(max(float(data.get("exaggeration", 0.5)), 0.25), 1.5)
        except (TypeError, ValueError):
            exaggeration = 0.5
        ref, err = reference_for(voice_id)
        if err:
            return jsonify(error=err), 409
        try:
            samples = realistic.synthesize(text, lang, ref, exaggeration)
        except Exception as exc:  # noqa: BLE001 - ex. mémoire GPU insuffisante
            return jsonify(error=f"Échec de la génération réaliste : {exc}"), 500
        wav_bytes = float_to_wav(samples, realistic.sample_rate)
    else:
        voice = CATALOG_BY_ID.get(voice_id)
        if not voice:
            return jsonify(error="Voix inconnue."), 404
        if not is_installed(voice["model"]):
            return jsonify(error="Cette voix n'est pas encore téléchargée."), 409
        try:
            speed = min(max(float(data.get("speed", 1.0)), 0.5), 2.0)
        except (TypeError, ValueError):
            speed = 1.0
        wav_bytes = piper_wav(voice, text, speed)

    return send_file(io.BytesIO(wav_bytes), mimetype="audio/wav", download_name="voix.wav")


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    print(f"\n  Voix IA est prête  →  {url}\n  (Ctrl+C pour arrêter)\n")
    if RealisticEngine.installed():
        print("  Mode réaliste installé : chargement du modèle en arrière-plan…\n")
        realistic.start_loading()
    if not os.environ.get("VOIX_IA_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PORT, threaded=True)
