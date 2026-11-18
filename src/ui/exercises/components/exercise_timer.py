from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_PALE_BLUE,
    EXERCISE_WHITE,
)


def format_time(seconds: int) -> str:
    """Convierte segundos a formato MM:SS."""
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def exercise_timer_label(time_text: str = "00:00", scale: float = 1.0) -> ft.Text:
    """El Text que muestra la hora. La vista lo conserva y cambia ``.value``
    cada segundo sin tener que reconstruir toda la pantalla."""
    return exercise_text(time_text, 15 * scale, EXERCISE_NAVY, bold=True)


def exercise_timer(
    label: ft.Text,
    *,
    scale: float = 1.0,
    on_click: Callable | None = None,
) -> ft.Container:
    """Pill de tiempo. Al pulsarla se pausa la practica."""
    return ft.Container(
        height=40 * scale,
        bgcolor=EXERCISE_WHITE,
        border=ft.Border.all(max(1, 2 * scale), EXERCISE_PALE_BLUE),
        border_radius=22 * scale,
        padding=ft.Padding.symmetric(horizontal=8 * scale),
        shadow=exercise_shadow(0.09, 5 * scale, 2 * scale),
        ink=on_click is not None,
        on_click=on_click,
        tooltip="Pause practice" if on_click else None,
        content=ft.Row(
            tight=True,
            spacing=3 * scale,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE, size=16 * scale, color=EXERCISE_BLUE),
                label,
            ],
        ),
    )
