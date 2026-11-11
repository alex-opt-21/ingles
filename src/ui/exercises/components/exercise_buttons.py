
import flet as ft
from collections.abc import Callable

from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
)


def _build_button(
    text: str,
    icon: str,
    on_click: Callable | None = None,
    bgcolor: str = EXERCISE_WHITE,
    color: str = EXERCISE_NAVY,
    width: int | None = None,
    height: int = 44,
    disabled: bool = False,
) -> ft.Button:

    return ft.Button(
        content=text,
        icon=icon,
        on_click=on_click,
        width=width,
        height=height,
        bgcolor=bgcolor,
        color=color,
        disabled=disabled,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=16),
            elevation=2,
            padding=12,
        ),
    )


def hint_button(
    on_click: Callable | None = None,
    disabled: bool = False,
) -> ft.Button:

    return _build_button(
        text="Hint",
        icon=ft.Icons.LIGHTBULB_OUTLINE,
        on_click=on_click,
        disabled=disabled,
    )


def skip_button(
    on_click: Callable | None = None,
    disabled: bool = False,
) -> ft.Button:

    return _build_button(
        text="Skip",
        icon=ft.Icons.SKIP_NEXT,
        on_click=on_click,
        disabled=disabled,
    )


def continue_button(
    on_click: Callable | None = None,
    disabled: bool = False,
) -> ft.Button:

    return _build_button(
        text="Continue",
        icon=ft.Icons.ARROW_FORWARD,
        on_click=on_click,
        bgcolor=EXERCISE_BLUE,
        color=EXERCISE_WHITE,
        height=50,
        disabled=disabled,
    )
