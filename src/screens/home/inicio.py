
import flet as ft
from ui.theme import (
    BLUE, BLUE_SOFT, NAVY, GREY, LINE,
    WHITE, RED, RED_BG, BG_TOP
)

BASE_W, BASE_H = 941, 1672
FONT = "Comic Sans MS"
SUBTEXT = "#58739F"
NAV_TEXT = "#536B96"


class HomeView:
    def __init__(self, page, user, total_exercises, on_practice,
                 on_logout, on_sentences=None):
        self.page = page
        self.user = user
        self.total = total_exercises
        self.on_practice = on_practice
        self.on_logout = on_logout
        self.on_sentences = on_sentences
        self.tab = "home"
        self._width, self._height = 440, 844
        self.shell = ft.Container()

    def show(self):
        self.tab = "home"
        self.page.clean()
        self.page.add(ft.Container(
            expand=True, bgcolor=WHITE,
            alignment=ft.Alignment.TOP_CENTER,
            content=self.shell
        ))
        self.page.on_resize = self._fit_card
        self._fit_card()
        self.render()

    def close(self):
        self.page.on_resize = None

    def _fit_card(self, e=None):
        width = min(self.page.width or 440, 540)
        height = self.page.height or 844
        if (abs(width-self._width) > 1 or
                abs(height-self._height) > 1 or
                self.shell.content is None):
            self._width, self._height = width, height
            self.render()

    def _at(self, x, y, w, h, content=None, on_click=None, **extra):
        sx, sy = self._width/BASE_W, self._height/BASE_H
        return ft.Container(
            left=x*sx, top=y*sy, width=w*sx, height=h*sy,
            alignment=extra.pop("alignment", ft.Alignment.CENTER),
            content=content, on_click=on_click, **extra
        )

    def _text(self, value, size, color=NAVY, bold=True,
              align=ft.TextAlign.LEFT):
        return ft.Text(
            str(value), size=size*self._width/BASE_W,
            color=color, font_family=FONT,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            text_align=align, max_lines=1, no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS
        )

    def _label(self, x, y, w, h, value, size, color=NAVY,
               bold=True, center=False):
        align = ft.TextAlign.CENTER if center else ft.TextAlign.LEFT
        box_align = ft.Alignment.CENTER if center else ft.Alignment.CENTER_LEFT
        return self._at(
            x, y, w, h, self._text(value, size, color, bold, align),
            alignment=box_align
        )

    def _touch(self, x, y, w, h, action):
        return self._at(x, y, w, h, on_click=action)

    def _background(self):
        return ft.Image(
            src="imagenes/home.png",
            width=self._width, height=self._height,
            fit=ft.BoxFit.FILL, left=0, top=0,
            error_content=ft.Container(
                bgcolor=BG_TOP, alignment=ft.Alignment.CENTER,
                content=ft.Text("Falta imagenes/home.png")
            )
        )

    def _done(self):
        return min(len(self.user.get("completed", [])), self.total)

    def _xp(self):
        return self.user.get("xp", 0)

    def _first_name(self):
        name = (self.user.get("name") or "").strip()
        return name.split()[0] if name else ""

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception:
            print(message)

    def _on_nav(self, key):
        if key in ("home", "profile"):
            self.tab = key
            self.render()
        elif key in ("lessons", "games"):
            self._coming_soon()

    def _on_practice(self, e=None):
        self.on_practice()

    def _on_flashcards(self, e=None):
        self.on_practice()

    def _on_sentences(self, e=None):
        if self.on_sentences:
            self.on_sentences()
        else:
            self._coming_soon()

    def _on_continue(self, e=None):
        self.on_practice()

    def _coming_soon(self, e=None):
        self._toast("This section is coming soon!")

    def _select_level(self, level):
        self._toast(f"{level} level coming soon!")

    def _on_logout(self, e=None):
        self.close()
        self.on_logout()

    def _nav_item(self, title, icon, tab):
        color = BLUE if self.tab == tab else NAV_TEXT
        sx = self._width/BASE_W
        return ft.Container(
            expand=True, alignment=ft.Alignment.CENTER,
            on_click=lambda e, target=tab: self._on_nav(target),
            content=ft.Column(
                spacing=3*sx,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=42*sx, color=color),
                    ft.Text(
                        title, size=24*sx, color=color,
                        font_family=FONT, weight=ft.FontWeight.BOLD,
                        max_lines=1, no_wrap=True
                    )
                ]
            )
        )

    def _bottom_navigation(self):
        return self._at(
            45, 1500, 851, 145,
            ft.Row(
                spacing=0, expand=True,
                controls=[
                    self._nav_item("Home", ft.Icons.HOME_ROUNDED, "home"),
                    self._nav_item("Lessons", ft.Icons.MENU_BOOK_ROUNDED, "lessons"),
                    self._nav_item("Games", ft.Icons.SPORTS_ESPORTS, "games"),
                    self._nav_item("Profile", ft.Icons.PERSON_OUTLINE, "profile")
                ]
            )
        )

    def _build_home(self):
        first = self._first_name()
        greeting = f"Hello, {first}!" if first else "Hello!"
        items = [self._background()]

        items.extend([
            self._label(275, 80, 410, 85, greeting,
                        46 if len(greeting) <= 13 else 42),
            self._label(302, 177, 355, 45,
                        "Ready to learn today?", 25, SUBTEXT, False),
            self._label(740, 125, 110, 75,
                        str(self._xp()), 29, NAVY, True, True),
            self._label(100, 285, 600, 75, "Continue Learning", 48),
            self._label(100, 350, 350, 45,
                        "At the Airport", 27, SUBTEXT, False),
            self._label(75, 635, 350, 60, "Flashcards", 40),
            self._label(76, 690, 350, 38,
                        "Learn vocabulary", 23, SUBTEXT, False),
            self._label(520, 635, 350, 60, "Sentences", 40),
            self._label(520, 690, 360, 38,
                        "Build correct sentences", 22, SUBTEXT, False),
            self._label(75, 895, 350, 60, "Questions", 40),
            self._label(76, 950, 350, 38,
                        "Ask and answer", 23, SUBTEXT, False),
            self._label(520, 895, 350, 60, "Phrases", 40),
            self._label(520, 950, 360, 38,
                        "Use common expressions", 22, SUBTEXT, False),
            self._label(350, 1045, 260, 60, "Songs", 45),
            self._label(350, 1095, 330, 42,
                        "Learn with music", 24, SUBTEXT, False),
            self._label(190, 1205, 410, 58, "Select Level", 41),
            self._label(190, 1255, 410, 42,
                        "Choose your difficulty", 23, SUBTEXT, False),
            self._label(70, 1330, 235, 55, "Basic", 31, NAVY, True, True),
            self._label(70, 1375, 235, 40,
                        "(1 - 20)", 23, SUBTEXT, False, True),
            self._label(355, 1330, 235, 55,
                        "Intermediate", 29, NAVY, True, True),
            self._label(355, 1375, 235, 40,
                        "(21 - 60)", 23, SUBTEXT, False, True),
            self._label(650, 1330, 235, 55,
                        "Advanced", 31, NAVY, True, True),
            self._label(650, 1375, 235, 40,
                        "(61 - 100)", 23, SUBTEXT, False, True)
        ])

        items.extend([
            self._touch(40, 270, 850, 282, self._on_continue),
            self._touch(40, 568, 410, 315, self._on_flashcards),
            self._touch(477, 568, 410, 315, self._on_sentences),
            self._touch(40, 895, 410, 100, self._coming_soon),
            self._touch(477, 895, 410, 100, self._coming_soon),
            self._touch(40, 1000, 850, 165, self._coming_soon),
            self._touch(65, 1300, 275, 130,
                        lambda e: self._select_level("Basic")),
            self._touch(355, 1300, 275, 130,
                        lambda e: self._select_level("Intermediate")),
            self._touch(650, 1300, 275, 130,
                        lambda e: self._select_level("Advanced")),
            self._touch(685, 137, 200, 112,
                        lambda e: self._on_nav("profile"))
        ])

        items.append(self._bottom_navigation())
        return items

    # PERFIL ILUSTRADO ORIGINAL
    def _build_profile(self):
        name = self.user.get("name", "") or "Student"
        email = self.user.get("email", "") or ""
        initial = name.strip()[:1].upper() or "?"

        items = [
            ft.Image(
                src="imagenes/profile.png",
                width=self._width, height=self._height,
                fit=ft.BoxFit.FILL, left=0, top=0,
                error_content=ft.Container(
                    bgcolor=BG_TOP, alignment=ft.Alignment.CENTER,
                    content=ft.Text("Falta imagenes/profile.png")
                )
            )
        ]

        items.extend([
            self._label(53, 49, 89, 95, "A", 73, WHITE, True, True),
            self._label(155, 48, 590, 105,
                        "English Adventure", 43, NAVY),
            self._label(250, 222, 445, 125,
                        "My Profile", 66, NAVY, True, True),
            self._label(148, 355, 645, 65,
                        "Here is your learning progress!",
                        33, SUBTEXT, False, True),
            self._label(174, 522, 218, 190,
                        initial, 115, WHITE, True, True),
            self._label(423, 520, 365, 95, name, 69, NAVY),
            self._label(423, 614, 365, 65,
                        email, 33, SUBTEXT, False),
            self._label(245, 794, 195, 67,
                        "Total XP", 37, NAVY, True, True),
            self._label(247, 862, 188, 90,
                        str(self._xp()), 61, NAVY, True, True),
            self._label(615, 794, 202, 67,
                        "Completed", 35, NAVY, True, True),
            self._label(613, 862, 205, 90,
                        f"{self._done()} / {self.total}",
                        46, NAVY, True, True)
        ])

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
            self._touch(92, 1001, 760, 131,
                        lambda e: self._on_nav("home")),
            self._touch(92, 1144, 760, 125, self._on_logout),
            self._label(250, 1300, 440, 90,
                        "My Achievements", 43, NAVY, True, True)
        ])

        return items

    def render(self):
        self.shell.width = self._width
        self.shell.height = self._height
        controls = (
            self._build_home()
            if self.tab == "home"
            else self._build_profile()
        )
        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=controls
        )
        self.page.update()
