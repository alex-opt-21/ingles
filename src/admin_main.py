
from pathlib import Path

import flet as ft

from screens.admin.admin_login import admin_login_screen
from screens.admin.dashboard import admin_dashboard


BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"


def main(page: ft.Page):
    page.title = "Bright English | Administración"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F2F6FC"

    try:
        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ):
            page.window.width = 1000
            page.window.height = 750
    except Exception as error:
        print(f"No se pudo configurar la ventana: {error}")

    state = {"admin": None}

    def cerrar_sesion():
        mostrar_login()

    def abrir_panel(admin):
        state["admin"] = admin
        admin_dashboard(page, admin, cerrar_sesion)

    def mostrar_login():
        state["admin"] = None

        # La pantalla de acceso valida las credenciales
        # y llama a abrir_panel(admin) si son correctas.
        admin_login_screen(
            page,
            on_success=abrir_panel,
            on_back=mostrar_login,
        )

    mostrar_login()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))
