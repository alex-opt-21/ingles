import flet as ft

from .exercise_theme import SHEET_IMAGE


def ExerciseSheet(
    content: ft.Control,
    *,
    width: float,
    height: float,
) -> ft.Stack:
    """Hoja de papel (imagen) con los controles reales colocados encima."""
    return ft.Stack(
        width=width,
        height=height,
        controls=[
            ft.Image(
                src=SHEET_IMAGE,
                left=0,
                top=0,
                width=width,
                height=height,
                fit=ft.BoxFit.FILL,
            ),
            content,
        ],
    )
