import flet as ft

from .exercise_theme import BACKGROUND_IMAGE


def ExerciseScreen(
    content: ft.Control,
    *,
    width: float,
    height: float,
    padding: ft.Padding | None = None,
) -> ft.Stack:
    """Pantalla completa: fondo de nubes + contenido en area segura.

    La usan el ejercicio, la pausa y los resultados, asi los tres comparten
    exactamente el mismo fondo.
    """
    return ft.Stack(
        width=width,
        height=height,
        controls=[
            ft.Image(
                src=BACKGROUND_IMAGE,
                left=0,
                top=0,
                width=width,
                height=height,
                fit=ft.BoxFit.COVER,
            ),
            ft.Container(
                left=0,
                top=0,
                width=width,
                height=height,
                padding=padding or ft.Padding.symmetric(horizontal=12, vertical=10),
                content=ft.SafeArea(content=content),
            ),
        ],
    )
