
"""Phrases Practice: diseño uniforme con Action Practice (Flet 1.x)."""

import asyncio
import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None

from services.ejercicios.pronunciacion_oraciones_service import (
    listen_and_check_sentence,
    preload,
)
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT_BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
)

FONDO_NUBES = "imagenes/fondo_nubes.png"
HOJA_CENTRAL = "imagenes/hoja_central.png"

CREAM = "#FFFCF7"
PALE_BLUE = "#EAF4FF"
BORDER_BLUE = "#A6CFFF"
LOCKED_BG = "#D5DCE8"
LOCKED_FG = "#8A97B0"
SILVER = "#E9EDF4"
YELLOW = "#FFD54A"
YELLOW_BG = "#FFF6CC"

BASE_W, BASE_H = 420, 870


def _shadow(opacity=0.09, blur=12, y=3):
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(opacity, "#153C81"),
        blur_radius=blur,
        offset=ft.Offset(0, y),
    )


class PhrasesView:
    """Mantiene la lógica y la interfaz pública de Phrases."""

    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home

        self.mode = "quiz"
        self._tick_id = 0
        self._player = None

        self._width = 440
        self._height = 844
        self.shell = ft.Container()

        self.timer_text = ft.Text("00:00")
        self.counter = ft.Text("1 / 1")

        self.rec_state = "idle"
        self.rec_message = None

        preload()

    # =====================================================
    # CICLO DE VIDA
    # =====================================================

    def show(self, resume=False):
        self.mode = "quiz"

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
        self._stop_audio_sync()

    def _mount(self):
        self.page.clean()
        self.page.padding = 0
        self.page.spacing = 0

        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=PALE_BLUE,
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
            self.timer_text.value = self.session.format_time(
                self.session.time_now()
            )

            try:
                self.timer_text.update()
            except Exception:
                pass

            await asyncio.sleep(1)

    # =====================================================
    # AUDIO
    # =====================================================

    def _toast(self, message):
        try:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text(message))
            )
        except Exception:
            print(message)

    async def _speak(self, src):
        if not src or fta is None:
            return

        self._stop_audio_sync()

        try:
            self._player = fta.Audio(
                src=src,
                autoplay=True,
            )
            self.page.services.append(self._player)
            self.page.update()

        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def _stop_audio_sync(self):
        try:
            if (
                self._player is not None
                and self._player in self.page.services
            ):
                self.page.services.remove(self._player)

            self._player = None
            self.page.update()

        except Exception:
            self._player = None

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
            await self._speak(
                self.session.current.get("audio")
            )

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()
        else:
            self._toast("No hints available.")

    def _on_skip(self, e=None):
        self._stop_audio_sync()
        self.rec_message = None

        if self.session.skip() == "finished":
            self.mode = "end"
            self._tick_id += 1

        self.render()

    async def _on_mic(self, e=None):
        ex = self.session.current

        if not self.session.is_solved(ex):
            self._toast("First choose the correct phrase.")
            return

        if self.rec_state != "idle":
            return

        self._stop_audio_sync()

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

        self._stop_audio_sync()

        result = self.session.advance()
        self.rec_message = None

        if result == "finished":
            self.mode = "end"
            self._tick_id += 1

        self.render()

    # =====================================================
    # PAUSA Y NAVEGACIÓN
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

        self._tick_id += 1
        self.mode = "end"
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
    # ESTILO VISUAL
    # =====================================================

    def _text(
        self,
        value,
        size=16,
        color=NAVY,
        bold=False,
        italic=False,
        align=ft.TextAlign.CENTER,
        max_lines=None,
    ):
        return ft.Text(
            str(value),
            size=size,
            color=color,
            weight=(
                ft.FontWeight.BOLD
                if bold
                else ft.FontWeight.NORMAL
            ),
            italic=italic,
            font_family=FONT,
            text_align=align,
            max_lines=max_lines,
        )

    # =====================================================
    # HEADER - IGUAL QUE ACTION PRACTICE
    # =====================================================

    def _header(self):
        scale = min(1.0, (self._width - 24) / 440)

        badge = ft.Container(
            width=46 * scale,
            height=48 * scale,
            bgcolor=BLUE,
            border_radius=15 * scale,
            border=ft.Border.all(
                max(1, 2 * scale),
                WHITE,
            ),
            shadow=_shadow(0.2, 7 * scale, 3 * scale),
            alignment=ft.Alignment.CENTER,
            content=self._text(
                "A",
                29 * scale,
                WHITE,
                True,
                True,
            ),
        )

        title = ft.Row(
            tight=True,
            spacing=7 * scale,
            controls=[
                badge,
                self._text(
                    "Phrases",
                    17 * scale,
                    bold=True,
                    italic=True,
                ),
            ],
        )

        self.timer_text.value = self.session.format_time(
            self.session.time_now()
        )

        self.counter.value = (
            f"{self.session.number} / {self.session.total}"
        )

        for control in (self.timer_text, self.counter):
            control.size = 15 * scale
            control.color = NAVY
            control.weight = ft.FontWeight.BOLD
            control.font_family = FONT

        timer = ft.Container(
            height=40 * scale,
            padding=ft.Padding.symmetric(
                horizontal=8 * scale,
            ),
            bgcolor=WHITE,
            border_radius=22 * scale,
            border=ft.Border.all(
                1.5 * scale,
                PALE_BLUE,
            ),
            shadow=_shadow(0.09, 5 * scale, 2 * scale),
            ink=True,
            on_click=self._on_pause,
            tooltip="Pause practice",
            content=ft.Row(
                tight=True,
                spacing=3 * scale,
                controls=[
                    ft.Icon(
                        ft.Icons.PAUSE_CIRCLE_OUTLINE,
                        size=16 * scale,
                        color=BLUE,
                    ),
                    self.timer_text,
                ],
            ),
        )

        counter = ft.Container(
            height=40 * scale,
            padding=ft.Padding.symmetric(
                horizontal=10 * scale,
            ),
            bgcolor=WHITE,
            border_radius=22 * scale,
            border=ft.Border.all(
                1.5 * scale,
                PALE_BLUE,
            ),
            shadow=_shadow(0.09, 5 * scale, 2 * scale),
            alignment=ft.Alignment.CENTER,
            content=self.counter,
        )

        return ft.Container(
            height=53 * scale,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5 * scale,
                controls=[
                    title,
                    ft.Row(
                        tight=True,
                        spacing=5 * scale,
                        controls=[
                            timer,
                            counter,
                        ],
                    ),
                ],
            ),
        )

    # =====================================================
    # ILUSTRACIÓN
    # =====================================================

    def _illustration(self, src, scale):
        return ft.Container(
            width=232 * scale,
            height=232 * scale,
            padding=8 * scale,
            bgcolor=CREAM,
            border_radius=30 * scale,
            border=ft.Border.all(
                max(1, 2 * scale),
                "#F0E9E0",
            ),
            shadow=_shadow(0.07, 9 * scale, 3 * scale),
            content=ft.Container(
                bgcolor=PALE_BLUE,
                border_radius=24 * scale,
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src=src,
                    width=215 * scale,
                    height=215 * scale,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=self._text(
                        "Image not available",
                        12 * scale,
                        SOFT_BLUE,
                    ),
                ),
            ),
        )

    # =====================================================
    # OPCIONES DE RESPUESTA
    # =====================================================

    def _option_button(self, ex, option, scale):
        selected = self.session.picked_for(ex) == option

        correct = selected and option == ex["answer"]
        wrong = selected and not correct

        eliminated = (
            self.session.hint_for(ex) == option
            and not selected
        )

        solved = self.session.is_solved(ex)

        accent = (
            GREEN if correct
            else RED if wrong
            else SILVER if eliminated
            else BORDER_BLUE
        )

        bg = (
            "#E9F8ED" if correct
            else "#FFF0F0" if wrong
            else "#F4F5F8" if eliminated
            else WHITE
        )

        fg = (
            GREEN if correct
            else RED if wrong
            else LOCKED_FG if eliminated
            else NAVY
        )

        return ft.Container(
            height=49 * scale,
            bgcolor=bg,
            border=ft.Border.all(
                max(1, 2 * scale),
                accent,
            ),
            border_radius=17 * scale,
            padding=ft.Padding.symmetric(
                horizontal=12 * scale,
            ),
            shadow=_shadow(0.06, 6 * scale, 2 * scale),
            ink=not (eliminated or solved),
            on_click=(
                None
                if eliminated or solved
                else lambda e, value=option: self.page.run_task(
                    self._choose,
                    value,
                )
            ),
            content=ft.Row(
                spacing=9 * scale,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=25 * scale,
                        height=25 * scale,
                        border_radius=13 * scale,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(
                            max(1, 2 * scale),
                            (
                                GREEN if correct
                                else RED if wrong
                                else "#9EADD0"
                            ),
                        ),
                        bgcolor=(
                            GREEN if correct
                            else RED if wrong
                            else WHITE
                        ),
                        content=(
                            ft.Icon(
                                (
                                    ft.Icons.CHECK
                                    if correct
                                    else ft.Icons.CLOSE
                                ),
                                size=17 * scale,
                                color=WHITE,
                            )
                            if correct or wrong
                            else None
                        ),
                    ),

                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=self._text(
                            "" if eliminated else option,
                            15.5 * scale,
                            fg,
                            bold=True,
                            align=ft.TextAlign.LEFT,
                            max_lines=2,
                        ),
                    ),
                ],
            ),
        )

    # =====================================================
    # BOTONES - MISMAS DIMENSIONES QUE ACTION PRACTICE
    # =====================================================

    def _small_button(
        self,
        label,
        icon,
        on_click,
        scale,
        enabled=True,
    ):
        color = BLUE if enabled else LOCKED_FG

        return ft.Container(
            width=104 * scale,
            height=50 * scale,
            bgcolor=WHITE if enabled else "#F4F6FA",
            border_radius=25 * scale,
            border=ft.Border.all(
                max(1, 1.5 * scale),
                BORDER_BLUE if enabled else SILVER,
            ),
            shadow=_shadow(0.08, 7 * scale, 3 * scale),
            ink=enabled,
            on_click=on_click if enabled else None,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                tight=True,
                spacing=5 * scale,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon,
                        size=17 * scale,
                        color=color,
                    ),
                    self._text(
                        label,
                        17 * scale,
                        color,
                        bold=True,
                    ),
                ],
            ),
        )

    def _mic_button(self, scale):
        recording = self.rec_state == "recording"

        return ft.Container(
            width=66 * scale,
            height=66 * scale,
            border_radius=34 * scale,
            bgcolor=RED if recording else BLUE,
            border=ft.Border.all(
                max(2, 5 * scale),
                "#CFE6FF",
            ),
            shadow=_shadow(0.2, 13 * scale, 4 * scale),
            alignment=ft.Alignment.CENTER,
            ink=not recording,
            on_click=(
                None
                if recording
                else lambda e: self.page.run_task(
                    self._on_mic,
                    e,
                )
            ),
            tooltip="Speak the phrase",
            content=ft.Icon(
                (
                    ft.Icons.GRAPHIC_EQ
                    if recording
                    else ft.Icons.MIC
                ),
                color=WHITE,
                size=32 * scale,
            ),
        )

    def _continue_button(self, scale):
        ex = self.session.current
        enabled = self.session.can_continue(ex)

        return ft.Container(
            width=222 * scale,
            height=52 * scale,
            bgcolor=GREEN if enabled else LOCKED_BG,
            border_radius=28 * scale,
            border=ft.Border.all(
                max(1, 2 * scale),
                GREEN,
            ),
            shadow=_shadow(0.1, 9 * scale, 3 * scale),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=self._on_next,
            content=ft.Row(
                tight=True,
                spacing=5 * scale,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    self._text(
                        (
                            "Finish"
                            if self.session.is_last
                            else "Continue"
                        ),
                        20 * scale,
                        WHITE if enabled else LOCKED_FG,
                        True,
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=21 * scale,
                        color=WHITE if enabled else LOCKED_FG,
                    ),
                ],
            ),
        )

    # =====================================================
    # FEEDBACK DE RESPUESTAS
    # =====================================================

    def _feedback(self, scale):
        ex = self.session.current

        if (
            self.rec_message is not None
            and self.session.is_solved(ex)
        ):
            ok, heard = self.rec_message

            msg = (
                "Great pronunciation!"
                if ok
                else f'I heard "{heard or "..."}". Try again.'
            )

            color = GREEN if ok else RED

        elif self.session.is_solved(ex):
            msg, color = (
                ("Correct!", GREEN)
                if self.session.is_pronounced(ex)
                else ("Correct! Now say it aloud.", GREEN)
            )

        elif self.session.picked_for(ex):
            msg = "Wrong. Try again."
            color = RED

        else:
            return None

        return self._text(
            msg,
            12 * scale,
            color,
            bold=True,
            max_lines=1,
        )

    # =====================================================
    # HOJA PRINCIPAL
    # =====================================================

    def _build_quiz(self):
        s = self.session
        ex = s.current

        header_scale = min(
            1.0,
            (self._width - 24) / 440,
        )

        header_h = 53 * header_scale

        # Reservamos espacio para SafeArea en móviles.
        paper_h = max(
            220,
            min(
                850,
                self._height - 20 - header_h - 5 - 46,
            ),
        )

        paper_w = min(self._width - 24, 480)

        sx = paper_w / BASE_W
        sy = paper_h / BASE_H
        scale = min(sx, sy)

        def place(x, y, w, h, control):
            return ft.Container(
                left=x * sx,
                top=y * sy,
                width=w * sx,
                height=h * sy,
                alignment=ft.Alignment.CENTER,
                content=control,
            )

        controls = [
            # Hoja central
            ft.Image(
                src=HOJA_CENTRAL,
                left=0,
                top=0,
                width=paper_w,
                height=paper_h,
                fit=ft.BoxFit.FILL,
                error_content=self._text(
                    "Sheet image not available",
                    13 * scale,
                    RED,
                ),
            ),

            # Encabezado de la hoja
            place(
                36, 72, 348, 38,
                ft.Container(
                    bgcolor="#B3D7FF",
                    border_radius=12 * scale,
                    alignment=ft.Alignment.CENTER,
                    content=self._text(
                        "PHRASES",
                        18 * scale,
                        bold=True,
                        italic=True,
                    ),
                ),
            ),

            # Título
            place(
                22, 115, 376, 43,
                self._text(
                    "Choose the best phrase",
                    25 * scale,
                    bold=True,
                ),
            ),

            # Subtítulo
            place(
                38, 165, 344, 45,
                self._text(
                    "Select the most appropriate phrase\n"
                    "for the situation.",
                    14 * scale,
                    SOFT_BLUE,
                    max_lines=2,
                ),
            ),

            # Imagen
            place(
                94, 221, 232, 232,
                self._illustration(
                    ex["image"],
                    scale,
                ),
            ),

            # Situación
            place(
                39, 465, 342, 51,
                ft.Container(
                    padding=ft.Padding.symmetric(
                        horizontal=12 * scale,
                    ),
                    bgcolor=YELLOW_BG,
                    border_radius=16 * scale,
                    border=ft.Border.all(
                        max(1, 1.5 * scale),
                        YELLOW,
                    ),
                    alignment=ft.Alignment.CENTER,
                    content=self._text(
                        ex.get("prompt", "Situation"),
                        15 * scale,
                        NAVY,
                        bold=True,
                        max_lines=2,
                    ),
                ),
            ),
        ]

        # Opciones
        for i, option in enumerate(
            ex["options"][:3]
        ):
            controls.append(
                place(
                    40,
                    525 + i * 57,
                    340,
                    49,
                    self._option_button(
                        ex,
                        option,
                        scale,
                    ),
                )
            )

        # Feedback
        feedback = self._feedback(scale)

        if feedback is not None:
            controls.append(
                place(
                    30, 688, 360, 20,
                    feedback,
                )
            )

        # Botones inferiores
        hint_enabled = (
            s.hint_available(ex)
            if hasattr(s, "hint_available")
            else True
        )

        controls.extend([
            place(
                38, 718, 104, 50,
                self._small_button(
                    "Hint",
                    ft.Icons.LIGHTBULB_OUTLINE,
                    self._on_hint,
                    scale,
                    hint_enabled,
                ),
            ),

            place(
                177, 710, 66, 66,
                self._mic_button(scale),
            ),

            place(
                278, 718, 104, 50,
                self._small_button(
                    "Skip",
                    ft.Icons.FAST_FORWARD,
                    self._on_skip,
                    scale,
                ),
            ),

            place(
                110, 779, 200, 17,
                self._text(
                    (
                        "Listening..."
                        if self.rec_state == "recording"
                        else "Tap to speak"
                    ),
                    12 * scale,
                    SOFT_BLUE,
                    bold=True,
                ),
            ),

            place(
                99, 800, 222, 52,
                self._continue_button(scale),
            ),
        ])

        return ft.Column(
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._header(),
                ft.Stack(
                    width=paper_w,
                    height=paper_h,
                    controls=controls,
                ),
            ],
        )

    # =====================================================
    # BOTONES DE PAUSA Y RESULTADOS
    # =====================================================

    def _menu_button(
        self,
        label,
        on_click,
        primary=False,
    ):
        return ft.Container(
            height=55,
            width=min(250, self._width - 100),
            bgcolor=BLUE if primary else WHITE,
            border=ft.Border.all(
                2,
                BLUE if primary else BORDER_BLUE,
            ),
            border_radius=24,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=on_click,
            shadow=_shadow(0.07, 8, 3),
            content=self._text(
                label,
                18,
                WHITE if primary else BLUE,
                bold=True,
            ),
        )

    # =====================================================
    # PANTALLA DE PAUSA
    # =====================================================

    def _build_paused(self):
        s = self.session

        return ft.Column(
            expand=True,
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    bgcolor=CREAM,
                    padding=26,
                    border_radius=30,
                    shadow=_shadow(0.09, 15, 3),
                    content=ft.Column(
                        spacing=18,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                ft.Icons.PAUSE_CIRCLE_FILLED,
                                color=BLUE,
                                size=82,
                            ),
                            self._text(
                                "Paused",
                                32,
                                bold=True,
                            ),
                            self._text(
                                f"Question {s.number} / {s.total}",
                                18,
                                SOFT_BLUE,
                            ),
                            self._text(
                                f"Time {s.format_time(s.time_now())}",
                                18,
                                SOFT_BLUE,
                            ),
                            self._menu_button(
                                "Resume",
                                self._on_resume,
                                True,
                            ),
                            self._menu_button(
                                "Finish now",
                                self._on_finish_now,
                            ),
                            self._menu_button(
                                "Save & exit",
                                self._on_save_exit,
                            ),
                        ],
                    ),
                ),
            ],
        )

    # =====================================================
    # ESTADÍSTICAS
    # =====================================================

    def _stat(self, icon, label, value, color):
        return ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=ft.Border.all(1, PALE_BLUE),
            border_radius=18,
            padding=10,
            content=ft.Column(
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon,
                        size=27,
                        color=color,
                    ),
                    self._text(
                        value,
                        21,
                        NAVY,
                        bold=True,
                    ),
                    self._text(
                        label,
                        12,
                        SOFT_BLUE,
                    ),
                ],
            ),
        )

    def _summary_line(self, label, value, color=NAVY):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self._text(
                    label,
                    15,
                    NAVY,
                    bold=True,
                ),
                self._text(
                    value,
                    15,
                    color,
                    bold=True,
                ),
            ],
        )

    # =====================================================
    # RESULTADOS A PANTALLA COMPLETA
    # =====================================================

    def _build_end(self):
        stats = self.session.summary()

        results = ft.Column(
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    ft.Icons.EMOJI_EVENTS,
                    color=GREEN,
                    size=72,
                ),
                self._text(
                    "Practice Completed!",
                    26,
                    bold=True,
                ),
                self._text(
                    "Great job! You finished your phrases practice.",
                    14,
                    SOFT_BLUE,
                    max_lines=2,
                ),

                ft.Row(
                    spacing=10,
                    controls=[
                        self._stat(
                            ft.Icons.ACCESS_TIME,
                            "Total Time",
                            stats["time"],
                            BLUE,
                        ),
                        self._stat(
                            ft.Icons.CHECK_CIRCLE_OUTLINE,
                            "Completed",
                            f'{stats["completed"]} / {stats["total"]}',
                            GREEN,
                        ),
                    ],
                ),

                ft.Row(
                    spacing=10,
                    controls=[
                        self._stat(
                            ft.Icons.CANCEL_OUTLINED,
                            "Wrong Answers",
                            str(stats["errors"]),
                            RED,
                        ),
                        self._stat(
                            ft.Icons.SKIP_NEXT,
                            "Skips Used",
                            str(stats["skips"]),
                            SOFT_BLUE,
                        ),
                    ],
                ),

                ft.Container(
                    bgcolor=WHITE,
                    border_radius=18,
                    padding=15,
                    content=ft.Column(
                        spacing=13,
                        controls=[
                            self._summary_line(
                                "XP Earned",
                                f'+{stats["xp_earned"]} XP',
                                GREEN,
                            ),
                            self._summary_line(
                                "Total XP",
                                f'{stats["xp_total"]} XP',
                            ),
                        ],
                    ),
                ),

                self._menu_button(
                    "Practice Again",
                    self._on_restart,
                    True,
                ),

                ft.Container(
                    padding=8,
                    ink=True,
                    on_click=self._on_home,
                    content=self._text(
                        "Back to Home",
                        16,
                        SOFT_BLUE,
                        bold=True,
                    ),
                ),
            ],
        )

        return ft.Container(
            width=self._width,
            height=self._height,
            bgcolor=CREAM,
            content=ft.SafeArea(
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=min(400, self._width - 30),
                            padding=ft.Padding.symmetric(
                                horizontal=8,
                                vertical=26,
                            ),
                            content=results,
                        ),
                    ],
                ),
            ),
        )

    # =====================================================
    # RENDER
    # =====================================================

    def render(self):
        if self.mode == "closed":
            return

        self.timer_text.value = self.session.format_time(
            self.session.time_now()
        )

        self.counter.value = (
            f"{self.session.number} / {self.session.total}"
        )

        self.shell.width = self._width
        self.shell.height = self._height

        # La pantalla final reemplaza al ejercicio.
        if self.mode == "end":
            self.shell.content = self._build_end()
            self.page.update()
            return

        content = (
            self._build_quiz()
            if self.mode == "quiz"
            else self._build_paused()
        )

        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=[
                ft.Image(
                    src=FONDO_NUBES,
                    left=0,
                    top=0,
                    width=self._width,
                    height=self._height,
                    fit=ft.BoxFit.COVER,
                ),
                ft.Container(
                    left=0,
                    top=0,
                    width=self._width,
                    height=self._height,
                    padding=ft.Padding.symmetric(
                        horizontal=12,
                        vertical=10,
                    ),
                    content=ft.SafeArea(
                        content=content,
                    ),
                ),
            ],
        )

        self.page.update()
