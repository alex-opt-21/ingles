import flet as ft

from ..core.exercise_common import exercise_text
from ..core.exercise_theme import (
    EXERCISE_NAVY,
    EXERCISE_YELLOW,
    EXERCISE_YELLOW_BG,
)


def exercise_situation_card(text: str, scale: float = 1.0) -> ft.Container:
    """Caja amarilla con la situacion / enunciado (Phrases)."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12 * scale),
        bgcolor=EXERCISE_YELLOW_BG,
        border_radius=16 * scale,
        border=ft.Border.all(max(1, 1.5 * scale), EXERCISE_YELLOW),
        alignment=ft.Alignment.CENTER,
        content=exercise_text(text, 15 * scale, EXERCISE_NAVY, bold=True, max_lines=2),
    )
