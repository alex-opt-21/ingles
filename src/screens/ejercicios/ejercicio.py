import asyncio

import flet as ft

from services.ejercicios.ejercicio_service import QuizSession, format_time
from services.ejercicios.pronunciacion_service import listen_and_check
from ui.theme import (
    APP_NAME, APP_TAGLINE, LOGO, OPTION_ICONS,
    BLUE, BLUE_SOFT, NAVY, GREY, LINE, TRACK, WHITE,
    GREEN, GREEN_DARK, GREEN_BG, RED, RED_BG,
    BG_TOP, BG_BOTTOM, RADIO_IDLE, ICON_IDLE, DISABLED_BG, DISABLED_TEXT,
    glass,
)

try:
    import flet_audio as fta
except ImportError:
    fta = None


# ---------- botones reutilizables ----------

def primary_button(label: str, on_click, enabled: bool = True) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Text(
                    label,
                    size=17,
                    weight=ft.FontWeight.W_600,
                    color=WHITE if enabled else DISABLED_TEXT,
                ),
                ft.Icon(
                    ft.Icons.CHEVRON_RIGHT,
                    size=22,
                    color=WHITE if enabled else DISABLED_TEXT,
                ),
            ],
        ),
        alignment=ft.Alignment.CENTER,
        height=54,
        border_radius=16,
        bgcolor=BLUE if enabled else DISABLED_BG,
        shadow=ft.BoxShadow(
            blur_radius=14,
            color=ft.Colors.with_opacity(0.3, BLUE),
            offset=ft.Offset(0, 5),
        ) if enabled else None,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        on_click=on_click if enabled else None,
    )


def pill_button(icon, label: str, on_click, enabled: bool = True) -> ft.Container:
    color = BLUE if enabled else DISABLED_TEXT
    return ft.Container(
        content=ft.Row(
            spacing=6,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=18, color=color),
                ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=color),
            ],
        ),
        padding=ft.Padding.symmetric(horizontal=16, vertical=11),
        border_radius=22,
        bgcolor=glass(0.9),
        border=ft.Border.all(1, LINE),
        on_click=on_click,
    )


