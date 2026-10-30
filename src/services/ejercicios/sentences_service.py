
from pathlib import Path

from services.ejercicios.ejercicio_service import (
    QuizSession,
    load_exercises,
    format_time,
)


def load_sentences(sentences_file: Path, assets_dir: Path = None):
    exercises = load_exercises(sentences_file, assets_dir)

    for exercise in exercises:
        required = ("id", "prompt", "hint", "answer", "options", "image")
        missing = [key for key in required if key not in exercise]

        if missing:
            raise ValueError(
                f"Ejercicio {exercise.get('id', '?')}: "
                f"faltan campos {missing}"
            )

        if len(exercise["options"]) != 3:
            raise ValueError(
                f"El ejercicio {exercise['id']} debe tener 3 opciones"
            )

        if exercise["answer"] not in exercise["options"]:
            raise ValueError(
                f"La respuesta correcta no está entre las opciones: "
                f"{exercise['id']}"
            )

    return exercises


class SentencesSession(QuizSession):
    """Sesión independiente de oraciones con XP compartido."""

    def __init__(self, exercises, user, save_progress=None):
        super().__init__(exercises, user, save_progress)

    def summary(self):
        stats = super().summary()
        stats["sentences"] = stats.pop("verbs")
        return stats
