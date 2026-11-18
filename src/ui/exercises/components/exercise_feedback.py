import flet as ft

from ..core.exercise_common import exercise_text
from ..core.exercise_theme import (
    EXERCISE_GREEN,
    EXERCISE_RED,
    EXERCISE_SOFT_BLUE,
)

_COLORS = {
    "success": EXERCISE_GREEN,
    "error": EXERCISE_RED,
    "info": EXERCISE_SOFT_BLUE,
}


def exercise_feedback(
    message: str,
    kind: str = "info",
    scale: float = 1.0,
    *,
    max_lines: int = 1,
    bold: bool | None = None,
) -> ft.Text:
    """kind: 'success', 'error' o 'info'. Solo presenta; no evalua respuestas.
    Por defecto es negrita salvo 'info' (pistas), que va normal."""
    if kind not in _COLORS:
        raise ValueError("kind debe ser 'success', 'error' o 'info'")
    if bold is None:
        bold = kind != "info"
    return exercise_text(message, 12 * scale, _COLORS[kind], bold=bold, max_lines=max_lines)
