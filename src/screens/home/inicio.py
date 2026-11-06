"""Pantalla Home de Saylo: interfaz creada con controles Flet reales.

Copia las imágenes del paquete a src/assets/imagenes/home/.
Esta vista espera que Flet sirva src/assets como carpeta de assets,
igual que el código original que utiliza imagenes/profile.png.
"""

import flet as ft
from screens.ranking import mostrar_ranking
from ui.theme import (
    BLUE, BLUE_SOFT, NAVY, GREY, LINE,
    WHITE, RED, RED_BG, BG_TOP
)

BASE_W, BASE_H = 941, 1672
FONT = "Comic Sans MS"
SUBTEXT = "#58739F"
NAV_TEXT = "#536B96"
ASSET_HOME = "imagenes/home/"


class HomeView:
    def __init__(self, page, user, total_exercises, on_practice,
                 on_logout, on_sentences=None, on_questions=None,
                 on_phrases=None):
        self.page = page
        self.user = user
        self.total = total_exercises
        self.on_practice = on_practice
        self.on_logout = on_logout
        self.on_sentences = on_sentences
        self.on_questions = on_questions
        self.on_phrases = on_phrases
        self.tab = "home"
        self._width, self._height = 440, 844
        self.shell = ft.Container()

    def show(self):
        self.tab = "home"
        self.page.clean()
        self.page.add(ft.Container(
            expand=True,
            bgcolor=WHITE,
            alignment=ft.Alignment.TOP_CENTER,
            content=self.shell,
        ))
        self.page.on_resize = self._fit_card
        self._fit_card()
        self.render()

    def close(self):
        self.page.on_resize = None

    def _fit_card(self, e=None):
        width = min(self.page.width or 440, 540)
        height = self.page.height or 844
        if (abs(width - self._width) > 1 or
                abs(height - self._height) > 1 or
                self.shell.content is None):
            self._width, self._height = width, height
            self.render()

    def _at(self, x, y, w, h, content=None, on_click=None, **extra):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        return ft.Container(
            left=x * sx, top=y * sy,
            width=w * sx, height=h * sy,
            alignment=extra.pop("alignment", ft.Alignment.CENTER),
            content=content, on_click=on_click, **extra,
        )

    def _text(self, value, size, color=NAVY, bold=True,
              align=ft.TextAlign.LEFT):
        return ft.Text(
            str(value),
            size=size * self._width / BASE_W,
            color=color,
            font_family=FONT,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            text_align=align,
            max_lines=1,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

    def _label(self, x, y, w, h, value, size, color=NAVY,
               bold=True, center=False):
        align = ft.TextAlign.CENTER if center else ft.TextAlign.LEFT
        box_align = ft.Alignment.CENTER if center else ft.Alignment.CENTER_LEFT
        return self._at(
            x, y, w, h,
            self._text(value, size, color, bold, align),
            alignment=box_align,
        )

    def _touch(self, x, y, w, h, action):
        return self._at(x, y, w, h, on_click=action)

    def _background(self):
        # Solamente las nubes son imagen de fondo. Ningún botón queda dibujado.
        return ft.Image(
            src=ASSET_HOME + "fondo.png",
            width=self._width,
            height=self._height,
            fit=ft.BoxFit.FILL,
            left=0, top=0,
            error_content=ft.Container(
                bgcolor=BG_TOP,
                alignment=ft.Alignment.CENTER,
                content=ft.Text("Falta imagenes/home/fondo.png"),
            ),
        )

    def _done(self):
        return min(len(self.user.get("completed", [])), max(self.total, 0))

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
        elif key == "ranking":
            # Abre el ranking existente de screens/ranking.py.
            # Al regresar, mostrar_ranking llamará self.show().
            self.close()
            mostrar_ranking(self.page, self.show)

    def _on_practice(self, e=None):
        self.on_practice()

    def _on_flashcards(self, e=None):
        self.on_practice()

    def _on_sentences(self, e=None):
        if self.on_sentences:
            self.on_sentences()
        else:
            self._coming_soon()

    def _on_questions(self, e=None):
        if self.on_questions:
            self.on_questions()
        else:
            self._coming_soon()

    def _on_phrases(self, e=None):
        if self.on_phrases:
            self.on_phrases()
        else:
            self._coming_soon()

    def _on_continue(self, e=None):
        self.on_practice()

    def _coming_soon(self, e=None):
        self._toast("This section is coming soon!")

    def _on_logout(self, e=None):
        self.close()
        self.on_logout()

    def _nav_item(self, title, icon, tab):
        color = BLUE if self.tab == tab else NAV_TEXT
        sx = self._width / BASE_W
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e, target=tab: self._on_nav(target),
            ink=True,
            border_radius=16 * sx,
            content=ft.Column(
                spacing=3 * sx,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=44 * sx, color=color),
                    ft.Text(
                        title, size=24 * sx, color=color,
                        font_family=FONT,
                        weight=ft.FontWeight.BOLD,
                        max_lines=1, no_wrap=True,
                    ),
                ],
            ),
        )

    def _bottom_navigation(self):
        sx = self._width / BASE_W
        return self._at(
            42, 1525, 857, 126,
            ft.Row(
                spacing=0,
                expand=True,
                controls=[
                    self._nav_item("Home", ft.Icons.HOME_ROUNDED, "home"),
                    self._nav_item("Ranking", ft.Icons.EMOJI_EVENTS_ROUNDED, "ranking"),
                    self._nav_item("Profile", ft.Icons.PERSON_OUTLINE, "profile"),
                ],
            ),
            bgcolor="#FAFEFF",
            border_radius=30 * sx,
            border=ft.Border.all(2 * sx, "#C7E8FA"),
            shadow=ft.BoxShadow(
                blur_radius=13 * sx,
                offset=ft.Offset(0, 3 * sx),
                color="#220A6BBB",
            ),
        )

    # Helpers para construir controles REALES dentro de cada tarjeta.
    def _card_text(self, x, y, w, h, value, size,
                   color=NAVY, bold=True, center=False):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        return ft.Container(
            left=x * sx, top=y * sy,
            width=w * sx, height=h * sy,
            alignment=ft.Alignment.CENTER if center else ft.Alignment.CENTER_LEFT,
            content=self._text(
                value, size, color, bold,
                ft.TextAlign.CENTER if center else ft.TextAlign.LEFT,
            ),
        )

    def _card_image(self, filename, x, y, w, h):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        return ft.Image(
            src=ASSET_HOME + filename,
            left=x * sx, top=y * sy,
            width=w * sx, height=h * sy,
            fit=ft.BoxFit.CONTAIN,
        )

    def _arrow(self, x, y, diameter):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        return ft.Container(
            left=x * sx, top=y * sy,
            width=diameter * sx, height=diameter * sy,
            bgcolor=WHITE,
            border_radius=diameter * sx,
            border=ft.Border.all(2 * sx, "#B8E8FF"),
            shadow=ft.BoxShadow(
                blur_radius=5 * sx, color="#190F89CA",
            ),
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.ARROW_FORWARD_ROUNDED,
                size=36 * sx, color=BLUE,
            ),
        )

    def _exercise_card(self, x, y, title, subtitle, image,
                       color, action, image_w=235):
        """Toda la tarjeta es un control táctil, no una región invisible."""
        sx, sy = self._width / BASE_W, self._height / BASE_H
        w, h = 421, 302
        children = [
            self._card_image(image, 27, 8, image_w, 194),
            self._card_text(28, 197, 340, 58, title, 41),
            self._card_text(30, 245, 310, 34, subtitle, 23, SUBTEXT, False),
            self._arrow(342, 216, 62),
        ]
        return self._at(
            x, y, w, h,
            ft.Stack(width=w * sx, height=h * sy, controls=children),
            on_click=action,
            ink=True,
            bgcolor=color,
            border_radius=42 * sx,
            border=ft.Border.all(3 * sx, WHITE),
            shadow=ft.BoxShadow(
                blur_radius=15 * sx,
                offset=ft.Offset(0, 4 * sx),
                color="#230F85C3",
            ),
        )

    def _hero_card(self):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        w, h = 877, 302
        progress = self._done() / self.total if self.total > 0 else 0
        children = [
            self._card_text(39, 27, 520, 70, "Continue Learning", 47),
            self._card_text(42, 91, 430, 46, "At the Airport", 29, SUBTEXT, False),
            self._card_text(
                42, 156, 310, 39,
                f"{self._done()} of {self.total} exercises", 24, SUBTEXT, False,
            ),
            self._card_image("avion.png", 426, 12, 400, 212),
            ft.ProgressBar(
                left=42 * sx, top=226 * sy,
                width=640 * sx,
                value=progress,
                color="#168BFF",
                bgcolor="#D6EAF8",
                bar_height=17 * sy,
                border_radius=12 * sx,
            ),
            self._arrow(754, 208, 77),
        ]
        return self._at(
            32, 265, w, h,
            ft.Stack(width=w * sx, height=h * sy, controls=children),
            on_click=self._on_continue,
            ink=True,
            bgcolor="#ECFAFF",
            border_radius=43 * sx,
            border=ft.Border.all(3 * sx, WHITE),
            shadow=ft.BoxShadow(
                blur_radius=17 * sx,
                offset=ft.Offset(0, 4 * sx),
                color="#2B248BBD",
            ),
        )

    def _music_card(self):
        sx, sy = self._width / BASE_W, self._height / BASE_H
        w, h = 877, 182
        children = [
            self._card_image("musica .png", 12, 7, 253, 167),
            self._card_text(266, 43, 290, 55, "Songs", 45),
            self._card_text(268, 96, 315, 42, "Learn with music", 24, SUBTEXT, False),
            self._card_image("musica logo.png", 550, 10, 215, 151),
            self._arrow(778, 62, 65),
        ]
        return self._at(
            32, 1236, w, h,
            ft.Stack(width=w * sx, height=h * sy, controls=children),
            bgcolor="#E9F9FF",
            border_radius=44 * sx,
            border=ft.Border.all(3 * sx, WHITE),
            shadow=ft.BoxShadow(
                blur_radius=14 * sx, color="#230F85C3",
            ),
            on_click=self._coming_soon,
            ink=True,
        )

    def _build_home(self):
        sx = self._width / BASE_W
        first = self._first_name()
        greeting = f"Hello, {first}!" if first else "Hello!"

        # Se usa únicamente la imagen de nubes como fondo.
        items = [self._background()]

        # Logo y contador XP: imágenes decorativas + texto real.
        items.extend([
            self._at(
                36, 15, 234, 210,
                ft.Image(src=ASSET_HOME + "logo.png", fit=ft.BoxFit.CONTAIN),
            ),
            self._label(282, 59, 363, 69, greeting,
                        43 if len(greeting) <= 15 else 34),
            self._label(285, 132, 354, 44,
                        "Ready to learn today?", 25, SUBTEXT, False),
            self._at(
                663, 80, 236, 84,
                ft.Image(src=ASSET_HOME + "estrella.png", fit=ft.BoxFit.CONTAIN),
            ),
            self._label(779, 95, 97, 46, str(self._xp()), 33,
                        NAVY, True, True),
        ])

        # Todas estas tarjetas son componentes Flet clicables.
        items.extend([
            self._hero_card(),
            self._exercise_card(
                32, 592, "Flashcards", "Learn vocabulary",
                "tarjetas .png", "#EAF9FF", self._on_flashcards,
            ),
            self._exercise_card(
                488, 592, "Sentences", "Build sentences",
                "oraciones .png", "#EFFDF4", self._on_sentences,
            ),
            self._exercise_card(
                32, 913, "Questions", "Ask and answer",
                "preguntas .png", "#F2EEFF", self._on_questions,
            ),
            self._exercise_card(
                488, 913, "Phrases", "Common expressions",
                "frases.png", "#FFF8DB", self._on_phrases,
            ),
            self._music_card(),
            self._bottom_navigation(),
        ])
        return items

    # PERFIL: se conserva la implementación original.
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
                    content=ft.Text("Falta imagenes/profile.png"),
                ),
            )
        ]

        items.extend([
            self._label(53, 49, 89, 95, "A", 73, WHITE, True, True),
            self._label(155, 48, 590, 105, "English Adventure", 43, NAVY),
            self._label(250, 222, 445, 125, "My Profile", 66, NAVY, True, True),
            self._label(148, 355, 645, 65,
                        "Here is your learning progress!",
                        33, SUBTEXT, False, True),
            self._label(174, 522, 218, 190, initial, 115, WHITE, True, True),
            self._label(423, 520, 365, 95, name, 69, NAVY),
            self._label(423, 614, 365, 65, email, 33, SUBTEXT, False),
            self._label(245, 794, 195, 67, "Total XP", 37, NAVY, True, True),
            self._label(247, 862, 188, 90,
                        str(self._xp()), 61, NAVY, True, True),
            self._label(615, 794, 202, 67,
                        "Completed", 35, NAVY, True, True),
            self._label(613, 862, 205, 90,
                        f"{self._done()} / {self.total}", 46, NAVY, True, True),
        ])

        items.extend([
            self._at(
                258, 1017, 430, 105,
                self._text("Back to Home", 47, NAVY),
                alignment=ft.Alignment.CENTER_LEFT,
                on_click=lambda e: self._on_nav("home"),
            ),
            self._at(
                258, 1160, 430, 98,
                self._text("Log out", 47, NAVY),
                alignment=ft.Alignment.CENTER_LEFT,
                on_click=self._on_logout,
            ),
            self._touch(92, 1001, 760, 131,
                        lambda e: self._on_nav("home")),
            self._touch(92, 1144, 760, 125, self._on_logout),
            self._label(250, 1300, 440, 90,
                        "My Achievements", 43, NAVY, True, True),
            self._bottom_navigation(),
        ])
        return items

    def render(self):
        self.shell.width = self._width
        self.shell.height = self._height
        if self.tab == "profile":
            controls = self._build_profile()
        else:
            controls = self._build_home()
        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=controls,
        )
        self.page.update()
