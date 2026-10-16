import difflib
import re

import speech_recognition as sr

# Palabras que suenan igual o muy parecido al verbo esperado
SOUND_ALIKES = {
    "eat": {"it", "eight", "eats", "eating", "heat", "meet", "e", "ate"},
    "read": {"red", "reed", "reid", "ready", "rid", "reads", "reading"},
    "write": {"right", "rite", "white", "wright", "writes", "writing", "ride"},
    "play": {"plays", "plea", "clay", "pray", "played"},
    "sing": {"sink", "sin", "thing", "singh", "sings"},
    "sleep": {"slip", "sleeps", "asleep", "sleeping"},
    "swim": {"swimming", "swims", "swam", "some"},
    "clean": {"cleans", "clean", "client"},
    "cook": {"cooks", "cooking", "book", "look"},
    "run": {"ron", "runs", "ran", "one"},
    "draw": {"drawn", "drew", "drawing", "draws", "drop"},
    "dance": {"dances", "dancing", "dunce", "dants"},
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z\s]", "", text.lower()).strip()


def _matches(heard_words: list[str], target: str, threshold: float) -> bool:
    aliases = SOUND_ALIKES.get(target, set())
    for w in heard_words:
        if w == target or w in aliases:
            return True
        if difflib.SequenceMatcher(None, w, target).ratio() >= threshold:
            return True
    return False


def listen_and_check(expected: str, threshold: float = 0.75):
    """Escucha el micrófono y devuelve (ok, lo_que_se_entendio)."""
    r = sr.Recognizer()
    r.pause_threshold = 0.6          # corta rápido tras una palabra corta
    r.non_speaking_duration = 0.4

    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
        result = r.recognize_google(audio, language="en-US", show_all=True)
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return False, ""

    if not result or "alternative" not in result:
        return False, ""

    transcripts = [
        _normalize(alt.get("transcript", ""))
        for alt in result["alternative"]
    ]
    transcripts = [t for t in transcripts if t]
    if not transcripts:
        return False, ""

    target = _normalize(expected)
    all_words = [w for t in transcripts for w in t.split()]

    ok = _matches(all_words, target, threshold)
    return ok, transcripts[0]