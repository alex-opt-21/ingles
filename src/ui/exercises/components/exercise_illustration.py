"""Contenedor de ilustraciones con dimensiones compartidas."""
import flet as ft

from ..core.exercise_theme import (
    EXERCISE_SOFT_BLUE,
    EXERCISE_NAVY,
)


ILLUSTRATION_SIZE = 274


def exercise_illustration(
    src: str | None = None,
    width: int = ILLUSTRATION_SIZE,
    height: int = ILLUSTRATION_SIZE,
    description: str = "Illustration",
) -> ft.Container:
    """La vista elige la imagen; este componente solo la presenta."""
    fallback = ft.Column(
        controls=[
            ft.Icon(ft.Icons.IMAGE_OUTLINED, size=42, color=EXERCISE_NAVY),
            ft.Text(description, color=EXERCISE_NAVY, size=13),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    content: ft.Control = (
        ft.Image(
            src=src,
            fit=ft.BoxFit.CONTAIN,
            width=max(1, width - 20),
            height=max(1, height - 20),
            error_content=fallback,
            semantics_label=description,
        )
        if src
        else fallback
    )

    return ft.Container(
        width=width,
        height=height,
        padding=10,
        bgcolor=EXERCISE_SOFT_BLUE,
        border_radius=18,
        alignment=ft.Alignment.CENTER,
        content=content,
    )
