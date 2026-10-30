"""Servicio de pronunciación de oraciones de Saylo.

Guardar como: src/services/ejercicios/pronunciacion_oraciones_service.py
Instalar (si hace falta): pip install faster-whisper sounddevice numpy

Esta función verifica la *transcripción* de una oración completa, no evalúa
fonemas ni acento nativo. El reconocimiento local depende del micrófono/modelo.
"""
import re
import threading
import warnings

import numpy as np
import sounddevice as sd

warnings.filterwarnings("ignore", category=DeprecationWarning, module="sounddevice")

SAMPLE_RATE = 16000
RECORD_SECONDS = 8                 # Más tiempo que una palabra suelta
MIN_VOLUME = 300
MODEL_SIZE = "base.en"             # CPU; usar 'small.en' para más precisión

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def preload():
    """Inicia carga en segundo plano; la primera vez puede descargar el modelo."""
    threading.Thread(target=_get_model, daemon=True).start()


def normalize_sentence(text):
    """Ignora puntuación/capitalización y expande contracciones comunes."""
    text = str(text or "").lower().replace("’", "'")
    contractions = {
        "i'm": "i am", "you're": "you are", "we're": "we are",
        "they're": "they are", "it's": "it is", "he's": "he is",
        "she's": "she is", "don't": "do not", "doesn't": "does not",
        "didn't": "did not", "can't": "cannot", "won't": "will not",
        "isn't": "is not", "aren't": "are not", "i've": "i have",
        "we've": "we have", "i'll": "i will", "we'll": "we will",
        "let's": "let us", "there's": "there is",
    }
    for short, long in contractions.items():
        text = re.sub(r"\b" + re.escape(short) + r"\b", long, text)
    text = re.sub(r"\beveryday\b", "every day", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _equivalent_word(heard, expected):
    # Transcripciones ambiguas de homófonos. NO aceptamos otras conjugaciones.
    homophones = {
        "read": {"red", "reed"},
        "write": {"right", "rite"},
    }
    return heard == expected or heard in homophones.get(expected, set())


def matches_sentence(heard, expected):
    """Comprueba que se hayan reconocido TODAS las palabras de la oración.

    No basta con reconocer una sola palabra ni con un porcentaje global alto,
    porque una palabra equivocada podría cambiar el sentido de la oración.
    """
    a = normalize_sentence(heard).split()
    b = normalize_sentence(expected).split()
    return bool(a and b) and len(a) == len(b) and all(
        _equivalent_word(h, t) for h, t in zip(a, b)
    )


def _record():
    audio = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    return audio


def listen_and_check_sentence(expected):
    """Graba una oración, transcribe con Whisper y devuelve (ok, heard)."""
    audio = _record()
    # Convertimos antes de abs para evitar overflow de int16 (-32768).
    if not audio.size or np.abs(audio.astype(np.int32)).max() < MIN_VOLUME:
        return False, ""

    audio_float = audio.flatten().astype(np.float32) / 32768.0
    segments, _ = _get_model().transcribe(
        audio_float,
        language="en",
        beam_size=3,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    heard = " ".join(segment.text.strip() for segment in segments).strip()
    if not heard:
        return False, ""
    return matches_sentence(heard, expected), heard
