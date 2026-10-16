
import flet as ft


def login_screen(page, on_submit, go_register):

    page.clean()

    # COLORES
    azul = "#1E3A70"
    azul_oscuro = "#172D55"
    celeste = "#80ADEB"
    blanco = "#FFFFFF"

    # CAMPO EMAIL
    email = ft.TextField(
        hint_text="Email",
        width=300,
        height=53,
        border_radius=27,
        keyboard_type=ft.KeyboardType.EMAIL,
        bgcolor=blanco,
        border_color="#E0E6EF",
        focused_border_color=celeste,
        prefix_icon=ft.Icons.MAIL_OUTLINE,
    )

    # CAMPO PASSWORD
    password = ft.TextField(
        hint_text="Password",
        password=True,
        can_reveal_password=True,
        width=300,
        height=53,
        border_radius=27,
        bgcolor=blanco,
        border_color="#E0E6EF",
        focused_border_color=celeste,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
    )

    # MENSAJE DE ERROR
    error = ft.Text(
        "",
        color="#DC2626",
        size=13,
        text_align=ft.TextAlign.CENTER,
    )

    # FUNCION ORIGINAL DEL LOGIN
    def submit(e=None):
        err = on_submit(email.value, password.value)

        if err:
            error.value = err
            page.update()

    password.on_submit = submit

    # LOGO SIN FONDO BLANCO
    logo = ft.Column(
        spacing=-13,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                "Bright",
                size=34,
                weight=ft.FontWeight.BOLD,
                color=azul_oscuro,
                font_family="Comic Sans MS",
                italic=True,
            ),
            ft.Text(
                "English",
                size=29,
                weight=ft.FontWeight.BOLD,
                color=celeste,
                font_family="Comic Sans MS",
                italic=True,
            ),
        ],
    )

    # BOTON AZUL CON FLECHA EN CIRCULO BLANCO
    login_button = ft.Button(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=32),

                ft.Text(
                    "Welcome Back",
                    size=17,
                    weight=ft.FontWeight.BOLD,
                    color=blanco,
                    font_family="Comic Sans MS",
                    italic=True,
                ),

                ft.Container(
                    width=32,
                    height=32,
                    bgcolor=blanco,
                    border_radius=20,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Icon(
                        ft.Icons.ARROW_FORWARD,
                        color=azul_oscuro,
                        size=19,
                    ),
                ),
            ],
        ),
        width=300,
        height=57,
        on_click=submit,
        style=ft.ButtonStyle(
            bgcolor=azul_oscuro,
            color=blanco,
            shape=ft.RoundedRectangleBorder(radius=30),
        ),
    )

    # BOTON CREAR CUENTA
    register_button = ft.OutlinedButton(
        content=ft.Text(
            "Create an account",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=azul_oscuro,
            font_family="Comic Sans MS",
            italic=True,
        ),
        width=300,
        height=55,
        on_click=lambda e: go_register(),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1.5, celeste),
            shape=ft.RoundedRectangleBorder(radius=30),
        ),
    )

    # TARJETA CENTRAL MAS DELICADA
    tarjeta = ft.Container(
        width=340,
        bgcolor="#F9FBFF",
        border_radius=32,
        padding=20,

        content=ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[

                ft.Text(
                    "Welcome Back",
                    size=27,
                    weight=ft.FontWeight.BOLD,
                    color=azul_oscuro,
                    font_family="Comic Sans MS",
                    italic=True,
                ),

                # LINEA CELESTE
                ft.Container(
                    width=135,
                    height=3,
                    bgcolor=celeste,
                    border_radius=10,
                ),

                ft.Container(height=10),

                email,

                password,

                # RECUPERAR CONTRASEÑA
                ft.Container(
                    width=300,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Text(
                                "Forgot your password?",
                                size=12,
                                color="#2581D9",
                            ),
                        ],
                    ),
                ),

                error,

                ft.Container(height=5),

                login_button,
            ],
        ),
    )

    # PANTALLA COMPLETA
    page.add(
        ft.Container(
            expand=True,
            content=ft.Stack(
                expand=True,
                controls=[

                    # FONDO ORIGINAL
                    ft.Image(
                        src="imagenes/login.png",
                        fit=ft.BoxFit.COVER,
                        left=0,
                        top=0,
                        right=0,
                        bottom=0,
                    ),

                    # CONTENIDO CENTRADO
                    ft.Container(
                        left=0,
                        top=0,
                        right=0,
                        bottom=0,

                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=20,

                            controls=[

                                ft.Container(height=15),

                                logo,

                                ft.Container(height=5),

                                tarjeta,

                                ft.Container(height=18),

                                register_button,

                            ],
                        ),
                    ),
                ],
            ),
        )
    )
