
import json
import random
import time
from pathlib import Path
from typing import Callable, Optional


XP_PER_EXERCISE = 10


def load_levels(exercises_file: Path) -> dict[str, dict]:
    """Carga los niveles de una lección."""

    exercises_file = Path(exercises_file)

    with exercises_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "levels" not in data:
        if "exercises" not in data:
            raise ValueError(
                f"El archivo {exercises_file} no contiene 'levels' ni 'exercises'."
            )

        return {
            "basic": {
                "id": "basic",
                "title": "Basic",
                "description": "Exercises from the original lesson format.",
                "exercises": data["exercises"],
            }
        }

    levels = data["levels"]

    if not isinstance(levels, list):
        raise ValueError("'levels' debe ser una lista.")

    result = {}

    for level in levels:
        if not isinstance(level, dict):
            continue

        level_id = level.get("id")

        if not level_id:
            raise ValueError("Cada nivel debe tener un identificador 'id'.")

        if level_id in result:
            raise ValueError(f"Hay un nivel duplicado con id '{level_id}'.")

        exercises = level.get("exercises", [])

        if not isinstance(exercises, list):
            raise ValueError(
                f"Los ejercicios del nivel '{level_id}' deben estar en una lista."
            )

        result[level_id] = level

    if not result:
        raise ValueError("El archivo no contiene niveles válidos.")

    return result


def load_exercises(
    exercises_file: Path,
    assets_dir: Optional[Path] = None,
    level_id: str = "basic",
) -> list[dict]:
    """Carga los ejercicios de un nivel específico."""

    levels = load_levels(exercises_file)

    if level_id not in levels:
        available = ", ".join(levels.keys())
        raise ValueError(
            f"Nivel '{level_id}' no encontrado. "
            f"Niveles disponibles: {available}"
        )

    exercises = levels[level_id].get("exercises", [])

    if not exercises:
        raise ValueError(f"El nivel '{level_id}' no contiene ejercicios.")

    required_fields = {"id", "image", "options", "answer"}

    for index, exercise in enumerate(exercises, start=1):
        missing = required_fields - exercise.keys()

        if missing:
            raise ValueError(
                f"Ejercicio {index} del nivel '{level_id}': "
                f"faltan los campos {', '.join(sorted(missing))}."
            )

    if assets_dir is not None:
        assets_dir = Path(assets_dir)

        for exercise in exercises:
            image_path = assets_dir / exercise["image"]

            if not image_path.exists():
                print(f"[!] No encuentro la imagen: {image_path}")

    return exercises


def format_time(seconds: float) -> str:
    """Convierte segundos a formato MM:SS."""

    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


