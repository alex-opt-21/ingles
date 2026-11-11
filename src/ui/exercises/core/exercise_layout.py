
"""Layout compartido de los ejercicios."""

from collections.abc import Callable
import flet as ft

from .exercise_sheet import ExerciseSheet
from .exercise_header import ExerciseHeader
from .exercise_theme import (
    BACKGROUND_IMAGE,
    EXERCISE_GREEN,
    EXERCISE_SOFT_BLUE,
    EXERCISE_NAVY,
    EXERCISE_WHITE,
)

from ..components.exercise_timer import exercise_timer
from ..components.exercise_counter import exercise_counter
from ..components.exercise_buttons import (
    hint_button,
    skip_button,
    continue_button,
)
from ..components.exercise_microphone import exercise_microphone
from ..components.exercise_illustration import exercise_illustration


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
    answer_builder: Callable,
    feedback: ft.Control | None,
    on_pause: Callable,
    on_hint: Callable,
    on_skip: Callable,
    on_microphone: Callable,
    on_continue: Callable,
    hint_enabled: bool,
    can_continue: bool,
    is_last: bool,
    recording: bool = False,
) -> tuple[ft.Control, ft.Text]:

    compact = width < 380
    header_scale = min(1, (width - 24) / 440)
    header_h = 92 if compact else 53 * header_scale

    paper_h = max(
        220,
        min(850, height - header_h - 37),
    )
    paper_w = min(width - 24, 480)

    sx = paper_w / 420
    sy = paper_h / 870
    scale = min(sx, sy)

    def slot(x, y, w, h, child):
        return ft.Container(
            left=x * sx,
            top=y * sy,
            width=w * sx,
            height=h * sy,
            alignment=ft.Alignment.CENTER,
            content=child,
        )

    def text(value, size, color=EXERCISE_NAVY, bold=False):
        return ft.Text(
            str(value),
            size=size * scale,
            color=color,
            text_align=ft.TextAlign.CENTER,
            weight=(
                ft.FontWeight.BOLD
                if bold
                else ft.FontWeight.NORMAL
            ),
        )

    timer = exercise_timer(time_text)
    timer_text = timer.content.controls[1]

    counter = exercise_counter(current, total)

    timer_click = ft.Container(
        content=timer,
        ink=True,
        border_radius=18,
        on_click=on_pause,
        tooltip="Pause practice",
    )

    pills = ft.Row(
        controls=[timer_click, counter],
        spacing=6,
        tight=True,
    )

    heading = ExerciseHeader(title)

    if compact:
        header = ft.Column(
            controls=[heading, pills],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    else:
        header = ft.Row(
            controls=[heading, pills],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=4,
        )

    hint = hint_button(
        on_click=on_hint,
        disabled=not hint_enabled,
    )
    skip = skip_button(on_click=on_skip)
    cont = continue_button(on_click=on_continue)

    cont.content = "Finish" if is_last else "Continue"
    cont.bgcolor = (
        EXERCISE_GREEN
        if can_continue
        else "#D5DCE8"
    )
    cont.color = (
        EXERCISE_WHITE
        if can_continue
        else "#8A97B0"
    )

    for control, w, h in (
        (hint, 104, 50),
        (skip, 104, 50),
        (cont, 222, 52),
    ):
        control.width = w * scale
        control.height = h * scale

    mic = exercise_microphone(
        on_click=None if recording else on_microphone,
        recording=recording,
        size=max(24, round(66 * scale)),
    )

    illustration = exercise_illustration(
        src=image_src,
        width=max(30, round(274 * scale)),
        height=max(30, round(274 * scale)),
    )

    controls = [
        slot(
            36, 80, 348, 38,
            ft.Container(
                bgcolor="#B3D7FF",
                border_radius=12 * scale,
                alignment=ft.Alignment.CENTER,
                content=text(
                    section_title,
                    18,
                    bold=True,
                ),
            ),
        ),
        slot(
            23, 129, 374, 52,
            text(prompt, 29, bold=True),
        ),
        slot(
            39, 187, 342, 42,
            text(hint_text, 14, EXERCISE_SOFT_BLUE),
        ),
        slot(
            73, 237, 274, 274,
            illustration,
        ),
    ]

    for index, option_control in enumerate(
        answer_builder(scale)[:3]
    ):
        controls.append(
            slot(
                40,
                525 + index * 57,
                340,
                49,
                option_control,
            )
        )

    if feedback is not None:
        feedback.width = None
        feedback.padding = 3 * scale

        feedback.content.spacing = 5 * scale
        feedback.content.controls[0].size = 14 * scale
        feedback.content.controls[1].size = 12 * scale

        controls.append(
            slot(30, 677, 360, 33, feedback)
        )

    controls.extend([
        slot(38, 718, 104, 50, hint),
        slot(177, 710, 66, 66, mic),
        slot(278, 718, 104, 50, skip),

        slot(
            110, 779, 200, 17,
            text(
                "Listening..." if recording else "Tap to speak",
                12,
                EXERCISE_SOFT_BLUE,
                True,
            ),
        ),

        slot(99, 800, 222, 52, cont),
    ])

    sheet = ExerciseSheet(
        ft.Stack(
            width=paper_w,
            height=paper_h,
            controls=controls,
        ),
        width=paper_w,
        height=paper_h,
    )

    body = ft.Container(
        left=0,
        top=0,
        width=width,
        height=height,
        padding=ft.Padding.symmetric(
            horizontal=12,
            vertical=10,
        ),
        content=ft.SafeArea(
            content=ft.Column(
                controls=[header, sheet],
                spacing=5,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ),
    )

    screen = ft.Stack(
        width=width,
        height=height,
        controls=[
            ft.Image(
                src=BACKGROUND_IMAGE,
                left=0,
                top=0,
                width=width,
                height=height,
                fit=ft.BoxFit.COVER,
            ),
            body,
        ],
    )

    return screen, timer_text
