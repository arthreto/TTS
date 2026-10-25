"""Mode « Réaliste » : moteur Chatterbox Multilingual (Resemble AI, licence MIT).

Beaucoup plus naturel que Piper, mais plus lourd : il faut une carte graphique
NVIDIA pour une génération rapide. Le modèle (~3 Go) est téléchargé depuis
Hugging Face au premier chargement.

Installation : lancer installer-mode-realiste.bat (Windows) ou .sh (Mac/Linux).
"""

import importlib.util
import os
import re
import threading

import numpy as np

# Chatterbox s'arrête à ~40 s d'audio par appel : on découpe le texte en morceaux.
MAX_CHUNK_CHARS = 250
PAUSE_SECONDS = 0.12


def split_text(text: str) -> list[str]:
    """Découpe en phrases, regroupées en morceaux d'au plus MAX_CHUNK_CHARS caractères."""
    sentences = re.split(r"(?<=[.!?…;:])\s+|\n+", text.strip())
    chunks: list[str] = []
    current = ""
    for sentence in filter(None, (s.strip() for s in sentences)):
        # Une phrase trop longue est coupée aux virgules, puis aux espaces.
        while len(sentence) > MAX_CHUNK_CHARS:
            cut = sentence.rfind(",", 0, MAX_CHUNK_CHARS)
            if cut < MAX_CHUNK_CHARS // 3:
                cut = sentence.rfind(" ", 0, MAX_CHUNK_CHARS)
            if cut <= 0:
                cut = MAX_CHUNK_CHARS
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[: cut + 1].strip())
            sentence = sentence[cut + 1 :].strip()
        if current and len(current) + 1 + len(sentence) > MAX_CHUNK_CHARS:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


class RealisticEngine:
    def __init__(self) -> None:
        self.state = "idle"  # idle | loading | ready | error
        self.error: str | None = None
        self.device: str | None = None
        self.gpu_name: str | None = None
        self._model = None
        self._default_conds = None
        self._conds_cache: dict[tuple[str, float], object] = {}
        self._state_lock = threading.Lock()
        self._gen_lock = threading.Lock()

    @staticmethod
    def installed() -> bool:
        return importlib.util.find_spec("chatterbox") is not None

    def status(self) -> dict:
        return {
            "installed": self.installed(),
            "state": self.state,
            "error": self.error,
            "device": self.device,
            "gpu": self.gpu_name,
        }

    def start_loading(self) -> None:
        with self._state_lock:
            if self.state in ("loading", "ready") or not self.installed():
                return
            self.state, self.error = "loading", None
        threading.Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS

            if torch.cuda.is_available():
                self.device = "cuda"
                self.gpu_name = torch.cuda.get_device_name(0)
            else:
                self.device = "cpu"
            self._model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            self._default_conds = self._model.conds
            self.state = "ready"
        except Exception as exc:  # noqa: BLE001 - affiché tel quel dans l'interface
            self.error = f"Impossible de charger le modèle réaliste : {exc}"
            self.state = "error"

    @property
    def sample_rate(self) -> int:
        return self._model.sr

    def synthesize(self, text: str, lang: str, ref_wav: str | None, exaggeration: float) -> np.ndarray:
        """Renvoie l'audio en float32 mono. ref_wav = None pour la voix intégrée."""
        if self.state != "ready":
            raise RuntimeError("Le modèle réaliste n'est pas encore chargé.")
        model = self._model
        with self._gen_lock:
            if ref_wav:
                key = (ref_wav, os.path.getmtime(ref_wav))
                if key not in self._conds_cache:
                    model.prepare_conditionals(ref_wav, exaggeration=exaggeration)
                    self._conds_cache[key] = model.conds
                model.conds = self._conds_cache[key]
            else:
                model.conds = self._default_conds

            pause = np.zeros(int(model.sr * PAUSE_SECONDS), dtype=np.float32)
            parts: list[np.ndarray] = []
            for chunk in split_text(text):
                wav = model.generate(chunk, language_id=lang, exaggeration=exaggeration)
                parts.append(wav.squeeze(0).numpy().astype(np.float32))
                parts.append(pause)
        return np.concatenate(parts[:-1]) if parts else np.zeros(0, dtype=np.float32)
