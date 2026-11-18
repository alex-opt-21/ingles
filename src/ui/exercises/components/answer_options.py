from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import (
    EXERCISE_BORDER_BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_LOCKED_FG,
    EXERCISE_NAVY as NAVY,
    EXERCISE_RED as RED,
    EXERCISE_SILVER,
    EXERCISE_WHITE as WHITE,
)


@dataclass(frozen=True)
class OptionStyle:
    height: float = 49
    radius: float = 17
    font_size: float = 20
    italic: bool = True
    max_lines: int = 1
    border_width: float = 2
    marker_size: float = 25
    gap: float = 12
    padding_x: float = 12
    hide_eliminated_text: bool = False


QUIZ_OPTIONS = OptionStyle()
PHRASES_OPTIONS = OptionStyle(font_size=15.5, italic=False, max_lines=2,
                              gap=9, hide_eliminated_text=True)
QUESTIONS_OPTIONS = OptionStyle(height=52, radius=24, font_size=18, max_lines=2,
                                border_width=1.7, marker_size=26, gap=11,
                                padding_x=14)


def answer_option(
    option: str,
    *,
    answer: str,
    picked: str | None,
    eliminated: str | None,
    solved: bool,
    on_choose: Callable[[str], Any],
    scale: float = 1.0,
    style: OptionStyle = QUIZ_OPTIONS,
    disabled: bool = False,
) -> ft.Container:
    selected = picked == option
    correct = selected and option == answer
    wrong = selected and not correct
    excluded = eliminated == option and not selected

    border = GREEN if correct else RED if wrong else EXERCISE_SILVER if excluded else EXERCISE_BORDER_BLUE
    bg = "#E9F8ED" if correct else "#FFF0F0" if wrong else "#F4F5F8" if excluded else WHITE
    fg = GREEN if correct else RED if wrong else EXERCISE_LOCKED_FG if excluded else NAVY
    locked = excluded or solved or disabled
    m = style.marker_size * scale

    async def choose(e):
        await on_choose(option)

    marker = ft.Container(
        width=m,
        height=m,
        border_radius=m / 2 + 0.5 * scale,
        alignment=ft.Alignment.CENTER,
        border=ft.Border.all(
            max(1, 2 * scale), GREEN if correct else RED if wrong else "#9EADD0"
        ),
        bgcolor=GREEN if correct else RED if wrong else WHITE,
        content=(
            ft.Icon(
                ft.Icons.CHECK if correct else ft.Icons.CLOSE,
                size=17 * scale,
                color=WHITE,
            )
            if selected
            else None
        ),
    )

    return ft.Container(
        height=style.height * scale,
        bgcolor=bg,
        border=ft.Border.all(max(1, style.border_width * scale), border),
        border_radius=style.radius * scale,
        padding=ft.Padding.symmetric(horizontal=style.padding_x * scale),
        shadow=exercise_shadow(0.06, 6 * scale, 2 * scale),
        ink=not locked,
        on_click=None if locked else choose,
        content=ft.Row(
            spacing=style.gap * scale,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                marker,
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER_LEFT,
                    content=exercise_text(
                        "" if (excluded and style.hide_eliminated_text) else option,
                        style.font_size * scale, fg,
                        bold=True, italic=style.italic,
                        align=ft.TextAlign.LEFT, max_lines=style.max_lines,
                    ),
                ),
            ],
        ),
    )


def answer_options(
    options: list[str],
    *,
    answer: str,
    picked: str | None,
    eliminated: str | None,
    solved: bool,
    on_choose: Callable[[str], Any],
    scale: float = 1.0,
    style: OptionStyle = QUIZ_OPTIONS,
    disabled: bool = False,
) -> list[ft.Control]:
    return [
        answer_option(
            option,
            answer=answer,
            picked=picked,
            eliminated=eliminated,
            solved=solved,
            on_choose=on_choose,
            scale=scale,
            style=style,
            disabled=disabled,
        )
        for option in options
    ]
