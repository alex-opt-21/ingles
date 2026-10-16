from pathlib import Path

import flet as ft

from services.auth import auth_service as auth
from services.ejercicios.ejercicio_service import QuizSession, load_exercises
from screens.welcome import welcome_screen
from screens.login import login_screen
from screens.register import register_screen
from screens.home.inicio import HomeView
from screens.ejercicios.ejercicio import QuizView
from ui.theme import APP_NAME, BG_TOP

BASE_DIR = Path(__file__).parent
EXERCISES_FILE = BASE_DIR / "data" / "acciones.json"
ASSETS_DIR = BASE_DIR / "assets"


def main(page: ft.Page):
    page.title = APP_NAME
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG_TOP
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    try:
        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ):
            page.window.width = 390
            page.window.height = 844
    except Exception as err:
        print(f"Could not resize the window: {err}")

    exercises = load_exercises(EXERCISES_FILE, ASSETS_DIR)
    state = {"user": None, "view": None} 

    def close_current():
        view = state["view"]
        if view is not None:
            view.close()
            state["view"] = None

    # ---------- navigation ----------

    def go_welcome():
        welcome_screen(page, go_login)

    def go_login(e=None):
        close_current()
        login_screen(page, do_login, go_register)

    def go_register(e=None):
        register_screen(page, do_register, go_login)

    def go_home():
        close_current()
        view = HomeView(
            page,
            state["user"],
            total_exercises=len(exercises),
            on_practice=start_quiz,
            on_logout=logout,
        )
        state["view"] = view
        view.show()

    def start_quiz(e=None):
        close_current()
        user = state["user"]
        session = QuizSession(exercises, user, save_progress=auth.save_progress)

        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        view = QuizView(page, session, on_home=back_to_home)
        state["view"] = view
        view.show()

    def logout(e=None):
        state["user"] = None
        go_login()

    # ---------- authentication ----------

    def do_login(email, password):
        ok, result = auth.login(email, password)
        if not ok:
            return result
        state["user"] = result
        go_home()
        return None

    def do_register(name, email, password, confirm):
        ok, result = auth.register(name, email, password, confirm)
        if not ok:
            return result
        state["user"] = result
        go_home()
        return None

    go_welcome()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))