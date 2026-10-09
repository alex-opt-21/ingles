import flet as ft


def login_screen(page, go_start):

    page.clean()

    page.add(
        ft.Container(
            expand=True,

            content=ft.Stack(
                controls=[

                    # Imagen de fondo login
                    ft.Image(
                        src="imagenes/login.png",
                        expand=True,
                        fit=ft.ImageFit.COVER
                    ),


                    # Elementos encima de la imagen
                    ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,

                        controls=[

                            ft.Container(
                                height=150
                            ),


                            ft.Text(
                                "Welcome Back",
                                size=30,
                                weight=ft.FontWeight.BOLD,
                                color="#1E3A70"
                            ),


                            ft.Container(
                                height=30
                            ),


                            ft.TextField(
                                hint_text="Email",
                                width=320,
                                border_radius=25
                            ),


                            ft.TextField(
                                hint_text="Password",
                                password=True,
                                can_reveal_password=True,
                                width=320,
                                border_radius=25
                            ),


                            ft.Container(
                                height=20
                            ),


                            ft.ElevatedButton(
                                text="Log In",
                                width=320,
                                height=55,

                                # Ir a la pantalla de ejercicios
                                on_click=go_start,

                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(
                                        radius=30
                                    )
                                )
                            ),


                            ft.Container(
                                height=25
                            ),


                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,

                                controls=[

                                    ft.Container(
                                        width=60,
                                        height=60,
                                        bgcolor="white",
                                        border_radius=30,
                                        content=ft.Text("G")
                                    ),

                                    ft.Container(
                                        width=60,
                                        height=60,
                                        bgcolor="white",
                                        border_radius=30,
                                        content=ft.Text("f")
                                    ),

                                    ft.Container(
                                        width=60,
                                        height=60,
                                        bgcolor="white",
                                        border_radius=30,
                                        content=ft.Text("")
                                    )

                                ]
                            ),


                            ft.Container(
                                height=30
                            ),


                            ft.OutlinedButton(
                                text="Create an account",
                                width=320,
                                height=50
                            )

                        ]
                    )
                ]
            )
        )
    )
