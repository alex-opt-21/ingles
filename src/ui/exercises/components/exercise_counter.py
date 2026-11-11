import flet as ft

from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
)


def exercise_counter(
    current: int = 1,
    total: int = 10,
) -> ft.Container:
    """
    Muestra el progreso del ejercicio.
    Ejemplo: 03 / 10
    """

    current = max(0, current)
    total = max(0, total)

    return ft.Container(
        padding=ft.Padding.symmetric(
            horizontal=14,
            vertical=9,
        ),
        bgcolor=EXERCISE_WHITE,
        border_radius=16,
        shadow=ft.BoxShadow(
            blur_radius=5,
            color="#20000000",
            offset=ft.Offset(0, 2),
        ),
        content=ft.Row(
            controls=[
                ft.Text(
                    f"{current:02d}",
                    size=17,
                    weight=ft.FontWeight.BOLD,
                    color=EXERCISE_BLUE,
                ),
                ft.Text(
                    "/",
                    size=14,
                    color="#9CA3AF",
                ),
                ft.Text(
                    f"{total:02d}",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=EXERCISE_NAVY,
                ),
            ],
            spacing=5,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )