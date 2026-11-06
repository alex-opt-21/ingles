from __future__ import annotations

import difflib
import re

import numpy as np
import sounddevice as sd

from services.ejercicios import pronunciacion_service as base

SAMPLE_RATE = base.SAMPLE_RATE  
RECORD_SECONDS = 9             
MIN_VOLUME = base.MIN_VOLUME
FUZZY_THRESHOLD = 0.80        
MIN_WORD_COVERAGE = 0.65     

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


def evaluate_phrase(heard: str, expected: str) -> tuple[bool, float]:
    """Compara TODA la frase, no una palabra aislada.

    Devuelve (aprobado, similitud_de_0_a_1). Es una medida aproximada basada
    en las palabras reconocidas por Whisper, no una nota fonética.
    """
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
    return similarity >= FUZZY_THRESHOLD and coverage >= MIN_WORD_COVERAGE, round(similarity, 3)


def listen_and_check(expected: str, seconds: float = RECORD_SECONDS) -> tuple[bool, str]:
    seconds = max(1.0, min(float(seconds), 20.0))
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
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
    ok, _score = evaluate_phrase(heard, expected)
    return ok, heard


def preload() -> None:
    """Precarga el modelo compartido si se llama al iniciar Songs."""
    base.preload()
