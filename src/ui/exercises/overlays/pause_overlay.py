from collections.abc import Callable
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
    EXERCISE_CREAM,
)


from ..components.exercise_buttons import _build_button


def pause_overlay(
    on_resume: Callable | None = None,
    on_finish: Callable | None = None,
    on_save_exit: Callable | None = None,
    visible: bool = True,
) -> ft.Container:
    """Solo UI: la vista ejecuta reanudar, finalizar y guardar."""
    return ft.Container(
        left=0,
        right=0,
        top=0,
        bottom=0,
        visible=visible,
        bgcolor="#990F172A",
        alignment=ft.Alignment.CENTER,
        content=ft.Container(
            width=320,
            bgcolor=EXERCISE_CREAM,
            border_radius=24,
            padding=24,
            content=ft.Column(
                tight=True,
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE, size=54, color=EXERCISE_BLUE),
                    ft.Text("Practice paused", size=23, weight=ft.FontWeight.BOLD, color=EXERCISE_NAVY),
                    ft.Text("What would you like to do?", size=13, color=EXERCISE_NAVY),
                    ft.Container(height=4),
                    _build_button("Resume", ft.Icons.PLAY_ARROW, on_resume, bgcolor=EXERCISE_BLUE, color=EXERCISE_WHITE, width=222, height=50, disabled=on_resume is None),
                    _build_button("Finish now", ft.Icons.FLAG_OUTLINED, on_finish, width=222, height=50, disabled=on_finish is None),
                    _build_button("Save & Exit", ft.Icons.SAVE_OUTLINED, on_save_exit, width=222, height=50, disabled=on_save_exit is None),
                ],
            ),
        ),
    )
