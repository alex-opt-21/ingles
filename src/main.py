
from pathlib import Path
import hashlib
import flet as ft

# ---------- SERVICES ----------
from services.auth import auth_service as auth
from services.achievements.achievement_service import AchievementService

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
from screens.songs.songs_view import SongsView, load_songs

from ui.theme import APP_NAME, BG_TOP


# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent

EXERCISES_FILE = BASE_DIR / "data" / "acciones.json"
SENTENCES_FILE = BASE_DIR / "data" / "sentences.json"
QUESTIONS_FILE = BASE_DIR / "data" / "preguntas.json"
PHRASES_FILE = BASE_DIR / "data" / "phrases.json"
SONGS_FILE = BASE_DIR / "data" / "songs.json"

ASSETS_DIR = BASE_DIR / "assets"


# ---------- PROGRESS IDENTIFIERS ----------
ACTION_MODULE_ID = "flashcards"
ACTION_LESSON_ID = "action_practice"
ACTION_LEVEL_ID = "basic"

SENTENCES_MODULE_ID = "sentences"
SENTENCES_LESSON_ID = "sentence_practice"
SENTENCES_LEVEL_ID = "basic"

QUESTIONS_MODULE_ID = "questions"
QUESTIONS_LESSON_ID = "question_practice"
QUESTIONS_LEVEL_ID = "basic"

PHRASES_MODULE_ID = "phrases"
PHRASES_LESSON_ID = "phrase_practice"
PHRASES_LEVEL_ID = "basic"

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

    state = {
        "user": None,
        "view": None,
        "achievements": None,
    }

    # ---------- ACHIEVEMENTS ----------
    def init_achievements():
        """Crea el servicio de logros para el usuario autenticado."""
        user = state["user"]

        if user:
            state["achievements"] = AchievementService(
                user,
                auth.save_progress,
            )
        else:
            state["achievements"] = None

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
            on_songs=start_songs,
            on_logout=logout,
        )

        state["view"] = view
        view.show()

    # ---------- ACTION PRACTICE: SAVE / RESTORE ----------
    def start_quiz(e=None, force_new=False):
        close_current()

        user = state["user"]

        if not user or not user.get("email"):
            print(
                "[!] No se puede iniciar Action Practice "
                "sin un usuario autenticado."
            )
            go_login()
            return

        email = user["email"]

        # Crear sesión independiente de Flash Cards.
        session = QuizSession(
            exercises=exercises,
            user=user,
            save_progress=auth.save_progress,

            save_session=lambda email, session_state: (
                auth.save_module_progress(
                    email,
                    ACTION_MODULE_ID,
                    ACTION_LESSON_ID,
                    ACTION_LEVEL_ID,
                    session_state,
                )
            ),

            clear_session=lambda email: (
                auth.clear_module_progress(
                    email,
                    ACTION_MODULE_ID,
                    ACTION_LESSON_ID,
                    ACTION_LEVEL_ID,
                )
            ),

            session_size=None,
            module_id=ACTION_MODULE_ID,
            lesson_id=ACTION_LESSON_ID,
            level_id=ACTION_LEVEL_ID,
        )

        restored = False

        # Recuperar únicamente el progreso de Flash Cards.
        if not force_new:

            saved_state = auth.get_module_progress(
                email,
                ACTION_MODULE_ID,
                ACTION_LESSON_ID,
                ACTION_LEVEL_ID,
            )

            if saved_state:
                restored = session.restore_state(saved_state)

                if restored:
                    print(
                        "[+] Sesión de Flash Cards recuperada: "
                        f"ejercicio {session.number}/{session.total} "
                        f"({session.current['id']})."
                    )
                else:
                    print(
                        "[!] La sesión guardada no coincide "
                        "con los ejercicios actuales. "
                        "Se comenzará una práctica nueva."
                    )

                    auth.clear_module_progress(
                        email,
                        ACTION_MODULE_ID,
                        ACTION_LESSON_ID,
                        ACTION_LEVEL_ID,
                    )

        else:
            # Reiniciar solamente esta práctica.
            auth.clear_module_progress(
                email,
                ACTION_MODULE_ID,
                ACTION_LESSON_ID,
                ACTION_LEVEL_ID,
            )

        # Volver al inicio.
        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        # Crear vista.
        view = QuizView(
            page,
            session,
            on_home=back_to_home,
            achievements=state["achievements"],
        )

        state["view"] = view
        view.show(resume=restored)
    
