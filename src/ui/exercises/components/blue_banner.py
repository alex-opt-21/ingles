import flet as ft
from typing import Optional


class BlueBanner(ft.Container):
    """Banner con un SVG de fondo y contenido encima."""

    def __init__(
        self,
        content: Optional[ft.Control] = None,
        width: int | float = 600,
        height: int | float = 230,
        alignment: Optional[ft.Alignment] = None,
        padding: int | float = 20,
        svg_src: str = "banner_azul.svg",
    ):
        super().__init__(
            width=width,
            height=height,
            padding=0,
            content=ft.Stack(
                width=width,
                height=height,
                controls=[
                    # SVG de fondo
                    ft.Image(
                        src=svg_src,
                        left=0,
                        top=0,
                        width=width,
                        height=height,
                        fit=ft.BoxFit.FILL,
                    ),
                    # Contenido superpuesto
                    ft.Container(
                        left=0,
                        top=0,
                        content=content,
                        width=width,
                        height=height,
                        alignment=alignment or ft.Alignment.CENTER,
                        padding=padding,
                    ),
                ],
            ),
        )
        self.banner_content = content