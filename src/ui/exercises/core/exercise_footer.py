from collections.abc import Callable
from dataclasses import dataclass
import flet as ft

from .exercise_common import exercise_text
from .exercise_frame import SlotFn
from .exercise_theme import EXERCISE_SOFT_BLUE
from ..components.exercise_buttons import continue_button, hint_button, skip_button
from ..components.exercise_microphone import exercise_microphone

Box = tuple[float, float, float, float]  # x, y, ancho, alto (unidades de diseno)


@dataclass(frozen=True)
class FooterPositions:
    hint: Box
    mic: Box
    skip: Box
    caption: Box
    cont: Box


# Hoja con imagen grande (Quiz)
QUIZ_FOOTER = FooterPositions(
    hint=(38, 718, 104, 50),
    mic=(177, 710, 66, 66),
    skip=(278, 718, 104, 50),
    caption=(110, 779, 200, 17),
    cont=(99, 800, 222, 52),
)

# Questions: microfono mas grande (72) y botones un pelo mas abajo
QUESTIONS_FOOTER = FooterPositions(
    hint=(40, 734, 105, 51),
    mic=(174, 722, 72, 72),
    skip=(275, 734, 105, 51),
    caption=(120, 795, 180, 16),
    cont=(99, 810, 222, 48),
)

# Hoja con campo de texto (Sentences)
SENTENCE_FOOTER = FooterPositions(
    hint=(38, 738, 104, 50),
    mic=(179, 730, 62, 62),
    skip=(278, 738, 104, 50),
    caption=(83, 796, 254, 19),
    cont=(99, 816, 222, 47),
)


def footer_slots(
    slot: SlotFn,
    scale: float,
    pos: FooterPositions,
    *,
    on_hint: Callable | None,
    on_skip: Callable | None,
    on_mic: Callable | None,
    on_continue: Callable | None,
    hint_enabled: bool = True,
    skip_enabled: bool = True,
    mic_disabled: bool = False,
    recording: bool = False,
    processing: bool = False,
    caption: str = "",
    caption_color: str = EXERCISE_SOFT_BLUE,
    can_continue: bool = False,
    is_last: bool = False,
) -> list[ft.Control]:
    return [
        slot(*pos.hint,
             hint_button(on_hint, disabled=not hint_enabled, scale=scale)),
        slot(*pos.mic,
             exercise_microphone(on_mic, recording=recording, processing=processing,
                                 disabled=mic_disabled, scale=scale, size=pos.mic[2])),
        slot(*pos.skip,
             skip_button(on_skip, disabled=not skip_enabled, scale=scale)),
        slot(*pos.caption,
             exercise_text(caption, 12 * scale, caption_color, bold=True, max_lines=1)),
        slot(*pos.cont,
             continue_button(on_continue, enabled=can_continue, is_last=is_last,
                             scale=scale, height=pos.cont[3])),
    ]
