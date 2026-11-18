import flet as ft

from ..core.exercise_common import exercise_text
from ..core.exercise_theme import EXERCISE_HEADING_BG


def exercise_section_heading(title: str, scale: float = 1.0, size: float = 18) -> ft.Container:
    """Barra azul con el tipo de actividad, ej. ``LOOK & CHOOSE``."""
    return ft.Container(
        height=36 * scale,
        bgcolor=EXERCISE_HEADING_BG,
        padding=ft.Padding.symmetric(horizontal=12 * scale),
        border_radius=12 * scale,
        alignment=ft.Alignment.CENTER,
        content=exercise_text(title, size * scale, bold=True, italic=True, max_lines=1),
    )
