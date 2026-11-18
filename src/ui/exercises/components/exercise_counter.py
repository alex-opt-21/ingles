import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import (
    EXERCISE_NAVY,
    EXERCISE_PALE_BLUE,
    EXERCISE_WHITE,
)


def exercise_counter(
    current: int = 1,
    total: int = 10,
    *,
    scale: float = 1.0,
) -> ft.Container:
    """Progreso del ejercicio, ej. ``1 / 80``."""
    current = max(0, current)
    total = max(0, total)
    return ft.Container(
        height=40 * scale,
        bgcolor=EXERCISE_WHITE,
        border=ft.Border.all(max(1, 2 * scale), EXERCISE_PALE_BLUE),
        border_radius=22 * scale,
        padding=ft.Padding.symmetric(horizontal=10 * scale),
        shadow=exercise_shadow(0.09, 5 * scale, 2 * scale),
        alignment=ft.Alignment.CENTER,
        content=exercise_text(f"{current} / {total}", 15 * scale, EXERCISE_NAVY, bold=True),
    )
