import flet as ft

from .exercise_theme import EXERCISE_FONT, EXERCISE_NAVY


def exercise_shadow(opacity: float = 0.09, blur: float = 12, y: float = 3) -> ft.BoxShadow:
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(opacity, "#153C81"),
        blur_radius=blur,
        offset=ft.Offset(0, y),
    )


def exercise_text(
    value,
    size: float = 16,
    color: str = EXERCISE_NAVY,
    *,
    bold: bool = False,
    italic: bool = False,
    align: ft.TextAlign = ft.TextAlign.CENTER,
    max_lines: int | None = None,
) -> ft.Text:
    """Texto con la fuente y estilo del tema (todos los textos deben pasar por aqui)."""
    return ft.Text(
        str(value),
        size=size,
        color=color,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
        italic=italic,
        font_family=EXERCISE_FONT,
        text_align=align,
        max_lines=max_lines,
    )
