import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import EXERCISE_BLUE, EXERCISE_WHITE


def exercise_badge(letter: str = "A", scale: float = 1.0) -> ft.Container:
    """Cuadro azul con la inicial del ejercicio (esquina superior izquierda)."""
    return ft.Container(
        width=46 * scale,
        height=48 * scale,
        bgcolor=EXERCISE_BLUE,
        border_radius=15 * scale,
        border=ft.Border.all(max(1, 2 * scale), EXERCISE_WHITE),
        shadow=exercise_shadow(0.2, 7 * scale, 3 * scale),
        alignment=ft.Alignment.CENTER,
        content=exercise_text(
            letter.upper(), 29 * scale, EXERCISE_WHITE, bold=True, italic=True
        ),
    )
