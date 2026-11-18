from collections.abc import Callable
import flet as ft

from .exercise_common import exercise_text
from ..components.exercise_badge import exercise_badge
from ..components.exercise_timer import exercise_timer
from ..components.exercise_counter import exercise_counter

BADGE_IMAGE_SIZE = 44  # tamano de la imagen del badge (a escala 1.0)


def header_scale(width: float) -> float:
    return min(1.0, (width - 24) / 440)


def header_height(width: float) -> float:
    return 53 * header_scale(width)


def _badge_image(src: str, scale: float) -> ft.Control:
    size = BADGE_IMAGE_SIZE * scale
    return ft.Container(
        width=size,
        height=size,
        alignment=ft.Alignment.CENTER,
        content=ft.Image(
            src=src,
            width=size,
            height=size,
            fit=ft.BoxFit.CONTAIN,
        ),
    )


def ExerciseHeader(
    title: str,
    *,
    width: float,
    current: int,
    total: int,
    timer_label: ft.Text,
    on_pause: Callable | None = None,
    badge_letter: str | None = None,
    badge_image: str | None = None,
    title_size: float = 17,
) -> ft.Control:
    """Una sola fila: badge + titulo a la izquierda, tiempo + progreso a la derecha.

    Si se pasa ``badge_image`` se muestra esa imagen en lugar de la letra.
    """
    scale = header_scale(width)

    if badge_image:
        badge = _badge_image(badge_image, scale)
    else:
        badge = exercise_badge(badge_letter or "A", scale)

    brand = ft.Row(
        tight=True,
        spacing=7 * scale,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            badge,
            exercise_text(title, title_size * scale, bold=True, italic=True, max_lines=1),
        ],
    )
    pills = ft.Row(
        tight=True,
        spacing=5 * scale,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            exercise_timer(timer_label, scale=scale, on_click=on_pause),
            exercise_counter(current, total, scale=scale),
        ],
    )
    return ft.Container(
        height=header_height(width),
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=5 * scale,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[brand, pills],
        ),
    )