from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow, exercise_text
from ..core.exercise_theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_BORDER_BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_LOCKED_BG,
    EXERCISE_LOCKED_FG,
    EXERCISE_SILVER,
    EXERCISE_WHITE as WHITE,
)


def _small_button(
    label: str,
    icon: str,
    *,
    on_click: Callable | None,
    disabled: bool,
    scale: float,
) -> ft.Container:
    enabled = not disabled
    color = BLUE if enabled else EXERCISE_LOCKED_FG
    return ft.Container(
        width=104 * scale,
        height=50 * scale,
        bgcolor=WHITE if enabled else "#F4F6FA",
        border_radius=25 * scale,
        border=ft.Border.all(
            max(1, 1.5 * scale), EXERCISE_BORDER_BLUE if enabled else EXERCISE_SILVER
        ),
        shadow=exercise_shadow(0.08, 7 * scale, 3 * scale),
        ink=enabled,
        on_click=on_click if enabled else None,
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            tight=True,
            spacing=5 * scale,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=17 * scale, color=color),
                exercise_text(label, 17 * scale, color, bold=True),
            ],
        ),
    )


def hint_button(on_click: Callable | None = None, disabled: bool = False,
                scale: float = 1.0) -> ft.Container:
    return _small_button("Hint", ft.Icons.LIGHTBULB_OUTLINE,
                         on_click=on_click, disabled=disabled, scale=scale)


def skip_button(on_click: Callable | None = None, disabled: bool = False,
                scale: float = 1.0) -> ft.Container:
    return _small_button("Skip", ft.Icons.FAST_FORWARD,
                         on_click=on_click, disabled=disabled, scale=scale)


def continue_button(
    on_click: Callable | None = None,
    *,
    enabled: bool = True,
    is_last: bool = False,
    scale: float = 1.0,
    height: float = 52,
) -> ft.Container:
    """Verde cuando se puede avanzar, gris (sin borde verde) cuando no.

    ``on_click`` se mantiene aunque este gris, para que la vista pueda
    explicar por que esta bloqueado (toast)."""
    fg = WHITE if enabled else EXERCISE_LOCKED_FG
    return ft.Container(
        width=222 * scale,
        height=height * scale,
        border_radius=(height / 2 + 2) * scale,
        bgcolor=GREEN if enabled else EXERCISE_LOCKED_BG,
        border=ft.Border.all(
            max(1, 2 * scale), GREEN if enabled else EXERCISE_SILVER
        ),
        shadow=exercise_shadow(0.1, 9 * scale, 3 * scale) if enabled else None,
        ink=enabled,
        on_click=on_click,
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            tight=True,
            spacing=5 * scale,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                exercise_text("Finish" if is_last else "Continue", 20 * scale, fg, bold=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=fg, size=21 * scale),
            ],
        ),
    )


def menu_button(text: str, on_click: Callable | None = None,
                *, primary: bool = False) -> ft.Container:
    """Boton ancho de las pantallas de pausa y resultados."""
    return ft.Container(
        height=55,
        bgcolor=BLUE if primary else WHITE,
        border=ft.Border.all(2, BLUE if primary else EXERCISE_BORDER_BLUE),
        border_radius=24,
        alignment=ft.Alignment.CENTER,
        ink=on_click is not None,
        on_click=on_click,
        shadow=exercise_shadow(0.07, 8, 3),
        content=exercise_text(text, 18, WHITE if primary else BLUE, bold=True),
    )


def action_button(
    label: str,
    icon: str,
    on_click: Callable | None = None,
    *,
    color: str = BLUE,
    scale: float = 1.0,
    width: float = 180,
    height: float = 44,
) -> ft.Container:
    """Boton relleno de una accion principal dentro de la hoja
    (ej. "Check answer" en azul, "Listen again" en verde)."""
    return ft.Container(
        width=width * scale,
        height=height * scale,
        bgcolor=color,
        border_radius=(height / 2 + 1) * scale,
        shadow=exercise_shadow(0.10, 7 * scale, 2 * scale),
        alignment=ft.Alignment.CENTER,
        ink=on_click is not None,
        on_click=on_click,
        content=ft.Row(
            tight=True,
            spacing=6 * scale,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=19 * scale, color=WHITE),
                exercise_text(label, 17 * scale, WHITE, bold=True, max_lines=1),
            ],
        ),
    )