# ---------- SENTENCES: SAVE / RESTORE ----------
    def start_sentences(e=None, force_new=False):
        close_current()

        user = state["user"]

        if not user or not user.get("email"):
            print("[!] No se puede iniciar Sentences sin un usuario autenticado.")
            go_login()
            return

        email = user["email"]

        session = SentencesSession(
            exercises=sentences,
            user=user,
            save_progress=auth.save_progress,

            save_session=lambda email, session_state: (
                auth.save_module_progress(
                    email,
                    SENTENCES_MODULE_ID,
                    SENTENCES_LESSON_ID,
                    SENTENCES_LEVEL_ID,
                    session_state,
                )
            ),

            clear_session=lambda email: (
                auth.clear_module_progress(
                    email,
                    SENTENCES_MODULE_ID,
                    SENTENCES_LESSON_ID,
                    SENTENCES_LEVEL_ID,
                )
            ),

            session_size=None,
            module_id=SENTENCES_MODULE_ID,
            lesson_id=SENTENCES_LESSON_ID,
            level_id=SENTENCES_LEVEL_ID,
        )

        restored = False

        if not force_new:
            saved_state = auth.get_module_progress(
                email,
                SENTENCES_MODULE_ID,
                SENTENCES_LESSON_ID,
                SENTENCES_LEVEL_ID,
            )

            if saved_state:
                restored = session.restore_state(saved_state)

                if restored:
                    print(
                        "[+] Sesión de Sentences recuperada: "
                        f"ejercicio {session.number}/{session.total} "
                        f"({session.current['id']})."
                    )
                else:
                    print(
                        "[!] La sesión guardada no coincide "
                        "con los ejercicios actuales. "
                        "Se comenzará una práctica nueva."
                    )

                    auth.clear_module_progress(
                        email,
                        SENTENCES_MODULE_ID,
                        SENTENCES_LESSON_ID,
                        SENTENCES_LEVEL_ID,
                    )

        else:
            auth.clear_module_progress(
                email,
                SENTENCES_MODULE_ID,
                SENTENCES_LESSON_ID,
                SENTENCES_LEVEL_ID,
            )

        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        view = SentencesView(
            page,
            session,
            on_home=back_to_home,
            achievements=state["achievements"],
        )

        state["view"] = view
        view.show(resume=restored)

    
# ---------- QUESTIONS & ANSWERS: SAVE / RESTORE ----------
    def start_questions(e=None, force_new=False):
        close_current()

        if not QUESTIONS_FILE.exists():
            print(f"No se encuentra el JSON de preguntas: {QUESTIONS_FILE}")
            go_home()
            return

        user = state["user"]

        if not user or not user.get("email"):
            print("[!] No se puede iniciar Questions sin un usuario autenticado.")
            go_login()
            return

        email = user["email"]

        session = QuestionsSession.from_json(
            path=QUESTIONS_FILE,
            user=user,
            save_progress=auth.save_progress,

            save_session=lambda email, session_state: (
                auth.save_module_progress(
                    email,
                    QUESTIONS_MODULE_ID,
                    QUESTIONS_LESSON_ID,
                    QUESTIONS_LEVEL_ID,
                    session_state,
                )
            ),

            clear_session=lambda email: (
                auth.clear_module_progress(
                    email,
                    QUESTIONS_MODULE_ID,
                    QUESTIONS_LESSON_ID,
                    QUESTIONS_LEVEL_ID,
                )
            ),

            module_id=QUESTIONS_MODULE_ID,
            lesson_id=QUESTIONS_LESSON_ID,
            level_id=QUESTIONS_LEVEL_ID,
        )

        restored = False

        if not force_new:
            saved_state = auth.get_module_progress(
                email,
                QUESTIONS_MODULE_ID,
                QUESTIONS_LESSON_ID,
                QUESTIONS_LEVEL_ID,
            )

            if saved_state:
                restored = session.restore_state(saved_state)

                if restored:
                    print(
                        "[+] Sesión de Questions recuperada: "
                        f"pregunta {session.number}/{session.total} "
                        f"({session.current['id']})."
                    )
                else:
                    print(
                        "[!] La sesión guardada no coincide "
                        "con las preguntas actuales. "
                        "Se comenzará una práctica nueva."
                    )

                    auth.clear_module_progress(
                        email,
                        QUESTIONS_MODULE_ID,
                        QUESTIONS_LESSON_ID,
                        QUESTIONS_LEVEL_ID,
                    )

        else:
            auth.clear_module_progress(
                email,
                QUESTIONS_MODULE_ID,
                QUESTIONS_LESSON_ID,
                QUESTIONS_LEVEL_ID,
            )

        def back_to_home():
            go_home()

        view = QuestionsView(
            page,
            session,
            on_home=back_to_home,
            achievements=state["achievements"],
        )

        state["view"] = view
        view.show(resume=restored)


    
