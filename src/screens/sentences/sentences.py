import asyncio
import hashlib
import time
import re
import os
from pathlib import Path
import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None

from services.ejercicios.sentences_service import format_time
from services.ejercicios.pronunciacion_oraciones_service import (
    listen_and_check_sentence, normalize_sentence,
    preload as preload_sentences,
)

# AJUSTA esta ruta a donde pusiste la carpeta `exercises` (ej. ui/exercises).
from ui.exercises.core.exercise_common import exercise_text
from ui.exercises.core.exercise_frame import ExerciseFrame
from ui.exercises.core.exercise_footer import SENTENCE_FOOTER, footer_slots
from ui.exercises.core.exercise_theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_NAVY as NAVY,
    EXERCISE_PALE_BLUE,
    EXERCISE_RED as RED,
    EXERCISE_SOFT_BLUE as SOFT,
)
from ui.exercises.components.exercise_buttons import action_button
from ui.exercises.components.exercise_feedback import exercise_feedback
from ui.exercises.components.exercise_heading import exercise_section_heading
from ui.exercises.components.exercise_illustration import exercise_illustration
from ui.exercises.components.exercise_text_input import exercise_text_input
from ui.exercises.components.sound_effects import SoundEffects
from ui.exercises.overlays.pause_overlay import pause_overlay
from ui.exercises.overlays.results_overlay import results_screen


