
import asyncio
import flet as ft

from services.ejercicios.sentences_service import format_time
from services.ejercicios.pronunciacion_service import listen_and_check
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
)

BASE_W, BASE_H = 941, 1672
BG = "imagenes/sentences/practica.png"


class SentencesView:
    def __init__(self, page, session, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"
        self.token = 0
        self.w, self.h = 440, 844
        self.sx = self.sy = self.scale = 1
        self.shell = ft.Container(expand=True)
        self.timer_text = ft.Text("00:00")
        self.is_recording = False

    def close(self):
        self.token += 1
        self.mode = "closed"
        self.page.on_resize = None

    def show(self):
        self.mode = "quiz"
        self.session.start()
        self.token += 1
        self.is_recording = False
        self.page.clean()
        self.page.padding = self.page.spacing = 0
        self.page.add(ft.Container(
            expand=True, padding=0, margin=0,
            bgcolor=WHITE, content=self.shell
        ))
        self.page.on_resize = self.resize
        self.resize()
        self.page.run_task(self.tick, self.token)

    def resize(self, e=None):
        self.w = self.page.width or 440
        self.h = self.page.height or 844
        self.sx, self.sy = self.w / BASE_W, self.h / BASE_H
        self.scale = min(self.sx, self.sy)
        self.render()

    def box(self, x, y, w, h, content=None, action=None, align=None):
        return ft.Container(
            left=x * self.sx, top=y * self.sy,
            width=w * self.sx, height=h * self.sy,
            alignment=align or ft.Alignment(0, 0),
            content=content, on_click=action
        )

    def txt(self, value, size, color=NAVY, lines=2):
        return ft.Text(
            str(value), size=size * self.scale, color=color,
            font_family=FONT, weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER, max_lines=lines
        )

    def snack(self, message):
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()

    async def tick(self, token):
        while token == self.token and self.mode == "quiz":
            self.timer_text.value = format_time(self.session.time_now())
            try:
                self.timer_text.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    def choose(self, option):
        result = self.session.choose(option)
        if result == "correct":
            self.snack("Correct! Well done.")
        elif result == "wrong":
            self.snack("Try again!")
        self.render()

    def hint(self, e=None):
        if not self.session.hint_available(self.session.current):
            self.snack("No hints available.")
            return
        if self.session.use_hint():
            self.snack("One incorrect option was eliminated.")
        else:
            self.snack("No hints available.")
        self.render()

    def skip(self, e=None):
        result = self.session.skip()
        self.snack("Exercise skipped." if result == "next"
                   else "You cannot skip now.")
        self.render()

    def continue_quiz(self, e=None):
        if not self.session.is_solved():
            self.snack("Choose the correct answer first.")
            return
        if self.session.advance() == "finished":
            self.mode = "end"
        self.render()

    async def microphone(self, e=None):
        if self.is_recording:
            return
        ex = self.session.current
        if not self.session.is_solved(ex):
            self.snack("First answer correctly.")
            return
        self.is_recording = True
        self.render()
        try:
            ok, heard = await asyncio.to_thread(
                listen_and_check, ex["answer"]
            )
            self.snack("Good pronunciation!" if ok
                       else f'I heard: "{heard or "..."}"')
        except Exception as err:
            print(f"Microphone error: {err}")
            self.snack("Microphone not available.")
        finally:
            self.is_recording = False
            self.render()

    def home(self, e=None):
        self.close()
        self.on_home()

    def restart(self, e=None):
        self.show()

    def build_circle(self, selected, correct):
        if selected and correct:
            ring, fill, symbol, symbol_color = GREEN, "#E8F8ED", "✓", GREEN
        elif selected:
            ring, fill, symbol, symbol_color = RED, "#FDEAEA", "✕", RED
        else:
            ring, fill, symbol, symbol_color = BLUE, WHITE, "", BLUE

        return ft.Container(
            width=48 * self.scale, height=48 * self.scale,
            bgcolor=ring, border_radius=999, padding=3 * self.scale,
            content=ft.Container(
                expand=True, bgcolor=fill, border_radius=999,
                alignment=ft.Alignment(0, 0),
                content=ft.Text(
                    symbol, size=27 * self.scale, color=symbol_color,
                    weight=ft.FontWeight.BOLD, font_family=FONT
                ) if selected else None
            )
        )

    def build_option(self, option, idx):
        ex = self.session.current
        selected = self.session.picked_for(ex) == option
        solved = self.session.is_solved(ex)
        hidden = self.session.hint_for(ex) == option

        if selected and option == ex["answer"]:
            border_color, fill_color, text_color = GREEN, "#E8F8ED", GREEN
        elif selected:
            border_color, fill_color, text_color = RED, "#FDEAEA", RED
        else:
            border_color, fill_color, text_color = BLUE, WHITE, NAVY

        content = ft.Row(
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=24 * self.scale,
            controls=[
                self.build_circle(selected, option == ex["answer"]),
                ft.Text(
                    "" if hidden else option,
                    size=43 * self.scale, color=text_color,
                    font_family=FONT, weight=ft.FontWeight.BOLD,
                    expand=True
                )
            ]
        )

        outer = ft.Container(
            expand=True, bgcolor=border_color,
            border_radius=55 * self.scale, padding=3 * self.scale,
            content=ft.Container(
                expand=True, bgcolor=fill_color,
                border_radius=52 * self.scale,
                padding=ft.Padding(25 * self.scale, 0, 25 * self.scale, 0),
                alignment=ft.Alignment(0, 0), content=content
            )
        )

        positions = [945, 1065, 1185]
        return self.box(
            82, positions[idx], 777, 100, outer,
            None if solved or hidden else
            (lambda e, value=option: self.choose(value))
        )

    def build_quiz(self):
        ex = self.session.current
        self.timer_text.size = 31 * self.scale
        self.timer_text.color = NAVY
        self.timer_text.font_family = FONT
        self.timer_text.weight = ft.FontWeight.BOLD

        items = [
            self.box(0, 0, BASE_W, BASE_H, ft.Image(
                src=BG, width=self.w, height=self.h, fit=ft.BoxFit.FILL
            )),
            self.box(65, 45, 105, 105, self.txt("A", 68, WHITE, 1)),
            self.box(180, 55, 330, 85,
                     self.txt("Action Practice", 40, NAVY, 1)),
            self.box(505, 55, 205, 85, ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.ALARM, color=BLUE,
                            size=38 * self.scale),
                    self.timer_text
                ]
            )),
            self.box(710, 55, 180, 85, self.txt(
                f"{self.session.number} / {self.session.total}",
                40, NAVY, 1
            )),
            self.box(285, 165, 370, 105,
                     self.txt("SENTENCES", 46, NAVY, 1)),
            self.box(80, 265, 780, 95,
                     self.txt("Complete the sentence", 62, NAVY, 1)),
            self.box(110, 355, 720, 90, self.txt(
                "Choose the correct option to\ncomplete the sentence.",
                31, SOFT, 2
            )),
            self.box(60, 435, 820, 470, ft.Image(
                src=ex["image"], width=820 * self.sx,
                height=470 * self.sy, fit=ft.BoxFit.CONTAIN
            )),
            self.box(85, 820, 775, 115,
                     self.txt(ex["prompt"], 52, NAVY, 1))
        ]

        items.append(self.box(
            70, 940, 800, 355,
            ft.Container(expand=True, bgcolor=WHITE)
        ))

        for i, option in enumerate(ex["options"][:3]):
            items.append(self.build_option(option, i))

        items.append(self.box(65, 1330, 245, 100, ft.Row(
            alignment=ft.MainAxisAlignment.CENTER, spacing=10,
            controls=[
                ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, color=BLUE,
                        size=37 * self.scale),
                self.txt("Hint", 38, BLUE, 1)
            ]
        ), self.hint))

        items.append(self.box(365, 1310, 200, 120, ft.Icon(
            ft.Icons.MIC, color=WHITE, size=95 * self.scale
        ), self.microphone))

        items.append(self.box(320, 1435, 300, 40, self.txt(
            "Listening..." if self.is_recording else "Tap to speak",
            27, SOFT, 1
        )))

        items.append(self.box(625, 1330, 245, 100, ft.Row(
            alignment=ft.MainAxisAlignment.CENTER, spacing=10,
            controls=[
                ft.Icon(ft.Icons.FAST_FORWARD, color=BLUE,
                        size=38 * self.scale),
                self.txt("Skip", 38, BLUE, 1)
            ]
        ), self.skip))

        items.append(self.box(190, 1500, 560, 110, ft.Row(
            alignment=ft.MainAxisAlignment.CENTER, spacing=12,
            controls=[
                self.txt(
                    "Finish" if self.session.is_last else "Continue",
                    46, WHITE, 1
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=WHITE,
                        size=48 * self.scale)
            ]
        ), self.continue_quiz if self.session.is_solved(ex) else None))

        return items

    def build_end(self):
        s = self.session.summary()
        card = ft.Container(
            width=760 * self.sx, height=1050 * self.sy,
            bgcolor=WHITE, border_radius=35 * self.scale,
            padding=25 * self.scale,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=18 * self.scale,
                controls=[
                    ft.Icon(ft.Icons.EMOJI_EVENTS, color=GREEN,
                            size=65 * self.scale),
                    self.txt("Practice Completed!", 42),
                    self.txt(f'{s["completed"]} / {s["total"]}', 35, GREEN),
                    self.txt(f'Time: {s["time"]}', 28),
                    self.txt(f'Wrong Answers: {s["errors"]}', 27),
                    self.txt(f'Skips Used: {s["skips"]}', 27),
                    self.txt(f'+{s["xp_earned"]} XP', 36, GREEN),
                    self.txt(f'Total XP: {s["xp_total"]}', 30),
                    ft.Container(
                        width=280 * self.scale, height=70 * self.scale,
                        bgcolor=GREEN, border_radius=35 * self.scale,
                        alignment=ft.Alignment(0, 0),
                        content=self.txt("Practice Again", 25, WHITE),
                        on_click=self.restart
                    ),
                    ft.Container(
                        width=280 * self.scale, height=70 * self.scale,
                        bgcolor=SOFT, border_radius=35 * self.scale,
                        alignment=ft.Alignment(0, 0),
                        content=self.txt("Back to Home", 25, NAVY),
                        on_click=self.home
                    )
                ]
            )
        )

        return [
            self.box(0, 0, BASE_W, BASE_H, ft.Image(
                src=BG, width=self.w, height=self.h, fit=ft.BoxFit.FILL
            )),
            self.box(90, 300, 760, 1050, card)
        ]

    def render(self):
        if self.mode == "closed":
            return
        controls = self.build_quiz() if self.mode == "quiz" else self.build_end()
        self.shell.width = self.w
        self.shell.height = self.h
        self.shell.content = ft.Stack(
            width=self.w, height=self.h, controls=controls
        )
        self.page.update()
