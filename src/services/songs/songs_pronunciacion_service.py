from __future__ import annotations

import difflib
import re
import threading

import numpy as np
import sounddevice as sd

from services.ejercicios import pronunciacion_service as base

SAMPLE_RATE = base.SAMPLE_RATE
MAX_RECORD_SECONDS = 15              # tope de seguridad si el usuario no vuelve a tocar
RECORD_SECONDS = MAX_RECORD_SECONDS  # alias por compatibilidad
HARD_MAX_SECONDS = 300               # tope absoluto (canción completa)
MIN_VOLUME = base.MIN_VOLUME

# Umbrales (similitud, cobertura) según el tipo de paso.
# Párrafos y canción completa son más permisivos: en textos largos
# el reconocimiento se equivoca más.
THRESHOLDS = {
    "line":  (0.80, 0.65),
    "group": (0.70, 0.55),
    "song":  (0.55, 0.45),
}
FUZZY_THRESHOLD = THRESHOLDS["line"][0]      # compatibilidad
MIN_WORD_COVERAGE = THRESHOLDS["line"][1]    # compatibilidad

_CONTRACTIONS = {
    "i'm": "i am",
    "you're": "you are", "we're": "we are", "they're": "they are",
    "it's": "it is", "that's": "that is", "there's": "there is",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "can't": "cannot", "cannot": "can not", "won't": "will not",
    "aren't": "are not", "isn't": "is not", "wasn't": "was not",
    "weren't": "were not", "couldn't": "could not", "wouldn't": "would not",
    "shouldn't": "should not", "haven't": "have not", "hasn't": "has not",
    "i've": "i have", "we've": "we have", "you've": "you have",
    "i'll": "i will", "we'll": "we will", "you'll": "you will",
    "i'd": "i would", "we'd": "we would", "you'd": "you would",
    "let's": "let us",
    "wanna": "want to", "gonna": "going to", "gotta": "got to",
    "'cause": "because", "'cos": "because", "cuz": "because",
}


def normalize_phrase(text: str) -> str:
    """Minúsculas y equivalencias; ignora coros entre paréntesis, p. ej. (oh)."""
    value = str(text or "").lower().replace("’", "'")
    value = re.sub(r"\([^)]*\)", " ", value)
    # Contracciones completas primero; evita remplazar pedazos de palabras.
    for before, after in sorted(_CONTRACTIONS.items(), key=lambda p: -len(p[0])):
        value = re.sub(r"(?<![a-z])" + re.escape(before) + r"(?![a-z])", after, value)
    value = re.sub(r"[^a-z\s]", " ", value)
    return " ".join(value.split())


def evaluate_phrase(heard: str, expected: str, kind: str = "line") -> tuple[bool, float]:
    """Compara TODA la frase, no una palabra aislada.

    `kind` ("line" | "group" | "song") elige los umbrales.
    Devuelve (aprobado, similitud_de_0_a_1). Es una medida aproximada basada
    en las palabras reconocidas por Whisper, no una nota fonética.
    """
    fuzzy, min_cov = THRESHOLDS.get(kind, THRESHOLDS["line"])
    target = normalize_phrase(expected)
    spoken = normalize_phrase(heard)
    if not target or not spoken:
        return False, 0.0

    target_words = target.split()
    spoken_words = spoken.split()
    matcher = difflib.SequenceMatcher(None, target_words, spoken_words, autojunk=False)
    # Cobertura ordenada: cuántas palabras esperadas aparecen en el orden correcto.
    matched_words = sum(block.size for block in matcher.get_matching_blocks())
    coverage = matched_words / max(1, len(target_words))
    word_similarity = matcher.ratio()
    char_similarity = difflib.SequenceMatcher(None, target, spoken, autojunk=False).ratio()
    similarity = 0.6 * word_similarity + 0.4 * char_similarity
    return similarity >= fuzzy and coverage >= min_cov, round(similarity, 3)


def listen_and_check(
    expected: str,
    stop_event: threading.Event | None = None,
    max_seconds: float = MAX_RECORD_SECONDS,
    kind: str = "line",
) -> tuple[bool, str]:
    """Graba hasta que stop_event se active (o se llegue a max_seconds)."""
    max_seconds = max(1.0, min(float(max_seconds), float(HARD_MAX_SECONDS)))
    stop_event = stop_event or threading.Event()

    total_frames = int(max_seconds * SAMPLE_RATE)
    chunks: list[np.ndarray] = []
    recorded = 0
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        while recorded < total_frames and not stop_event.is_set():
            frames = min(1024, total_frames - recorded)
            data, _overflow = stream.read(frames)
            chunks.append(data.copy())
            recorded += len(data)

    if not chunks:
        return False, ""
    audio = np.concatenate(chunks)
    if audio.size == 0 or np.max(np.abs(audio.astype(np.float32))) < MIN_VOLUME:
        return False, ""

    audio_f32 = audio.flatten().astype(np.float32) / 32768.0
    # Reutiliza el MISMO modelo en memoria, sin descargarlo dos veces.
    # _get_model es una función interna del servicio existente: si se renombra,
    # actualizar esta importación.
    segments, _ = base._get_model().transcribe(
        audio_f32,
        language="en",
        beam_size=2,
        vad_filter=True,
        condition_on_previous_text=False,
    )
    heard = " ".join(segment.text for segment in segments).strip()
    ok, _score = evaluate_phrase(heard, expected, kind)
    return ok, heard


def preload() -> None:
    """Precarga el modelo compartido si se llama al iniciar Songs."""
    base.preload()