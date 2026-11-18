
import hashlib
import json
import time
from copy import deepcopy


def load_phrases(json_path, assets_dir):
    json_path = __import__("pathlib").Path(json_path)
    assets_dir = __import__("pathlib").Path(assets_dir)

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("exercises") or data.get("phrases") or data

    phrases = []

    for i, ex in enumerate(items, start=1):
        obj = deepcopy(ex)
        obj.setdefault("id", f"phrase_{i}")

        if obj.get("image"):
            obj["image"] = str(obj["image"]).replace("\\", "/")

        if obj.get("audio"):
            obj["audio"] = str(obj["audio"]).replace("\\", "/")

        phrases.append(obj)

    return phrases


class PhrasesSession:

    def __init__(
        self,
        exercises,
        user=None,
        save_progress=None,
        save_session=None,
        clear_session=None,
        module_id="phrases",
        lesson_id="phrase_practice",
        level_id="basic",
    ):
        self.exercises = list(exercises)
        self.user = user or {}

        self.save_progress_cb = save_progress
        self.save_session_cb = save_session
        self.clear_session_cb = clear_session

        self.module_id = module_id
        self.lesson_id = lesson_id
        self.level_id = level_id

        self.total = len(self.exercises)

        self.index = 0
        self.started_at = None
        self.elapsed_before_pause = 0
        self._paused = True
        self._ended = False

        self._picked = {}
        self._pronounced = set()
        self._hint_hidden = {}

        self._errors = 0
        self._skips = 0

        self.xp = int(self.user.get("xp", 0))
        self.xp_earned = 0
        self.completed = set(self.user.get("completed", []))

        self.has_progress = False

        self.signature = self._build_signature()

    # =====================================================
    # IDENTIDAD DE LA SESIÓN
    # =====================================================

    def _build_signature(self):
        data = [
            {
                "id": ex.get("id"),
                "answer": ex.get("answer"),
                "options": ex.get("options", []),
            }
            for ex in self.exercises
        ]

        raw = json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
        )

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, path, **kwargs):
        path = __import__("pathlib").Path(path)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("exercises") or data.get("phrases") or data

        return cls(items, **kwargs)

    # =====================================================
    # PROPIEDADES
    # =====================================================

    @property
    def current(self):
        return self.exercises[self.index]

    @property
    def number(self):
        return self.index + 1

    @property
    def is_last(self):
        return self.index >= self.total - 1

    def key_for(self, ex=None):
        ex = ex or self.current
        return ex.get("id") or f"idx_{self.index}"

    def picked_for(self, ex=None):
        return self._picked.get(self.key_for(ex))

    def hint_for(self, ex=None):
        return self._hint_hidden.get(self.key_for(ex))

    def is_solved(self, ex=None):
        ex = ex or self.current
        return self.picked_for(ex) == ex.get("answer")

    def is_pronounced(self, ex=None):
        return self.key_for(ex) in self._pronounced

    def can_continue(self, ex=None):
        ex = ex or self.current
        return self.is_solved(ex) and self.is_pronounced(ex)

    def hint_available(self, ex=None):
        ex = ex or self.current
        key = self.key_for(ex)

        return (
            key not in self._hint_hidden
            and not self.is_solved(ex)
        )

    def format_time(self, seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def time_now(self):
        if self.started_at is None:
            return int(self.elapsed_before_pause)

        return int(
            self.elapsed_before_pause
            + time.time()
            - self.started_at
        )

    # =====================================================
    # PROGRESO Y PERSISTENCIA
    # =====================================================

    def to_state(self):
        return {
            "version": 1,
            "module_id": self.module_id,
            "lesson_id": self.lesson_id,
            "level_id": self.level_id,
            "signature": self.signature,
            "exercise_ids": [
                ex.get("id") for ex in self.exercises
            ],
            "index": self.index,
            "picked": dict(self._picked),
            "pronounced": list(self._pronounced),
            "hint_hidden": dict(self._hint_hidden),
            "errors": self._errors,
            "skips": self._skips,
            "xp": self.xp,
            "xp_earned": self.xp_earned,
            "completed": list(self.completed),
            "elapsed": self.time_now(),
            "status": "paused" if self._paused else "in_progress",
        }

    def persist_now(self):
        if self._ended:
            return

        if not callable(self.save_session_cb):
            return

        email = self.user.get("email")

        if not email:
            return

        try:
            self.save_session_cb(email, self.to_state())
            self.has_progress = True
        except Exception as err:
            print(f"Error guardando progreso de Phrases: {err}")

    def restore_state(self, data):
        if not isinstance(data, dict):
            return False

        if data.get("module_id") != self.module_id:
            return False

        if data.get("lesson_id") != self.lesson_id:
            return False

        if data.get("level_id") != self.level_id:
            return False

        if data.get("signature") != self.signature:
            return False

        try:
            index = int(data.get("index", 0))

            if not 0 <= index < self.total:
                return False

            self.index = index
            self._picked = dict(data.get("picked", {}))
            self._pronounced = set(data.get("pronounced", []))
            self._hint_hidden = dict(data.get("hint_hidden", {}))

            self._errors = int(data.get("errors", 0))
            self._skips = int(data.get("skips", 0))

            self.xp = int(data.get("xp", self.user.get("xp", 0)))
            self.xp_earned = int(data.get("xp_earned", 0))

            self.completed = set(
                data.get("completed", self.user.get("completed", []))
            )

            self.elapsed_before_pause = max(
                0,
                int(data.get("elapsed", 0)),
            )

            self.started_at = None
            self._paused = True
            self._ended = False
            self.has_progress = True

            return True

        except (TypeError, ValueError):
            return False

    def clear_saved_progress(self):
        email = self.user.get("email")

        if not email or not callable(self.clear_session_cb):
            return

        try:
            self.clear_session_cb(email)
        except Exception as err:
            print(f"Error limpiando progreso de Phrases: {err}")

        self.has_progress = False

    # =====================================================
    # CICLO DE VIDA
    # =====================================================

    def start(self):
        self.clear_saved_progress()

        self.index = 0
        self.started_at = time.time()
        self.elapsed_before_pause = 0

        self._paused = False
        self._ended = False

        self._picked = {}
        self._pronounced = set()
        self._hint_hidden = {}

        self._errors = 0
        self._skips = 0
        self.xp_earned = 0

        self.has_progress = False

    def pause(self):
        if self._ended:
            return

        if self.started_at is not None:
            self.elapsed_before_pause = self.time_now()
            self.started_at = None

        self._paused = True
        self.persist_now()

    def resume(self):
        if self._ended:
            return

        if self.started_at is None:
            self.started_at = time.time()

        self._paused = False

    def finish_early(self):
        self.pause()

    # =====================================================
    # ACCIONES DEL EJERCICIO
    # =====================================================

    def _save_user_progress(self):
        if not callable(self.save_progress_cb):
            return

        try:
            self.save_progress_cb(
                self.user,
                self.xp,
                list(self.completed),
            )
        except Exception as err:
            print(f"Error guardando XP de Phrases: {err}")

    def choose(self, option):
        ex = self.current
        key = self.key_for(ex)

        if self.is_solved(ex):
            return "ignored"

        self._picked[key] = option

        if option == ex.get("answer"):
            if key not in self.completed:
                self.completed.add(key)
                self.xp += 5
                self.xp_earned += 5

            self._save_user_progress()
            self.persist_now()

            return "correct"

        self._errors += 1
        self.persist_now()

        return "wrong"

    def use_hint(self):
        ex = self.current
        key = self.key_for(ex)

        if not self.hint_available(ex):
            return False

        for option in ex.get("options", []):
            if option != ex.get("answer"):
                self._hint_hidden[key] = option
                self.persist_now()
                return True

        return False

    def mark_pronounced(self, ex=None):
        self._pronounced.add(self.key_for(ex))
        self.persist_now()

    def skip(self):
        self._skips += 1
        return self.advance(force=True)

    def advance(self, force=False):
        if not force and not self.can_continue(self.current):
            return "blocked"

        if self.is_last:
            self._end()
            return "finished"

        self.index += 1
        self.persist_now()

        return "next"

    def _end(self):
        if self.started_at is not None:
            self.elapsed_before_pause = self.time_now()
            self.started_at = None

        self._paused = True
        self._ended = True

        self.clear_saved_progress()

    # =====================================================
    # RESUMEN
    # =====================================================

    def summary(self):
        completed_count = sum(
            1
            for ex in self.exercises
            if self.key_for(ex) in self.completed
        )

        return {
            "time": self.format_time(self.time_now()),
            "completed": completed_count,
            "total": self.total,
            "errors": self._errors,
            "skips": self._skips,
            "xp_earned": self.xp_earned,
            "xp_total": self.xp,
        }
