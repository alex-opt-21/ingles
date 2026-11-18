import asyncio
import flet as ft

from services.ejercicios.questions_service import format_time

# AJUSTA esta ruta a donde pusiste la carpeta `exercises` (ej. ui/exercises).
from ui.exercises.core.exercise_choice_layout import ChoiceLayout, QUESTIONS_PRESET
from ui.exercises.core.exercise_theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_PALE_BLUE,
    EXERCISE_RED as RED,
    EXERCISE_SOFT_BLUE as SOFT,
)
from ui.exercises.components.answer_options import answer_options
from ui.exercises.components.exercise_illustrated_question import (
    exercise_illustrated_question,
)
from ui.exercises.overlays.pause_overlay import pause_overlay
from ui.exercises.overlays.results_overlay import results_screen

try:
    import flet_audio as fta
except ImportError:
    fta = None

# Ilustraciones JSON: "imagenes/questions/Fiesta.png" y "imagenes/questions/Niño.png"
# Las coordenadas del globo de cada escena estan en
# exercises/components/exercise_illustrated_question.py (tabla SCENES).


class QuestionsView:
    """Interfaz: QuestionsView(page, session, on_home).show()."""

    TITLE = "Questions Practice"
    SECTION = "QUESTIONS & ANSWERS"

    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"  # quiz, paused, end, closed
        self.w = 440
        self.h = 844
        self.shell = ft.Container()
        self._timer_label: ft.Text | None = None  # lo crea ChoiceLayout
        self._token = 0
        self._recording = False
        self._mic_message = None  # (ok, heard)
        self._audio_player = None

    # ------------------ Ciclo de vida ------------------

    def show(self, resume=False):
        """show(resume=True) restaura el progreso guardado si existe."""
        self._token += 1
        self._stop_audio()
        self.mode = "quiz"
        self._recording = False
        self._mic_message = None
        if not (resume and self.session.resume_saved()):
            self.session.start()
        self.page.clean()
        self.page.padding = 0
        self.page.spacing = 0
        self.page.add(ft.Container(
            expand=True,
            bgcolor=EXERCISE_PALE_BLUE,
            alignment=ft.Alignment.TOP_CENTER,
            content=self.shell,
        ))
        self.page.on_resize = self._fit
        self._fit(force=True)
        self.page.run_task(self._tick, self._token)

    def close(self):
        self._token += 1
        self._stop_audio()
        self.mode = "closed"
        self.page.on_resize = None
        self.session.pause()

    def _fit(self, e=None, force=False):
        w = max(270, min(self.page.width or 440, 520))
        h = max(360, self.page.height or 844)
        if force or abs(w - self.w) > 1 or abs(h - self.h) > 1 or self.shell.content is None:
            self.w, self.h = w, h
            self.render()

    async def _tick(self, token):
        while token == self._token and self.mode == "quiz":
            if self._timer_label is not None:
                self._timer_label.value = format_time(self.session.time_now())
                try:
                    self._timer_label.update()
                except Exception:
                    pass
            await asyncio.sleep(1)

    def _toast(self, text):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(text)))
        except Exception:
            print(text)

    # ------------------ Audio / pronunciación ------------------

    def _stop_audio(self):
        player = self._audio_player
        self._audio_player = None
        if player is not None:
            try:
                if player in self.page.services:
                    self.page.services.remove(player)
                    self.page.update()
            except Exception as err:
                print(f"Error deteniendo audio: {err}")

    def _play_audio(self, src):
        """Reproduce un audio opcional del JSON sin await play()/release()."""
        if not src or fta is None:
            return
        self._stop_audio()
        try:
            player = fta.Audio(src=src, autoplay=True)
            self.page.services.append(player)
            self._audio_player = player
            self.page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def listen_again(self, e=None):
        if self.mode == "quiz" and self.session.is_solved() and not self._recording:
            self._play_audio(self.session.current.get("audio"))

    async def _choose(self, option):
        result = self.session.choose(option)
        if result == "ignored":
            return
        self._mic_message = None
        self.render()
        if result == "correct":
            self._play_audio(self.session.current.get("audio"))

    async def _on_mic(self, e=None):
        if self._recording or self.mode != "quiz":
            return
        if not self.session.is_solved():
            self._toast("First choose the correct answer.")
            return
        self._stop_audio()
        self._recording = True
        self._mic_message = None
        current_id = self.session.current["id"]
        answer = self.session.current["answer"]
        self.render()
        try:
            # Se importa aquí para que puedas previsualizar la pantalla
            # aunque todavía no hayas instalado Whisper/sounddevice.
            from services.ejercicios.pronunciacion_oraciones_service import (
                listen_and_check_sentence,
            )
            ok, heard = await asyncio.to_thread(listen_and_check_sentence, answer)
            if self.mode == "quiz" and self.session.current["id"] == current_id:
                self._mic_message = (ok, heard)
                if ok:
                    self.session.mark_pronounced(self.session.current)
        except Exception as err:
            print(f"Error con el micrófono: {err}")
            self._toast("Microphone not available. Check your microphone and dependencies.")
        finally:
            self._recording = False
            if self.mode == "quiz":
                self.render()

    # ------------------ Acciones ------------------

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()
        else:
            self._toast("No hint available.")

    def _on_skip(self, e=None):
        if self._recording:
            return
        self._stop_audio()
        result = self.session.skip()
        self._mic_message = None
        if result == "finished":
            self.mode = "end"
            self._token += 1
        self.render()

    def _on_continue(self, e=None):
        if self._recording:
            return
        result = self.session.advance()
        if result == "blocked":
            self._toast(
                "Say the full answer correctly to continue."
                if self.session.is_solved()
                else "First choose the correct answer."
            )
            return
        self._stop_audio()
        self._mic_message = None
        if result == "finished":
            self._token += 1
            self.mode = "end"
        self.render()

    def _on_pause(self, e=None):
        if self.mode != "quiz" or self._recording:
            return
        self._stop_audio()
        self.session.pause()
        self.mode = "paused"
        self._token += 1
        self.render()

    def _on_resume(self, e=None):
        self.session.resume()
        self.mode = "quiz"
        self._token += 1
        self.render()
        self.page.run_task(self._tick, self._token)

    def _on_finish_now(self, e=None):
        self.session.finish_early()
        self._token += 1
        self.mode = "end"
        self.render()

    def _on_save_exit(self, e=None):
        try:
            self.session.save_progress()
        except Exception as err:
            self._toast(f"Could not save progress: {err}")
            return
        self.close()
        self.on_home()

    def _on_restart(self, e=None):
        self.show(resume=False)

    def _on_home(self, e=None):
        self.close()
        self.on_home()

    # ------------------ Pantallas (solo datos -> componentes) ------------------

    def _feedback(self) -> tuple[str, str] | None:
        if self._mic_message is not None:
            ok, heard = self._mic_message
            if ok:
                return "Great pronunciation!", "success"
            return f'I heard: "{heard or "..."}". Try again.', "error"
        if self.session.is_pronounced():
            return "Great! You can continue.", "success"
        if self.session.is_solved():
            return "Correct! Now say the full answer.", "success"
        if self.session.picked_for():
            return "Wrong answer. Try again.", "error"
        return None

    def _build_quiz(self):
        s = self.session
        ex = s.current
        return ChoiceLayout(
            preset=QUESTIONS_PRESET,
            width=self.w,
            height=self.h,
            title=self.TITLE,
            current=s.number,
            total=s.total,
            time_text=format_time(s.time_now()),
            section_title=self.SECTION,
            prompt="Choose the correct answer",
            hint_text="Read the question and select\nthe best response.",
            # Solo una de las dos imagenes; el texto se monta en el globo del PNG.
            media_builder=lambda k: exercise_illustrated_question(
                src=ex.get("image", ""),
                question=ex["question"],
                scene=ex.get("scene"),
                scale=k,
            ),
            answer_builder=lambda scale: answer_options(
                ex["options"],
                answer=ex["answer"],
                picked=s.picked_for(ex),
                eliminated=s.hint_for(ex),
                solved=s.is_solved(ex),
                on_choose=self._choose,
                scale=scale,
                style=QUESTIONS_PRESET.option_style,
                disabled=self._recording,
            ),
            feedback=self._feedback(),
            on_pause=self._on_pause,
            on_hint=self._on_hint,
            on_skip=self._on_skip,
            on_microphone=self._on_mic,
            on_continue=self._on_continue,   # explica por que sigue bloqueado
            hint_enabled=s.hint_available(ex),
            can_continue=s.can_continue(),
            is_last=s.is_last,
            recording=self._recording,
        )

    def _build_paused(self):
        s = self.session
        return pause_overlay(
            question_text=f"Question {s.number} / {s.total}",
            time_text=format_time(s.time_now()),
            on_resume=self._on_resume,
            on_finish=self._on_finish_now,
            on_save_exit=self._on_save_exit,
            width=self.w,
            height=self.h,
        )

    def _build_end(self):
        st = self.session.summary()
        return results_screen(
            title="Practice Completed!",
            subtitle="Questions & Answers",
            stats=[
                (ft.Icons.ACCESS_TIME, "Total Time", st["time"], BLUE),
                (ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                 f'{st["completed"]} / {st["total"]}', GREEN),
                (ft.Icons.CANCEL_OUTLINED, "Wrong Answers", str(st["errors"]), RED),
                (ft.Icons.SKIP_NEXT, "Skips Used", str(st["skips"]), SOFT),
            ],
            details=[
                ("Correct on First Try", str(st["first_try"])),
                ("XP Earned", f'+{st["xp_earned"]} XP', GREEN),
            ],
            on_retry=self._on_restart,
            on_exit=self._on_home,
            width=self.w,
            height=self.h,
        )

    # ------------------ Render general ------------------

    def render(self):
        if self.mode == "closed":
            return
        if self.mode == "quiz":
            screen, self._timer_label = self._build_quiz()
        elif self.mode == "paused":
            screen = self._build_paused()
        else:
            screen = self._build_end()
        self.shell.width = self.w
        self.shell.height = self.h
        self.shell.content = screen
        self.page.update()