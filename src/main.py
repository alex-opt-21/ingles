from pathlib import Path
import hashlib
import flet as ft

# ---------- SERVICES ----------
from services.auth import auth_service as auth

from services.ejercicios.ejercicio_service import (
    QuizSession,
    load_exercises,
)

from services.ejercicios.sentences_service import (
    SentencesSession,
    load_sentences,
)

from services.ejercicios.questions_service import QuestionsSession
from services.ejercicios.phrases_service import PhrasesSession, load_phrases

# ---------- SCREENS ----------
from screens.welcome import welcome_screen
from screens.login import login_screen
from screens.register import register_screen
from screens.home.inicio import HomeView
from screens.ejercicios.ejercicio import QuizView
from screens.sentences.sentences import SentencesView
from screens.questions.question import QuestionsView
from screens.phrases.phrases import PhrasesView

from ui.theme import APP_NAME, BG_TOP

# ---------- PATHS ----------
# Este archivo va en src/main.py.
BASE_DIR = Path(__file__).resolve().parent
EXERCISES_FILE = BASE_DIR / "data" / "acciones.json"
SENTENCES_FILE = BASE_DIR / "data" / "sentences.json"
QUESTIONS_FILE = BASE_DIR / "data" / "preguntas.json"
PHRASES_FILE = BASE_DIR / "data" / "phrases.json"
ASSETS_DIR = BASE_DIR / "assets"


def main(page: ft.Page):
    # ---------- CONFIGURATION ----------
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
        print(f"Window error: {err}")

    # ---------- LOAD DATA ----------
    exercises = load_exercises(EXERCISES_FILE, ASSETS_DIR)
    sentences = load_sentences(SENTENCES_FILE, ASSETS_DIR)

    state = {"user": None, "view": None}

    # ---------- CLOSE VIEW ----------
    def close_current():
        view = state["view"]
        if view is not None:
            view.close()
            state["view"] = None

    # ---------- WELCOME ----------
    def go_welcome():
        welcome_screen(page, go_login)

    # ---------- LOGIN ----------
    def go_login(e=None):
        close_current()
        login_screen(page, do_login, go_register)

    # ---------- REGISTER ----------
    def go_register(e=None):
        register_screen(page, do_register, go_login)

    # ---------- HOME ----------
    def go_home():
        close_current()
        view = HomeView(
            page,
            state["user"],
            total_exercises=len(exercises),
            on_practice=start_quiz,
            on_sentences=start_sentences,
            on_questions=start_questions,
            on_phrases=start_phrases,
            on_logout=logout,
        )
        state["view"] = view
        view.show()

    # ---------- ACTION PRACTICE ----------
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

    # ---------- SENTENCES ----------
    def start_sentences(e=None):
        close_current()
        user = state["user"]
        session = SentencesSession(sentences, user, save_progress=auth.save_progress)

        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        view = SentencesView(page, session, on_home=back_to_home)
        state["view"] = view
        view.show()

    # ---------- QUESTIONS & ANSWERS ----------
    def start_questions(e=None):
        close_current()

        if not QUESTIONS_FILE.exists():
            print(f"No se encuentra el JSON de preguntas: {QUESTIONS_FILE}")
            go_home()
            return

        # El servicio de Questions almacena progreso local. Separar por
        # usuario evita que uno reanude el avance de otro.
        user = state["user"] or {}
        identity = str(
            user.get("id") or user.get("_id") or user.get("email") or "local"
        )
        user_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        progress_file = Path.home() / ".saylo" / f"questions_{user_hash}.json"

        session = QuestionsSession.from_json(
            path=QUESTIONS_FILE,
            progress_file=progress_file,
        )

        def back_to_home():
            go_home()

        view = QuestionsView(page, session, on_home=back_to_home)
        state["view"] = view
        view.show(resume=session.has_progress)

    # ---------- PHRASES ----------
    def start_phrases(e=None):
        close_current()

        if not PHRASES_FILE.exists():
            print(f"No se encuentra el JSON de frases: {PHRASES_FILE}")
            go_home()
            return

        phrases = load_phrases(PHRASES_FILE, ASSETS_DIR)
        if not phrases:
            print("No hay ejercicios en phrases.json")
            go_home()
            return

        user = state["user"] or {}

        # Mantener la partida guardada de cada usuario por separado.
        identity = str(
            user.get("id") or user.get("_id") or user.get("email") or "local"
        )
        user_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        progress_dir = Path.home() / ".saylo"
        progress_dir.mkdir(parents=True, exist_ok=True)
        progress_file = progress_dir / f"phrases_{user_hash}.json"

        session = PhrasesSession(
            phrases,
            user,
            save_progress=auth.save_progress,
            progress_file=progress_file,
        )

        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        view = PhrasesView(page, session, on_home=back_to_home)
        state["view"] = view
        view.show(resume=session.has_progress)

    # ---------- LOGOUT ----------
    def logout(e=None):
        close_current()
        state["user"] = None
        go_login()

    # ---------- AUTHENTICATION ----------
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

    # ---------- START ----------
    go_welcome()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))
