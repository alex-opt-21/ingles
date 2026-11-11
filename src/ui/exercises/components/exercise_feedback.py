"""Feedback visual común a Quiz, Sentences, Questions y Phrases."""
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_GREEN,
    EXERCISE_RED,
    EXERCISE_BLUE,
    EXERCISE_NAVY,
)


def exercise_feedback(
    message: str,
    kind: str = "info",
    visible: bool = True,
    width: int = 330,
) -> ft.Container:
    """kind: 'success', 'error' o 'info'. No evalúa respuestas."""
    styles = {
        "success": (EXERCISE_GREEN, "#EBF8F1", ft.Icons.CHECK_CIRCLE_OUTLINE),
        "error": (EXERCISE_RED, "#FFF0F0", ft.Icons.ERROR_OUTLINE),
        "info": (EXERCISE_BLUE, "#EAF3FF", ft.Icons.INFO_OUTLINE),
    }
    if kind not in styles:
        raise ValueError("kind debe ser 'success', 'error' o 'info'")

    accent, background, icon = styles[kind]
    return ft.Container(
        width=width,
        visible=visible,
        padding=12,
        bgcolor=background,
        border=ft.Border.all(1, accent),
        border_radius=14,
        content=ft.Row(
            controls=[
                ft.Icon(icon, color=accent, size=22),
                ft.Text(message, color=EXERCISE_NAVY, size=14, expand=True),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
