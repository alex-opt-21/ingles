import asyncio
import struct
from pathlib import Path
import flet as ft

from services.ejercicios.questions_service import format_time
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
)

try:
    import flet_audio as fta
except ImportError:
    fta = None

FONDO_NUBES = "imagenes/fondo_nubes.png"
HOJA_CENTRAL = "imagenes/hoja_central.png"

# Ilustraciones JSON: "imagenes/questions/Fiesta.png" y "imagenes/questions/Niño.png"

# Para que los controles sigan pegados a la hoja; no hay scroll.
HOJA_W, HOJA_H = 420, 870
ALTURA_MAX_HOJA = 850
AZUL_BORDE = "#9FC9FF"
AZUL_SUAVE = "#EAF3FF"
AZUL_TITULO = "#B2D6FF"
CREMA = "#FFFCF7"
GRIS_BG = "#D7DDE8"
GRIS_FG = "#8391AE"


def _sombra(op=0.08, blur=10, dy=3):
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(op, NAVY),
        blur_radius=blur,
        offset=ft.Offset(0, dy),
    )


class QuestionsView:
    """Interfaz: QuestionsView(page, session, on_home).show()."""

    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"  # quiz, paused, end, closed
        self.w = 440
        self.h = 844
        self.shell = ft.Container()
        self.timer_text = ft.Text("00:00")
        self.counter_text = ft.Text("1 / 5")
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
            bgcolor=AZUL_SUAVE,
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
            self.timer_text.value = format_time(self.session.time_now())
            try:
                self.timer_text.update()
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

    # ------------------ Componentes reales ------------------

    def _text(self, value, size, color=NAVY, bold=False, italic=False,
              align=ft.TextAlign.CENTER, lines=None):
        return ft.Text(
            str(value), size=size, color=color,
            font_family=FONT, italic=italic,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            text_align=align, max_lines=lines,
        )

    def _badge(self, s):
        return ft.Container(
            width=46 * s, height=48 * s,
            bgcolor=BLUE,
            border_radius=15 * s,
            border=ft.Border.all(2 * s, WHITE),
            alignment=ft.Alignment.CENTER,
            shadow=_sombra(0.16, 8 * s),
            content=self._text("A", 28 * s, WHITE, bold=True, italic=True),
        )

    def _pill(self, content, width, s, on_click=None):
        return ft.Container(
            width=width * s,
            height=40 * s,
            bgcolor=WHITE,
            border_radius=22 * s,
            border=ft.Border.all(max(1, 1.5 * s), AZUL_SUAVE),
            alignment=ft.Alignment.CENTER,
            shadow=_sombra(0.10, 7 * s),
            on_click=on_click,
            ink=on_click is not None,
            content=content,
        )

    def _header(self):
        s = min(1, (self.w - 24) / 440)
        self.timer_text.size = 15 * s
        self.timer_text.font_family = FONT
        self.timer_text.weight = ft.FontWeight.BOLD
        self.timer_text.color = NAVY
        self.counter_text.size = 15 * s
        self.counter_text.weight = ft.FontWeight.BOLD
        self.counter_text.font_family = FONT
        self.counter_text.color = NAVY
        timer = self._pill(
            ft.Row(tight=True, spacing=3 * s,
                   alignment=ft.MainAxisAlignment.CENTER,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER,
                   controls=[
                       ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE, color=BLUE, size=17 * s),
                       self.timer_text,
                   ]),
            88, s, on_click=self._on_pause,
        )
        counter = self._pill(self.counter_text, 72, s)
        return ft.Container(
            height=53 * s,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=3 * s,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(tight=True, spacing=6 * s,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[
                               self._badge(s),
                               self._text("Questions Practice", 16 * s, bold=True, italic=True),
                           ]),
                    ft.Row(tight=True, spacing=4 * s,
                           vertical_alignment=ft.CrossAxisAlignment.CENTER,
                           controls=[timer, counter]),
                ],
            ),
        )

    def _section(self, s):
        return ft.Container(
            bgcolor=AZUL_TITULO,
            border_radius=12 * s,
            alignment=ft.Alignment.CENTER,
            content=self._text("QUESTIONS & ANSWERS", 17 * s,
                               bold=True, italic=True),
        )

    def _illustrated_question(self, ex, s):
        """Muestra Fiesta/Niño y coloca la pregunta EN su burbuja original.

        Las imágenes ya tienen un globo de diálogo blanco. El texto es Flet:
        no está incrustado en el PNG. Conservar la proporción de los PNG evita
        deformar los personajes, y las coordenadas porcentuales se adaptan.
        """
        scene = str(ex.get("scene", "")).lower()
        src = ex.get("image", "")
        if not scene:
            scene = "fiesta" if "fiesta" in src.lower() else "nino"

        # Tamaño proporcional medido en las imágenes originales que compartiste.
        # Si reemplazas los PNG por otros recortes, ajusta aquí estos valores.
        if scene == "fiesta":
            ratio = 1448 / 1086
            # Centro horizontal, centro vertical y ancho/alto seguro del globo.
            cx, cy, tw, th = 0.70, 0.34, 0.36, 0.28
        else:
            ratio = 1403 / 1121
            cx, cy, tw, th = 0.68, 0.39, 0.34, 0.25

        # Área disponible dentro del papel: 344×253 unidades, sin deformar.
        max_w, max_h = 344 * s, 253 * s
        iw = min(max_w, max_h * ratio)
        ih = iw / ratio

        question = str(ex["question"])
        font_size = (16 if len(question) <= 24 else 14 if len(question) <= 38 else 12.5) * s

        # Esta capa de texto coincide con el globo pintado en el PNG.
        return ft.Stack(
            width=iw,
            height=ih,
            controls=[
                ft.Image(
                    src=src,
                    left=0, top=0,
                    width=iw, height=ih,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Container(
                        bgcolor=AZUL_SUAVE,
                        alignment=ft.Alignment.CENTER,
                        content=self._text("Missing image: " + src, 12 * s, RED),
                    ),
                ),
                ft.Container(
                    left=(cx - tw / 2) * iw,
                    top=(cy - th / 2) * ih,
                    width=tw * iw,
                    height=th * ih,
                    alignment=ft.Alignment.CENTER,
                    padding=0,
                    content=ft.Text(
                        question,
                        size=font_size,
                        font_family=FONT,
                        color=NAVY,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=5,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ),
            ],
        )

    def _option(self, ex, option, s):
        chosen = self.session.picked_for(ex) == option
        correct = chosen and self.session.is_solved(ex)
        wrong = chosen and not correct
        removed = self.session.hint_for(ex) == option
        solved = self.session.is_solved(ex)
        border = GREEN if correct else RED if wrong else "#D4DAE2" if removed else AZUL_BORDE
        bg = "#E8F8EE" if correct else "#FFF0F0" if wrong else "#F2F4F7" if removed else WHITE
        fg = GREEN if correct else RED if wrong else GRIS_FG if removed else NAVY

        async def pick(e):
            await self._choose(option)

        return ft.Container(
            bgcolor=bg,
            border=ft.Border.all(max(1, 1.7 * s), border),
            border_radius=24 * s,
            padding=ft.Padding.symmetric(horizontal=14 * s),
            shadow=_sombra(0.06, 6 * s, 2 * s),
            alignment=ft.Alignment.CENTER_LEFT,
            on_click=pick if not (solved or removed or self._recording) else None,
            ink=not (solved or removed or self._recording),
            content=ft.Row(
                spacing=11 * s,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=26 * s, height=26 * s,
                        border_radius=14 * s,
                        bgcolor=GREEN if correct else RED if wrong else WHITE,
                        border=ft.Border.all(max(1, 2 * s), GREEN if correct else RED if wrong else "#9FB0D2"),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.CHECK if correct else ft.Icons.CLOSE,
                                        color=WHITE, size=17 * s) if chosen else None,
                    ),
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=self._text(option, 18 * s, fg,
                                           bold=True, italic=True,
                                           align=ft.TextAlign.LEFT, lines=2),
                    ),
                ],
            ),
        )

    def _small_button(self, name, icon, s, action, enabled=True):
        return ft.Container(
            bgcolor=WHITE if enabled else "#F3F5F9",
            border=ft.Border.all(max(1, 1.5 * s), AZUL_BORDE if enabled else "#D9DFE9"),
            border_radius=26 * s,
            shadow=_sombra(0.07, 6 * s),
            alignment=ft.Alignment.CENTER,
            on_click=action if enabled else None,
            ink=enabled,
            content=ft.Row(
                tight=True, spacing=5 * s,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=18 * s, color=BLUE if enabled else GRIS_FG),
                    self._text(name, 18 * s, BLUE if enabled else GRIS_FG, bold=True),
                ],
            ),
        )

    def _microphone(self, s):
        return ft.Container(
            width=72 * s, height=72 * s,
            bgcolor=RED if self._recording else BLUE,
            border_radius=38 * s,
            border=ft.Border.all(5 * s, "#D7EBFF"),
            shadow=_sombra(0.20, 12 * s),
            alignment=ft.Alignment.CENTER,
            on_click=None if self._recording else self._on_mic,
            ink=not self._recording,
            content=ft.Icon(
                ft.Icons.GRAPHIC_EQ if self._recording else ft.Icons.MIC,
                size=32 * s, color=WHITE,
            ),
        )

    def _continue(self, s):
        ready = self.session.can_continue()
        return ft.Container(
            bgcolor=GREEN if ready else GRIS_BG,
            border=ft.Border.all(max(1, 2 * s), GREEN),
            border_radius=30 * s,
            shadow=_sombra(0.09, 9 * s),
            alignment=ft.Alignment.CENTER,
            on_click=self._on_continue,  # Explica por qué sigue bloqueado
            ink=True,
            content=ft.Row(
                tight=True, spacing=6 * s,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self._text("Finish" if self.session.is_last else "Continue",
                               21 * s, WHITE if ready else GRIS_FG, bold=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT,
                            size=23 * s, color=WHITE if ready else GRIS_FG),
                ],
            ),
        )

    def _feedback(self, s):
        if self._mic_message is not None:
            ok, heard = self._mic_message
            label = "Great pronunciation!" if ok else f'I heard: "{heard or "..."}". Try again.'
            return self._text(label, 12 * s, GREEN if ok else RED, bold=True, lines=1)
        if self.session.is_pronounced():
            return self._text("Great! You can continue.", 12 * s, GREEN, bold=True)
        if self.session.is_solved():
            return self._text("Correct! Now say the full answer.", 12 * s, GREEN, bold=True)
        if self.session.picked_for():
            return self._text("Wrong answer. Try again.", 12 * s, RED, bold=True)
        return None

    # ------------------ Hoja fija y responsive ------------------

    def _build_quiz(self):
        ex = self.session.current
        header_scale = min(1, (self.w - 24) / 440)
        header_h = 53 * header_scale
        paper_h = max(250, min(ALTURA_MAX_HOJA, self.h - 20 - header_h - 17))
        paper_w = min(self.w - 24, 480)
        sx, sy = paper_w / HOJA_W, paper_h / HOJA_H
        s = min(sx, sy)

        def place(x, y, w, h, control):
            return ft.Container(
                left=x * sx, top=y * sy,
                width=w * sx, height=h * sy,
                alignment=ft.Alignment.CENTER,
                content=control,
            )

        controls = [
            ft.Image(
                src=HOJA_CENTRAL, left=0, top=0,
                width=paper_w, height=paper_h,
                fit=ft.BoxFit.FILL,
                error_content=self._text("Missing hoja_central.png", 13 * s, RED),
            ),
            place(33, 81, 354, 38, self._section(s)),
            place(25, 132, 370, 52,
                  self._text("Choose the correct answer", 27 * s,
                             NAVY, bold=True, lines=2)),
            place(37, 186, 346, 43,
                  self._text("Read the question and select\nthe best response.",
                             14 * s, SOFT, lines=2)),
            # Solo una de tus DOS imágenes. El texto se monta en el globo
            # blanco que viene en el propio PNG; no duplicamos la burbuja.
            place(38, 244, 344, 253, self._illustrated_question(ex, s)),
        ]

        for i, option in enumerate(ex["options"][:3]):
            controls.append(place(43, 520 + 61 * i, 334, 52,
                                  self._option(ex, option, s)))

        feedback = self._feedback(s)
        if feedback is not None:
            controls.append(place(40, 704, 340, 19, feedback))

        controls += [
            place(40, 734, 105, 51,
                  self._small_button("Hint", ft.Icons.LIGHTBULB_OUTLINE,
                                     s, self._on_hint,
                                     enabled=self.session.hint_available(ex))),
            place(174, 722, 72, 72, self._microphone(s)),
            place(275, 734, 105, 51,
                  self._small_button("Skip", ft.Icons.FAST_FORWARD,
                                     s, self._on_skip)),
            place(120, 795, 180, 16,
                  self._text("Listening..." if self._recording else "Tap to speak",
                             12 * s, SOFT, bold=True)),
            place(99, 810, 222, 48, self._continue(s)),
        ]
        return ft.Column(
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._header(),
                ft.Stack(width=paper_w, height=paper_h, controls=controls),
            ],
        )

    # ------------------ Pausa y resultados ------------------

    def _action_button(self, label, action, primary=False):
        return ft.Container(
            height=56,
            bgcolor=BLUE if primary else WHITE,
            border=ft.Border.all(2, BLUE if primary else AZUL_BORDE),
            border_radius=26,
            alignment=ft.Alignment.CENTER,
            shadow=_sombra(),
            on_click=action, ink=True,
            content=self._text(label, 18, WHITE if primary else BLUE, bold=True),
        )

    def _build_paused(self):
        return ft.Column(
            expand=True, alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            controls=[ft.Container(
                bgcolor=CREMA, border_radius=30, padding=25,
                shadow=_sombra(0.10, 15),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, size=74, color=BLUE),
                        self._text("Paused", 30, NAVY, bold=True),
                        self._text(f"Question {self.session.number} / {self.session.total}", 18, SOFT),
                        self._text(f"Time {format_time(self.session.time_now())}", 17, SOFT),
                        self._action_button("Resume", self._on_resume, primary=True),
                        self._action_button("Finish now", self._on_finish_now),
                        self._action_button("Save & exit", self._on_save_exit),
                    ],
                ),
            )],
        )

    def _stat(self, icon, label, value, color):
        return ft.Container(
            expand=True, bgcolor=WHITE,
            border_radius=18, padding=11,
            border=ft.Border.all(1, AZUL_SUAVE),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
                controls=[
                    ft.Icon(icon, size=26, color=color),
                    self._text(value, 22, NAVY, bold=True),
                    self._text(label, 12, SOFT),
                ],
            ),
        )

    def _build_end(self):
        st = self.session.summary()
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[ft.Container(
                bgcolor=CREMA,
                border_radius=29,
                padding=18,
                shadow=_sombra(),
                content=ft.Column(
                    spacing=17,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.EMOJI_EVENTS, size=65, color=GREEN),
                        self._text("Practice Completed!", 28, NAVY, bold=True),
                        self._text("Questions & Answers", 15, SOFT),
                        ft.Row(spacing=9, controls=[
                            self._stat(ft.Icons.ACCESS_TIME, "Total time", st["time"], BLUE),
                            self._stat(ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                                       f'{st["completed"]} / {st["total"]}', GREEN),
                        ]),
                        ft.Row(spacing=9, controls=[
                            self._stat(ft.Icons.CANCEL_OUTLINED, "Wrong answers",
                                       str(st["errors"]), RED),
                            self._stat(ft.Icons.SKIP_NEXT, "Skips",
                                       str(st["skips"]), SOFT),
                        ]),
                        ft.Container(
                            bgcolor=WHITE, border_radius=16, padding=16,
                            content=ft.Column(spacing=10, controls=[
                                self._text(f'Correct on first try: {st["first_try"]}', 17, NAVY),
                                self._text(f'XP earned: +{st["xp_earned"]}', 19, GREEN, bold=True),
                            ]),
                        ),
                        self._action_button("Practice Again", self._on_restart, primary=True),
                        self._action_button("Back to Home", self._on_home),
                    ],
                ),
            )],
        )

    # ------------------ Render general ------------------

    def render(self):
        if self.mode == "closed":
            return
        self.timer_text.value = format_time(self.session.time_now())
        self.counter_text.value = f"{self.session.number} / {self.session.total}"
        views = {
            "quiz": self._build_quiz,
            "paused": self._build_paused,
            "end": self._build_end,
        }
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
                    content=ft.SafeArea(content=views[self.mode]()),
                ),
            ],
        )
        self.page.update()
