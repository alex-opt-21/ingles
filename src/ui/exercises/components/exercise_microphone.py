
import flet as ft
from collections.abc import Callable

from ..core.exercise_theme import (
    EXERCISE_GREEN,
    EXERCISE_RED,
    EXERCISE_WHITE,
)

MICROPHONE_SIZE = 66
MICROPHONE_ICON_SIZE = 29

PROCESSING_COLOR = "#94A3B8"
DISABLED_COLOR = "#CBD5E1"


def exercise_microphone(
    on_click: Callable | None = None,
    recording: bool = False,
    processing: bool = False,
    disabled: bool = False,
    size: int = MICROPHONE_SIZE,
) -> ft.IconButton:
    """
    Botón de micrófono reutilizable.

    Estados:
    - Normal: verde, listo para grabar.
    - Grabando: rojo, permite detener.
    - Procesando: gris, deshabilitado.
    - Deshabilitado: gris claro.

    La lógica de audio se maneja desde cada vista.
    """

    if disabled:
        bgcolor = DISABLED_COLOR
        icon = ft.Icons.MIC_OFF

    elif processing:
        bgcolor = PROCESSING_COLOR
        icon = ft.Icons.HOURGLASS_TOP

    elif recording:
        bgcolor = EXERCISE_RED
        icon = ft.Icons.STOP

    else:
        bgcolor = EXERCISE_GREEN
        icon = ft.Icons.MIC

    tooltip = (
        "Unavailable" if disabled
        else "Processing..." if processing
        else "Stop recording" if recording
        else "Start recording"
    )

    return ft.IconButton(
        icon=icon,
        icon_color=EXERCISE_WHITE,
        icon_size=MICROPHONE_ICON_SIZE,
        bgcolor=bgcolor,
        width=size,
        height=size,
        padding=0,
        tooltip=tooltip,
        disabled=disabled or processing,
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.CircleBorder(),
            elevation=3,
        ),
    )
