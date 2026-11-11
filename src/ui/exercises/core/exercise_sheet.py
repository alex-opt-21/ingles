
import flet as ft

from .exercise_theme import SHEET_IMAGE


def ExerciseSheet(
    content: ft.Control,
    *,
    width: float,
    height: float,
) -> ft.Stack:

    return ft.Stack(
        width=width,
        height=height,
        controls=[
            ft.Image(
                src=SHEET_IMAGE,
                width=width,
                height=height,
                fit=ft.BoxFit.FILL,
            ),
            content,
        ],
    )
