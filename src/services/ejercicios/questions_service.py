
from __future__ import annotations

import hashlib
import json
import re
import time


def format_time(seconds):
    n = max(0, int(seconds))
    return f"{n // 60:02d}:{n % 60:02d}"


def _norm(text):
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


class QuestionsSession:
    def __init__(
        self,
        exercises,
        user=None,
        save_progress=None,
        save_session=None,
        clear_session=None,
        module_id="questions",
        lesson_id="question_practice",
        level_id="basic",
    ):
        if not exercises:
            raise ValueError("QuestionsSession necesita al menos un ejercicio.")

        self.exercises = [dict(e) for e in exercises]

        for i, ex in enumerate(self.exercises):
            ex.setdefault("id", f"question_{i + 1}")

            if not ex.get("question") or not ex.get("answer"):
                raise ValueError(
                    f"El ejercicio {ex['id']} requiere question y answer."
                )

            opts = ex.get("options", [])

            if len(opts) < 2 or not any(
                _norm(v) == _norm(ex["answer"]) for v in opts
            ):
                raise ValueError(
                    f"El ejercicio {ex['id']} requiere opciones "
                    "y la respuesta correcta."
                )

        self.user = user or {}
        self.save_progress_callback = save_progress
        self.save_session_callback = save_session
        self.clear_session_callback = clear_session

        self.module_id = module_id
        self.lesson_id = lesson_id
        self.level_id = level_id

        ids = "|".join(
            str(e["id"]) + ":" + str(e["answer"])
            for e in self.exercises
        )
        self._signature = hashlib.sha256(
            ids.encode("utf-8")
        ).hexdigest()

        self._reset_fields()

    @classmethod
    def from_json(cls, path=None, **kwargs):
        from pathlib import Path

        default = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "preguntas.json"
        )

        file = Path(path) if path else default

        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        exercises = data["exercises"] if isinstance(data, dict) else data

        return cls(exercises, **kwargs)

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
        return False

    def _key(self, ex=None):
        return str((ex or self.current)["id"])

    def _resume_clock(self):
        if not self._ended and self._paused:
            self._started_at = time.monotonic()
            self._paused = False

    def start(self):
        self.clear_saved_progress()
        self._reset_fields()
        self._resume_clock()

    def pause(self):
        if not self._paused:
            self._elapsed += time.monotonic() - self._started_at
            self._started_at = None
            self._paused = True

        self.persist_now()

    def resume(self):
        self._resume_clock()

    def time_now(self):
        return self._elapsed + (
            time.monotonic() - self._started_at
            if not self._paused else 0.0
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
            self.persist_now()
            return "correct"

        self._errors += 1
        self._attempts[key] = self._attempts.get(key, 0) + 1

        self.persist_now()
        return "wrong"

    def hint_available(self, ex=None):
        ex = ex or self.current
        key = self._key(ex)

        return (
            not self._ended
            and not self.is_solved(ex)
            and key not in self._hints
            and any(
                _norm(v) != _norm(ex["answer"])
                for v in ex["options"]
            )
        )

    def use_hint(self):
        ex = self.current

        if not self.hint_available(ex):
            return False

        wrong = [
            v for v in ex["options"]
            if _norm(v) != _norm(ex["answer"])
        ]

        self._hints[self._key()] = wrong[0]
        self.persist_now()
        return True

    def hint_for(self, ex=None):
        return self._hints.get(self._key(ex))

    def mark_pronounced(self, ex=None):
        if self.is_solved(ex):
            self._pronounced.add(self._key(ex))
            self.persist_now()
            return True

        return False

    def can_continue(self):
        return (
            self.is_solved()
            and self.is_pronounced()
            and not self._ended
        )

    def _end(self):
        self.pause()
        self._ended = True
        self.clear_saved_progress()

    def advance(self):
        if not self.can_continue():
            return "blocked"

        self._completed.add(self._key())

        if self.is_last:
            self._end()
            return "finished"

        self.index += 1
        self.persist_now()
        return "next"

    def skip(self):
        if self._ended:
            return "ignored"

        self._skipped.add(self._key())

        if self.is_last:
            self._end()
            return "finished"

        self.index += 1
        self.persist_now()
        return "next"

    def finish_early(self):
        if not self._ended:
            self._end()

    def to_state(self):
        elapsed = self.time_now()

        return {
            "version": 1,
            "module_id": self.module_id,
            "lesson_id": self.lesson_id,
            "level_id": self.level_id,
            "signature": self._signature,
            "exercise_ids": [
                str(ex["id"]) for ex in self.exercises
            ],
            "index": self.index,
            "picked": self._picked,
            "pronounced": sorted(self._pronounced),
            "hints": self._hints,
            "attempts": self._attempts,
            "errors": self._errors,
            "completed": sorted(self._completed),
            "skipped": sorted(self._skipped),
            "elapsed": elapsed,
            "status": "paused" if self._paused else "in_progress",
        }

    def restore_state(self, data):
        if not isinstance(data, dict):
            return False

        if data.get("signature") != self._signature:
            return False

        if data.get("module_id") != self.module_id:
            return False

        if data.get("lesson_id") != self.lesson_id:
            return False

        if data.get("level_id") != self.level_id:
            return False

        try:
            self._reset_fields()

            self.index = min(
                max(int(data.get("index", 0)), 0),
                self.total - 1,
            )

            self._picked = dict(data.get("picked", {}))
            self._pronounced = set(data.get("pronounced", []))
            self._hints = dict(data.get("hints", {}))
            self._attempts = dict(data.get("attempts", {}))
            self._errors = int(data.get("errors", 0))
            self._completed = set(data.get("completed", []))
            self._skipped = set(data.get("skipped", []))
            self._elapsed = float(data.get("elapsed", 0))

            self._paused = True
            self._started_at = None
            self._ended = False

            return True

        except (TypeError, ValueError, KeyError):
            self._reset_fields()
            return False

    def persist_now(self):
        if self._ended or not self.save_session_callback:
            return

        email = self.user.get("email")

        if not email:
            return

        self.save_session_callback(email, self.to_state())

    def save_progress(self):
        """Compatible con el botón Save & Exit de QuestionsView."""
        self.pause()

    def clear_saved_progress(self):
        if not self.clear_session_callback:
            return

        email = self.user.get("email")

        if email:
            self.clear_session_callback(email)

    def summary(self):
        completed = len(self._completed)

        first_try = sum(
            1 for key in self._completed
            if self._attempts.get(key, 0) == 0
        )

        xp = completed * 10

        return {
            "time": format_time(self.time_now()),
            "completed": completed,
            "total": self.total,
            "errors": self._errors,
            "skips": len(self._skipped),
            "first_try": first_try,
            "xp_earned": xp,
            "xp_total": xp,
        }
