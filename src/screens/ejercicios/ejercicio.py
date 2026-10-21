
import asyncio
import flet as ft
from services.ejercicios.ejercicio_service import QuizSession, format_time
from services.ejercicios.pronunciacion_service import listen_and_check
from ui.theme import (
    EXERCISE_BLUE as BLUE, EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT_BLUE, EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED, EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT, BG_TOP, BG_BOTTOM,
)

try:
    import flet_audio as fta
except ImportError:
    fta = None

BASE_W = 941
BASE_H = 1672


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
        self._width = 440
        self._height = 844
        self.timer_text = ft.Text("00:00")
        self.counter = ft.Text("1 / 16")
        self.shell = ft.Container()

    # Ciclo de vida de la pantalla
    def show(self):
        self.mode = "quiz"
        self.session.start()
        self.timer_text.value = "00:00"
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

    def _mount(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=WHITE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell,
            )
        )
        self.page.on_resize = self._fit_card
        self._fit_card()

    def _fit_card(self, e=None):
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
            self.timer_text.value = format_time(self.session.time_now())
            try:
                self.timer_text.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    # Audio y avisos
    async def _speak(self, src):
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

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception as err:
            print(f"{message} ({err})")

    # Respuestas, pista, microfono y navegacion
    async def _choose(self, option):
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

    def _on_skip(self, e):
        result = self.session.skip()
        if result == "next":
            self.rec_message = None
            self.render()
        elif result == "blocked":
            self._toast("Answer this verb to continue.")

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

    # Sistema de posiciones
    def _at(self, x, y, w, h, content=None, on_click=None, **extra):
        sx = self._width / BASE_W
        sy = self._height / BASE_H
        return ft.Container(
            left=x * sx,
            top=y * sy,
            width=w * sx,
            height=h * sy,
            alignment=extra.pop("alignment", ft.Alignment.CENTER),
            content=content,
            on_click=on_click,
            **extra,
        )

    def _text(
        self, value, size, color=NAVY, bold=True,
        italic=False, align=ft.TextAlign.CENTER,
    ):
        sx = self._width / BASE_W
        return ft.Text(
            value,
            size=size * sx,
            color=color,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            italic=italic,
            font_family=FONT,
            text_align=align,
            max_lines=1,
        )

    def _background(self):
        return ft.Image(
            src="imagenes/action_practice.png",
            width=self._width,
            height=self._height,
            fit=ft.BoxFit.FILL,
            left=0,
            top=0,
            error_content=ft.Container(
                bgcolor=BG_TOP,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("Falta imagenes/action_practice.png"),
            ),
        )

    # Opciones sobre los cuadros originales
    def _option_overlay(self, option, index):
        ex = self.session.current
        s = self.session
        picked = s.picked_for(ex)
        selected = picked == option
        correct = selected and option == ex["answer"]
        wrong = selected and not correct
        eliminated = s.hint_for(ex) == option and not selected
        centers_y = [1060, 1160, 1260]
        cy = centers_y[index]
        sx = self._width / BASE_W
        color = GREEN if correct else RED if wrong else NAVY

        async def choose(e):
            await self._choose(option)

        controls = [
            self._at(
                288, cy - 39, 420, 78,
                self._text(
                    option, 45, color=color, italic=True,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
        ]
        if selected:
            controls.append(
                self._at(
                    207, cy - 25, 48, 50,
                    ft.Icon(
                        ft.Icons.CHECK if correct else ft.Icons.CLOSE,
                        color=color,
                        size=31 * sx,
                    ),
                )
            )
        controls.append(
            self._at(
                165, cy - 43, 615, 86,
                on_click=None if eliminated or s.is_solved(ex) else choose,
            )
        )
        return controls

    def _feedback(self):
        ex = self.session.current
        picked = self.session.picked_for(ex)
        if self.rec_message is not None and self.session.is_solved(ex):
            ok, heard = self.rec_message
            msg = (
                "Great pronunciation!"
                if ok else f'I heard "{heard or "..."}". Try again.'
            )
            color = GREEN if ok else RED
        elif self.session.is_solved(ex):
            msg, color = "Correct!", GREEN
        elif picked:
            msg, color = "Wrong. Try again.", RED
        else:
            return None
        return self._at(250, 982, 445, 38, self._text(msg, 21, color))

    # Pantalla de ejercicios: posiciones originales
    def _build_quiz(self):
        s = self.session
        ex = s.current
        sx = self._width / BASE_W
        sy = self._height / BASE_H
        items = [self._background()]
        items.extend([
            self._at(
                77, 48, 96, 93,
                self._text("A", 70, WHITE),
            ),
            self._at(
                175, 55, 310, 87,
                self._text("Action Practice", 36, NAVY, italic=True),
            ),
            self._at(
                525, 73, 35, 57,
                ft.Icon(ft.Icons.ALARM, color=BLUE, size=27 * sx),
            ),
            self._at(
                559, 73, 100, 57,
                self.timer_text,
            ),
            self._at(
                718, 69, 153, 65,
                self.counter,
            ),
            self._at(
                314, 212, 306, 70,
                self._text("LOOK & CHOOSE", 31),
            ),
            self._at(
                106, 290, 730, 100,
                self._text(ex["prompt"], 56),
            ),
            self._at(
                105, 404, 733, 60,
                self._text(ex["hint"], 25, SOFT_BLUE, bold=False),
            ),
            self._at(
                214, 480, 515, 455,
                ft.Image(
                    src=ex["image"],
                    fit=ft.BoxFit.CONTAIN,
                    width=515 * sx,
                    height=455 * sy,
                ),
            ),
        ])
        for i, option in enumerate(ex["options"]):
            items.extend(self._option_overlay(option, i))

        items.extend([
            # Hint
            self._at(
                112, 1351, 222, 91,
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Icon(
                            ft.Icons.LIGHTBULB_OUTLINE,
                            color=BLUE,
                            size=34 * sx,
                        ),
                        self._text("Hint", 38, BLUE),
                    ],
                ),
                on_click=self._on_hint if s.hint_available(ex) else None,
            ),
            # Microfono
            self._at(
                392, 1335, 155, 130,
                ft.Icon(ft.Icons.MIC, color=WHITE, size=69 * sx),
                on_click=self._on_mic,
            ),
            # Tap to speak
            self._at(
                345, 1460, 250, 35,
                self._text(
                    "Listening..." if self.rec_state == "recording"
                    else "Tap to speak",
                    22, SOFT_BLUE,
                ),
            ),
            # Skip funcional
            self._at(
                610, 1351, 225, 91,
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Icon(
                            ft.Icons.FAST_FORWARD,
                            color=BLUE,
                            size=32 * sx,
                        ),
                        self._text("Skip", 38, BLUE),
                    ],
                ),
                on_click=self._on_skip,
            ),
            # Continue
            self._at(
                270, 1510, 410, 88,
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=7,
                    controls=[
                        self._text(
                            "Finish" if s.is_last else "Continue",
                            39, WHITE,
                        ),
                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT,
                            color=WHITE,
                            size=38 * sx,
                        ),
                    ],
                ),
                on_click=self._on_next if s.is_solved(ex) else None,
            ),
        ])
        feedback = self._feedback()
        if feedback:
            items.append(feedback)
        return items

    # Pantalla final sin lista de verbos
    def _build_end(self):
        stats = self.session.summary()
        sx = self._width / BASE_W
        sy = self._height / BASE_H

        def icon_circle(icon, color):
            return ft.Container(
                width=90 * sx,
                height=90 * sy,
                border_radius=100,
                bgcolor=ft.Colors.with_opacity(0.13, color),
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, color=color, size=54 * sx),
            )

        def stat(x, y, icon, value, caption, color):
            return self._at(
                x, y, 335, 215,
                ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        icon_circle(icon, color),
                        self._text(value, 49, NAVY),
                        self._text(caption, 28, SOFT_BLUE, bold=False),
                    ],
                ),
            )

        # Fondo limpio, sin dibujos de botones de ejercicios
        items = [
            self._at(
                0, 0, BASE_W, BASE_H,
                ft.Container(bgcolor=BG_TOP),
            ),
            self._at(
                -145, -125, 450, 405,
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.15, BLUE),
                    border_radius=200 * sx,
                ),
            ),
            self._at(
                685, -130, 430, 415,
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.15, BLUE),
                    border_radius=200 * sx,
                ),
            ),
            # Tarjeta blanca
            self._at(
                58, 245, 825, 1370,
                ft.Container(
                    bgcolor=WHITE,
                    border_radius=50 * sx,
                ),
            ),
            # Trofeo
            self._at(
                387, 285, 165, 130,
                ft.Icon(
                    ft.Icons.EMOJI_EVENTS,
                    color=GREEN,
                    size=94 * sx,
                ),
            ),
            # Titulo
            self._at(
                98, 408, 745, 95,
                self._text("Practice Completed!", 58),
            ),
            self._at(
                92, 510, 755, 60,
                self._text(
                    "Great job! You finished your practice.",
                    28, NAVY, bold=False,
                ),
            ),
            # Estadisticas principales
            stat(
                115, 610, ft.Icons.ACCESS_TIME,
                stats["time"], "Total Time", BLUE,
            ),
            stat(
                490, 610, ft.Icons.CHECK_CIRCLE_OUTLINE,
                f'{stats["completed"]} / {stats["total"]}',
                "Completed", GREEN,
            ),
            stat(
                115, 834, ft.Icons.CANCEL_OUTLINED,
                str(stats["errors"]), "Wrong Answers", RED,
            ),
            stat(
                490, 834, ft.Icons.SKIP_NEXT,
                str(stats["skips"]), "Skips Used", SOFT_BLUE,
            ),
            # Separador
            self._at(
                123, 1082, 695, 3,
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.25, BLUE),
                ),
            ),
            # Primer intento
            self._at(
                132, 1105, 680, 52,
                self._text(
                    "Correct on First Try",
                    39,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            self._at(
                132, 1159, 680, 58,
                self._text(
                    f'{stats["first_try"]} / {stats["total"]}',
                    40,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            # XP obtenidos
            self._at(
                132, 1243, 420, 61,
                self._text(
                    "XP Earned", 39,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            self._at(
                550, 1243, 250, 61,
                self._text(
                    f'+{stats["xp_earned"]} XP',
                    39, GREEN,
                    align=ft.TextAlign.RIGHT,
                ),
                alignment=ft.Alignment.CENTER_RIGHT,
            ),
            # XP acumulados
            self._at(
                132, 1315, 680, 60,
                self._text(
                    "Total XP", 39,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            self._at(
                132, 1370, 680, 55,
                self._text(
                    f'{stats["xp_total"]} XP',
                    40,
                    align=ft.TextAlign.LEFT,
                ),
                alignment=ft.Alignment.CENTER_LEFT,
            ),
            self._at(
                123, 1440, 695, 3,
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.25, BLUE),
                ),
            ),
            # Practice Again
            self._at(
                123, 1470, 695, 100,
                ft.Container(
                    bgcolor=BLUE,
                    border_radius=65 * sx,
                    alignment=ft.Alignment.CENTER,
                    content=self._text(
                        "Practice Again", 44, WHITE,
                    ),
                ),
                on_click=self._on_restart,
            ),
            # Regresar al inicio
            self._at(
                330, 1570, 280, 43,
                self._text("Back to Home", 24, SOFT_BLUE),
                on_click=self._on_home,
            ),
        ]
        return items

    def render(self):
        if self.mode == "closed":
            return

        s = self.session
        self.counter.value = f"{s.number} / {s.total}"
        sx = self._width / BASE_W

        self.counter.size = 36 * sx
        self.counter.weight = ft.FontWeight.BOLD
        self.counter.color = NAVY

        self.timer_text.size = 35 * sx
        self.timer_text.weight = ft.FontWeight.BOLD
        self.timer_text.color = NAVY

        self.shell.width = self._width
        self.shell.height = self._height
        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=(
                self._build_quiz()
                if self.mode == "quiz"
                else self._build_end()
            ),
        )
        self.page.update()
