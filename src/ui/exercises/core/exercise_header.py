import flet as ft


def ExerciseHeader(
    title: str,
    subtitle: str = "",
) -> ft.Control:

    return ft.Column(
        controls=[
            ft.Text(
                title,
                size=23,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                subtitle,
                size=13,
            ) if subtitle else ft.Container(),
        ],
        spacing=4,
    )