from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_screen import ExerciseScreen
from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_CREAM,
    EXERCISE_SOFT_BLUE,
)
from ..components.exercise_buttons import menu_button


def pause_overlay(
    *,
    question_text: str,
    time_text: str,
    on_resume: Callable | None = None,
    on_finish: Callable | None = None,
    on_save_exit: Callable | None = None,
    width: float = 440,
    height: float = 844,
) -> ft.Control:
    """Pantalla de pausa completa (mismo fondo de nubes que el ejercicio).

    Solo UI: la vista ejecuta reanudar, finalizar y guardar.
    ``question_text`` p. ej. ``"Question 3 / 16"``."""
    card = ft.Container(
        bgcolor=EXERCISE_CREAM,
        padding=26,
        border_radius=30,
        shadow=exercise_shadow(0.09, 15, 3),
        content=ft.Column(
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=EXERCISE_BLUE, size=82),
                exercise_text("Paused", 32, bold=True),
                exercise_text(question_text, 18, EXERCISE_SOFT_BLUE),
                exercise_text(f"Time {time_text}", 18, EXERCISE_SOFT_BLUE),
                menu_button("Resume", on_resume, primary=True),
                menu_button("Finish now", on_finish),
                menu_button("Save & exit", on_save_exit),
            ],
        ),
    )
    body = ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[card],
    )
    return ExerciseScreen(body, width=width, height=height)
