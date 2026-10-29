
import flet as ft

from services.admin import admin_service


def admin_login_screen(page, on_success, on_back):
    page.clean()

    azul = "#1E3A70"
    azul_oscuro = "#172D55"
    celeste = "#80ADEB"
    blanco = "#FFFFFF"

    email = ft.TextField(
        label="Correo administrativo",
        width=320,
        keyboard_type=ft.KeyboardType.EMAIL,
        prefix_icon=ft.Icons.MAIL_OUTLINE,
        border_radius=14,
        autofocus=True,
    )

    password = ft.TextField(
        label="Contraseña",
        width=320,
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        border_radius=14,
    )

    mensaje = ft.Text(
        "",
        color="#DC2626",
        size=13,
        text_align=ft.TextAlign.CENTER,
    )

    boton_ingresar = ft.Button(
        content=ft.Text(
            "Ingresar al panel",
            color=blanco,
            weight=ft.FontWeight.BOLD,
        ),
        width=320,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=azul_oscuro,
            color=blanco,
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )

    def ingresar(e=None):
        boton_ingresar.disabled = True
        mensaje.value = ""
        page.update()

        try:
            ok, resultado = admin_service.admin_login(
                email.value,
                password.value,
            )

            if not ok:
                mensaje.value = resultado
                password.value = ""
                return

            on_success(resultado)

        except Exception as error:
            import traceback
            print("\n=== ERROR EN ADMINISTRACION ===")
            traceback.print_exc()

            mensaje.value = (
                f"Error al abrir el panel: {type(error).__name__}. "
                "Revisa la terminal."
            )

        finally:
            boton_ingresar.disabled = False
            page.update()

    boton_ingresar.on_click = ingresar
    password.on_submit = ingresar

    tarjeta = ft.Container(
        width=380,
        padding=28,
        border_radius=24,
        bgcolor=blanco,
        shadow=ft.BoxShadow(
            blur_radius=18,
            color=ft.Colors.with_opacity(0.10, "#172D55"),
            offset=ft.Offset(0, 5),
        ),
        content=ft.Column(
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                ft.Container(
                    width=72,
                    height=72,
                    border_radius=36,
                    bgcolor="#EAF3FF",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.ADMIN_PANEL_SETTINGS,
                        size=38,
                        color=azul,
                    ),
                ),
                ft.Text(
                    "Administración",
                    size=27,
                    weight=ft.FontWeight.BOLD,
                    color=azul_oscuro,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Acceso exclusivo para administradores",
                    size=13,
                    color=azul,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=4),
                email,
                password,
                mensaje,
                boton_ingresar,
                ft.TextButton(
                    content=ft.Text("Volver"),
                    on_click=lambda e: on_back(),
                ),
            ],
        ),
    )

    page.add(
        ft.Container(
            expand=True,
            padding=20,
            bgcolor="#F2F6FC",
            alignment=ft.Alignment.CENTER,
            content=tarjeta,
        )
    )
