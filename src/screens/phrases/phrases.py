"""Phrases Practice (Flet 1.x). Solo logica: lo visual vive en `exercises`."""

import asyncio
import flet as ft

from services.ejercicios.pronunciacion_oraciones_service import (
    listen_and_check_sentence,
    preload,
)

from ui.exercises.core.exercise_choice_layout import ChoiceLayout, PHRASES_PRESET
from ui.exercises.core.exercise_theme import EXERCISE_PALE_BLUE
from ui.exercises.components.answer_options import answer_options
from ui.exercises.components.exercise_illustration import exercise_illustration
from ui.exercises.components.sound_effects import SoundEffects
from ui.exercises.overlays.pause_overlay import pause_overlay
from ui.exercises.overlays.results_overlay import results_screen
from ui.exercises.core.exercise_theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_SOFT_BLUE as SOFT_BLUE,
)


class PhrasesView:

    TITLE = "Phrases"
    SECTION = "PHRASES"
    ICON = "imagenes/home/frases.png"   # AJUSTA: ruta relativa a assets

    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home

        self.mode = "quiz"
        self._tick_id = 0
        self.sfx = SoundEffects(page)

        self._width = 440
        self._height = 844
        self.shell = ft.Container()
        self._timer_label: ft.Text | None = None  # lo crea ChoiceLayout

        self.rec_state = "idle"
        self.rec_message = None

        preload()

    # =====================================================
    # CICLO DE VIDA
    # =====================================================

    def show(self, resume=False):
        self.mode = "quiz"
        self.sfx.stop()

        if resume and getattr(self.session, "has_progress", False):
            if hasattr(self.session, "resume"):
                self.session.resume()
        else:
            self.session.start()

        self.rec_state = "idle"
        self.rec_message = None

        self._mount()

        self._tick_id += 1
        self.page.run_task(self._tick, self._tick_id)

    def close(self):
        self._tick_id += 1
        self.mode = "closed"
        self.page.on_resize = None
        self.sfx.stop()

    def _mount(self):
        self.page.clean()
        self.page.padding = 0
        self.page.spacing = 0

        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=EXERCISE_PALE_BLUE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell,
            )
        )

        self.page.on_resize = self._fit
        self._fit(force=True)

    def _fit(self, e=None, force=False):
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
        while token == self._tick_id and self.mode == "quiz":
            if self._timer_label is not None:
                self._timer_label.value = self.session.format_time(
                    self.session.time_now()
                )
                try:
                    self._timer_label.update()
                except Exception:
                    pass

            await asyncio.sleep(1)

    # =====================================================
    # MENSAJES
    # =====================================================

    def _toast(self, message):
        try:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text(message))
            )
        except Exception:
            print(message)

    def _finish_ui(self):
        self.mode = "end"
        self._tick_id += 1
        self.sfx.finish()

    # =====================================================
    # ACCIONES DEL EJERCICIO
    # =====================================================

    async def _choose(self, option):
        result = self.session.choose(option)

        if result == "ignored":
            return

        self.rec_message = None
        self.render()

        if result == "correct":
            self.sfx.voice(self.session.current.get("audio"))
        else:
            self.sfx.wrong()

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()
        else:
            self._toast("No hints available.")

    def _on_skip(self, e=None):
        self.sfx.stop_voice()
        self.rec_message = None

        if self.session.skip() == "finished":
            self._finish_ui()

        self.render()

    async def _on_mic(self, e=None):
        ex = self.session.current

        if not self.session.is_solved(ex):
            self._toast("First choose the correct phrase.")
            return

        if self.rec_state != "idle":
            return

        self.sfx.stop_voice()

        self.rec_state = "recording"
        self.rec_message = None
        self.render()

        try:
            ok, heard = await asyncio.to_thread(
                listen_and_check_sentence,
                ex.get("answer", ""),
            )

            self.rec_message = (ok, heard)

            if ok:
                self.session.mark_pronounced(ex)

        except Exception as err:
            print(f"Mic error: {err}")
            self._toast("Could not access the microphone.")

        finally:
            self.rec_state = "idle"

            if self.mode == "quiz":
                self.render()

    def _on_next(self, e=None):
        ex = self.session.current

        if not self.session.can_continue(ex):
            self._toast(
                "Choose the correct phrase first."
                if not self.session.is_solved(ex)
                else "You cannot continue yet."
            )
            return

        self.sfx.stop_voice()

        result = self.session.advance()
        self.rec_message = None

        if result == "finished":
            self._finish_ui()

        self.render()

    # =====================================================
    # PAUSA Y NAVEGACION
    # =====================================================

    def _on_pause(self, e=None):
        if self.mode != "quiz" or self.rec_state != "idle":
            return

        if hasattr(self.session, "pause"):
            self.session.pause()

        self.mode = "paused"
        self._tick_id += 1
        self.render()

    def _on_resume(self, e=None):
        if hasattr(self.session, "resume"):
            self.session.resume()

        self.mode = "quiz"
        self._tick_id += 1
        self.render()

        self.page.run_task(self._tick, self._tick_id)

    def _on_finish_now(self, e=None):
        if hasattr(self.session, "finish_early"):
            self.session.finish_early()

        self._finish_ui()
        self.render()

    def _on_save_exit(self, e=None):
        if hasattr(self.session, "pause"):
            self.session.pause()

        self.close()
        self.on_home()

    def _on_restart(self, e=None):
        self.show()

    def _on_home(self, e=None):
        self.close()
        self.on_home()

    # =====================================================
    # PANTALLAS (solo datos -> componentes)
    # =====================================================

    def _feedback(self, ex) -> tuple[str, str] | None:
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
            preset=PHRASES_PRESET,
            width=self._width,
            height=self._height,
            title=self.TITLE,
            badge_image=self.ICON,
            current=s.number,
            total=s.total,
            time_text=s.format_time(s.time_now()),
            section_title=self.SECTION,
            prompt="Choose the best phrase",
            hint_text="Select the most appropriate phrase\nfor the situation.",
            situation=ex.get("prompt", "Situation"),
            media_builder=lambda k: exercise_illustration(
                ex["image"], scale=k, size=232
            ),
            answer_builder=lambda scale: answer_options(
                ex["options"],
                answer=ex["answer"],
                picked=s.picked_for(ex),
                eliminated=s.hint_for(ex),
                solved=s.is_solved(ex),
                on_choose=self._choose,
                scale=scale,
                style=PHRASES_PRESET.option_style,
            ),
            feedback=self._feedback(ex),
            on_pause=self._on_pause,
            on_hint=self._on_hint,
            on_skip=self._on_skip,
            on_microphone=self._on_mic,
            on_continue=self._on_next,
            hint_enabled=(
                s.hint_available(ex) if hasattr(s, "hint_available") else True
            ),
            can_continue=s.can_continue(ex),
            is_last=s.is_last,
            recording=self.rec_state == "recording",
            mic_disabled=not s.is_solved(ex),
        )

    def _build_paused(self):
        s = self.session
        return pause_overlay(
            question_text=f"Question {s.number} / {s.total}",
            time_text=s.format_time(s.time_now()),
            on_resume=self._on_resume,
            on_finish=self._on_finish_now,
            on_save_exit=self._on_save_exit,
            width=self._width,
            height=self._height,
        )

    def _build_end(self):
        st = self.session.summary()
        return results_screen(
            title="Practice Completed!",
            subtitle="Great job! You finished your phrases practice.",
            stats=[
                (ft.Icons.ACCESS_TIME, "Total Time", st["time"], BLUE),
                (ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                 f'{st["completed"]} / {st["total"]}', GREEN),
                (ft.Icons.CANCEL_OUTLINED, "Wrong Answers", str(st["errors"]), RED),
                (ft.Icons.SKIP_NEXT, "Skips Used", str(st["skips"]), SOFT_BLUE),
            ],
            details=[
                ("XP Earned", f'+{st["xp_earned"]} XP', GREEN),
                ("Total XP", f'{st["xp_total"]} XP'),
            ],
            on_retry=self._on_restart,
            on_exit=self._on_home,
            width=self._full_size()[0],
            height=self._full_size()[1],
        )

    # =====================================================
    # RENDER
    # =====================================================

    def _full_size(self):
        """Tamano real de la ventana (para la pantalla final)."""
        return (self.page.width or self._width, self.page.height or self._height)

    def render(self):
        if self.mode == "closed":
            return
        w, h = self._width, self._height
        if self.mode == "quiz":
            screen, self._timer_label = self._build_quiz()
        elif self.mode == "paused":
            # El ejercicio queda debajo y la pausa se dibuja encima.
            quiz, self._timer_label = self._build_quiz()
            screen = ft.Stack(
                width=w,
                height=h,
                controls=[quiz, self._build_paused()],
            )
        else:
            # Pantalla final: ocupa todo el espacio de la ventana.
            w, h = self._full_size()
            screen = self._build_end()

        self.shell.width = w
        self.shell.height = h
        self.shell.content = screen
        self.page.update()