import json
import time
from copy import deepcopy
from pathlib import Path


DEFAULT_PROGRESS_FILE = Path("phrases_progress.json")


def load_phrases(json_path, assets_dir):
    json_path = Path(json_path)
    assets_dir = Path(assets_dir)
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
    def __init__(self, exercises, user=None, save_progress=None, progress_file=DEFAULT_PROGRESS_FILE):
        self.exercises = list(exercises)
        self.user = user or {}
        self.save_progress_cb = save_progress
        self.progress_file = Path(progress_file)
        self.total = len(self.exercises)
        self.index = 0
        self.started_at = None
        self.elapsed_before_pause = 0
        self.paused_at = None
        self._picked = {}
        self._pronounced = set()
        self._hint_hidden = {}
        self._errors = 0
        self._skips = 0
        self.xp = int(self.user.get("xp", 0))
        self.xp_earned = 0
        self.completed = set(self.user.get("completed", []))
        self.has_progress = False
        self._load_progress()

    # helpers
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

    def format_time(self, seconds):
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def time_now(self):
        if self.started_at is None:
            return self.elapsed_before_pause
        return self.elapsed_before_pause + int(time.time() - self.started_at)

    # lifecycle
    def start(self):
        self.index = 0
        self.started_at = time.time()
        self.elapsed_before_pause = 0
        self.paused_at = None
        self._picked = {}
        self._pronounced = set()
        self._hint_hidden = {}
        self._errors = 0
        self._skips = 0
        self.xp_earned = 0
        self.has_progress = False
        self._delete_progress_file()

    def pause(self):
        if self.started_at is not None:
            self.elapsed_before_pause = self.time_now()
            self.started_at = None
        self._save_progress_file()
        self.has_progress = True

    def resume(self):
        if self.started_at is None:
            self.started_at = time.time()

    def finish_early(self):
        self.pause()

    # exercise actions
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
            return "correct"
        self._errors += 1
        return "wrong"

    def use_hint(self):
        ex = self.current
        key = self.key_for(ex)
        if key in self._hint_hidden or self.is_solved(ex):
            return False
        for opt in ex.get("options", []):
            if opt != ex.get("answer"):
                self._hint_hidden[key] = opt
                return True
        return False

    def mark_pronounced(self, ex=None):
        self._pronounced.add(self.key_for(ex))
        self._save_user_progress()

    def skip(self):
        self._skips += 1
        return self.advance(force=True)

    def advance(self, force=False):
        if not force and not self.can_continue(self.current):
            return "blocked"
        if self.is_last:
            self._delete_progress_file()
            self.has_progress = False
            return "finished"
        self.index += 1
        self._save_progress_file()
        self.has_progress = True
        return "next"

    def summary(self):
        return {
            "time": self.format_time(self.time_now()),
            "completed": len([ex for ex in self.exercises if self.key_for(ex) in self.completed]),
            "total": self.total,
            "errors": self._errors,
            "skips": self._skips,
            "xp_earned": self.xp_earned,
            "xp_total": self.xp,
        }

    def _save_user_progress(self):
        if callable(self.save_progress_cb):
            try:
                self.save_progress_cb(self.user, self.xp, list(self.completed))
            except Exception:
                pass

    def _load_progress(self):
        if not self.progress_file.exists():
            return
        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            self.index = int(data.get("index", 0))
            self.elapsed_before_pause = int(data.get("elapsed_before_pause", 0))
            self._picked = dict(data.get("picked", {}))
            self._pronounced = set(data.get("pronounced", []))
            self._hint_hidden = dict(data.get("hint_hidden", {}))
            self._errors = int(data.get("errors", 0))
            self._skips = int(data.get("skips", 0))
            self.xp = int(data.get("xp", self.xp))
            self.xp_earned = int(data.get("xp_earned", 0))
            self.completed = set(data.get("completed", list(self.completed)))
            self.has_progress = True
        except Exception:
            self.has_progress = False

    def _save_progress_file(self):
        try:
            payload = {
                "index": self.index,
                "elapsed_before_pause": self.time_now(),
                "picked": self._picked,
                "pronounced": list(self._pronounced),
                "hint_hidden": self._hint_hidden,
                "errors": self._errors,
                "skips": self._skips,
                "xp": self.xp,
                "xp_earned": self.xp_earned,
                "completed": list(self.completed),
            }
            self.progress_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _delete_progress_file(self):
        try:
            self.progress_file.unlink(missing_ok=True)
        except Exception:
            pass
