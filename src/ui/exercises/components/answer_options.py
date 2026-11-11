
"""Opciones visuales reutilizables."""

from collections.abc import Callable
from typing import Any
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_NAVY as NAVY,
    EXERCISE_WHITE as WHITE,
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
) -> list[ft.Control]:

    result = []

    for option in options:
        correct = option == picked == answer
        wrong = option == picked and not correct
        excluded = option == eliminated and option != picked

        accent = (
            GREEN if correct
            else RED if wrong
            else "#E9EDF4" if excluded
            else "#A6CFFF"
        )

        bg = (
            "#E9F8ED" if correct
            else "#FFF0F0" if wrong
            else "#F4F5F8" if excluded
            else WHITE
        )

        fg = (
            GREEN if correct
            else RED if wrong
            else "#8A97B0" if excluded
            else NAVY
        )

        async def choose(e, value=option):
            await on_choose(value)

        result.append(
            ft.Container(
                height=49 * scale,
                bgcolor=bg,
                border=ft.Border.all(
                    max(1, 2 * scale),
                    accent,
                ),
                border_radius=17 * scale,
                padding=ft.Padding.symmetric(
                    horizontal=12 * scale,
                ),
                ink=not (excluded or solved),
                on_click=(
                    None
                    if excluded or solved
                    else choose
                ),
                content=ft.Row(
                    spacing=12 * scale,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            (
                                ft.Icons.CHECK_CIRCLE
                                if correct
                                else ft.Icons.CANCEL
                                if wrong
                                else ft.Icons.RADIO_BUTTON_UNCHECKED
                            ),
                            size=25 * scale,
                            color=(
                                accent
                                if correct or wrong
                                else "#9EADD0"
                            ),
                        ),
                        ft.Text(
                            option,
                            expand=True,
                            size=19 * scale,
                            color=fg,
                            weight=ft.FontWeight.BOLD,
                            max_lines=1,
                        ),
                    ],
                ),
            )
        )

    return result