class SentencesView:

    TITLE = "Sentences"
    SECTION = "SENTENCES"
    ICON = "imagenes/home/oraciones .png"   

    def __init__(self, page: ft.Page, session, on_home, achievements=None):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.achievements = achievements
        self.mode = "quiz"  # quiz | paused | end | closed
        self.token = 0
        self.w, self.h = 440, 844
        self.shell = ft.Container()
        self._timer_label: ft.Text | None = None  # lo crea ExerciseFrame
        self.is_recording = False
        self.rec_message = None
        self.rec_ok = False
        self.typed_value = ""
        self.text_feedback = ""
        self.text_ok = set()
        self.spoken_ok = set()
        self.hint_message = ""
        self.paused_at = "00:00"
        self.final_time = "00:00"
        # Permite pausar visualmente incluso en versiones antiguas del servicio.
        self._pause_offset = 0.0
        self._pause_started = None
        self._audio_player = None
        self._audio_request = 0
        # Efectos (wrong / finish). El audio de las oraciones sigue usando
        # su propio reproductor (_audio_player) para no mezclarse.
        self.sfx = SoundEffects(page)

    # =============== AUDIO DE ORACIONES ===============

    @staticmethod
    def _sentence_audio_src(sentence):
        """Misma regla de nombres que generar_audios_sentences.py."""
        sentence = sentence.strip()
        slug = re.sub(r"[^a-z0-9]+", "_", sentence.lower()).strip("_")[:42].rstrip("_")
        slug = slug or "sentence"
        digest = hashlib.sha1(sentence.encode("utf-8")).hexdigest()[:10]
        return f"audio/sentences/{slug}_{digest}.mp3"

    def _remove_audio_service(self):
        """Retira el reproductor anterior sin esperar una llamada nativa bloqueante.

        Evitamos ``await player.release()``: en algunas versiones de Flet
        esa llamada puede terminar en TimeoutException de 30 segundos.
        """
        player = self._audio_player
        self._audio_player = None
        if player is None:
            return
        try:
            if player in self.page.services:
                self.page.services.remove(player)
                self.page.update()
        except Exception as err:
            print(f"No se pudo retirar el reproductor: {err}")

    async def _release_audio(self):
        """Mantiene la firma async que usa microphone()."""
        self._remove_audio_service()

    def _stop_audio(self):
        """Cancela reproducciones pendientes al cambiar de ejercicio."""
        self._audio_request += 1
        self._remove_audio_service()

    async def _play_sentence_audio(self, key, sentence):
        """Reproduce un MP3 local mediante autoplay, sin invocar play().

        El src que recibe Flet es relativo al assets_dir configurado en main.py.
        """
        if fta is None:
            self.snack("Instala flet-audio: uv add flet-audio")
            return

        self._audio_request += 1
        request = self._audio_request
        self._remove_audio_service()
        if request != self._audio_request or self.mode != "quiz" or key != self._key():
            return

        src = self._sentence_audio_src(sentence)
        # Busca el archivo en assets, aunque la vista esté en una subcarpeta.
        # El reproductor siempre recibe la ruta relativa a assets_dir.
        posibles = []
        if os.environ.get("FLET_ASSETS_DIR"):
            posibles.append(Path(os.environ["FLET_ASSETS_DIR"]) / src)
        posibles += [p / "assets" / src for p in Path(__file__).resolve().parents]
        ruta_local = next((p for p in posibles if p.is_file()), None)
        if ruta_local is None:
            print("MP3 NO ENCONTRADO. Se buscó en:")
            for p in posibles:
                print(" -", p)
            self.snack(f"No encuentro el audio: {src}")
            return

        try:
            print(f"Cargando audio: {src} ({ruta_local.stat().st_size} bytes)")
            player = fta.Audio(
                src=src,
                autoplay=True,  # Flet reproduce cuando el servicio se monta
                release_mode=fta.ReleaseMode.STOP,
                on_loaded=lambda e: print(f"Audio cargado: {src}"),
                on_state_change=lambda e: print(
                    f"Estado audio {src}: {getattr(e, 'state', 'desconocido')}"
                ),
            )
            self.page.services.append(player)
            self._audio_player = player
            self.page.update()
            # No llamar await player.play() inmediatamente después de montar:
            # algunas versiones/entornos no completan esa operación y esperan 30 s.
        except Exception as err:
            print(f"No se pudo iniciar audio {src}: {err}")
            self._remove_audio_service()
            self.snack(f"No se pudo reproducir el audio: {src}")

    def listen_again(self, e=None):
        """Permite escuchar nuevamente la oración después de escribirla bien."""
        if self.mode == "quiz" and self._written_ready() and not self.is_recording:
            self.page.run_task(
                self._play_sentence_audio,
                self._key(),
                self._expected_sentence(self.session.current),
            )

    # =============== CICLO DE VIDA ===============

    def show(self, resume=False):
        self._stop_audio()
        self.sfx.stop()
        self.token += 1
        self.mode = "quiz"
        self.is_recording = False
        self.rec_message = None
        self.rec_ok = False
        self.typed_value = ""
        self.text_feedback = ""
        self.text_ok.clear()
        self.spoken_ok.clear()
        self.hint_message = ""
        # Carga el modelo local sin bloquear la interfaz.
        preload_sentences()
        self._pause_offset = 0.0
        self._pause_started = None
        self.final_time = "00:00"
        has_progress = getattr(self.session, "has_progress", False)
        if callable(has_progress):
            has_progress = has_progress()
        if resume and has_progress and callable(getattr(self.session, "resume", None)):
            self.session.resume()
        else:
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
        self.page.on_resize = self.resize
        self.resize()
        self.page.run_task(self.tick, self.token)

    def close(self):
        self._stop_audio()
        self.sfx.stop()
        self.token += 1
        self.mode = "closed"
        self.page.on_resize = None

    def resize(self, e=None):
        ancho = min(max(self.page.width or 440, 280), 520)
        alto = max(self.page.height or 844, 400)
        if abs(ancho - self.w) > 1 or abs(alto - self.h) > 1 or self.shell.content is None:
            self.w = ancho
            self.h = alto
            self.render()

    def _native_pause(self):
        return (callable(getattr(self.session, "pause", None)) and
                callable(getattr(self.session, "resume", None)))

    def _tiempo_activo(self):
        """Segundos activos. El fallback no cambia el estado interno del servicio."""
        actual = self.session.time_now()
        if self._native_pause():
            return actual
        if isinstance(actual, (int, float)):
            descuento = self._pause_offset
            if self._pause_started is not None:
                descuento += time.monotonic() - self._pause_started
            return max(0, actual - descuento)
        return actual

    async def tick(self, token):
        while token == self.token and self.mode == "quiz":
            if self._timer_label is not None:
                self._timer_label.value = format_time(self._tiempo_activo())
                try:
                    self._timer_label.update()
                except Exception:
                    pass
            await asyncio.sleep(1)

    # =============== INTERACCIONES ===============

    def snack(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception:
            try:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                print(message)

    # =============== RESPUESTA ESCRITA + ORACIÓN HABLADA ===============

    @staticmethod
    def _normalize_written(value):
        return normalize_sentence(value)

    @staticmethod
    def _expected_sentence(ex):
        # Si sentences_service tiene la oración completa, se usa directamente.
        for key in ("sentence", "full_sentence", "expected_sentence"):
            if ex.get(key):
                return str(ex[key]).strip()
        prompt = str(ex.get("prompt") or "")
        answer = str(ex.get("answer") or "").strip()
        # Ej.: "She ___ a book." + "reads" -> "She reads a book."
        blank = r"_{2,}|\{blank\}|\[blank\]|\.{3,}|…+"
        if re.search(blank, prompt, flags=re.I):
            return re.sub(blank, lambda _: answer, prompt, count=1, flags=re.I).strip()
        return answer  # Requiere `sentence` si prompt no incluye hueco.

    def _key(self):
        return (self.session.number, str(self.session.current.get("prompt", "")))

    def _written_ready(self):
        return self._key() in self.text_ok and self.session.is_solved()

    def _spoken_ready(self):
        return self._key() in self.spoken_ok

    def _reset_exercise(self):
        self.typed_value = ""
        self.text_feedback = ""
        self.rec_message = None
        self.rec_ok = False
        self.hint_message = ""

    def on_text_change(self, e):
        if not self._written_ready():
            self.typed_value = e.control.value or ""

    def check_written(self, e=None):
        if self.mode != "quiz" or self.is_recording:
            return
        if self._written_ready():
            return
        ex = self.session.current
        typed = self._normalize_written(self.typed_value)
        expected = self._expected_sentence(ex)
        answer = str(ex["answer"])
        play_sentence = None
        # Para ejercicios con hueco aceptamos tanto una palabra como la oración.
        valid = {self._normalize_written(answer), self._normalize_written(expected)}
        if not typed:
            self.text_feedback = "Write your answer first."
        elif typed in valid:
            result = self.session.choose(ex["answer"])
            if result == "correct" or self.session.is_solved(ex):
                self.text_ok.add(self._key())
                self.text_feedback = "Correct! Listen, then say the sentence."
                # Se dispara DESPUES de renderizar para que Flet ya tenga UI montada.
                play_sentence = expected
            else:
                self.text_feedback = "The session could not save your answer."
        else:
            # Llamamos al servicio si puede registrar un error sin pasar por una opción.
            wrong = getattr(self.session, "register_wrong_answer", None)
            if callable(wrong):
                try:
                    wrong()
                except TypeError:
                    pass  # El servicio puede exigir otra firma.
            self.text_feedback = "Not quite. Check your sentence and try again."
            self.sfx.wrong()
        self.render()
        if play_sentence is not None:
            self.page.run_task(self._play_sentence_audio, self._key(), play_sentence)

    def hint(self, e=None):
        if self.mode != "quiz" or self._written_ready():
            return
        ex = self.session.current
        available = getattr(self.session, "hint_available", None)
        if callable(available) and not available(ex):
            self.snack("No hints available.")
            return
        use = getattr(self.session, "use_hint", None)
        if callable(use) and not use():
            self.snack("No hints available.")
            return
        answer = str(ex.get("answer", ""))
        self.hint_message = f"Hint: the missing part starts with '{answer[:2]}…'"
        self.render()

    def skip(self, e=None):
        if self.mode != "quiz" or self.is_recording:
            return
        self._stop_audio()
        result = self.session.skip()
        if result == "finished":
            self._show_end()
            return
        if result in ("blocked", "ignored", False, None):
            self.snack("You cannot skip this exercise.")
        else:
            self._reset_exercise()
            self.render()

    def continue_quiz(self, e=None):
        if self.mode != "quiz" or self.is_recording:
            return
        if not self._written_ready():
            self.snack("First write the correct answer.")
            return
        if not self._spoken_ready():
            self.snack("Now pronounce the complete sentence.")
            return

        # El servicio puede devolver "next", "finished" o None incluso
        # cuando YA cambió de ejercicio. Por eso comprobamos el estado real
        # y no interpretamos None automáticamente como un bloqueo.
        self._stop_audio()
        before_key = self._key()
        before_number = getattr(self.session, "number", None)
        was_last = bool(self.session.is_last)
        result = self.session.advance()
        moved = (
            self._key() != before_key
            or getattr(self.session, "number", None) != before_number
        )

        if result == "finished":
            self._show_end()
            return

        # Algunos servicios avanzan con None o True; otros retornan "next".
        # Si realmente cambió la pregunta, el avance fue exitoso.
        if moved:
            self._reset_exercise()
            self.render()
            return

        # Si el último ejercicio se marcó como finalizado internamente,
        # mostrar resultados incluso si advance() no devolvió "finished".
        if was_last and result not in ("blocked", "ignored", False):
            finished = getattr(self.session, "finished", None)
            if callable(finished):
                finished = finished()
            if finished is True or result in ("next", "advanced", True):
                self._show_end()
                return

        if result == "blocked":
            self.snack("The session has not unlocked Continue. Check the pronunciation state.")
        else:
            self.snack("The session did not advance. Check sentences_service.py (advance).")

    async def microphone(self, e=None):
        if self.mode != "quiz" or self.is_recording:
            return
        if not self._written_ready():
            self.snack("First write and check the correct answer.")
            return
        key = self._key()
        sentence = self._expected_sentence(self.session.current)
        self.is_recording = True
        self.rec_ok = False
        self.rec_message = None
        self._stop_audio()
        self.render()
        try:
            # No grabar el MP3 reproducido: podría engañar al reconocimiento.
            await self._release_audio()
            ok, heard = await asyncio.to_thread(listen_and_check_sentence, sentence)
            # Evitar aplicar un resultado si la pregunta cambió.
            if self.mode == "quiz" and key == self._key():
                self.rec_ok = bool(ok)
                if ok:
                    # La interfaz debe avisar a la sesión de que se pronunció bien;
                    # si advance() exige is_pronounced(), devolvería "blocked".
                    mark = getattr(self.session, "mark_pronounced", None)
                    if callable(mark):
                        try:
                            mark(self.session.current)
                        except TypeError:
                            # Compatibilidad con servicios que no reciben ex.
                            mark()
                        except Exception as err:
                            print(f"Could not mark pronunciation in session: {err}")
                            self.rec_message = "Pronunciation was correct but could not be saved."
                            self.render()
                            return
                    self.spoken_ok.add(key)
                    self.rec_message = "Great! You pronounced the sentence."
                else:
                    self.rec_message = f'I heard: "{heard or "(silence)"}". Try again.'
        except Exception as err:
            print(f"Sentence microphone error: {err}")
            self.rec_message = "Microphone unavailable. Check the audio device."
        finally:
            self.is_recording = False
            if self.mode == "quiz":
                self.render()

    def pause(self, e=None):
        if self.mode != "quiz" or self.is_recording:
            return
        self._stop_audio()
        self.paused_at = format_time(self._tiempo_activo())
        if self._native_pause():
            self.session.pause()
        else:
            self._pause_started = time.monotonic()
        # La vista deja de actualizar el reloj. El servicio debe detener su
        # cronometro real mediante pause() para no sumar tiempo en la pausa.
        self.mode = "paused"
        self.token += 1
        self.render()

    def resume(self, e=None):
        if self.mode != "paused":
            return
        if self._native_pause():
            self.session.resume()
        elif self._pause_started is not None:
            self._pause_offset += time.monotonic() - self._pause_started
            self._pause_started = None
        self.mode = "quiz"
        self.token += 1
        self.render()
        self.page.run_task(self.tick, self.token)

    def finish_now(self, e=None):
        if self.mode not in ("quiz", "paused"):
            return
        finish_fn = getattr(self.session, "finish_early", None)
        if callable(finish_fn):
            finish_fn()
        self._show_end()

    def _show_end(self):
        self._stop_audio()
        self.final_time = format_time(self._tiempo_activo())
        self.token += 1
        self.mode = "end"
        self.sfx.finish()
        self.render()

    def save_exit(self, e=None):
        # Conserva el progreso si el servicio implementa pause/resume.
        if self.mode == "quiz":
            pause_fn = getattr(self.session, "pause", None)
            if callable(pause_fn):
                pause_fn()
        self.home()

    def home(self, e=None):
        self.close()
        self.on_home()

    def restart(self, e=None):
        self.show()

    # =============== PANTALLAS (solo datos -> componentes) ===============

    def _feedback(self) -> tuple[str, str] | None:
        """Mensaje de feedback como (texto, kind) o None."""
        if self.rec_message:
            return self.rec_message, "success" if self.rec_ok else "error"
        if self.text_feedback:
            return self.text_feedback, "success" if self._written_ready() else "error"
        if self.hint_message:
            return self.hint_message, "info"
        return None

    def build_quiz(self):
        ex = self.session.current
        ready = self._written_ready()
        spoken = self._spoken_ready()
        prompt_display = self._expected_sentence(ex) if ready else ex["prompt"]

        hint_available = getattr(self.session, "hint_available", None)
        can_hint = not ready and (not callable(hint_available) or hint_available(ex))

        def slots(slot, k):
            pieces = [
                slot(36, 75, 348, 38, exercise_section_heading(self.SECTION, k)),
                slot(20, 116, 380, 52,
                     exercise_text("Write the sentence", 27 * k, NAVY, bold=True, max_lines=2)),
                slot(32, 172, 356, 34,
                     exercise_text("Complete it, then say the full sentence aloud.",
                                   13 * k, SOFT, max_lines=2)),
                slot(88, 209, 244, 244, exercise_illustration(ex["image"], scale=k, size=238)),
                slot(26, 456, 368, 75,
                     exercise_text(prompt_display, 21 * k, GREEN if ready else NAVY,
                                   bold=True, max_lines=3)),
                slot(38, 537, 344, 79,
                     exercise_text_input(
                         self.typed_value,
                         hint_text="Type the missing word or complete sentence…",
                         on_change=self.on_text_change,
                         on_submit=self.check_written,
                         read_only=ready,
                         correct=ready,
                         scale=k,
                     )),
                slot(120, 630, 180, 44,
                     action_button(
                         "Listen again" if ready else "Check answer",
                         ft.Icons.VOLUME_UP if ready else ft.Icons.CHECK,
                         self.listen_again if ready else self.check_written,
                         color=GREEN if ready else BLUE,
                         scale=k,
                     )),
            ]

            fb = self._feedback()
            if fb is not None:
                message, kind = fb
                pieces.append(slot(30, 681, 360, 38,
                                   exercise_feedback(message, kind, k, max_lines=2)))

            pieces += footer_slots(
                slot, k, SENTENCE_FOOTER,
                on_hint=self.hint,
                on_skip=self.skip,
                on_mic=self.microphone,
                on_continue=self.continue_quiz,   # explica el bloqueo con un snack
                hint_enabled=can_hint,
                skip_enabled=not self.is_recording,
                mic_disabled=not ready,
                recording=self.is_recording,
                caption=("Listening…" if self.is_recording
                         else "Pronunciation accepted ✓" if spoken
                         else "Tap to speak the full sentence"),
                caption_color=GREEN if spoken else SOFT,
                can_continue=ready and spoken,
                is_last=bool(self.session.is_last),
            )
            return pieces

        return ExerciseFrame(
            width=self.w,
            height=self.h,
            title=self.TITLE,
            badge_image=self.ICON,
            current=self.session.number,
            total=self.session.total,
            time_text=format_time(self._tiempo_activo()),
            on_pause=self.pause,
            slots=slots,
            min_sheet_height=260,
        )

    def build_paused(self):
        return pause_overlay(
            question_text=f"Question {self.session.number} / {self.session.total}",
            time_text=self.paused_at,
            on_resume=self.resume,
            on_finish=self.finish_now,
            on_save_exit=self.save_exit,
            width=self.w,
            height=self.h,
        )

    def build_end(self):
        stats = self.session.summary()
        tiempo_final = stats.get("time", self.final_time)
        if not self._native_pause():
            tiempo_final = self.final_time
        total = stats.get("total", self.session.total)
        return results_screen(
            stats=[
                (ft.Icons.ACCESS_TIME, "Total Time", tiempo_final, BLUE),
                (ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                 f'{stats.get("completed", 0)} / {total}', GREEN),
                (ft.Icons.CANCEL_OUTLINED, "Wrong Answers",
                 str(stats.get("errors", 0)), RED),
                (ft.Icons.SKIP_NEXT, "Skips Used", str(stats.get("skips", 0)), SOFT),
            ],
            details=[
                ("XP Earned", f'+{stats.get("xp_earned", 0)} XP', GREEN),
                ("Total XP", f'{stats.get("xp_total", 0)} XP'),
            ],
            on_retry=self.restart,
            on_exit=self.home,
            width=self._full_size()[0],
            height=self._full_size()[1],
        )

    # =============== RENDER ===============

    def _full_size(self):
        """Tamano real de la ventana (para la pantalla final)."""
        return (self.page.width or self.w, self.page.height or self.h)

    def render(self):
        if self.mode == "closed":
            return
        w, h = self.w, self.h
        if self.mode == "quiz":
            screen, self._timer_label = self.build_quiz()
        elif self.mode == "paused":
            # El ejercicio queda debajo y la pausa se dibuja encima.
            quiz, self._timer_label = self.build_quiz()
            screen = ft.Stack(
                width=w,
                height=h,
                controls=[quiz, self.build_paused()],
            )
        else:
            # Pantalla final: ocupa todo el espacio de la ventana.
            w, h = self._full_size()
            screen = self.build_end()

        self.shell.width = w
        self.shell.height = h
        self.shell.content = screen
        self.page.update()