class QuizSession:
    """
    Controla una práctica de Flashcards.

    El progreso se guarda por módulo, lección y nivel.
    Los XP y ejercicios que ya dieron XP se mantienen
    independientemente de la sesión actual.
    """

    def __init__(
        self,
        exercises: list[dict],
        user: dict,
        save_progress: Optional[Callable[[str, dict], None]] = None,
        session_size: Optional[int] = None,
        level_id: str = "basic",
        lesson_id: str = "action_practice",
        save_session: Optional[Callable[[str, dict], None]] = None,
        clear_session: Optional[Callable[[str], None]] = None,
        module_id: str = "flashcards",
    ):
        if not exercises:
            raise ValueError("No se puede crear una sesión sin ejercicios.")

        if session_size is not None and session_size <= 0:
            raise ValueError("session_size debe ser mayor que cero.")

        ids = [ex.get("id") for ex in exercises]

        if any(not ex_id for ex_id in ids):
            raise ValueError("Todos los ejercicios deben tener un 'id'.")

        if len(ids) != len(set(ids)):
            raise ValueError("Hay identificadores de ejercicios duplicados.")

        self.exercises = exercises
        self.user = user

        self._save_progress = save_progress
        self._save_session = save_session
        self._clear_session = clear_session

        self.session_size = session_size
        self.level_id = level_id
        self.lesson_id = lesson_id
        self.module_id = module_id

        self.xp = user.get("xp", 0)
        self.completed = list(user.get("completed", []))

        self.started = False
        self.finished = False

        self.reset()

    # ---------- Reinicio ----------

    def reset(self) -> None:
        """Reinicia la práctica y genera un nuevo orden."""

        total_exercises = len(self.exercises)

        if (
            self.session_size is not None
            and self.session_size < total_exercises
        ):
            self.order = random.sample(
                range(total_exercises),
                self.session_size,
            )
        else:
            self.order = list(range(total_exercises))

        self.index = 0

        # Estado de los ejercicios de esta ronda.
        self.picked = {}
        self.hint_used = {}

        # Estadísticas generales.
        self.errors = 0
        self.skips = 0

        # Identificadores necesarios para recuperar la práctica.
        self.solved_in_round = set()
        self.failed_ids = set()
        self.first_try = set()
        self.pronounced = set()

        self._xp_start = self.xp

        self.elapsed = 0.0
        self.started = False
        self.finished = False

        self.t0 = time.perf_counter()
        self._paused_at = None
        self._paused_total = 0.0

    # ---------- Persistencia ----------

    def to_state(self) -> dict:
        """Convierte el estado actual en un diccionario JSON."""

        return {
            "version": 2,
            "module_id": self.module_id,
            "lesson_id": self.lesson_id,
            "level_id": self.level_id,

            "exercise_ids": [
                self.exercises[i]["id"]
                for i in self.order
            ],

            "index": self.index,

            "picked": dict(self.picked),
            "hint_used": dict(self.hint_used),

            "solved": sorted(self.solved_in_round),
            "failed_ids": sorted(self.failed_ids),
            "first_try": sorted(self.first_try),
            "pronounced": sorted(self.pronounced),

            "errors": self.errors,
            "skips": self.skips,

            "xp_start": self._xp_start,
            "elapsed": self.time_now(),

            "status": (
                "paused"
                if self._paused_at is not None
                else "in_progress"
            ),
        }

    def restore_state(self, state: Optional[dict]) -> bool:
        """Restaura una práctica guardada."""

        if not isinstance(state, dict):
            return False

        if state.get("lesson_id", self.lesson_id) != self.lesson_id:
            return False

        if state.get("level_id", self.level_id) != self.level_id:
            return False

        if state.get("module_id", self.module_id) != self.module_id:
            return False

        by_id = {
            exercise["id"]: index
            for index, exercise in enumerate(self.exercises)
        }

        saved_ids = state.get("exercise_ids")

        if not isinstance(saved_ids, list) or not saved_ids:
            return False

        if len(saved_ids) != len(set(saved_ids)):
            return False

        if any(ex_id not in by_id for ex_id in saved_ids):
            return False

        try:
            restored_order = [by_id[ex_id] for ex_id in saved_ids]
            restored_index = int(state.get("index", 0))
            elapsed = max(0.0, float(state.get("elapsed", 0.0)))

            errors = max(0, int(state.get("errors", 0)))
            skips = max(0, int(state.get("skips", 0)))
            xp_start = int(state.get("xp_start", self.xp))

        except (TypeError, ValueError):
            return False

        if not 0 <= restored_index < len(restored_order):
            return False

        valid_ids = set(saved_ids)

        self.order = restored_order
        self.index = restored_index

        picked = state.get("picked", {})
        hints = state.get("hint_used", {})

        if not isinstance(picked, dict):
            picked = {}

        if not isinstance(hints, dict):
            hints = {}

        self.picked = {
            key: value
            for key, value in picked.items()
            if key in valid_ids and isinstance(value, str)
        }

        self.hint_used = {
            key: value
            for key, value in hints.items()
            if key in valid_ids and isinstance(value, str)
        }

        self.solved_in_round = (
            set(state.get("solved", state.get("solved_in_round", [])))
            & valid_ids
        )

        self.failed_ids = (
            set(state.get("failed_ids", []))
            & valid_ids
        )

        self.first_try = (
            set(state.get("first_try", []))
            & valid_ids
        )

        self.pronounced = (
            set(state.get("pronounced", []))
            & valid_ids
        )

        self.errors = errors
        self.skips = skips
        self._xp_start = xp_start
        self.elapsed = elapsed

        # La práctica se recupera pausada.
        now = time.perf_counter()

        self.t0 = now - elapsed
        self._paused_at = now
        self._paused_total = 0.0

        self.started = True
        self.finished = False

        return True

    def persist_now(self) -> None:
        """Guarda el estado actual de la práctica."""

        if not self.started or self.finished:
            return

        if not self._save_session:
            return

        email = self.user.get("email")

        if not email:
            print("[!] No se guardó la sesión: falta el email del usuario.")
            return

        try:
            self._save_session(email, self.to_state())

        except Exception as err:
            print(f"[!] No se pudo guardar la sesión: {err}")

    def _clear_persisted_session(self) -> None:
        """Elimina únicamente la sesión actual."""

        if not self._clear_session:
            return

        email = self.user.get("email")

        if not email:
            return

        try:
            self._clear_session(email)

        except Exception as err:
            print(f"[!] No se pudo eliminar la sesión: {err}")

    # ---------- Ciclo de vida ----------

    def start(self) -> None:
        """Comienza una práctica nueva."""

        self.reset()
        self.started = True
        self.persist_now()

    @property
    def has_progress(self) -> bool:
        return self.started and not self.finished

    def pause(self) -> None:
        if self._paused_at is None and not self.finished:
            self._paused_at = time.perf_counter()
            self.persist_now()

    def resume(self) -> None:
        if self._paused_at is not None and not self.finished:
            self._paused_total += (
                time.perf_counter() - self._paused_at
            )

            self._paused_at = None
            self.persist_now()

    def finish(self) -> None:
        if self.finished:
            return

        self.elapsed = self.time_now()
        self.finished = True

        self._clear_persisted_session()

    def finish_early(self) -> None:
        self.finish()

    def time_now(self) -> float:
        end = (
            self._paused_at
            if self._paused_at is not None
            else time.perf_counter()
        )

        return max(
            0.0,
            end - self.t0 - self._paused_total,
        )

    # ---------- Propiedades ----------

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
        return self.user.get("name", "Student")

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

    # ---------- Consultas de ejercicios ----------

    def picked_for(self, ex: dict):
        return self.picked.get(ex["id"])

    def hint_for(self, ex: dict):
        return self.hint_used.get(ex["id"])

    def is_solved(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return ex["id"] in self.solved_in_round

    def hint_available(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current

        return (
            not self.is_solved(ex)
            and ex["id"] not in self.hint_used
        )

    def is_pronounced(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current
        return ex["id"] in self.pronounced

    def mark_pronounced(self, ex: Optional[dict] = None) -> None:
        ex = ex or self.current
        self.pronounced.add(ex["id"])
        self.persist_now()

    def can_continue(self, ex: Optional[dict] = None) -> bool:
        ex = ex or self.current

        return (
            self.is_solved(ex)
            and self.is_pronounced(ex)
        )

    # ---------- Acciones ----------

    def choose(self, option: str) -> str:
        """Registra una respuesta."""

        ex = self.current
        ex_id = ex["id"]

        if self.is_solved(ex):
            return "ignored"

        self.picked[ex_id] = option

        if option != ex["answer"]:
            self.errors += 1
            self.failed_ids.add(ex_id)

            self.persist_now()
            return "wrong"

        self.solved_in_round.add(ex_id)

        if ex_id not in self.failed_ids:
            self.first_try.add(ex_id)

        # Evitar entregar XP más de una vez por ejercicio.
        if ex_id not in self.completed:
            self.completed.append(ex_id)
            self.xp += XP_PER_EXERCISE

            # Mantener sincronizados los datos del usuario.
            self.user["xp"] = self.xp
            self.user["completed"] = list(self.completed)

            if self._save_progress:
                try:
                    self._save_progress(
                        self.user["email"],
                        {
                            "xp": self.xp,
                            "completed": self.completed,
                        },
                    )
                except Exception as err:
                    print(f"[!] No se pudo guardar el XP: {err}")

        self.persist_now()
        return "correct"

    def use_hint(self) -> bool:
        """Elimina una opción incorrecta."""

        ex = self.current

        if not self.hint_available(ex):
            return False

        picked = self.picked_for(ex)

        candidates = [
            option
            for option in ex["options"]
            if option != ex["answer"] and option != picked
        ]

        if not candidates:
            return False

        self.hint_used[ex["id"]] = candidates[0]
        self.persist_now()

        return True

    def skip(self) -> str:
        """Salta el ejercicio actual."""

        ex_id = self.current["id"]

        if not self.is_solved():
            self.skips += 1
            self.errors += 1
            self.failed_ids.add(ex_id)

            self.picked.pop(ex_id, None)

        if self.is_last:
            self.finish()
            return "finished"

        self.index += 1
        self.persist_now()

        return "next"

    def back(self) -> bool:
        """Regresa al ejercicio anterior."""

        if self.is_first:
            return False

        self.index -= 1
        self.persist_now()

        return True

    def advance(self) -> str:
        """Avanza cuando el ejercicio está resuelto y pronunciado."""

        if not self.can_continue():
            return "blocked"

        if self.is_last:
            self.finish()
            return "finished"

        self.index += 1
        self.persist_now()

        return "next"

    # ---------- Resumen ----------

    def summary(self) -> dict:
        """Devuelve el resumen general de la práctica."""

        return {
            "level": self.level_id,
            "lesson_id": self.lesson_id,
            "time": format_time(self.elapsed),
            "completed": self.correct_count,
            "total": self.total,
            "errors": self.errors,
            "skips": self.skips,
            "first_try": self.first_try_count,
            "xp_total": self.xp,
            "xp_earned": self.xp_earned,
        }
