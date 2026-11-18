from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow
from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_BORDER_BLUE,
    EXERCISE_FONT,
    EXERCISE_GREEN,
    EXERCISE_LOCKED_FG,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
)


def exercise_text_input(
    value: str = "",
    *,
    hint_text: str = "",
    on_change: Callable | None = None,
    on_submit: Callable | None = None,
    read_only: bool = False,
    correct: bool = False,
    lines: int = 2,
    scale: float = 1.0,
) -> ft.Container:
    """Campo de respuesta escrita. Borde azul; verde cuando ya es correcta."""
    field = ft.TextField(
        value=value,
        hint_text=hint_text,
        hint_style=ft.TextStyle(size=13 * scale, color=EXERCISE_LOCKED_FG),
        text_size=17 * scale,
        text_style=ft.TextStyle(
            color=EXERCISE_NAVY,
            weight=ft.FontWeight.W_500,
            font_family=EXERCISE_FONT,
        ),
        cursor_color=EXERCISE_BLUE,
        border=ft.NoInputBorder(),
        bgcolor=ft.Colors.TRANSPARENT,
        multiline=True,
        min_lines=lines,
        max_lines=lines,
        read_only=read_only,
        on_change=on_change,
        on_submit=on_submit,
        shift_enter=True,
    )
    return ft.Container(
        border_radius=18 * scale,
        border=ft.Border.all(
            max(1, 2 * scale), EXERCISE_GREEN if correct else EXERCISE_BORDER_BLUE
        ),
        bgcolor=EXERCISE_WHITE,
        padding=ft.Padding.symmetric(horizontal=6 * scale),
        shadow=exercise_shadow(0.08, 7 * scale, 2 * scale),
        content=field,
    )
