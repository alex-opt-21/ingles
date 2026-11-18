
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

    def __init__(
        self,
        exercises,
        user,
        save_progress=None,
        save_session=None,
        clear_session=None,
        session_size=None,
        module_id="sentences",
        lesson_id="sentence_practice",
        level_id="basic",
    ):
        super().__init__(
            exercises=exercises,
            user=user,
            save_progress=save_progress,
            save_session=save_session,
            clear_session=clear_session,
            session_size=session_size,
            module_id=module_id,
            lesson_id=lesson_id,
            level_id=level_id,
        )

    def summary(self):
        return super().summary()
