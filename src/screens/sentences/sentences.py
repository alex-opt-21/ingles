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
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
)

# Imágenes que ya usas en la pantalla Action Practice.
FONDO_NUBES = "imagenes/fondo_nubes.png"
HOJA_CENTRAL = "imagenes/hoja_central.png"

# Base de posiciones de la hoja: todo queda PEGADO al papel, sin scroll.
HOJA_BASE_W = 420
HOJA_BASE_H = 870
ALTURA_MAX_HOJA = 850
RESERVA_VERTICAL = 96

CREMA = "#FFFCF7"
AZUL_CLARO = "#EAF4FF"
BORDE_AZUL = "#A6CFFF"
BLOQUEADO = "#D5DCE8"
LETRA_BLOQUEADA = "#8A97B0"
GRIS_CLARO = "#E9EDF4"


def sombra(opacidad=0.10, blur=10, dy=3):
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(opacidad, "#153C81"),
        blur_radius=blur,
        offset=ft.Offset(0, dy),
    )


class SentencesView:
    """Conserva la interfaz pública anterior: show(), close(), render()."""

    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"  # quiz | paused | end | closed
        self.token = 0
        self.w, self.h = 440, 844
        self.shell = ft.Container()
        self.timer_text = ft.Text("00:00")
        self.counter_text = ft.Text("1 / 16")
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
            bgcolor=AZUL_CLARO,
            alignment=ft.Alignment.TOP_CENTER,
            content=self.shell,
        ))
        self.page.on_resize = self.resize
        self.resize()
        self.page.run_task(self.tick, self.token)

    def close(self):
        self._stop_audio()
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
            self.timer_text.value = format_time(self._tiempo_activo())
            try:
                self.timer_text.update()
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
                    # MUY IMPORTANTE: la interfaz sabía que se pronunció
                    # correctamente, pero antes NO avisaba a SentencesSession.
                    # Si advance() exige is_pronounced(), devolvía "blocked".
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

    # =============== COMPONENTES DE FLET ===============

    def txt(self, value, size=16, color=NAVY, bold=False, italic=False,
            lines=2, align=ft.TextAlign.CENTER):
        return ft.Text(
            str(value),
            size=size,
            color=color,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            italic=italic,
            font_family=FONT,
            text_align=align,
            max_lines=lines,
        )

    def header(self):
        k = min(1.0, (self.w - 24) / 440)
        badge = ft.Container(
            width=46*k, height=48*k,
            bgcolor=BLUE,
            border_radius=15*k,
            border=ft.Border.all(max(1, 2*k), WHITE),
            shadow=sombra(0.19, 7*k, 3*k),
            alignment=ft.Alignment.CENTER,
            content=self.txt("A", 29*k, WHITE, bold=True, italic=True, lines=1),
        )
        self.timer_text.color = NAVY
        self.timer_text.size = 15*k
        self.timer_text.weight = ft.FontWeight.BOLD
        self.timer_text.font_family = FONT
        self.counter_text.value = f"{self.session.number} / {self.session.total}"
        self.counter_text.color = NAVY
        self.counter_text.size = 15*k
        self.counter_text.weight = ft.FontWeight.BOLD
        self.counter_text.font_family = FONT

        def pill(content, on_click=None):
            return ft.Container(
                height=40*k,
                bgcolor=WHITE,
                border=ft.Border.all(max(1, 2*k), AZUL_CLARO),
                border_radius=22*k,
                padding=ft.Padding.symmetric(horizontal=8*k),
                shadow=sombra(0.07, 6*k, 2*k),
                alignment=ft.Alignment.CENTER,
                ink=on_click is not None,
                on_click=on_click,
                content=content,
            )

        reloj = pill(ft.Row(
            tight=True,
            spacing=3*k,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE, size=16*k, color=BLUE),
                self.timer_text,
            ],
        ), self.pause)
        contador = pill(self.counter_text)
        return ft.Container(
            height=53*k,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3*k,
                controls=[
                    ft.Row(
                        tight=True, spacing=6*k,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[badge, self.txt("Sentence Practice", 15*k, NAVY,
                                                  bold=True, italic=True, lines=1)],
                    ),
                    ft.Row(
                        tight=True, spacing=5*k,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[reloj, contador],
                    ),
                ],
            ),
        )

    def etiqueta(self, k):
        return ft.Container(
            bgcolor="#B3D7FF",
            border_radius=12*k,
            alignment=ft.Alignment.CENTER,
            content=self.txt("SENTENCES", 18*k, NAVY, bold=True, italic=True, lines=1),
        )

    def imagen_ejercicio(self, src, k):
        return ft.Container(
            width=238*k,
            height=238*k,
            padding=8*k,
            bgcolor=CREMA,
            border_radius=32*k,
            border=ft.Border.all(max(1, 2*k), "#F0E9E0"),
            shadow=sombra(0.09, 9*k, 3*k),
            content=ft.Container(
                bgcolor=AZUL_CLARO,
                border_radius=24*k,
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src=src,
                    fit=ft.BoxFit.CONTAIN,
                    width=222*k,
                    height=222*k,
                    error_content=self.txt("Image not available", 13*k, SOFT),
                ),
            ),
        )

    def written_input(self, k):
        answered = self._written_ready()
        color = GREEN if answered else BORDE_AZUL
        field = ft.TextField(
            value=self.typed_value,
            hint_text="Type the missing word or complete sentence…",
            hint_style=ft.TextStyle(size=13*k, color=LETRA_BLOQUEADA),
            text_size=17*k,
            text_style=ft.TextStyle(color=NAVY, weight=ft.FontWeight.W_500,
                                    font_family=FONT),
            cursor_color=BLUE,
            border=ft.NoInputBorder(),
            bgcolor=ft.Colors.TRANSPARENT,
            multiline=True,
            min_lines=2,
            max_lines=2,
            read_only=answered,
            on_change=self.on_text_change,
            on_submit=self.check_written,
            shift_enter=True,
        )
        return ft.Container(
            border_radius=18*k,
            border=ft.Border.all(max(1, 2*k), color),
            bgcolor=WHITE,
            padding=ft.Padding.symmetric(horizontal=6*k),
            shadow=sombra(0.08, 7*k, 2*k),
            content=field,
        )

    def verify_button(self, k):
        verified = self._written_ready()
        return ft.Container(
            width=180*k, height=44*k,
            bgcolor=GREEN if verified else BLUE,
            border_radius=23*k,
            shadow=sombra(0.10, 7*k, 2*k),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self.listen_again if verified else self.check_written,
            content=ft.Row(
                tight=True, spacing=6*k,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.VOLUME_UP if verified
                            else ft.Icons.CHECK, size=19*k, color=WHITE),
                    self.txt("Listen again" if verified else "Check answer",
                             17*k, WHITE, bold=True, lines=1),
                ],
            ),
        )

    def small_button(self, label, icon, k, callback, active=True):
        return ft.Container(
            width=104*k, height=50*k,
            border_radius=25*k,
            bgcolor=WHITE if active else "#F3F5F8",
            border=ft.Border.all(max(1, 1.5*k), BORDE_AZUL if active else GRIS_CLARO),
            shadow=sombra(0.08, 7*k, 3*k),
            alignment=ft.Alignment.CENTER,
            ink=active,
            on_click=callback if active else None,
            content=ft.Row(
                tight=True, spacing=5*k,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, color=BLUE if active else LETRA_BLOQUEADA, size=17*k),
                    self.txt(label, 17*k, BLUE if active else LETRA_BLOQUEADA, bold=True, lines=1),
                ],
            ),
        )

    def mic_button(self, k):
        recording = self.is_recording
        ready = self._written_ready()
        return ft.Container(
            width=62*k, height=62*k,
            bgcolor=RED if recording else BLUE if ready else BLOQUEADO,
            border_radius=31*k,
            border=ft.Border.all(max(2, 5*k), "#CFE6FF"),
            shadow=sombra(0.19, 13*k, 4*k),
            alignment=ft.Alignment.CENTER,
            ink=ready and not recording,
            on_click=self.microphone if ready and not recording else None,
            tooltip="Verify the written answer, then speak the sentence",
            content=ft.Icon(
                ft.Icons.GRAPHIC_EQ if recording else ft.Icons.MIC,
                color=WHITE if ready else LETRA_BLOQUEADA,
                size=32*k,
            ),
        )

    def btn_continue(self, k):
        enabled = self._written_ready() and self._spoken_ready()
        label = "Finish" if self.session.is_last else "Continue"
        return ft.Container(
            width=222*k, height=47*k,
            bgcolor=GREEN if enabled else BLOQUEADO,
            border=ft.Border.all(max(1, 2*k), GREEN),
            border_radius=26*k,
            alignment=ft.Alignment.CENTER,
            ink=enabled,
            on_click=self.continue_quiz if enabled else None,
            shadow=sombra(0.09, 8*k, 3*k),
            content=ft.Row(
                tight=True, spacing=5*k,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.txt(label, 20*k, WHITE if enabled else LETRA_BLOQUEADA,
                             bold=True, lines=1),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT,
                            color=WHITE if enabled else LETRA_BLOQUEADA,
                            size=21*k),
                ],
            ),
        )

    def feedback(self, k):
        if self.rec_message:
            return self.txt(self.rec_message, 12*k,
                            GREEN if self.rec_ok else RED, bold=True, lines=2)
        if self.text_feedback:
            return self.txt(self.text_feedback, 12*k,
                            GREEN if self._written_ready() else RED,
                            bold=True, lines=2)
        if self.hint_message:
            return self.txt(self.hint_message, 12*k, SOFT, lines=2)
        return None

    # =============== HOJA CENTRAL FIJA ===============

    def build_quiz(self):
        ex = self.session.current
        k_header = min(1.0, (self.w - 24) / 440)
        header_h = 53 * k_header
        available_h = self.h - 20 - header_h - 5 - 12
        paper_h = max(260, min(ALTURA_MAX_HOJA, available_h))
        paper_w = min(self.w - 24, 480)
        sx = paper_w / HOJA_BASE_W
        sy = paper_h / HOJA_BASE_H
        k = min(sx, sy)

        def at(x, y, width, height, component):
            return ft.Container(
                left=x*sx, top=y*sy,
                width=width*sx, height=height*sy,
                alignment=ft.Alignment.CENTER,
                content=component,
            )

        prompt_display = self._expected_sentence(ex) if self._written_ready() else ex["prompt"]
        pieces = [
            ft.Image(
                src=HOJA_CENTRAL,
                left=0, top=0, width=paper_w, height=paper_h,
                fit=ft.BoxFit.FILL,
                error_content=self.txt("Missing hoja_central.png", 14*k, RED),
            ),
            at(36, 75, 348, 38, self.etiqueta(k)),
            at(20, 116, 380, 52,
               self.txt("Write the sentence", 27*k, NAVY, bold=True, lines=2)),
            at(32, 172, 356, 34,
               self.txt("Complete it, then say the full sentence aloud.",
                        13*k, SOFT, lines=2)),
            at(88, 209, 244, 244, self.imagen_ejercicio(ex["image"], k)),
            at(26, 456, 368, 75,
               self.txt(prompt_display, 21*k,
                        GREEN if self._written_ready() else NAVY,
                        bold=True, lines=3)),
            at(38, 537, 344, 79, self.written_input(k)),
            at(120, 630, 180, 44, self.verify_button(k)),
        ]

        status = self.feedback(k)
        if status is not None:
            pieces.append(at(30, 681, 360, 38, status))

        ready = self._written_ready()
        hint_available = getattr(self.session, "hint_available", None)
        can_hint = not ready and (
            not callable(hint_available) or hint_available(ex)
        )
        pieces.extend([
            at(38, 738, 104, 50,
               self.small_button("Hint", ft.Icons.LIGHTBULB_OUTLINE,
                                 k, self.hint, can_hint)),
            at(179, 730, 62, 62, self.mic_button(k)),
            at(278, 738, 104, 50,
               self.small_button("Skip", ft.Icons.FAST_FORWARD,
                                 k, self.skip, not self.is_recording)),
            at(83, 796, 254, 19,
               self.txt("Listening…" if self.is_recording
                        else "Pronunciation accepted ✓" if self._spoken_ready()
                        else "Tap to speak the full sentence",
                        12*k, GREEN if self._spoken_ready() else SOFT,
                        bold=True, lines=1)),
            at(99, 816, 222, 45, self.btn_continue(k)),
        ])

        return ft.Column(
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.header(),
                ft.Stack(width=paper_w, height=paper_h, controls=pieces),
            ],
        )

    def menu_btn(self, label, callback, primary=False):
        return ft.Container(
            height=55,
            border_radius=24,
            border=ft.Border.all(2, BLUE if primary else BORDE_AZUL),
            bgcolor=BLUE if primary else WHITE,
            alignment=ft.Alignment.CENTER,
            on_click=callback,
            ink=True,
            shadow=sombra(0.08, 8, 3),
            content=self.txt(label, 18, WHITE if primary else BLUE, bold=True),
        )

    def build_paused(self):
        return ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    bgcolor=CREMA,
                    border_radius=30,
                    padding=24,
                    shadow=sombra(0.13, 16, 5),
                    content=ft.Column(
                        spacing=17,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=BLUE, size=78),
                            self.txt("Paused", 30, NAVY, bold=True),
                            self.txt(f"Question {self.session.number} / {self.session.total}", 17, SOFT),
                            self.txt(f"Time {self.paused_at}", 17, SOFT),
                            self.menu_btn("Resume", self.resume, primary=True),
                            self.menu_btn("Finish now", self.finish_now),
                            self.menu_btn("Save & exit", self.save_exit),
                        ],
                    ),
                ),
            ],
        )

    # =============== PANTALLA FINAL ===============

    def estadistica(self, icon, title, value, color):
        return ft.Container(
            expand=True,
            padding=10,
            bgcolor=WHITE,
            border_radius=18,
            border=ft.Border.all(1, AZUL_CLARO),
            content=ft.Column(
                spacing=5,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=27, color=color),
                    self.txt(value, 22, NAVY, bold=True),
                    self.txt(title, 12, SOFT),
                ],
            ),
        )

    def summary_line(self, title, value, color=NAVY):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self.txt(title, 15, NAVY, bold=True),
                self.txt(value, 15, color, bold=True),
            ],
        )

    def build_end(self):
        stats = self.session.summary()
        tiempo_final = stats.get("time", self.final_time)
        if not self._native_pause():
            tiempo_final = self.final_time
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,  # solo resultado; el ejercicio NO tiene scroll
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Container(
                    bgcolor=CREMA,
                    border_radius=29,
                    padding=17,
                    shadow=sombra(0.09, 14, 4),
                    content=ft.Column(
                        spacing=16,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.EMOJI_EVENTS, size=66, color=GREEN),
                            self.txt("Practice Completed!", 27, NAVY, bold=True),
                            self.txt("Great job! You finished your practice.", 14, SOFT),
                            ft.Row(spacing=9, controls=[
                                self.estadistica(ft.Icons.ACCESS_TIME, "Total Time",
                                                tiempo_final, BLUE),
                                self.estadistica(ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                                                f'{stats.get("completed", 0)} / {stats.get("total", self.session.total)}', GREEN),
                            ]),
                            ft.Row(spacing=9, controls=[
                                self.estadistica(ft.Icons.CANCEL_OUTLINED, "Wrong Answers",
                                                str(stats.get("errors", 0)), RED),
                                self.estadistica(ft.Icons.SKIP_NEXT, "Skips Used",
                                                str(stats.get("skips", 0)), SOFT),
                            ]),
                            ft.Container(
                                bgcolor=WHITE,
                                border_radius=18,
                                padding=15,
                                content=ft.Column(spacing=12, controls=[
                                    self.summary_line("XP Earned", f'+{stats.get("xp_earned", 0)} XP', GREEN),
                                    self.summary_line("Total XP", f'{stats.get("xp_total", 0)} XP'),
                                ]),
                            ),
                            self.menu_btn("Practice Again", self.restart, primary=True),
                            ft.Container(
                                padding=8,
                                ink=True,
                                on_click=self.home,
                                content=self.txt("Back to Home", 16, SOFT, bold=True),
                            ),
                        ],
                    ),
                ),
            ],
        )

    # =============== CAPAS: NUBES + HOJA + OBJETOS ===============

    def render(self):
        if self.mode == "closed":
            return
        if self.mode == "quiz":
            self.timer_text.value = format_time(self._tiempo_activo())
        self.counter_text.value = f"{self.session.number} / {self.session.total}"
        builder = {
            "quiz": self.build_quiz,
            "paused": self.build_paused,
            "end": self.build_end,
        }[self.mode]
        self.shell.width = self.w
        self.shell.height = self.h
        self.shell.content = ft.Stack(
            width=self.w,
            height=self.h,
            controls=[
                ft.Image(
                    src=FONDO_NUBES,
                    left=0, top=0,
                    width=self.w, height=self.h,
                    fit=ft.BoxFit.COVER,
                ),
                ft.Container(
                    left=0, top=0,
                    width=self.w, height=self.h,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    content=ft.SafeArea(content=builder()),
                ),
            ],
        )
        self.page.update()
