
import flet as ft
from ui.theme import (
    BLUE, BLUE_SOFT, NAVY, GREY, LINE, WHITE,
    RED, RED_BG, BG_TOP, HOME_SUBTEXT, HOME_NAV_TEXT,
    HOME_CARD_BORDER, HOME_XP_COLOR, HOME_BUTTON_TEXT,
)

BASE_W, BASE_H = 941, 1672
FONT = "Comic Sans MS"


class HomeView:
    def __init__(self, page: ft.Page, user: dict, total_exercises: int, on_practice, on_logout):
        self.page, self.user, self.total = page, user, total_exercises
        self.on_practice, self.on_logout = on_practice, on_logout
        self.tab, self._width, self._height = "home", 440, 844
        self.shell = ft.Container()

    # PANTALLA PRINCIPAL

    def show(self):
        self.tab = "home"
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True, bgcolor=WHITE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell
            )
        )
        self.page.on_resize = self._fit_card
        self._fit_card()
        self.render()

    def close(self):
        self.page.on_resize = None

    def _fit_card(self, e=None):
        width = min(self.page.width or 440, 540)
        height = self.page.height or 844
        if (
            abs(width - self._width) > 1
            or abs(height - self._height) > 1
            or self.shell.content is None
        ):
            self._width, self._height = width, height
            self.render()

    # POSICIONES Y TEXTOS

    def _at(self, x, y, w, h, content=None, on_click=None, **extra):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        return ft.Container(
            left=x*sx, top=y*sy, width=w*sx, height=h*sy,
            alignment=extra.pop("alignment", ft.Alignment.CENTER),
            content=content, on_click=on_click, **extra
        )

    def _text(self, value, size, color=NAVY, bold=True, align=ft.TextAlign.LEFT):
        return ft.Text(
            str(value), size=size*self._width/BASE_W, color=color,
            font_family=FONT,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            text_align=align, max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS
        )

    def _label(self, x, y, w, h, value, size, color=NAVY, bold=True, center=False):
        align = ft.TextAlign.CENTER if center else ft.TextAlign.LEFT
        box_align = ft.Alignment.CENTER if center else ft.Alignment.CENTER_LEFT
        return self._at(
            x, y, w, h,
            self._text(value, size, color, bold, align),
            alignment=box_align
        )

    def _background(self):
        return ft.Image(
            src="imagenes/home.png", width=self._width,
            height=self._height, fit=ft.BoxFit.FILL,
            left=0, top=0,
            error_content=ft.Container(
                bgcolor=BG_TOP, alignment=ft.Alignment.CENTER,
                content=ft.Text("Falta imagenes/home.png")
            )
        )

    def _touch(self, x, y, w, h, action):
        return self._at(x, y, w, h, on_click=action)

    # DATOS DEL USUARIO

    def _done(self):
        return min(len(self.user.get("completed", [])), self.total)

    def _xp(self):
        return self.user.get("xp", 0)

    def _first_name(self):
        name = (self.user.get("name") or "").strip()
        return name.split()[0] if name else ""

    # NAVEGACION

    def _toast(self, message):
        try:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text(message))
            )
        except Exception:
            print(message)

    def _on_nav(self, key):
        if key in ("lessons", "games"):
            self._toast("Coming soon!")
            return
        self.tab = key
        self.render()

    def _on_practice(self, e=None):
        self.on_practice()

    def _on_logout(self, e=None):
        self.close()
        self.on_logout()

    def _coming_soon(self, e=None):
        self._toast("Coming soon!")

    # MENU HOME

    def _build_home(self):
        first = self._first_name()
        greeting = f"Hello, {first}!" if first else "Hello!"
        items = [self._background()]

        # Encabezado y puntos XP
        items.extend([
            self._label(285, 104, 360, 87, greeting, 50),
            self._label(302, 183, 347, 53, "Ready to learn today?", 27, HOME_SUBTEXT, False),
            self._touch(685, 137, 200, 112, lambda e: self._on_nav("profile")),
            self._at(
                755, 145, 96, 82,
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        str(self._xp()), size=17,
                        weight=ft.FontWeight.BOLD,
                        color=HOME_XP_COLOR,
                        font_family=FONT,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1, no_wrap=True
                    )
                ),
                alignment=ft.Alignment.CENTER
            ),
        ])

        # Continue Learning
        items.extend([
            self._touch(40, 270, 850, 282, self._on_practice),
            self._label(100, 294, 630, 93, "Continue Learning", 58),
            self._label(
                372, 471, 90, 48,
                f"{self._done()}/{self.total}",
                27, NAVY, True, True
            ),
            self._touch(755, 433, 120, 123, self._on_practice),
        ])

        # Tarjetas principales
        cards = [
            ("Lessons", "Explore new topics", 40, 568, 72, 780, 53, lambda e: self._on_nav("lessons")),
            ("Practice", "Build your skills", 477, 568, 500, 780, 53, self._on_practice),
            ("Mini Games", "Learn while playing", 40, 895, 72, 1080, 50, lambda e: self._on_nav("games")),
            ("My Progress", "See how far you go", 477, 895, 501, 1080, 49, lambda e: self._on_nav("profile")),
        ]

        for title, subtitle, tx, ty, x, y, size, action in cards:
            height = 315 if ty == 568 else 295
            items.extend([
                self._touch(tx, ty, 410, height, action),
                self._label(x, y, 335, 57, title, size),
                self._label(
                    x+1, y+55, 335, 42, subtitle,
                    25 if title == "My Progress" else 27,
                    HOME_SUBTEXT, False
                ),
            ])

        # Learning Path
        items.extend([
            self._label(160, 1210, 450, 63, "Learning Path", 47),
            self._label(
                162, 1262, 320, 44,
                "Your next steps", 26, HOME_SUBTEXT, False
            ),
        ])

        # View All
        items.append(self._at(
            710, 1208, 175, 88,
            content=ft.Container(
                expand=True, alignment=ft.Alignment.CENTER,
                padding=ft.Padding.symmetric(horizontal=5, vertical=2),
                border_radius=40,
                bgcolor=ft.Colors.with_opacity(0.92, WHITE),
                border=ft.Border.all(2, HOME_CARD_BORDER),
                content=ft.Row(
                    spacing=0,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            "View All", size=11,
                            weight=ft.FontWeight.BOLD,
                            color=HOME_BUTTON_TEXT,
                            font_family=FONT, no_wrap=True
                        ),
                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT,
                            size=14, color=HOME_BUTTON_TEXT
                        ),
                    ]
                )
            ),
            on_click=self._coming_soon
        ))

        # Barra inferior
        nav = [
            ("Home", 45, 74, 161, BLUE, "home"),
            ("Lessons", 251, 291, 151, HOME_NAV_TEXT, "lessons"),
            ("Games", 470, 514, 129, HOME_NAV_TEXT, "games"),
            ("Profile", 681, 706, 159, HOME_NAV_TEXT, "profile"),
        ]

        for title, hx, lx, lw, color, tab in nav:
            items.extend([
                self._touch(
                    hx, 1510, 192, 145,
                    lambda e, target=tab: self._on_nav(target)
                ),
                self._label(
                    lx, 1595, lw, 46, title,
                    31 if tab == "home" else 30,
                    color, True, True
                ),
            ])

        return items

    # PERFIL CON PLANTILLA PROFILE.PNG

    def _build_profile(self):
        name = self.user.get("name", "") or "Student"
        email = self.user.get("email", "") or ""
        initial = name.strip()[:1].upper() or "?"

        items = [
            ft.Image(
                src="imagenes/profile.png",
                width=self._width,
                height=self._height,
                fit=ft.BoxFit.FILL,
                left=0,
                top=0,
                error_content=ft.Container(
                    bgcolor=BG_TOP,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("Falta imagenes/profile.png")
                )
            )
        ]

        # Encabezado
        items.extend([
            self._label(53, 49, 89, 95, "A", 73, WHITE, True, True),
            self._label(
                155, 48, 590, 105,
                "English Adventure", 43, NAVY
            ),
            self._label(
                250, 222, 445, 125,
                "My Profile", 66, NAVY, True, True
            ),
            self._label(
                148, 355, 645, 65,
                "Here is your learning progress!",
                33, HOME_SUBTEXT, False, True
            ),
        ])

        # Nombre y correo: ambos un poquito más grandes
        items.extend([
            self._label(
                174, 522, 218, 190,
                initial, 115, WHITE, True, True
            ),
            self._label(
                423, 520, 365, 95,
                name, 69, NAVY
            ),
            self._label(
                423, 614, 365, 65,
                email, 33, HOME_SUBTEXT, False
            ),
        ])

        # Puntos y ejercicios completados
        items.extend([
            self._label(
                245, 794, 195, 67,
                "Total XP", 37, NAVY, True, True
            ),
            self._label(
                247, 862, 188, 90,
                str(self._xp()), 61, NAVY, True, True
            ),
            self._label(
                615, 794, 202, 67,
                "Completed", 35, NAVY, True, True
            ),
            self._label(
                613, 862, 205, 90,
                f"{self._done()} / {self.total}",
                46, NAVY, True, True
            ),
        ])

        # Botones
        items.extend([
            self._at(
                258, 1017, 430, 105,
                self._text("Back to Home", 47, NAVY),
                alignment=ft.Alignment.CENTER_LEFT,
                on_click=lambda e: self._on_nav("home")
            ),
            self._at(
                258, 1160, 430, 98,
                self._text("Log out", 47, NAVY),
                alignment=ft.Alignment.CENTER_LEFT,
                on_click=self._on_logout
            ),
            self._touch(
                92, 1001, 760, 131,
                lambda e: self._on_nav("home")
            ),
            self._touch(
                92, 1144, 760, 125,
                self._on_logout
            ),
        ])

        # Logros
        items.append(
            self._label(
                250, 1300, 440, 90,
                "My Achievements", 43, NAVY, True, True
            )
        )

        return items

    # MOSTRAR HOME O PERFIL

    def render(self):
        self.shell.width, self.shell.height = self._width, self._height
        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=(
                self._build_home()
                if self.tab == "home"
                else self._build_profile()
            )
        )
        self.page.update()
