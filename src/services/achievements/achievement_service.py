import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ACHIEVEMENTS_FILE = BASE_DIR / "data" / "achievements.json"

MODULES = {"flashcards", "sentences", "questions", "phrases", "songs"}


class AchievementService:
    def __init__(self, user, save_progress):
        self.user = user
        self.save_progress = save_progress  # save_progress(email, dict)

        data = user.get("achievements") or {}
        self.unlocked = set(data.get("unlocked", []))
        self.completed_modules = set(data.get("completed_modules", []))
        self.perfect_practices = int(data.get("perfect_practices", 0))

        self.achievements = self._load_achievements()

    def _load_achievements(self):
        try:
            data = json.loads(ACHIEVEMENTS_FILE.read_text(encoding="utf-8"))
            return data.get("achievements", [])
        except (OSError, ValueError):
            print("No se pudo cargar achievements.json")
            return []

    def _save(self):
        data = {
            "unlocked": sorted(self.unlocked),
            "completed_modules": sorted(self.completed_modules),
            "perfect_practices": self.perfect_practices,
        }
        self.user["achievements"] = data
        email = self.user.get("email")
        if email:
            try:
                self.save_progress(email, {"achievements": data})
            except Exception as err:
                print(f"[!] No se pudieron guardar los logros: {err}")

    def _is_met(self, cond: dict, event: str) -> bool:
        kind = cond.get("type")
        if kind == "practice_started":
            return event == "started"
        if kind == "module_completed":
            return cond.get("module") in self.completed_modules
        if kind == "perfect_practices":
            return self.perfect_practices >= cond.get("target", 0)
        if kind == "all_modules_completed":
            return MODULES.issubset(self.completed_modules)
        if kind == "achievements_unlocked":
            return len(self.unlocked) >= cond.get("target", 0)
        return False

    def _evaluate(self, event: str) -> list[dict]:
        """Desbloquea todo lo que se cumpla. Repite hasta estabilizarse,
        porque un logro nuevo puede disparar 'Collector' o 'Achievement Hunter'."""
        new = []
        changed = True
        while changed:
            changed = False
            for a in self.achievements:
                if a["id"] in self.unlocked:
                    continue
                if self._is_met(a["condition"], event):
                    self.unlocked.add(a["id"])
                    new.append(a)
                    changed = True
        if new:
            self._save()
        return new

    # ---------- API pública ----------

    def practice_started(self) -> list[dict]:
        return self._evaluate("started")

    def practice_completed(self, module: str, perfect: bool = False) -> list[dict]:
        if module not in MODULES:
            return []
        self.completed_modules.add(module)
        if perfect:
            self.perfect_practices += 1
        self._save()  # guarda contadores aunque no haya logros nuevos
        return self._evaluate("completed")