class QuizView:
    def __init__(self, page: ft.Page, session: QuizSession, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz" 
        self._tick_id = 0
        self._player = None
        self.rec_state = "idle"    
        self.rec_message = None 
        self._build_static()

    # ================= construcción de contenedores fijos =================

    def _build_static(self):
        self.counter = ft.Text()
        self.counter_pill = ft.Container(
            content=self.counter,
            padding=ft.Padding.symmetric(horizontal=14, vertical=6),
            border_radius=20,
            bgcolor=glass(0.9),
            border=ft.Border.all(1, LINE),
        )

        self.back_btn = ft.Container(
            width=40,
            height=40,
            border_radius=20,
            bgcolor=glass(0.9),
            border=ft.Border.all(1, LINE),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.ARROW_BACK_IOS_NEW, size=16, color=BLUE),
            on_click=self._on_back,
        )

        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self.back_btn,
                        ft.Image(
                            src=LOGO,
                            width=40,
                            height=40,
                            fit=ft.BoxFit.CONTAIN,
                            error_content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=28, color=GREY),
                        ),
                        ft.Column(
                            spacing=0,
                            controls=[
                                ft.Text(APP_NAME, size=16, weight=ft.FontWeight.BOLD, color=NAVY),
                                ft.Text(APP_TAGLINE, size=12, color=GREY),
                            ],
                        ),
                    ],
                ),
                self.counter_pill,
            ],
        )
        header_box = ft.Container(
            content=header,
            padding=ft.Padding.only(left=16, right=16, top=8),
        )

        self.progress_holder = ft.Container(padding=ft.Padding.symmetric(horizontal=16))

        self.timer_text = ft.Text("00:00", size=13, weight=ft.FontWeight.W_600, color=NAVY)
        self.timer_chip = ft.Container(
            content=ft.Row(
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(ft.Icons.TIMER_OUTLINED, size=16, color=BLUE), self.timer_text],
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=18,
            bgcolor=glass(0.9),
            border=ft.Border.all(1, LINE),
        )

        self.content = ft.Column(
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        body = ft.Container(
            content=self.content,
            expand=True,
            padding=ft.Padding.only(left=16, right=16, top=4, bottom=12),
        )

        self.shell = ft.Container(
            width=390,
            height=844,
            content=ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=10,
                    controls=[header_box, self.progress_holder, body],
                ),
            ),
        )

    # ================= ciclo de vida =================

    def show(self):
        """Monta el layout y arranca la ronda."""
        self.mode = "quiz"
        self.session.start()
        self.timer_text.value = "00:00"
        self._mount()
        self.render()
        self._tick_id += 1
        self.page.run_task(self._tick, self._tick_id)

    def close(self):
        """Detiene el cronómetro y el audio (al salir de la pantalla)."""
        self._tick_id += 1
        self.mode = "closed"
        self.page.on_resize = None

    def _mount(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
                gradient=ft.LinearGradient(
                    begin=ft.Alignment.TOP_CENTER,
                    end=ft.Alignment.BOTTOM_CENTER,
                    colors=[BG_TOP, BG_BOTTOM],
                ),
                content=self.shell,
            )
        )
        self.page.on_resize = self._fit_card
        self._fit_card()

    def _fit_card(self, e=None):
        if self.page.width:
            self.shell.width = min(self.page.width, 440)
        if self.page.height:
            self.shell.height = self.page.height
        self.page.update()

    async def _tick(self, token: int):
        while self._tick_id == token and self.mode == "quiz":
            self.timer_text.value = format_time(self.session.time_now())
            try:
                self.timer_text.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    # ================= audio y avisos =================

    async def _speak(self, src: str):
        if fta is None:
            return
        try:
            page = self.page
            if self._player is not None and self._player in page.services:
                page.services.remove(self._player)
            new = fta.Audio(src=src, autoplay=True)
            page.services.append(new)
            self._player = new
            page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def _toast(self, message: str):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception as err:
            print(f"{message} ({err})")

    # ================= handlers (solo delegan al backend) =================

    async def _choose(self, option: str):
        result = self.session.choose(option)
        if result == "ignored":
            return
        self.render()
        if result == "correct":
            await self._speak(self.session.current["audio"])

    def _on_back(self, e):
        self.rec_message = None
        if self.session.back():
            self.render()
        else:
            self._on_home() 

    def _on_next(self, e):
        self.rec_message = None
        result = self.session.advance()
        if result == "finished":
            self.mode = "end"
            self.render()
        elif result == "next":
            self.render()

    def _on_hint(self, e):
        if self.session.use_hint():
            self.render()

    async def _on_listen(self, e):
        ex = self.session.current
        if self.session.is_solved(ex):
            await self._speak(ex["audio"])
        else:
            self._toast("First choose the correct answer.")

    async def _on_mic(self, e):
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
            self.rec_message = await asyncio.to_thread(
                listen_and_check, ex["answer"]
            )
        except Exception as err:
            print(f"Mic error: {err}")
            self._toast("Could not access the microphone.")
        finally:
            self.rec_state = "idle"
            self.render()

    def _on_restart(self, e=None):
        self.show()

    def _on_home(self, e=None):
        self.close()
        self.on_home()

    # ================= piezas de UI =================

    def _progress_bar(self) -> ft.Container:
        done = self.session.number
        rest = self.session.total - done
        parts = [ft.Container(expand=done, height=6, bgcolor=BLUE)]
        if rest > 0:
            parts.append(ft.Container(expand=rest, height=6))
        return ft.Container(
            height=6,
            border_radius=3,
            bgcolor=TRACK,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Row(spacing=0, controls=parts),
        )

    def _option_tile(self, ex: dict, option: str) -> ft.Container:
        s = self.session
        picked = s.picked_for(ex)
        selected = picked == option
        correct = selected and option == ex["answer"]
        wrong = selected and not correct
        eliminated = s.hint_for(ex) == option and not selected

        if correct:
            border, bg, accent = GREEN, GREEN_BG, GREEN
            radio = ft.Container(
                width=22, height=22, border_radius=11, bgcolor=GREEN,
                border=ft.Border.all(2, GREEN), alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.CHECK, size=14, color=WHITE),
            )
        elif wrong:
            border, bg, accent = RED, RED_BG, RED
            radio = ft.Container(
                width=22, height=22, border_radius=11,
                border=ft.Border.all(2, RED), alignment=ft.Alignment.CENTER,
                content=ft.Container(width=10, height=10, border_radius=5, bgcolor=RED),
            )
        else:
            border, bg, accent = LINE, glass(0.9), ICON_IDLE
            radio = ft.Container(
                width=22, height=22, border_radius=11,
                border=ft.Border.all(2, RADIO_IDLE),
            )

        row: list[ft.Control] = [
            radio,
            ft.Text(
                option,
                size=16,
                weight=ft.FontWeight.W_600,
                color=NAVY,
                expand=True,
                style=ft.TextStyle(
                    decoration=ft.TextDecoration.LINE_THROUGH if eliminated else None
                ),
            ),
        ]
        icon_name = OPTION_ICONS.get(option.lower())
        icon = getattr(ft.Icons, icon_name, None) if icon_name else None
        if icon is not None:
            row.append(ft.Icon(icon, size=22, color=accent))

        async def handler(e):
            await self._choose(option)

        return ft.Container(
            content=ft.Row(row, spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=52,
            padding=ft.Padding.symmetric(horizontal=16),
            border_radius=16,
            bgcolor=bg,
            border=ft.Border.all(1.5 if selected else 1, border),
            opacity=0.4 if eliminated else 1,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            on_click=None if eliminated else handler,
        )

    def _picture(self, ex: dict) -> ft.Container:
        return ft.Container(
            height=210,
            border_radius=20,
            bgcolor="#EEF2FA",
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=ft.BoxShadow(
                blur_radius=18,
                color=ft.Colors.with_opacity(0.12, "#1F2A55"),
                offset=ft.Offset(0, 6),
            ),
            content=ft.Stack(
                controls=[
                    ft.Image(
                        src=ex["image"],
                        fit=ft.BoxFit.COVER,
                        left=0, top=0, right=0, bottom=0,
                        error_content=ft.Container(
                            bgcolor=LINE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=48, color=GREY),
                        ),
                    ),
                    ft.Container(
                        content=ft.Text(ex.get("image_credit", ""), size=9, color=WHITE),
                        right=10,
                        bottom=8,
                    ),
                ]
            ),
        )

    def _feedback(self, ex: dict) -> ft.Control:
        picked = self.session.picked_for(ex)
        if self.rec_message is not None and self.session.is_solved(ex):
            ok, heard = self.rec_message
            return ft.Container(
                height=26,
                alignment=ft.Alignment.CENTER_LEFT,
                content=ft.Row(
                    spacing=6,
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if ok else ft.Icons.CANCEL,
                            size=18,
                            color=GREEN if ok else RED,
                        ),
                        ft.Text(
                            "Great pronunciation!" if ok else f'I heard "{heard or "..."}". Try again.',
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=GREEN_DARK if ok else RED,
                        ),
                    ],
                ),
            )
        else:
            body_ctrl = ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CANCEL, size=18, color=RED),
                    ft.Text(
                        "Wrong. Try again.",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=RED,
                    ),
                ],
            )
        return ft.Container(content=body_ctrl, height=26, alignment=ft.Alignment.CENTER_LEFT)

    def _mic_button(self) -> ft.Column:
        listening = self.rec_state == "recording"
        color = RED if listening else BLUE
        label = "Listening..." if listening else "Tap to speak"

        return ft.Column(
            spacing=4,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                ft.Container(
                    width=84,
                    height=84,
                    border_radius=42,
                    bgcolor=ft.Colors.with_opacity(0.12, color),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=62,
                        height=62,
                        border_radius=31,
                        alignment=ft.Alignment.CENTER,
                        bgcolor=color,
                        shadow=ft.BoxShadow(
                            blur_radius=16,
                            color=ft.Colors.with_opacity(0.4, color),
                            offset=ft.Offset(0, 6),
                        ),
                        content=ft.Icon(ft.Icons.MIC, size=30, color=WHITE),
                        on_click=self._on_mic,
                    ),
                ),
                ft.Text(label, size=11, color=color),
            ],
        )

    def _actions_row(self, ex: dict) -> ft.Row:
        s = self.session
        hint_available = s.hint_available(ex)
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                pill_button(ft.Icons.VOLUME_UP, "Listen", self._on_listen, enabled=s.is_solved(ex)),
                self._mic_button(),
                pill_button(
                    ft.Icons.LIGHTBULB_OUTLINE,
                    "Hint",
                    self._on_hint if hint_available else None,
                    enabled=hint_available,
                ),
            ],
        )

    # ================= pantallas =================

    def _build_quiz(self) -> list[ft.Control]:
        s = self.session
        ex = s.current

        topic_chip = ft.Container(
            content=ft.Row(
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.VISIBILITY_OUTLINED, size=15, color=BLUE),
                    ft.Text(
                        "LOOK AND CHOOSE",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color=BLUE,
                        style=ft.TextStyle(letter_spacing=1.0),
                    ),
                ],
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=18,
            bgcolor=BLUE_SOFT,
        )

        return [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[topic_chip, self.timer_chip],
            ),
            ft.Column(
                spacing=4,
                controls=[
                    ft.Text(ex["prompt"], size=30, weight=ft.FontWeight.W_800, color=NAVY),
                    ft.Text(ex["hint"], size=13, color=GREY),
                ],
            ),
            self._picture(ex),
            ft.Column(spacing=10, controls=[self._option_tile(ex, opt) for opt in ex["options"]]),
            self._feedback(ex),
            self._actions_row(ex),
            primary_button(
                "Finish" if s.is_last else "Continue",
                self._on_next,
                enabled=s.is_solved(ex),
            ),
        ]

    def _build_end(self) -> list[ft.Control]:
        s = self.session
        return [
            ft.Container(height=24),
            ft.Container(
                padding=24,
                border_radius=28,
                bgcolor=glass(0.9),
                border=ft.Border.all(1, LINE),
                content=ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=84,
                            height=84,
                            border_radius=42,
                            bgcolor=GREEN_BG,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.EMOJI_EVENTS, size=44, color=GREEN),
                        ),
                        ft.Text(
                            "You did it!",
                            size=28,
                            weight=ft.FontWeight.W_800,
                            color=NAVY,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text("Your total time", size=13, color=GREY),
                        ft.Text(
                            format_time(s.elapsed),
                            size=48,
                            weight=ft.FontWeight.W_800,
                            color=BLUE,
                        ),
                        ft.Text(
                            "No mistakes, perfect!" if s.errors == 0 else f"Failed attempts: {s.errors}",
                            size=13,
                            color=GREY,
                        ),
                        ft.Text(f"{s.user_name} · Total XP: {s.xp}", size=13, color=GREY),
                        ft.Container(height=6),
                        ft.Column(
                            spacing=6,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=[
                                primary_button("Practice again", self._on_restart),
                                ft.TextButton(content=ft.Text("Back to Home"), on_click=self._on_home),
                            ],
                        ),
                    ],
                ),
            ),
        ]

    def render(self):
        s = self.session
        in_quiz = self.mode == "quiz"

        self.counter_pill.visible = in_quiz
        self.back_btn.visible = in_quiz
        self.progress_holder.visible = in_quiz

        if in_quiz:
            self.back_btn.opacity = 1
            self.back_btn.on_click = self._on_back
            self.counter.spans = [
                ft.TextSpan(str(s.number), ft.TextStyle(weight=ft.FontWeight.BOLD, color=NAVY)),
                ft.TextSpan(f" / {s.total}", ft.TextStyle(color=GREY)),
            ]
            self.counter.size = 12
            self.progress_holder.content = self._progress_bar()
            self.content.controls = self._build_quiz()
        else:
            self.content.controls = self._build_end()

        self.page.update()