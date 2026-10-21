
import json
import time
from pathlib import Path
from typing import Callable, Optional

XP_PER_EXERCISE = 10


def load_exercises(exercises_file: Path, assets_dir: Optional[Path] = None) -> list[dict]:
    with open(exercises_file, encoding="utf-8") as f:
        exercises = json.load(f)["exercises"]
    if assets_dir is not None:
        for ex in exercises:
            ruta = assets_dir / ex["image"]
            if not ruta.exists():
                print(f"[!] No encuentro la imagen: {ruta}")
    return exercises


def format_time(seconds: float) -> str:
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


class QuizSession:
    """Control de ejercicios, Skip, XP y resultados."""

    def __init__(
        self,
        exercises: list[dict],
        user: dict,
        save_progress: Optional[Callable[[str, dict], None]] = None,
    ):
        self.exercises = exercises
        self.user = user
        self._save_progress = save_progress
        self.xp = user["xp"]
        self.completed = list(user["completed"])
        self.reset()

    def reset(self) -> None:
        self.index = 0
        self.order = list(range(len(self.exercises)))
        self.picked = {}
        self.hint_used = {}
        self.errors = 0
        self.skips = 0
        self.errors_by_verb = {}
        self.skips_by_verb = {}
        self.solved_in_round = set()
        self.first_try = set()
        self._xp_start = self.xp
        self.elapsed = 0.0
        self.t0 = time.perf_counter()

    def start(self) -> None:
        self.reset()

    def finish(self) -> None:
        self.elapsed = self.time_now()

    def time_now(self) -> float:
        return time.perf_counter() - self.t0

    @property
    def total(self) -> int:
        return len(self.exercises)

    @property
    def number(self) -> int:
        return self.index + 1

    @property
    def is_first(self) -> bool:
        return self.index == 0

    @property
    def is_last(self) -> bool:
        return self.index == self.total - 1

    @property
    def current(self) -> dict:
        return self.exercises[self.order[self.index]]

    @property
    def user_name(self) -> str:
        return self.user["name"]

    @property
    def correct_count(self) -> int:
        return len(self.solved_in_round)

    @property
    def pending_count(self) -> int:
        return self.total - self.correct_count

    @property
    def first_try_count(self) -> int:
        return len(self.first_try)

    @property
    def xp_earned(self) -> int:
        return self.xp - self._xp_start

    def picked_for(self, ex: dict):
        return self.picked.get(ex["id"])

    def hint_for(self, ex: dict):
        return self.hint_used.get(ex["id"])

    def is_solved(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return self.picked_for(ex) == ex["answer"]

    def hint_available(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return not self.is_solved(ex) and ex["id"] not in self.hint_used

    def choose(self, option: str) -> str:
        ex = self.current
        ex_id = ex["id"]
        if self.is_solved(ex):
            return "ignored"

        self.picked[ex_id] = option
        if option != ex["answer"]:
            self.errors += 1
            self.errors_by_verb[ex_id] = self.errors_by_verb.get(ex_id, 0) + 1
            return "wrong"

        self.solved_in_round.add(ex_id)
        if not self.errors_by_verb.get(ex_id) and not self.skips_by_verb.get(ex_id):
            self.first_try.add(ex_id)

        if ex_id not in self.completed:
            self.completed.append(ex_id)
            self.xp += XP_PER_EXERCISE
            if self._save_progress:
                self._save_progress(
                    self.user["email"],
                    {"xp": self.xp, "completed": self.completed},
                )
        return "correct"

    def use_hint(self) -> bool:
        ex = self.current
        if not self.hint_available(ex):
            return False

        picked = self.picked_for(ex)
        candidates = [
            o for o in ex["options"]
            if o != ex["answer"] and o != picked
        ]
        if not candidates:
            return False

        self.hint_used[ex["id"]] = candidates[0]
        return True

    def skip(self) -> str:
        """Deja el verbo pendiente y lo mueve al final."""
        if self.is_solved() or self.is_last:
            return "blocked"

        ex_id = self.current["id"]
        self.skips += 1
        self.skips_by_verb[ex_id] = self.skips_by_verb.get(ex_id, 0) + 1
        self.picked.pop(ex_id, None)

        position = self.order.pop(self.index)
        self.order.append(position)
        return "next"

    def back(self) -> bool:
        if self.is_first:
            return False
        self.index -= 1
        return True

    def advance(self) -> str:
        """Solo termina cuando los 16 verbos están correctos."""
        if not self.is_solved():
            return "blocked"
        if self.is_last:
            if self.correct_count != self.total:
                return "blocked"
            self.finish()
            return "finished"
        self.index += 1
        return "next"

    def verb_results(self) -> list[dict]:
        return [
            {
                "verb": ex["answer"],
                "correct": ex["id"] in self.solved_in_round,
                "errors": self.errors_by_verb.get(ex["id"], 0),
                "skips": self.skips_by_verb.get(ex["id"], 0),
                "first_try": ex["id"] in self.first_try,
            }
            for ex in self.exercises
        ]

    def summary(self) -> dict:
        return {
            "time": format_time(self.elapsed),
            "completed": self.correct_count,
            "total": self.total,
            "errors": self.errors,
            "skips": self.skips,
            "first_try": self.first_try_count,
            "xp_total": self.xp,
            "xp_earned": self.xp_earned,
            "verbs": self.verb_results(),
        }