# ---------- PHRASES: SAVE / RESTORE ----------
    def start_phrases(e=None, force_new=False):
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

        user = state["user"]

        if not user or not user.get("email"):
            print("[!] No se puede iniciar Phrases sin un usuario autenticado.")
            go_login()
            return

        email = user["email"]

        session = PhrasesSession(
            exercises=phrases,
            user=user,
            save_progress=auth.save_progress,

            save_session=lambda email, session_state: (
                auth.save_module_progress(
                    email,
                    PHRASES_MODULE_ID,
                    PHRASES_LESSON_ID,
                    PHRASES_LEVEL_ID,
                    session_state,
                )
            ),

            clear_session=lambda email: (
                auth.clear_module_progress(
                    email,
                    PHRASES_MODULE_ID,
                    PHRASES_LESSON_ID,
                    PHRASES_LEVEL_ID,
                )
            ),

            module_id=PHRASES_MODULE_ID,
            lesson_id=PHRASES_LESSON_ID,
            level_id=PHRASES_LEVEL_ID,
        )

        restored = False

        if not force_new:
            saved_state = auth.get_module_progress(
                email,
                PHRASES_MODULE_ID,
                PHRASES_LESSON_ID,
                PHRASES_LEVEL_ID,
            )

            if saved_state:
                restored = session.restore_state(saved_state)

                if restored:
                    print(
                        "[+] Sesión de Phrases recuperada: "
                        f"ejercicio {session.number}/{session.total} "
                        f"({session.current['id']})."
                    )
                else:
                    print(
                        "[!] La sesión guardada no coincide "
                        "con los ejercicios actuales. "
                        "Se comenzará una práctica nueva."
                    )

                    auth.clear_module_progress(
                        email,
                        PHRASES_MODULE_ID,
                        PHRASES_LESSON_ID,
                        PHRASES_LEVEL_ID,
                    )

        else:
            auth.clear_module_progress(
                email,
                PHRASES_MODULE_ID,
                PHRASES_LESSON_ID,
                PHRASES_LEVEL_ID,
            )

        def back_to_home():
            user["xp"] = session.xp
            user["completed"] = list(session.completed)
            go_home()

        view = PhrasesView(
            page,
            session,
            on_home=back_to_home,
            achievements=state["achievements"],
        )

        state["view"] = view
        view.show(resume=restored)


    # ---------- SONGS: KARAOKE SPEAKING ----------
    def start_songs(e=None):
        close_current()

        songs = load_songs(SONGS_FILE)

        view = SongsView(
            page,
            songs=songs,
            on_home=go_home,
            achievements=state["achievements"],
        )

        state["view"] = view
        view.show()

    # ---------- LOGOUT ----------
    def logout(e=None):
        close_current()

        state["user"] = None
        state["achievements"] = None

        go_login()

    # ---------- AUTHENTICATION ----------
    def do_login(email, password):
        ok, result = auth.login(email, password)

        if not ok:
            return result

        state["user"] = result

        init_achievements()
        go_home()

        return None

    def do_register(name, email, password, confirm):
        ok, result = auth.register(
            name,
            email,
            password,
            confirm,
        )

        if not ok:
            return result

        state["user"] = result

        init_achievements()
        go_home()

        return None

    # ---------- START ----------
    go_welcome()


if __name__ == "__main__":
    ft.run(
        main,
        assets_dir=str(ASSETS_DIR),
    )
