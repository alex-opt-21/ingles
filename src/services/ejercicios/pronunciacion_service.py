import difflib
import re
import threading
import time
import warnings

import numpy as np
import sounddevice as sd

# Oculta la advertencia de sounddevice con NumPy 2.5 (no afecta el funcionamiento)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sounddevice")

SAMPLE_RATE = 16000
MAX_RECORD_SECONDS = 10     # límite máximo de grabación
MIN_RECORD_SECONDS = 0.4    # evita toques accidentales dobles
MIN_VOLUME = 300
MODEL_SIZE = "base.en"      # "tiny.en" = más rápido, "small.en" = más preciso
FUZZY_THRESHOLD = 0.80

SOUND_ALIKES = {
    "read": {"red", "reed"},
    "write": {"right", "rite"},
    "eat": {"eats", "eating", "ate"},
    "teach": {"teaches", "teaching", "taught"},
    "listen": {"listens", "listening"},
    "speak": {"speaks", "speaking"},
    "learn": {"learns", "learning", "learned"},
    "practice": {"practise", "practices", "practicing"},
}

_model = None
_model_lock = threading.Lock()


def _get_model():
    """Carga el modelo local una sola vez (la primera vez lo descarga)."""
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def preload():
    """Llama esto al abrir la pantalla para que el modelo ya esté listo."""
    threading.Thread(target=_get_model, daemon=True).start()


def _normalize(text):
    return re.sub(r"[^a-z\s]", "", text.lower()).strip()


def _record(stop_event=None, max_seconds=MAX_RECORD_SECONDS):
    """Graba hasta que stop_event se active o pasen max_seconds."""
    chunks = []

    def callback(indata, frames, time_info, status):
        chunks.append(indata.copy())

    start = time.monotonic()
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=callback,
    ):
        while time.monotonic() - start < max_seconds:
            if stop_event is not None:
                if stop_event.wait(0.05):
                    break
            else:
                time.sleep(0.05)

    if not chunks:
        return np.zeros((0, 1), dtype="int16")
    return np.concatenate(chunks)


def _matches(heard, target):
    aliases = SOUND_ALIKES.get(target, set())
    for w in heard.split():
        if w == target or w in aliases:
            return True
        if difflib.SequenceMatcher(None, w, target).ratio() >= FUZZY_THRESHOLD:
            return True
    return False


def listen_and_check(expected, stop_event=None, max_seconds=MAX_RECORD_SECONDS):
    """Graba (hasta 2º toque o max_seconds), transcribe en local y compara.
    Devuelve (ok, heard)."""
    audio = _record(stop_event, max_seconds)

    # Muy corto o en silencio: no transcribir (Whisper inventaría texto
    # como "Thank you." a partir del silencio).
    if audio.size < MIN_RECORD_SECONDS * SAMPLE_RATE:
        return False, ""
    if np.abs(audio).max() < MIN_VOLUME:
        return False, ""

    audio_f32 = audio.flatten().astype(np.float32) / 32768.0
    segments, _ = _get_model().transcribe(
        audio_f32,
        language="en",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    heard = _normalize(" ".join(s.text for s in segments))
    if not heard:
        return False, ""

    return _matches(heard, _normalize(expected)), heard