from collections.abc import Callable
from dataclasses import dataclass
import flet as ft

from .exercise_common import exercise_text
from .exercise_footer import (
    QUESTIONS_FOOTER,
    QUIZ_FOOTER,
    Box,
    FooterPositions,
    footer_slots,
)
from .exercise_frame import ExerciseFrame
from .exercise_theme import EXERCISE_NAVY, EXERCISE_SOFT_BLUE
from ..components.answer_options import (
    PHRASES_OPTIONS,
    QUESTIONS_OPTIONS,
    QUIZ_OPTIONS,
    OptionStyle,
)
from ..components.exercise_feedback import exercise_feedback
from ..components.exercise_heading import exercise_section_heading
from ..components.exercise_situation import exercise_situation_card


@dataclass(frozen=True)
class ChoicePreset:
    heading: Box
    title: Box
    subtitle: Box
    media: Box
    options_x: float
    options_y: float
    options_w: float
    options_step: float
    feedback: Box
    footer: FooterPositions
    option_style: OptionStyle
    title_size: float = 29
    subtitle_size: float = 14
    heading_size: float = 18
    header_title_size: float = 17
    min_sheet_height: float = 220
    situation: Box | None = None


QUIZ_PRESET = ChoicePreset(
    heading=(36, 80, 348, 38),
    title=(23, 129, 374, 52),
    subtitle=(39, 187, 342, 42),
    media=(73, 237, 274, 274),
    options_x=40, options_y=525, options_w=340, options_step=57,
    feedback=(30, 691, 360, 17),
    footer=QUIZ_FOOTER,
    option_style=QUIZ_OPTIONS,
)

PHRASES_PRESET = ChoicePreset(
    heading=(36, 72, 348, 38),
    title=(22, 115, 376, 43),
    subtitle=(38, 165, 344, 45),
    media=(94, 221, 232, 232),
    options_x=40, options_y=525, options_w=340, options_step=57,
    feedback=(30, 688, 360, 20),
    footer=QUIZ_FOOTER,
    option_style=PHRASES_OPTIONS,
    title_size=25,
    situation=(39, 465, 342, 51),
)

QUESTIONS_PRESET = ChoicePreset(
    heading=(33, 81, 354, 38),
    title=(25, 132, 370, 52),
    subtitle=(37, 186, 346, 43),
    media=(38, 244, 344, 253),
    options_x=43, options_y=520, options_w=334, options_step=61,
    feedback=(40, 704, 340, 19),
    footer=QUESTIONS_FOOTER,
    option_style=QUESTIONS_OPTIONS,
    title_size=27,
    heading_size=17,
    header_title_size=16,
    min_sheet_height=250,
)


def ChoiceLayout(
    *,
    preset: ChoicePreset,
    width: float,
    height: float,
    title: str,
    current: int,
    total: int,
    time_text: str,
    section_title: str,
    prompt: str,
    hint_text: str,
    media_builder: Callable[[float], ft.Control],
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
    situation: str | None = None,
    badge_letter: str | None = None,
    badge_image: str | None = None,
) -> tuple[ft.Control, ft.Text]:
    """Devuelve ``(pantalla, timer_label)``.

    media_builder(scale)  -> imagen / ilustracion central
    answer_builder(scale) -> controles de respuesta (se usan las 3 primeras)
    feedback              -> (mensaje, kind) con kind en success/error/info, o None
    situation             -> texto para la tarjeta amarilla (solo si el preset la define)
    badge_image           -> ruta (relativa a assets) de la imagen del badge del header
    """

    def slots(slot, k):
        controls = [
            slot(*preset.heading,
                 exercise_section_heading(section_title, k, preset.heading_size)),
            slot(*preset.title,
                 exercise_text(prompt, preset.title_size * k, EXERCISE_NAVY,
                               bold=True, max_lines=2)),
            slot(*preset.subtitle,
                 exercise_text(hint_text, preset.subtitle_size * k,
                               EXERCISE_SOFT_BLUE, max_lines=2)),
            slot(*preset.media, media_builder(k)),
        ]
        if situation is not None and preset.situation is not None:
            controls.append(slot(*preset.situation, exercise_situation_card(situation, k)))

        h = preset.option_style.height
        for i, option in enumerate(answer_builder(k)[:3]):
            controls.append(slot(preset.options_x,
                                 preset.options_y + i * preset.options_step,
                                 preset.options_w, h, option))

        if feedback is not None:
            message, kind = feedback
            controls.append(slot(*preset.feedback, exercise_feedback(message, kind, k)))

        controls += footer_slots(
            slot, k, preset.footer,
            on_hint=on_hint, on_skip=on_skip, on_mic=on_microphone,
            on_continue=on_continue,
            hint_enabled=hint_enabled,
            recording=recording, processing=processing,
            caption="Listening..." if recording else "Tap to speak",
            can_continue=can_continue, is_last=is_last,
        )
        return controls

    return ExerciseFrame(
        width=width, height=height, title=title,
        current=current, total=total, time_text=time_text,
        on_pause=on_pause, slots=slots,
        badge_letter=badge_letter, badge_image=badge_image,
        title_size=preset.header_title_size,
        min_sheet_height=preset.min_sheet_height,
    )