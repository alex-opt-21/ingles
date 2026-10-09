import flet as ft

from screens.login import login_screen


def welcome_screen(page):

    page.clean()

    page.add(
        ft.Container(
            expand=True,

            content=ft.Stack(
                controls=[

                    # Imagen de fondo pantalla principal
                    ft.Image(
                        src="imagenes/welcome.png",
                        expand=True,
                        fit=ft.ImageFit.COVER
                    ),

                    # Botón encima de la imagen
                    ft.Column(
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,

                        controls=[

                            ft.Container(
                                height=60
                            ),

                            ft.ElevatedButton(
                                text="Get Started",
                                width=280,
                                height=55,

                                # Ir a pantalla de login
                                on_click=lambda e: login_screen(page),

                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(
                                        radius=30
                                    )
                                )
                            )
                        ]
                    )
                ]
            )
        )
    )
