
"""Pantalla completa de resultados compartida."""

from collections.abc import Callable, Sequence
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_NAVY as NAVY,
    EXERCISE_WHITE as WHITE,
    EXERCISE_CREAM as CREAM,
)

from ..components.exercise_buttons import _build_button


def _stat(
    label: str,
    value: str,
    color: str,
) -> ft.Container:

    return ft.Container(
        expand=True,
        bgcolor=WHITE,
        border_radius=18,
        padding=ft.Padding.symmetric(
            vertical=16,
            horizontal=6,
        ),
        content=ft.Column(
            tight=True,
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    value,
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
                ft.Text(
                    label,
                    size=13,
                    color=NAVY,
                ),
            ],
        ),
    )


def _detail_row(
    label: str,
    value: str,
) -> ft.Row:

    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        spacing=12,
        controls=[
            ft.Text(
                label,
                size=13,
                color=NAVY,
                weight=ft.FontWeight.BOLD,
                expand=True,
            ),
            ft.Text(
                value,
                size=13,
                color=NAVY,
                weight=ft.FontWeight.BOLD,
            ),
        ],
    )


def results_screen(
    correct: int,
    total: int,
    *,
    details: Sequence[tuple[str, str]] = (),
    elapsed_time: str | None = None,
    on_retry: Callable | None = None,
    on_exit: Callable | None = None,
    width: float = 440,
    height: float = 844,
) -> ft.Container:

    total = max(0, int(total))
    correct = min(total, max(0, int(correct)))

    accuracy = (
        round(correct * 100 / total)
        if total
        else 0
    )

    inner_width = min(400, max(200, width - 36))
    buttons_width = min(278, inner_width)

    info = [
        ft.Icon(
            ft.Icons.EMOJI_EVENTS_OUTLINED,
            size=54,
            color=BLUE,
        ),

        ft.Text(
            "Practice complete!",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=NAVY,
            text_align=ft.TextAlign.CENTER,
        ),

        ft.Text(
            "Your results",
            size=15,
            color=NAVY,
        ),

        ft.Row(
            spacing=12,
            controls=[
                _stat(
                    "Correct",
                    f"{correct}/{total}",
                    GREEN,
                ),
                _stat(
                    "Accuracy",
                    f"{accuracy}%",
                    BLUE,
                ),
            ],
        ),
    ]

    if details:
        info.append(
            ft.Container(
                bgcolor=WHITE,
                border_radius=18,
                padding=16,
                content=ft.Column(
                    tight=True,
                    spacing=13,
                    controls=[
                        _detail_row(label, value)
                        for label, value in details
                    ],
                ),
            )
        )

    if elapsed_time:
        info.append(
            ft.Text(
                f"Time: {elapsed_time}",
                size=14,
                color=NAVY,
            )
        )

    info.extend([
        ft.Container(height=8),

        _build_button(
            "Try again",
            ft.Icons.REPLAY,
            on_retry,
            bgcolor=BLUE,
            color=WHITE,
            width=buttons_width,
            height=56,
            disabled=on_retry is None,
        ),

        _build_button(
            "Exit",
            ft.Icons.HOME_OUTLINED,
            on_exit,
            bgcolor=WHITE,
            color=NAVY,
            width=buttons_width,
            height=56,
            disabled=on_exit is None,
        ),
    ])

    return ft.Container(
        width=width,
        height=height,
        bgcolor=CREAM,
        content=ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=inner_width,
                        padding=ft.Padding.symmetric(
                            vertical=26,
                        ),
                        content=ft.Column(
                            tight=True,
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=info,
                        ),
                    ),
                ],
            ),
        ),
    )
