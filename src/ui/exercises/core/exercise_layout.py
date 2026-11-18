from collections.abc import Callable
import flet as ft

from .exercise_common import exercise_text
from .exercise_header import ExerciseHeader, header_height
from .exercise_screen import ExerciseScreen
from .exercise_sheet import ExerciseSheet
from .exercise_theme import (
    EXERCISE_NAVY,
    EXERCISE_SOFT_BLUE,
    SHEET_ADJUST_X,
    SHEET_ADJUST_Y,
    SHEET_HEIGHT,
    SHEET_MAX_HEIGHT,
    SHEET_VERTICAL_RESERVE,
    SHEET_WIDTH,
)
from ..components.exercise_buttons import continue_button, hint_button, skip_button
from ..components.exercise_feedback import exercise_feedback
from ..components.exercise_heading import exercise_section_heading
from ..components.exercise_illustration import exercise_illustration
from ..components.exercise_microphone import exercise_microphone
from ..components.exercise_timer import exercise_timer_label


def ExerciseLayout(
    *,
    width: float,
    height: float,
    title: str,
    current: int,
    total: int,
    time_text: str,
    section_title: str,
    prompt: str,
    hint_text: str,
    image_src: str,
    answer_builder: Callable[[float], list[ft.Control]],
    feedback: tuple[str, str] | None,
    on_pause: Callable,
    on_hint: Callable,
    on_skip: Callable,
    on_microphone: Callable,
    on_continue: Callable,
    hint_enabled: bool,
    can_continue: bool,
    is_last: bool,
    recording: bool = False,
    processing: bool = False,
    badge_letter: str | None = None,
    badge_image: str | None = None,
) -> tuple[ft.Control, ft.Text]:
    """Devuelve ``(pantalla, timer_label)``.

    ``timer_label`` es el ft.Text del cronometro: la vista cambia su ``.value``
    cada segundo y llama a ``.update()`` sin reconstruir la pantalla.

    ``answer_builder(scale)`` devuelve la lista de controles de respuesta
    (se muestran las 3 primeras). ``feedback`` es ``(mensaje, kind)`` con
    kind en {'success', 'error', 'info'} o None.

    ``badge_image`` es la ruta (relativa a assets) de la imagen que se muestra
    en el badge del header. Si es None se usa ``badge_letter``.
    """
    paper_h = max(
        220,
        min(SHEET_MAX_HEIGHT, height - header_height(width) - SHEET_VERTICAL_RESERVE),
    )
    paper_w = min(width - 24, 480)

    sx = paper_w / SHEET_WIDTH
    sy = paper_h / SHEET_HEIGHT
    scale = min(sx, sy)

    def slot(x, y, w, h, child):
        return ft.Container(
            left=(x + SHEET_ADJUST_X) * sx,
            top=(y + SHEET_ADJUST_Y) * sy,
            width=w * sx,
            height=h * sy,
            alignment=ft.Alignment.CENTER,
            content=child,
        )

    timer_label = exercise_timer_label(time_text, min(1.0, (width - 24) / 440))

    controls = [
        slot(36, 80, 348, 38, exercise_section_heading(section_title, scale)),
        slot(23, 129, 374, 52,
             exercise_text(prompt, 29 * scale, EXERCISE_NAVY, bold=True, max_lines=2)),
        slot(39, 187, 342, 42,
             exercise_text(hint_text, 14 * scale, EXERCISE_SOFT_BLUE, max_lines=2)),
        slot(73, 237, 274, 274, exercise_illustration(image_src, scale=scale)),
    ]

    for i, option_control in enumerate(answer_builder(scale)[:3]):
        controls.append(slot(40, 525 + i * 57, 340, 49, option_control))

    if feedback is not None:
        message, kind = feedback
        controls.append(slot(30, 691, 360, 17, exercise_feedback(message, kind, scale)))

    controls.extend([
        slot(38, 718, 104, 50,
             hint_button(on_hint, disabled=not hint_enabled, scale=scale)),
        slot(177, 710, 66, 66,
             exercise_microphone(on_microphone, recording=recording,
                                 processing=processing, scale=scale)),
        slot(278, 718, 104, 50, skip_button(on_skip, scale=scale)),
        slot(110, 779, 200, 17,
             exercise_text("Listening..." if recording else "Tap to speak",
                           12 * scale, EXERCISE_SOFT_BLUE, bold=True)),
        slot(99, 800, 222, 52,
             continue_button(on_continue, enabled=can_continue,
                             is_last=is_last, scale=scale)),
    ])

    sheet = ExerciseSheet(
        ft.Stack(width=paper_w, height=paper_h, controls=controls),
        width=paper_w,
        height=paper_h,
    )

    body = ft.Column(
        expand=True,
        spacing=5,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ExerciseHeader(
                title,
                width=width,
                current=current,
                total=total,
                timer_label=timer_label,
                on_pause=on_pause,
                badge_letter=badge_letter,
                badge_image=badge_image,
            ),
            sheet,
        ],
    )
    return ExerciseScreen(body, width=width, height=height), timer_label