import flet as ft


def welcome_screen(page, go_login):

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
                        fit=ft.BoxFit.COVER
                    ),

                    # Botón encima de la imagen
                    ft.Column(
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,

                        controls=[

                            ft.Container(
                                height=60
                            ),

                            ft.Button(
                                content=ft.Text("Get Started"),
                                width=280,
                                height=55,

                                # Ir a pantalla de login (lo maneja main.py)
                                on_click=go_login,

                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(
                                        radius=30
                                    )
                                )
                            ),

                            ft.Container(
                                height=40
                            ),
                        ]
                    )
                ]
            )
        )
    )