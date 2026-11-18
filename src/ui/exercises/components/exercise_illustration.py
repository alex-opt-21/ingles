import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import EXERCISE_PALE_BLUE, EXERCISE_SOFT_BLUE

ILLUSTRATION_SIZE = 274


def exercise_illustration(
    src: str | None = None,
    *,
    scale: float = 1.0,
    size: float = ILLUSTRATION_SIZE,
    description: str = "Illustration",
) -> ft.Container:
    """La vista elige la imagen; este componente solo la presenta.
    ``size`` (unidades de diseno) permite marcos mas pequenos que 274."""
    scale = scale * size / ILLUSTRATION_SIZE
    fallback = exercise_text("Image not available", 14 * scale, EXERCISE_SOFT_BLUE)

    content: ft.Control = (
        ft.Image(
            src=src,
            width=254 * scale,
            height=254 * scale,
            fit=ft.BoxFit.CONTAIN,
            error_content=fallback,
            semantics_label=description,
        )
        if src
        else fallback
    )

    return ft.Container(
        width=ILLUSTRATION_SIZE * scale,
        height=ILLUSTRATION_SIZE * scale,
        padding=9 * scale,
        border_radius=34 * scale,
        bgcolor="#FFFDF8",
        border=ft.Border.all(max(1, 2 * scale), "#F0E9E0"),
        shadow=exercise_shadow(0.07, 9 * scale, 3 * scale),
        content=ft.Container(
            border_radius=25 * scale,
            bgcolor=EXERCISE_PALE_BLUE,
            alignment=ft.Alignment.CENTER,
            content=content,
        ),
    )
