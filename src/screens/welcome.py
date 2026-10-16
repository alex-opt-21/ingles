import flet as ft

def welcome_screen(page, go_login):

    page.clean()

    page.add(
        ft.Container(
            expand=True,
            content=ft.Stack(
                controls=[

                    # FONDO ORIGINAL - NO CAMBIAR
                    ft.Image(
                        src="imagenes/welcome.png",
                        expand=True,
                        fit=ft.BoxFit.COVER
                    ),

                    # TITULO BRIGHT ENGLISH
                    ft.Container(
                        top=145,  # <- aqui lo baje un poquito mas
                        left=0,
                        right=0,
                        content=ft.Column(
                            spacing=-15,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    "Bright",
                                    size=65,
                                    weight=ft.FontWeight.BOLD,
                                    color="#172D55",
                                    font_family="Comic Sans MS",
                                    italic=True,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Text(
                                    "English",
                                    size=55,
                                    weight=ft.FontWeight.BOLD,
                                    color="#80ADEB",
                                    font_family="Comic Sans MS",
                                    italic=True,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ]
                        )
                    ),

                    # BOTON ABAJO
                    ft.Column(
                        alignment=ft.MainAxisAlignment.END,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[

                            ft.Container(height=60),

                            ft.Button(
                                content=ft.Text(
                                    "Get Started",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                    font_family="Comic Sans MS",
                                    italic=True,
                                ),
                                width=280,
                                height=55,
                                on_click=go_login,
                                style=ft.ButtonStyle(
                                    bgcolor="#173F7A",  # fondo azul
                                    shape=ft.RoundedRectangleBorder(
                                        radius=30
                                    )
                                )
                            ),

                            ft.Container(height=40),
                        ]
                    )
                ]
            )
        )
    )