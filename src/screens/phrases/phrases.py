"""Phrases de Saylo adaptado a Flet 1.x (sin helpers ft.padding/ft.border obsoletos)."""
import asyncio
from pathlib import Path
import json

import flet as ft

try:
    import flet_audio as fta
except Exception:
    fta = None

from services.ejercicios.pronunciacion_oraciones_service import listen_and_check_sentence, preload
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT_BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
    BG_TOP,
    BG_BOTTOM,
)


FONDO_NUBES = "imagenes/fondo_nubes.png"
HOJA_CENTRAL = "imagenes/hoja_central.png"
LOCKED_BG = "#D9DDE7"
LOCKED_FG = "#8B96AE"
LIGHT_BG = "#F8FBFF"
YELLOW = "#FFD54A"
YELLOW_BG = "#FFF6CC"


class PhrasesView:
    def __init__(self, page: ft.Page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"  # quiz | paused | end | closed
        self._tick_id = 0
        self._audio = None
        self._player = None
        self._width = 440
        self._height = 844
        self.shell = ft.Container(expand=True)
        self.timer_text = ft.Text("00:00")
        self.counter_text = ft.Text("1 / 1")
        self.rec_state = "idle"
        self.rec_message = None
        preload()

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
        self.render()
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
                bgcolor=WHITE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell,
            )
        )
        self.page.on_resize = self._fit
        self._fit()

    def _fit(self, e=None):
        width = min(self.page.width or 440, 540)
        height = self.page.height or 844
        if (
            abs(width - self._width) > 1
            or abs(height - self._height) > 1
            or self.shell.content is None
        ):
            self._width = width
            self._height = height
            self.render()

    async def _tick(self, token):
        while self._tick_id == token and self.mode == "quiz":
            self.timer_text.value = self.session.format_time(self.session.time_now())
            try:
                self.timer_text.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    def _toast(self, msg: str):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(msg)))
        except Exception:
            print(msg)

    # -------- audio --------
    async def _speak(self, src: str | None):
        if not src or fta is None:
            return
        self._stop_audio_sync()
        try:
            player = fta.Audio(src=src, autoplay=True)
            self.page.services.append(player)
            self._player = player
            self.page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def _stop_audio_sync(self):
        try:
            if self._player and self._player in self.page.services:
                self.page.services.remove(self._player)
            self._player = None
            self.page.update()
        except Exception:
            self._player = None

    # -------- actions --------
    async def _choose(self, option):
        result = self.session.choose(option)
        if result == "ignored":
            return
        self.rec_message = None
        self.render()
        if result == "correct":
            await self._speak(self.session.current.get("audio"))

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()
        else:
            self._toast("No hints available.")

    def _on_skip(self, e=None):
        self._stop_audio_sync()
        self.rec_message = None
        result = self.session.skip()
        if result == "finished":
            self.mode = "end"
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
            expected = ex.get("answer", "")
            ok, heard = await asyncio.to_thread(listen_and_check_sentence, expected)
            self.rec_message = (ok, heard)
            if ok:
                self.session.mark_pronounced(ex)
        except Exception as err:
            print(f"Mic error: {err}")
            self._toast("Could not access the microphone.")
        finally:
            self.rec_state = "idle"
            self.render()

    def _on_next(self, e=None):
        ex = self.session.current
        if not self.session.can_continue(ex):
            if not self.session.is_solved(ex):
                self._toast("Choose the correct phrase first.")
            else:
                self._toast("You cannot continue yet.")
            return
        self._stop_audio_sync()
        result = self.session.advance()
        self.rec_message = None
        if result == "finished":
            self.mode = "end"
        self.render()

    def _on_pause(self, e=None):
        if self.mode != "quiz":
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
        self.render()
        self._tick_id += 1
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

    # -------- widgets --------
    def _scale(self):
        ref_w = 440
        ref_h = 844
        return self._width / ref_w, self._height / ref_h

    def _badge_a(self, sx, sy):
        size = 42 * sx
        return ft.Container(
            width=size,
            height=size,
            bgcolor=BLUE,
            border_radius=14 * sx,
            alignment=ft.Alignment.CENTER,
            shadow=ft.BoxShadow(
                blur_radius=8 * sx,
                color=ft.Colors.with_opacity(0.15, "black"),
                offset=ft.Offset(0, 3 * sy),
            ),
            content=ft.Text("A", color=WHITE, size=24 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
        )

    def _pill(self, text, sx, sy, icon=None):
        controls = []
        if icon:
            controls.append(ft.Icon(icon, color=BLUE, size=14 * sx))
        if isinstance(text, ft.Text):
            text.color = NAVY
            text.size = 15 * sx
            text.weight = ft.FontWeight.BOLD
            text.font_family = FONT
            controls.append(text)
        else:
            controls.append(ft.Text(str(text), color=NAVY, size=15 * sx, weight=ft.FontWeight.BOLD, font_family=FONT))
        return ft.Container(
            height=34 * sy,
            padding=ft.Padding.symmetric(horizontal=12 * sx, vertical=6 * sy),
            bgcolor=WHITE,
            border_radius=18 * sx,
            border=ft.Border.all(1, "#D8E5FF"),
            shadow=ft.BoxShadow(
                blur_radius=5 * sx,
                color=ft.Colors.with_opacity(0.08, "black"),
                offset=ft.Offset(0, 2 * sy),
            ),
            content=ft.Row(spacing=5 * sx, controls=controls, alignment=ft.MainAxisAlignment.CENTER),
        )

    def _header(self, sx, sy):
        title = ft.Text("Phrases", color=NAVY, size=18 * sx, weight=ft.FontWeight.BOLD, italic=True, font_family=FONT)
        right = ft.Row(
            spacing=8 * sx,
            controls=[
                self._pill(self.timer_text, sx, sy, ft.Icons.PAUSE_CIRCLE_OUTLINE),
                self._pill(f"{self.session.number} / {self.session.total}", sx, sy),
            ],
        )
        pause_touch = ft.GestureDetector(on_tap=self._on_pause, content=right.controls[0])
        right.controls[0] = pause_touch
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(spacing=10 * sx, controls=[self._badge_a(sx, sy), title]),
                right,
            ],
        )

    def _feedback(self, sx):
        ex = self.session.current
        if self.rec_message is not None and self.session.is_solved(ex):
            ok, heard = self.rec_message
            msg = "Great pronunciation!" if ok else f'I heard "{heard or "..."}". Try again.'
            color = GREEN if ok else RED
        elif self.session.is_solved(ex):
            if self.session.is_pronounced(ex):
                msg, color = "Correct!", GREEN
            else:
                msg, color = "Correct! Now say it aloud.", GREEN
        elif self.session.picked_for(ex):
            msg, color = "Wrong. Try again.", RED
        else:
            return None
        return ft.Text(msg, size=12 * sx, color=color, font_family=FONT, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)

    def _image_card(self, ex, sx, sy):
        img = ft.Image(src=ex["image"], fit=ft.BoxFit.CONTAIN, width=290 * sx, height=175 * sy)
        return ft.Container(
            width=320 * sx,
            height=188 * sy,
            padding=ft.Padding.all(8 * sx),
            alignment=ft.Alignment.CENTER,
            content=img,
        )

    def _situation_chip(self, ex, sx, sy):
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18 * sx, vertical=8 * sy),
            bgcolor=YELLOW_BG,
            border_radius=16 * sx,
            border=ft.Border.all(1.2, YELLOW),
            content=ft.Text(ex.get("prompt", "Situation"), color=NAVY, size=15 * sx, weight=ft.FontWeight.BOLD, font_family=FONT, text_align=ft.TextAlign.CENTER),
        )

    def _option(self, option, sx, sy):
        ex = self.session.current
        selected = self.session.picked_for(ex) == option
        solved = self.session.is_solved(ex)
        hidden = self.session.hint_for(ex) == option and not selected
        if selected and option == ex["answer"]:
            border_color, text_color, fill = GREEN, GREEN, "#EAF8EF"
        elif selected and option != ex["answer"]:
            border_color, text_color, fill = RED, RED, "#FDECEC"
        else:
            border_color, text_color, fill = "#9CC5FF", NAVY, WHITE

        circle = ft.Container(
            width=22 * sx,
            height=22 * sx,
            border_radius=11 * sx,
            border=ft.Border.all(2, border_color),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.CHECK if selected and option == ex["answer"] else ft.Icons.CLOSE,
                            color=border_color, size=12 * sx) if selected else None,
        )
        label = ft.Text("" if hidden else option, size=14 * sx, color=text_color, font_family=FONT, weight=ft.FontWeight.BOLD)
        cont = ft.Container(
            height=42 * sy,
            border_radius=16 * sx,
            bgcolor=fill,
            border=ft.Border.all(1.6, border_color),
            padding=ft.Padding.symmetric(horizontal=12 * sx, vertical=0),
            on_click=None if solved or hidden else (lambda e, val=option: self.page.run_task(self._choose, val)),
            content=ft.Row(
                spacing=10 * sx,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[circle, ft.Container(expand=True, content=label)],
            ),
        )
        return cont

    def _small_button(self, label, icon, sx, sy, on_click):
        return ft.Container(
            width=95 * sx,
            height=44 * sy,
            bgcolor=WHITE,
            border_radius=16 * sx,
            border=ft.Border.all(1.2, "#D8E5FF"),
            shadow=ft.BoxShadow(
                blur_radius=5 * sx,
                color=ft.Colors.with_opacity(0.06, "black"),
                offset=ft.Offset(0, 2 * sy),
            ),
            on_click=on_click,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4 * sx,
                controls=[ft.Icon(icon, color=BLUE, size=16 * sx), ft.Text(label, color=BLUE, size=14 * sx, weight=ft.FontWeight.BOLD, font_family=FONT)],
            ),
        )

    def _mic_button(self, sx, sy):
        color = RED if self.rec_state == "recording" else BLUE
        return ft.Container(
            width=56 * sx,
            height=56 * sx,
            border_radius=30 * sx,
            bgcolor=color,
            alignment=ft.Alignment.CENTER,
            shadow=ft.BoxShadow(
                blur_radius=10 * sx,
                color=ft.Colors.with_opacity(0.18, color),
                offset=ft.Offset(0, 4 * sy),
            ),
            on_click=lambda e: self.page.run_task(self._on_mic, e),
            content=ft.Icon(ft.Icons.MIC, color=WHITE, size=24 * sx),
        )

    def _continue_button(self, sx, sy):
        ex = self.session.current
        enabled = self.session.can_continue(ex)
        label = "Finish" if self.session.is_last else "Continue"
        return ft.Container(
            width=210 * sx,
            height=48 * sy,
            bgcolor=GREEN if enabled else LOCKED_BG,
            border_radius=20 * sx,
            border=ft.Border.all(1.5, GREEN if enabled else "#A7B3C9"),
            alignment=ft.Alignment.CENTER,
            on_click=self._on_next if enabled else self._on_next,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4 * sx,
                controls=[
                    ft.Text(label, color=WHITE if enabled else LOCKED_FG, size=16 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=WHITE if enabled else LOCKED_FG, size=18 * sx),
                ],
            ),
        )

    def _build_quiz(self):
        sx, sy = self._scale()
        ex = self.session.current
        self.counter_text.value = f"{self.session.number} / {self.session.total}"
        self.timer_text.value = self.session.format_time(self.session.time_now())
        feedback = self._feedback(sx)

        card_content = ft.Column(
            spacing=6 * sy,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=14 * sx, vertical=4 * sy),
                    bgcolor="#CFE0FF",
                    border_radius=12 * sx,
                    content=ft.Text("PHRASES", color=NAVY, size=12 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
                ),
                ft.Text("Choose the best phrase", color=NAVY, size=21 * sx, weight=ft.FontWeight.BOLD, font_family=FONT, text_align=ft.TextAlign.CENTER),
                ft.Text("Select the most appropriate\nphrase for the situation.", color=SOFT_BLUE, size=12 * sx, font_family=FONT, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                self._image_card(ex, sx, sy),
                self._situation_chip(ex, sx, sy),
                self._option(ex["options"][0], sx, sy),
                self._option(ex["options"][1], sx, sy),
                self._option(ex["options"][2], sx, sy),
                feedback if feedback else ft.Container(height=12 * sy),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=14 * sx,
                    controls=[
                        self._small_button("Hint", ft.Icons.LIGHTBULB_OUTLINE, sx, sy, self._on_hint),
                        self._mic_button(sx, sy),
                        self._small_button("Skip", ft.Icons.FAST_FORWARD, sx, sy, self._on_skip),
                    ],
                ),
                ft.Text("Listening..." if self.rec_state == "recording" else "Tap to speak", color=SOFT_BLUE, size=11 * sx, font_family=FONT, weight=ft.FontWeight.BOLD),
                self._continue_button(sx, sy),
            ],
        )

        paper = ft.Container(
            width=min(self._width - 26 * sx, 390 * sx),
            height=min(self._height - 96 * sy, 700 * sy),
            image=ft.DecorationImage(src=HOJA_CENTRAL, fit=ft.BoxFit.FILL),
            padding=ft.Padding.only(left=18 * sx, right=18 * sx, top=18 * sy, bottom=18 * sy),
            content=card_content,
        )

        return ft.Stack(
            expand=True,
            controls=[
                ft.Image(src=FONDO_NUBES, width=self._width, height=self._height, fit=ft.BoxFit.COVER, left=0, top=0),
                ft.SafeArea(
                    content=ft.Column(
                        spacing=12 * sy,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(padding=ft.Padding.only(left=14 * sx, right=14 * sx, top=6 * sy), content=self._header(sx, sy)),
                            paper,
                        ],
                    )
                ),
            ],
        )

    def _build_paused(self):
        sx, sy = self._scale()
        def button(label, primary, on_click):
            return ft.Container(
                width=230 * sx,
                height=50 * sy,
                bgcolor=BLUE if primary else WHITE,
                border_radius=20 * sx,
                border=ft.Border.all(1.2, BLUE),
                alignment=ft.Alignment.CENTER,
                on_click=on_click,
                content=ft.Text(label, color=WHITE if primary else BLUE, size=16 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
            )
        return ft.Stack(
            expand=True,
            controls=[
                self._build_quiz(),
                ft.Container(width=self._width, height=self._height, left=0, top=0,
                             bgcolor=ft.Colors.with_opacity(0.82, WHITE)),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=280 * sx,
                        padding=ft.Padding.all(22 * sx),
                        bgcolor=WHITE,
                        border_radius=24 * sx,
                        shadow=ft.BoxShadow(blur_radius=16 * sx, color=ft.Colors.with_opacity(0.12, "black"), offset=ft.Offset(0, 6 * sy)),
                        content=ft.Column(
                            tight=True,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=12 * sy,
                            controls=[
                                ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=BLUE, size=48 * sx),
                                ft.Text("Paused", color=NAVY, size=24 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
                                ft.Text(f"Question {self.session.number} / {self.session.total}", color=SOFT_BLUE, size=14 * sx, font_family=FONT),
                                ft.Text(f"Time {self.session.format_time(self.session.time_now())}", color=SOFT_BLUE, size=14 * sx, font_family=FONT),
                                button("Resume", True, self._on_resume),
                                button("Finish now", False, self._on_finish_now),
                                button("Save & exit", False, self._on_save_exit),
                            ],
                        ),
                    )
                )
            ],
        )

    def _build_end(self):
        sx, sy = self._scale()
        stats = self.session.summary()
        def stat(label, value, color=NAVY):
            return ft.Column(
                spacing=2 * sy,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(value, color=color, size=20 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
                    ft.Text(label, color=SOFT_BLUE, size=11 * sx, font_family=FONT, text_align=ft.TextAlign.CENTER),
                ],
            )
        card = ft.Container(
            width=320 * sx,
            padding=ft.Padding.all(22 * sx),
            bgcolor=WHITE,
            border_radius=26 * sx,
            shadow=ft.BoxShadow(blur_radius=18 * sx, color=ft.Colors.with_opacity(0.10, "black"), offset=ft.Offset(0, 8 * sy)),
            content=ft.Column(
                spacing=12 * sy,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.EMOJI_EVENTS, color=GREEN, size=58 * sx),
                    ft.Text("Practice Completed!", color=NAVY, size=24 * sx, weight=ft.FontWeight.BOLD, font_family=FONT),
                    ft.Text("Great job! You finished your phrases practice.", color=SOFT_BLUE, size=12 * sx, font_family=FONT, text_align=ft.TextAlign.CENTER),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[stat("Total Time", stats["time"]), stat("Completed", f'{stats["completed"]} / {stats["total"]}', GREEN)]),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND, controls=[stat("Wrong Answers", str(stats["errors"]), RED), stat("Skips Used", str(stats["skips"]))]),
                    ft.Divider(color="#E6EEF9"),
                    stat("XP Earned", f'+{stats["xp_earned"]} XP', GREEN),
                    stat("Total XP", f'{stats["xp_total"]} XP'),
                    ft.Container(width=220 * sx, height=46 * sy, bgcolor=GREEN, border_radius=18 * sx, alignment=ft.Alignment.CENTER, on_click=self._on_restart, content=ft.Text("Practice Again", color=WHITE, size=16 * sx, weight=ft.FontWeight.BOLD, font_family=FONT)),
                    ft.Container(width=220 * sx, height=36 * sy, alignment=ft.Alignment.CENTER, on_click=self._on_home, content=ft.Text("Back to Home", color=SOFT_BLUE, size=12 * sx, weight=ft.FontWeight.BOLD, font_family=FONT)),
                ],
            ),
        )
        return ft.Stack(
            expand=True,
            controls=[
                ft.Container(width=self._width, height=self._height, bgcolor=BG_TOP),
                ft.Image(src=FONDO_NUBES, width=self._width, height=self._height, fit=ft.BoxFit.COVER, left=0, top=0),
                ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=card),
            ],
        )

    def render(self):
        if self.mode == "closed":
            return
        if self.mode == "quiz":
            content = self._build_quiz()
        elif self.mode == "paused":
            content = self._build_paused()
        else:
            content = self._build_end()
        self.shell.width = self._width
        self.shell.height = self._height
        self.shell.content = content
        self.page.update()
