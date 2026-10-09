import flet as ft


def register_screen(page, on_submit, go_login):

    page.clean()

    name = ft.TextField(hint_text="Nombre", width=320, border_radius=25, bgcolor="white")
    email = ft.TextField(
        hint_text="Email",
        width=320,
        border_radius=25,
        keyboard_type=ft.KeyboardType.EMAIL,
        bgcolor="white",
    )
    password = ft.TextField(
        hint_text="Contraseña (mín. 6 caracteres)",
        password=True,
        can_reveal_password=True,
        width=320,
        border_radius=25,
        bgcolor="white",
    )
    confirm = ft.TextField(
        hint_text="Repite la contraseña",
        password=True,
        can_reveal_password=True,
        width=320,
        border_radius=25,
        bgcolor="white",
    )

    error = ft.Text("", color="#DC2626", size=13, text_align=ft.TextAlign.CENTER)

    def submit(e=None):
        err = on_submit(name.value, email.value, password.value, confirm.value)
        if err:
            error.value = err
            page.update()

    confirm.on_submit = submit

    page.add(
        ft.Container(
            expand=True,
            content=ft.Stack(
                expand=True,
                controls=[
                    ft.Image(
                        src="imagenes/login.png",
                        fit=ft.BoxFit.COVER,
                        left=0, top=0, right=0, bottom=0,
                    ),
                    ft.Container(
                        left=0, top=0, right=0, bottom=0,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=14,
                            controls=[
                                ft.Text(
                                    "Create Account",
                                    size=30,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1E3A70",
                                ),
                                name,
                                email,
                                password,
                                confirm,
                                error,
                                ft.Button(
                                    content=ft.Text("Register", size=16, weight=ft.FontWeight.BOLD),
                                    width=320,
                                    height=55,
                                    on_click=submit,
                                    style=ft.ButtonStyle(
                                        bgcolor="#1E3A70",
                                        color="white",
                                        shape=ft.RoundedRectangleBorder(radius=30),
                                    ),
                                ),
                                ft.TextButton(
                                    content=ft.Text("¿Ya tienes cuenta? Inicia sesión"),
                                    on_click=lambda e: go_login(),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )
    )