from collections.abc import Callable, Sequence
import flet as ft

from ..core.exercise_common import exercise_text
from ..core.exercise_theme import (
    EXERCISE_CREAM,
    EXERCISE_GREEN,
    EXERCISE_NAVY,
    EXERCISE_PALE_BLUE,
    EXERCISE_SOFT_BLUE,
    EXERCISE_WHITE,
)
from ..components.exercise_buttons import menu_button

# (icono, etiqueta, valor, color)
Stat = tuple[str, str, str, str]
# (etiqueta, valor) o (etiqueta, valor, color)
Detail = tuple


def _stat_card(icon: str, label: str, value: str, color: str) -> ft.Container:
    return ft.Container(
        expand=True,
        bgcolor=EXERCISE_WHITE,
        border=ft.Border.all(1, EXERCISE_PALE_BLUE),
        border_radius=18,
        padding=12,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Icon(icon, color=color, size=29),
                exercise_text(value, 23, EXERCISE_NAVY, bold=True),
                exercise_text(label, 12, EXERCISE_SOFT_BLUE),
            ],
        ),
    )


def _detail_row(label: str, value: str, color: str = EXERCISE_NAVY) -> ft.Row:
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            exercise_text(label, 16, EXERCISE_NAVY, bold=True),
            exercise_text(value, 16, color, bold=True),
        ],
    )


def _achievement_row(name: str, description: str) -> ft.Row:
    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.EMOJI_EVENTS, color=EXERCISE_GREEN, size=28),
            ft.Column(
                expand=True,
                spacing=1,
                controls=[
                    exercise_text(name, 15, EXERCISE_NAVY, bold=True),
                    exercise_text(description, 12, EXERCISE_SOFT_BLUE, max_lines=2),
                ],
            ),
        ],
    )


def results_screen(
    *,
    stats: Sequence[Stat],
    details: Sequence[Detail] = (),
    achievements: Sequence[dict] = (),
    title: str = "Practice Completed!",
    subtitle: str = "Great job! You finished your practice.",
    retry_label: str = "Practice Again",
    exit_label: str = "Back to Home",
    on_retry: Callable | None = None,
    on_exit: Callable | None = None,
    width: float = 440,
    height: float = 844,
) -> ft.Control:
    """Pantalla final a pantalla completa. Cada ejercicio decide QUE mostrar:

    stats        -> tarjetas con icono, de dos en dos (cuadricula)
    details      -> lineas "etiqueta ........ valor" dentro de una tarjeta blanca
    achievements -> lista de dicts {"name", "description"} recien desbloqueados

    La tarjeta crema se expande para ocupar todo el espacio disponible y el
    contenido queda centrado verticalmente (con scroll si no cabe).
    """
    rows = [
        ft.Row(spacing=10, controls=[_stat_card(*s) for s in stats[i:i + 2]])
        for i in range(0, len(stats), 2)
    ]

    controls: list[ft.Control] = [
        ft.Icon(ft.Icons.EMOJI_EVENTS, color=EXERCISE_GREEN, size=72),
        exercise_text(title, 27, bold=True),
        exercise_text(subtitle, 15, EXERCISE_SOFT_BLUE, max_lines=2),
        *rows,
    ]

    if details:
        controls.append(
            ft.Container(
                padding=15,
                bgcolor=EXERCISE_WHITE,
                border_radius=18,
                content=ft.Column(
                    spacing=13,
                    controls=[_detail_row(*d) for d in details],
                ),
            )
        )

    if achievements:
        controls.append(
            ft.Container(
                padding=15,
                bgcolor=EXERCISE_WHITE,
                border=ft.Border.all(1.5, EXERCISE_GREEN),
                border_radius=18,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        exercise_text(
                            "Achievement unlocked!"
                            if len(achievements) == 1
                            else "Achievements unlocked!",
                            16, EXERCISE_GREEN, bold=True,
                        ),
                        *[
                            _achievement_row(a["name"], a["description"])
                            for a in achievements
                        ],
                    ],
                ),
            )
        )

    controls.append(menu_button(retry_label, on_retry, primary=True))
    controls.append(menu_button(exit_label, on_exit))

    # Pantalla completa: sin ExerciseScreen (no hay marco ni fondo de nubes),
    # el color crema cubre toda la ventana de borde a borde.
    return ft.Container(
        expand=True,
        width=width,
        height=height,
        bgcolor=EXERCISE_CREAM,
        padding=ft.Padding.only(left=22, right=22, top=24, bottom=16),
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=controls,
        ),
    )