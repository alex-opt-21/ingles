import json
import random
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
    """Control de ejercicios, Skip, Pausa, XP y resultados."""

    def __init__(
        self,
        exercises: list[dict],
        user: dict,
        save_progress: Optional[Callable[[str, dict], None]] = None,
        session_size: Optional[int] = None,   # ej. 20 => 20 verbos al azar por sesión
    ):
        self.exercises = exercises
        self.user = user
        self._save_progress = save_progress
        self.session_size = session_size
        self.xp = user["xp"]
        self.completed = list(user["completed"])
        self.started = False
        self.finished = False
        self.reset()

    def reset(self) -> None:
        n = len(self.exercises)
        if self.session_size and self.session_size < n:
            self.order = random.sample(range(n), self.session_size)
        else:
            self.order = list(range(n))
        self.index = 0
        self.picked = {}
        self.hint_used = {}
        self.errors = 0
        self.skips = 0
        self.errors_by_verb = {}
        self.skips_by_verb = {}
        self.solved_in_round = set()
        self.first_try = set()
        self.pronounced = set()          # verbos pronunciados correctamente
        self._xp_start = self.xp
        self.elapsed = 0.0
        self.started = False
        self.finished = False
        self.t0 = time.perf_counter()
        self._paused_at = None
        self._paused_total = 0.0

    # ---------- ciclo de vida ----------
    def start(self) -> None:
        self.reset()
        self.started = True

    @property
    def has_progress(self) -> bool:
        return self.started and not self.finished

    def pause(self) -> None:
        if self._paused_at is None:
            self._paused_at = time.perf_counter()

    def resume(self) -> None:
        if self._paused_at is not None:
            self._paused_total += time.perf_counter() - self._paused_at
            self._paused_at = None

    def finish(self) -> None:
        if self.finished:
            return
        self.elapsed = self.time_now()
        self.finished = True

    def finish_early(self) -> None:
        """Termina la práctica con lo que lleva (botón 'Finish now')."""
        self.finish()

    def time_now(self) -> float:
        end = self._paused_at if self._paused_at is not None else time.perf_counter()
        return max(0.0, end - self.t0 - self._paused_total)

    # ---------- propiedades ----------
    @property
    def total(self) -> int:
        return len(self.order)

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

    def is_pronounced(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return ex["id"] in self.pronounced

    def mark_pronounced(self, ex: Optional[dict] = None) -> None:
        ex = ex or self.current
        self.pronounced.add(ex["id"])

    def can_continue(self, ex: Optional[dict] = None) -> bool:
        """Continue solo se habilita si acertó Y pronunció bien."""
        ex = ex or self.current
        return self.is_solved(ex) and self.is_pronounced(ex)

    # ---------- acciones ----------
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
        """Salta a la siguiente card y marca el verbo como error.
        Si ya estaba resuelto, solo avanza sin penalizar.
        En el último ejercicio, termina la práctica."""
        ex_id = self.current["id"]
        if not self.is_solved():
            self.skips += 1
            self.skips_by_verb[ex_id] = self.skips_by_verb.get(ex_id, 0) + 1
            self.errors += 1                                   # cuenta como error
            self.errors_by_verb[ex_id] = self.errors_by_verb.get(ex_id, 0) + 1
            self.picked.pop(ex_id, None)                       # limpia intento previo

        if self.is_last:
            self.finish()
            return "finished"
        self.index += 1
        return "next"

    def back(self) -> bool:
        if self.is_first:
            return False
        self.index -= 1
        return True

    def advance(self) -> str:
        """Continue: requiere verbo resuelto y bien pronunciado.
        En el último, termina."""
        if not self.can_continue():
            return "blocked"
        if self.is_last:
            self.finish()
            return "finished"
        self.index += 1
        return "next"

    # ---------- resumen ----------
    def verb_results(self) -> list[dict]:
        return [
            {
                "verb": self.exercises[i]["answer"],
                "correct": self.exercises[i]["id"] in self.solved_in_round,
                "errors": self.errors_by_verb.get(self.exercises[i]["id"], 0),
                "skips": self.skips_by_verb.get(self.exercises[i]["id"], 0),
                "first_try": self.exercises[i]["id"] in self.first_try,
            }
            for i in self.order
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