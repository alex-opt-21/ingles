import asyncio
import flet as ft

from services.ejercicios.ejercicio_service import QuizSession, format_time
from services.ejercicios.pronunciacion_service import listen_and_check

# AJUSTA esta ruta a donde pusiste la carpeta `exercises` (ej. ui/exercises).
from ui.exercises.core.exercise_choice_layout import ChoiceLayout, QUIZ_PRESET
from ui.exercises.components.answer_options import answer_options
from ui.exercises.components.exercise_illustration import exercise_illustration
from ui.exercises.components.sound_effects import SoundEffects
from ui.exercises.overlays.pause_overlay import pause_overlay
from ui.exercises.overlays.results_overlay import results_screen
from ui.exercises.core.exercise_theme import (
    EXERCISE_BLUE,
    EXERCISE_GREEN,
    EXERCISE_PALE_BLUE,
    EXERCISE_RED,
    EXERCISE_SOFT_BLUE,
)


class QuizView:

    TITLE = "Flash Cards"
    SECTION = "LOOK & CHOOSE"
    ICON = "imagenes/home/tarjetas .png"   # ruta relativa a assets

    def __init__(self, page: ft.Page, session: QuizSession, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"       # quiz | paused | end | closed
        self._tick_id = 0
        self.sfx = SoundEffects(page)
        self.rec_state = "idle"
        self.rec_message = None
        self._width = 440
        self._height = 844
        self._timer_label: ft.Text | None = None   # lo crea el layout
        self.shell = ft.Container()

    # ---------- Ciclo de vida ----------

    def show(self, resume=False):
        self.mode = "quiz"
        self._tick_id += 1
        if resume and self.session.has_progress:
            self.session.resume()
        else:
            self.session.start()
        self.rec_state = "idle"
        self.rec_message = None
        self._mount()
        self.page.run_task(self._tick, self._tick_id)

    def close(self):
        if self.session.has_progress:
            self.session.pause()
            self.session.persist_now()
        self._tick_id += 1
        self.mode = "closed"
        self.page.on_resize = None
        self.sfx.stop()

    def _mount(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=EXERCISE_PALE_BLUE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell,
            )
        )
        self.page.on_resize = self._fit_card
        self._fit_card(force=True)

    def _fit_card(self, e=None, force=False):
        width = max(270, min(self.page.width or 440, 520))
        height = max(360, self.page.height or 844)
        if (
            force
            or abs(width - self._width) > 1
            or abs(height - self._height) > 1
            or self.shell.content is None
        ):
            self._width = width
            self._height = height
            self.render()

    async def _tick(self, token):
        ticks_since_save = 0
        while self._tick_id == token and self.mode == "quiz":
            if self._timer_label is not None:
                self._timer_label.value = format_time(self.session.time_now())
                try:
                    self._timer_label.update()
                except Exception:
                    pass

            # Guarda el tiempo cada 5 s por si se cierra la app sin Save & Exit.
            ticks_since_save += 1
            if ticks_since_save >= 5:
                self.session.persist_now()
                ticks_since_save = 0

            await asyncio.sleep(1)

    # ---------- Mensajes y acciones de QuizSession ----------

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception as err:
            print(f"{message} ({err})")

    async def _choose(self, option):
        result = self.session.choose(option)
        if result == "ignored":
            return
        self.render()
        if result == "correct":
            self.sfx.voice(self.session.current.get("audio"))
        else:
            self.sfx.wrong()

    def _on_back(self, e=None):
        self.rec_message = None
        if self.session.back():
            self.render()
        else:
            self._on_home()

    def _finish_ui(self):
        self.mode = "end"
        self._tick_id += 1
        self.sfx.finish()

    def _on_next(self, e=None):
        result = self.session.advance()
        if result == "blocked":
            if self.session.is_solved():
                self._toast("Say the word correctly to continue.")
            else:
                self._toast("First choose the correct answer.")
            return
        self.rec_message = None
        if result == "finished":
            self._finish_ui()
        self.render()

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()

    def _on_skip(self, e=None):
        self.rec_message = None
        result = self.session.skip()
        if result == "finished":
            self._finish_ui()
        self.render()

    async def _on_listen(self, e=None):
        ex = self.session.current
        if self.session.is_solved(ex):
            self.sfx.voice(ex.get("audio"))
        else:
            self._toast("First choose the correct answer.")

    async def _on_mic(self, e=None):
        ex = self.session.current
        if not self.session.is_solved(ex):
            self._toast("First choose the correct answer.")
            return
        if self.rec_state != "idle":
            return
        self.rec_state = "recording"
        self.rec_message = None
        self.render()
        try:
            result = await asyncio.to_thread(listen_and_check, ex["answer"])
            self.rec_message = result
            if result[0]:
                self.session.mark_pronounced(ex)
        except Exception as err:
            print(f"Mic error: {err}")
            self._toast("Could not access the microphone.")
        finally:
            self.rec_state = "idle"
            if self.mode == "quiz":
                self.render()

    # ---------- Pausa y navegacion ----------

    def _on_pause(self, e=None):
        if self.mode != "quiz" or self.rec_state != "idle":
            return
        self.session.pause()
        self.mode = "paused"
        self._tick_id += 1
        self.render()

    def _on_resume(self, e=None):
        self.session.resume()
        self.mode = "quiz"
        self.render()
        self._tick_id += 1
        self.page.run_task(self._tick, self._tick_id)

    def _on_finish_now(self, e=None):
        # Finish now cierra la practica y elimina la sesion pendiente.
        self.session.finish_early()
        self._finish_ui()
        self.render()

    def _on_save_exit(self, e=None):
        self.session.pause()
        self.session.persist_now()
        self.close()
        self.on_home()

    def _on_restart(self, e=None):
        self.show()

    def _on_home(self, e=None):
        if self.session.has_progress:
            self.session.pause()
            self.session.persist_now()
        self.close()
        self.on_home()

    # ---------- Construccion de pantallas (solo datos -> componentes) ----------

    def _feedback(self, ex) -> tuple[str, str] | None:
        """Mensaje de feedback como (texto, kind) o None."""
        s = self.session
        if self.rec_message is not None and s.is_solved(ex):
            ok, heard = self.rec_message
            if ok:
                return "Great pronunciation!", "success"
            return f'I heard "{heard or "..."}". Try again.', "error"
        if s.is_solved(ex):
            if s.is_pronounced(ex):
                return "Correct!", "success"
            return "Correct! Now say it aloud.", "success"
        if s.picked_for(ex):
            return "Wrong. Try again.", "error"
        return None

    def _build_quiz(self):
        s = self.session
        ex = s.current
        return ChoiceLayout(
            preset=QUIZ_PRESET,
            width=self._width,
            height=self._height,
            title=self.TITLE,
            badge_image=self.ICON,
            current=s.number,
            total=s.total,
            time_text=format_time(s.time_now()),
            section_title=self.SECTION,
            prompt=ex["prompt"],
            hint_text=ex["hint"],
            media_builder=lambda k: exercise_illustration(ex["image"], scale=k),
            answer_builder=lambda scale: answer_options(
                ex["options"],
                answer=ex["answer"],
                picked=s.picked_for(ex),
                eliminated=s.hint_for(ex),
                solved=s.is_solved(ex),
                on_choose=self._choose,
                scale=scale,
                style=QUIZ_PRESET.option_style,
            ),
            feedback=self._feedback(ex),
            on_pause=self._on_pause,
            on_hint=self._on_hint,
            on_skip=self._on_skip,
            on_microphone=self._on_mic,
            on_continue=self._on_next,
            hint_enabled=s.hint_available(ex),
            can_continue=s.can_continue(),
            is_last=s.is_last,
            recording=self.rec_state == "recording",
        )

    def _build_paused(self):
        s = self.session
        return pause_overlay(
            question_text=f"Question {s.number} / {s.total}",
            time_text=format_time(s.time_now()),
            on_resume=self._on_resume,
            on_finish=self._on_finish_now,
            on_save_exit=self._on_save_exit,
            width=self._width,
            height=self._height,
        )

    def _build_end(self):
        st = self.session.summary()
        return results_screen(
            stats=[
                (ft.Icons.ACCESS_TIME, "Total Time", st["time"], EXERCISE_BLUE),
                (ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                 f'{st["completed"]} / {st["total"]}', EXERCISE_GREEN),
                (ft.Icons.CANCEL_OUTLINED, "Wrong Answers", str(st["errors"]), EXERCISE_RED),
                (ft.Icons.SKIP_NEXT, "Skips Used", str(st["skips"]), EXERCISE_SOFT_BLUE),
            ],
            details=[
                ("Correct on First Try", f'{st["first_try"]} / {st["total"]}'),
                ("XP Earned", f'+{st["xp_earned"]} XP', EXERCISE_GREEN),
                ("Total XP", f'{st["xp_total"]} XP'),
            ],
            on_retry=self._on_restart,
            on_exit=self._on_home,
            width=self._width,
            height=self._height,
        )

    # ---------- Render ----------

    def render(self):
        if self.mode == "closed":
            return
        if self.mode == "quiz":
            screen, self._timer_label = self._build_quiz()
        elif self.mode == "paused":
            screen = self._build_paused()
        else:
            screen = self._build_end()

        self.shell.width = self._width
        self.shell.height = self._height
        self.shell.content = screen
        self.page.update()