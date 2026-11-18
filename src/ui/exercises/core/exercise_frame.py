from collections.abc import Callable
import flet as ft

from .exercise_header import ExerciseHeader, header_height, header_scale
from .exercise_screen import ExerciseScreen
from .exercise_sheet import ExerciseSheet
from .exercise_theme import (
    SHEET_ADJUST_X,
    SHEET_ADJUST_Y,
    SHEET_HEIGHT,
    SHEET_MAX_HEIGHT,
    SHEET_VERTICAL_RESERVE,
    SHEET_WIDTH,
)
from ..components.exercise_timer import exercise_timer_label

SlotFn = Callable[[float, float, float, float, ft.Control], ft.Control]
SlotsBuilder = Callable[[SlotFn, float], list[ft.Control]]


def ExerciseFrame(
    *,
    width: float,
    height: float,
    title: str,
    current: int,
    total: int,
    time_text: str,
    on_pause: Callable | None,
    slots: SlotsBuilder,
    badge_letter: str | None = None,
    title_size: float = 17,
    min_sheet_height: float = 220,
) -> tuple[ft.Control, ft.Text]:
    """Devuelve ``(pantalla, timer_label)``.

    ``slots(slot, scale)`` devuelve la lista de controles posicionados sobre
    la hoja. ``timer_label`` es el ft.Text del cronometro: la vista cambia su
    ``.value`` cada segundo y llama ``.update()`` sin reconstruir nada.
    """
    paper_h = max(
        min_sheet_height,
        min(SHEET_MAX_HEIGHT, height - header_height(width) - SHEET_VERTICAL_RESERVE),
    )
    paper_w = min(width - 24, 480)

    sx = paper_w / SHEET_WIDTH
    sy = paper_h / SHEET_HEIGHT
    scale = min(sx, sy)

    def slot(x, y, w, h, child):
        return ft.Container(
            left=(x + SHEET_ADJUST_X) * sx,
            top=(y + SHEET_ADJUST_Y) * sy,
            width=w * sx,
            height=h * sy,
            alignment=ft.Alignment.CENTER,
            content=child,
        )

    timer_label = exercise_timer_label(time_text, header_scale(width))

    sheet = ExerciseSheet(
        ft.Stack(width=paper_w, height=paper_h, controls=slots(slot, scale)),
        width=paper_w,
        height=paper_h,
    )
    body = ft.Column(
        expand=True,
        spacing=5,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ExerciseHeader(
                title,
                width=width,
                current=current,
                total=total,
                timer_label=timer_label,
                on_pause=on_pause,
                badge_letter=badge_letter,
                title_size=title_size,
            ),
            sheet,
        ],
    )
    return ExerciseScreen(body, width=width, height=height), timer_label
