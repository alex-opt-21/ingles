from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_CREAM,
    EXERCISE_PALE_BLUE,
    EXERCISE_SOFT_BLUE,
    EXERCISE_WHITE,
)

# Tamanos de la capa de pausa (ajusta aqui si quieres mas grande o pequeno)
CARD_MAX_WIDTH = 280
BUTTON_HEIGHT = 42
BUTTON_FONT = 15
TITLE_FONT = 22
INFO_FONT = 13
ICON_SIZE = 46


def _pause_button(label: str, on_click: Callable | None, primary: bool = False) -> ft.Container:
    """Boton compacto, mismo estilo que menu_button pero mas pequeno."""
    return ft.Container(
        height=BUTTON_HEIGHT,
        border_radius=BUTTON_HEIGHT / 2,
        bgcolor=EXERCISE_BLUE if primary else EXERCISE_WHITE,
        border=None if primary else ft.Border.all(2, EXERCISE_PALE_BLUE),
        alignment=ft.Alignment.CENTER,
        ink=on_click is not None,
        on_click=on_click,
        content=exercise_text(
            label,
            BUTTON_FONT,
            EXERCISE_WHITE if primary else EXERCISE_BLUE,
            bold=True,
        ),
    )


def pause_overlay(
    *,
    question_text: str,
    time_text: str,
    on_resume: Callable | None = None,
    on_finish: Callable | None = None,
    on_save_exit: Callable | None = None,
    width: float = 440,
    height: float = 844,
) -> ft.Control:
    """Capa de pausa que se dibuja ENCIMA del ejercicio.

    La vista la coloca dentro de un ft.Stack, encima de la pantalla del
    ejercicio. Tiene un fondo oscuro semitransparente (se ve el ejercicio
    detras) y la tarjeta de pausa centrada. Ocupa todo el espacio del Stack.

    Solo UI: la vista ejecuta reanudar, finalizar y guardar.
    ``question_text`` p. ej. ``"Question 3 / 16"``.
    """
    card = ft.Container(
        width=max(230, min(width - 72, CARD_MAX_WIDTH)),
        bgcolor=EXERCISE_CREAM,
        padding=20,
        border_radius=24,
        shadow=exercise_shadow(0.09, 15, 3),
        content=ft.Column(
            tight=True,
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=EXERCISE_BLUE, size=ICON_SIZE),
                exercise_text("Paused", TITLE_FONT, bold=True),
                exercise_text(question_text, INFO_FONT, EXERCISE_SOFT_BLUE),
                exercise_text(f"Time {time_text}", INFO_FONT, EXERCISE_SOFT_BLUE),
                ft.Container(height=2),
                _pause_button("Resume", on_resume, primary=True),
                _pause_button("Finish now", on_finish),
                _pause_button("Save & exit", on_save_exit),
            ],
        ),
    )
    return ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
        alignment=ft.Alignment.CENTER,
        on_click=lambda e: None,  # bloquea los toques al ejercicio de abajo
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[card],
        ),
    )