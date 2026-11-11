
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
)


def format_time(seconds: int) -> str:
    """Convierte segundos a formato MM:SS."""
    seconds = max(0, seconds)

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return f"{minutes:02d}:{remaining_seconds:02d}"


def exercise_timer(
    time_text: str = "00:00",
    color: str = EXERCISE_NAVY,
    bgcolor: str = EXERCISE_WHITE,
) -> ft.Container:

    return ft.Container(
        padding=ft.Padding.symmetric(
            horizontal=14,
            vertical=9,
        ),
        bgcolor=bgcolor,
        border_radius=18,
        shadow=ft.BoxShadow(
            blur_radius=5,
            color="#20000000",
            offset=ft.Offset(0, 2),
        ),
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.TIMER_OUTLINED,
                    size=19,
                    color=EXERCISE_BLUE,
                ),
                ft.Text(
                    time_text,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
            ],
            spacing=7,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )
