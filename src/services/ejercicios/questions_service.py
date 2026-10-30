from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path


def format_time(seconds):
    n = max(0, int(seconds))
    return f"{n // 60:02d}:{n % 60:02d}"


def _norm(text):
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


class QuestionsSession:
    def __init__(self, exercises, progress_file=None):
        if not exercises:
            raise ValueError("QuestionsSession necesita al menos un ejercicio.")
        self.exercises = [dict(e) for e in exercises]
        for i, ex in enumerate(self.exercises):
            ex.setdefault("id", f"question_{i + 1}")
            if not ex.get("question") or not ex.get("answer"):
                raise ValueError(f"El ejercicio {ex['id']} requiere question y answer.")
            opts = ex.get("options", [])
            if len(opts) < 2 or not any(_norm(v) == _norm(ex["answer"]) for v in opts):
                raise ValueError(f"El ejercicio {ex['id']} requiere opciones y la respuesta correcta.")
        self.progress_file = Path(progress_file or (Path.home() / ".saylo" / "questions_progress.json"))
        ids = "|".join(str(e["id"]) + ":" + str(e["answer"]) for e in self.exercises)
        self._signature = hashlib.sha256(ids.encode("utf-8")).hexdigest()
        self._reset_fields()

    @classmethod
    def from_json(cls, path=None, progress_file=None):
        default = Path(__file__).resolve().parents[2] / "data" / "preguntas.json"
        file = Path(path) if path else default
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data["exercises"] if isinstance(data, dict) else data, progress_file)

    def _reset_fields(self):
        self.index = 0
        self._picked = {}
        self._pronounced = set()
        self._hints = {}
        self._errors = 0
        self._attempts = {}
        self._completed = set()
        self._skipped = set()
        self._elapsed = 0.0
        self._started_at = None
        self._paused = True
        self._ended = False

    @property
    def current(self):
        return self.exercises[self.index]

    @property
    def number(self):
        return self.index + 1

    @property
    def total(self):
        return len(self.exercises)

    @property
    def is_last(self):
        return self.index == len(self.exercises) - 1

    @property
    def has_progress(self):
        return self.progress_file.is_file()

    def _key(self, ex=None):
        return str((ex or self.current)["id"])

    def _resume_clock(self):
        if not self._ended and self._paused:
            self._started_at = time.monotonic()
            self._paused = False

    def start(self):
        self._reset_fields()
        self._resume_clock()
        try:
            self.progress_file.unlink(missing_ok=True)
        except OSError:
            pass

    def pause(self):
        if not self._paused:
            self._elapsed += time.monotonic() - self._started_at
            self._started_at = None
            self._paused = True

    def resume(self):
        self._resume_clock()

    def time_now(self):
        return self._elapsed + (
            time.monotonic() - self._started_at if not self._paused else 0.0
        )

    def picked_for(self, ex=None):
        return self._picked.get(self._key(ex))

    def is_solved(self, ex=None):
        ex = ex or self.current
        return _norm(self.picked_for(ex)) == _norm(ex["answer"])

    def is_pronounced(self, ex=None):
        return self._key(ex) in self._pronounced

    def choose(self, option):
        ex = self.current
        key = self._key()
        if self._ended or self._paused or self.is_solved(ex):
            return "ignored"
        if option == self._hints.get(key):
            return "ignored"
        self._picked[key] = option
        if _norm(option) == _norm(ex["answer"]):
            return "correct"
        self._errors += 1
        self._attempts[key] = self._attempts.get(key, 0) + 1
        return "wrong"

    def hint_available(self, ex=None):
        ex = ex or self.current
        key = self._key(ex)
        return (not self._ended and not self.is_solved(ex)
                and key not in self._hints
                and any(_norm(v) != _norm(ex["answer"]) for v in ex["options"]))

    def use_hint(self):
        ex = self.current
        if not self.hint_available(ex):
            return False
        wrong = [v for v in ex["options"] if _norm(v) != _norm(ex["answer"])]
        self._hints[self._key()] = wrong[0]
        return True

    def hint_for(self, ex=None):
        return self._hints.get(self._key(ex))

    def mark_pronounced(self, ex=None):
        if self.is_solved(ex):
            self._pronounced.add(self._key(ex))
            return True
        return False

    def can_continue(self):
        return self.is_solved() and self.is_pronounced() and not self._ended

    def _end(self):
        self.pause()
        self._ended = True
        try:
            self.progress_file.unlink(missing_ok=True)
        except OSError:
            pass

    def advance(self):
        if not self.can_continue():
            return "blocked"
        self._completed.add(self._key())
        if self.is_last:
            self._end()
            return "finished"
        self.index += 1
        return "next"

    def skip(self):
        if self._ended:
            return "ignored"
        self._skipped.add(self._key())
        if self.is_last:
            self._end()
            return "finished"
        self.index += 1
        return "next"

    def finish_early(self):
        if not self._ended:
            self._end()

    def save_progress(self):
        """Guarda la sesión en disco (no solo cierra la vista)."""
        self.pause()
        if self._ended:
            return
        data = {
            "signature": self._signature,
            "index": self.index,
            "picked": self._picked,
            "pronounced": sorted(self._pronounced),
            "hints": self._hints,
            "attempts": self._attempts,
            "errors": self._errors,
            "completed": sorted(self._completed),
            "skipped": sorted(self._skipped),
            "elapsed": self._elapsed,
        }
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        self.progress_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def resume_saved(self):
        if not self.has_progress:
            return False
        data = json.loads(self.progress_file.read_text(encoding="utf-8"))
        if data.get("signature") != self._signature:
            return False
        self._reset_fields()
        self.index = min(max(int(data["index"]), 0), self.total - 1)
        self._picked = dict(data.get("picked", {}))
        self._pronounced = set(data.get("pronounced", []))
        self._hints = dict(data.get("hints", {}))
        self._attempts = dict(data.get("attempts", {}))
        self._errors = int(data.get("errors", 0))
        self._completed = set(data.get("completed", []))
        self._skipped = set(data.get("skipped", []))
        self._elapsed = float(data.get("elapsed", 0))
        self._resume_clock()
        return True

    def summary(self):
        completed = len(self._completed)
        first_try = sum(1 for k in self._completed if self._attempts.get(k, 0) == 0)
        xp = completed * 10
        return {
            "time": format_time(self.time_now()),
            "completed": completed,
            "total": self.total,
            "errors": self._errors,
            "skips": len(self._skipped),
            "first_try": first_try,
            "xp_earned": xp,
            "xp_total": xp,  # XP de esta sesión; conectar con cuenta para acumulados reales
        }
