from collections.abc import Callable
import flet as ft

from ..core.exercise_common import exercise_shadow
from ..core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_LOCKED_BG,
    EXERCISE_LOCKED_FG,
    EXERCISE_RED,
    EXERCISE_WHITE,
)

MICROPHONE_SIZE = 66
PROCESSING_COLOR = "#94A3B8"


def exercise_microphone(
    on_click: Callable | None = None,
    *,
    recording: bool = False,
    processing: bool = False,
    disabled: bool = False,
    scale: float = 1.0,
    size: float = MICROPHONE_SIZE,
) -> ft.Container:
    """Boton de microfono circular (``size`` en unidades de diseno).

    Normal: azul. Grabando: rojo con icono de stop (clicable para parar).
    Procesando: gris (no clicable). Deshabilitado: gris claro bloqueado.
    La logica de audio vive en la vista."""
    icon_color = EXERCISE_WHITE
    if disabled:
        color, icon, tip = EXERCISE_LOCKED_BG, ft.Icons.MIC, "Unavailable"
        icon_color = EXERCISE_LOCKED_FG
    elif processing:
        color, icon, tip = PROCESSING_COLOR, ft.Icons.HOURGLASS_TOP, "Processing..."
    elif recording:
        color, icon, tip = EXERCISE_RED, ft.Icons.STOP, "Tap to stop"
    else:
        color, icon, tip = EXERCISE_BLUE, ft.Icons.MIC, "Speak the answer"

    clickable = not (disabled or processing)
    return ft.Container(
        width=size * scale,
        height=size * scale,
        border_radius=(size / 2 + 1) * scale,
        bgcolor=color,
        border=ft.Border.all(max(2, 5 * scale), "#CFE6FF"),
        shadow=exercise_shadow(0.2, 13 * scale, 4 * scale),
        alignment=ft.Alignment.CENTER,
        ink=clickable,
        on_click=on_click if clickable else None,
        tooltip=tip,
        content=ft.Icon(icon, color=icon_color, size=32 * scale),
    )