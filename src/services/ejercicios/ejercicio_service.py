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
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


class QuizSession:
    """Estado y reglas de una ronda de ejercicios para un usuario."""

    def __init__(
        self,
        exercises: list[dict],
        user: dict,
        save_progress: Optional[Callable[[str, dict], None]] = None,
    ):
        self.exercises = exercises
        self.user = user
        self._save_progress = save_progress
        self.xp: int = user["xp"]
        self.completed: list = list(user["completed"])
        self.reset()

    # ---------- ciclo de la ronda ----------

    def reset(self) -> None:
        self.index = 0
        self.picked: dict = {}      
        self.hint_used: dict = {}   
        self.errors = 0
        self.elapsed = 0.0
        self.t0 = time.perf_counter()

    def start(self) -> None:
        """Reinicia la ronda y arranca el cronómetro."""
        self.reset()

    def finish(self) -> None:
        self.elapsed = time.perf_counter() - self.t0

    def time_now(self) -> float:
        return time.perf_counter() - self.t0

    # ---------- consultas ----------

    @property
    def total(self) -> int:
        return len(self.exercises)

    @property
    def number(self) -> int:
        """Número del ejercicio actual (empezando en 1)."""
        return self.index + 1

    @property
    def is_first(self) -> bool:
        return self.index == 0

    @property
    def is_last(self) -> bool:
        return self.index == self.total - 1

    @property
    def current(self) -> dict:
        return self.exercises[self.index]

    @property
    def user_name(self) -> str:
        return self.user["name"]

    def picked_for(self, ex: dict):
        return self.picked.get(ex["id"])

    def hint_for(self, ex: dict):
        return self.hint_used.get(ex["id"])

    def is_solved(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return self.picked.get(ex["id"]) == ex["answer"]

    def hint_available(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return not self.is_solved(ex) and ex["id"] not in self.hint_used

    # ---------- acciones ----------

    def choose(self, option: str) -> str:
        """Devuelve 'ignored' | 'correct' | 'wrong'."""
        ex = self.current
        if self.is_solved(ex):
            return "ignored"
        self.picked[ex["id"]] = option
        if option == ex["answer"]:
            if ex["id"] not in self.completed:
                self.completed.append(ex["id"])
                self.xp += XP_PER_EXERCISE
                if self._save_progress:
                    self._save_progress(
                        self.user["email"],
                        {"xp": self.xp, "completed": self.completed},
                    )
            return "correct"
        self.errors += 1
        return "wrong"

    def use_hint(self) -> bool:
        ex = self.current
        if not self.hint_available(ex):
            return False
        picked = self.picked_for(ex)
        candidates = [o for o in ex["options"] if o != ex["answer"] and o != picked]
        if not candidates:
            return False
        self.hint_used[ex["id"]] = candidates[0]
        return True

    def back(self) -> bool:
        if self.is_first:
            return False
        self.index -= 1
        return True

    def advance(self) -> str:
        """Devuelve 'blocked' | 'next' | 'finished'. Exige haber acertado."""
        if not self.is_solved():
            return "blocked"
        if self.is_last:
            self.finish()
            return "finished"
        self.index += 1
        return "next"