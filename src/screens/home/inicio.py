import flet as ft

# Adjust this import to where your theme lives (e.g. ui.theme)
from ui.theme import (
    APP_NAME, APP_TAGLINE, LOGO,
    BLUE, BLUE_SOFT, NAVY, GREY, LINE, TRACK, WHITE, RED, RED_BG,
    BG_TOP, BG_BOTTOM,
    glass,
)

AMBER = "#FFB800"


class HomeView:
    def __init__(self, page: ft.Page, user: dict, total_exercises: int, on_practice, on_logout):
        self.page = page
        self.user = user                  # needs: name, email, xp, completed
        self.total = total_exercises
        self.on_practice = on_practice    # opens the exercise
        self.on_logout = on_logout
        self.tab = "home"                 # "home" | "profile"

        self.body = ft.Column(
            spacing=16,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.nav = ft.Container(padding=ft.Padding.only(left=12, right=12, bottom=10))

        self.shell = ft.Container(
            width=390,
            height=844,
            content=ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=10,
                    controls=[
                        self._build_header(),
                        ft.Container(
                            content=self.body,
                            expand=True,
                            padding=ft.Padding.symmetric(horizontal=16),
                        ),
                        self.nav,
                    ],
                ),
            ),
        )

    # ================= life cycle =================

    def show(self):
        self.tab = "home"
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
        self.render()

    def close(self):
        self.page.on_resize = None

    def _fit_card(self, e=None):
        if self.page.width:
            self.shell.width = min(self.page.width, 440)
        if self.page.height:
            self.shell.height = self.page.height
        self.page.update()

    def _toast(self, message: str):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception as err:
            print(f"{message} ({err})")

    # ================= handlers =================

    def _on_nav(self, key: str):
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

    # ================= UI pieces =================

    def _done(self) -> int:
        return min(len(self.user["completed"]), self.total)

    def _build_header(self) -> ft.Control:
        xp_chip = ft.Container(
            content=ft.Row(
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.STAR, size=20, color=AMBER),
                    ft.Text(str(self.user["xp"]), size=15, weight=ft.FontWeight.W_800, color=NAVY),
                ],
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border_radius=20,
            bgcolor=glass(0.9),
            border=ft.Border.all(1, LINE),
        )
        return ft.Container(
            padding=ft.Padding.only(left=16, right=16, top=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Image(
                                src=LOGO,
                                width=44,
                                height=44,
                                fit=ft.BoxFit.CONTAIN,
                                error_content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=30, color=GREY),
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[
                                    ft.Text(APP_NAME, size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                                    ft.Text(APP_TAGLINE, size=12, color=GREY),
                                ],
                            ),
                        ],
                    ),
                    xp_chip,
                ],
            ),
        )

    def _progress_bar(self, done: int) -> ft.Container:
        rest = self.total - done
        parts = []
        if done > 0:
            parts.append(ft.Container(expand=done, height=6, bgcolor=BLUE))
        if rest > 0:
            parts.append(ft.Container(expand=rest, height=6))
        return ft.Container(
            height=6,
            expand=True,
            border_radius=3,
            bgcolor=TRACK,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Row(spacing=0, controls=parts),
        )

    def _practice_card(self) -> ft.Container:
        done = self._done()
        return ft.Container(
            padding=18,
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[WHITE, "#EAF3FF"],
            ),
            border=ft.Border.all(1, LINE),
            shadow=ft.BoxShadow(
                blur_radius=18,
                color=ft.Colors.with_opacity(0.10, "#1F2A55"),
                offset=ft.Offset(0, 6),
            ),
            on_click=self._on_practice,
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=64,
                        height=64,
                        border_radius=18,
                        bgcolor=BLUE_SOFT,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.EDIT_NOTE, size=34, color=BLUE),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=4,
                        controls=[
                            ft.Text("Practice 1", size=20, weight=ft.FontWeight.W_800, color=NAVY),
                            ft.Text("Look and choose", size=13, color=GREY),
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    self._progress_bar(done),
                                    ft.Text(f"{done}/{self.total}", size=12, color=GREY),
                                ],
                            ),
                        ],
                    ),
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=20,
                        bgcolor=WHITE,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=24, color=BLUE),
                    ),
                ],
            ),
        )

    def _stat(self, label: str, value: str) -> ft.Control:
        return ft.Column(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(value, size=20, weight=ft.FontWeight.W_800, color=BLUE),
                ft.Text(label, size=12, color=GREY),
            ],
        )

    # ================= tabs =================

    def _build_home(self) -> list[ft.Control]:
        name = (self.user.get("name") or "").strip()
        first = name.split()[0] if name else ""
        return [
            ft.Column(
                spacing=2,
                controls=[
                    ft.Text(
                        f"Hello, {first}!" if first else "Hello!",
                        size=30,
                        weight=ft.FontWeight.W_800,
                        color=NAVY,
                    ),
                    ft.Text("Ready to learn today?", size=14, color=GREY),
                ],
            ),
            ft.Text("Practice", size=16, weight=ft.FontWeight.W_700, color=NAVY),
            self._practice_card(),
        ]

    def _build_profile(self) -> list[ft.Control]:
        name = (self.user.get("name") or "").strip()
        return [
            ft.Container(height=8),
            ft.Container(
                padding=24,
                border_radius=28,
                bgcolor=glass(0.9),
                border=ft.Border.all(1, LINE),
                content=ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=84,
                            height=84,
                            border_radius=42,
                            bgcolor=BLUE_SOFT,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(
                                (name[:1] or "?").upper(),
                                size=36,
                                weight=ft.FontWeight.W_800,
                                color=BLUE,
                            ),
                        ),
                        ft.Text(name, size=22, weight=ft.FontWeight.W_800, color=NAVY),
                        ft.Text(self.user.get("email", ""), size=13, color=GREY),
                        ft.Container(height=4),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                            controls=[
                                self._stat("Total XP", str(self.user["xp"])),
                                self._stat("Completed", f"{self._done()}/{self.total}"),
                            ],
                        ),
                    ],
                ),
            ),
            ft.Container(
                height=52,
                border_radius=16,
                bgcolor=RED_BG,
                alignment=ft.Alignment.CENTER,
                on_click=self._on_logout,
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.LOGOUT, size=20, color=RED),
                        ft.Text("Log out", size=16, weight=ft.FontWeight.W_600, color=RED),
                    ],
                ),
            ),
        ]

    # ================= navbar =================

    def _nav_item(self, key: str, icon, label: str) -> ft.Container:
        active = self.tab == key
        color = BLUE if active else GREY
        return ft.Container(
            expand=True,
            padding=ft.Padding.symmetric(vertical=8),
            border_radius=18,
            bgcolor=BLUE_SOFT if active else None,
            on_click=lambda e, k=key: self._on_nav(k),
            content=ft.Column(
                spacing=2,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=26, color=color),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=color),
                ],
            ),
        )

    def _build_nav(self) -> ft.Container:
        return ft.Container(
            padding=6,
            border_radius=26,
            bgcolor=glass(0.95),
            border=ft.Border.all(1, LINE),
            shadow=ft.BoxShadow(
                blur_radius=16,
                color=ft.Colors.with_opacity(0.08, "#1F2A55"),
                offset=ft.Offset(0, 4),
            ),
            content=ft.Row(
                spacing=4,
                controls=[
                    self._nav_item("home", ft.Icons.HOME, "Home"),
                    self._nav_item("lessons", ft.Icons.MENU_BOOK, "Lessons"),
                    self._nav_item("games", ft.Icons.SPORTS_ESPORTS, "Games"),
                    self._nav_item("profile", ft.Icons.PERSON_OUTLINE, "Profile"),
                ],
            ),
        )

    # ================= render =================

    def render(self):
        self.body.controls = self._build_home() if self.tab == "home" else self._build_profile()
        self.nav.content = self._build_nav()
        self.page.update()