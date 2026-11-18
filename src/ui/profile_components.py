
"""Componentes del perfil. Todos reciben `s` (escala) y NO usan coordenadas
fijas ni imagenes de fondo: crecen y se reacomodan segun el ancho disponible."""

import flet as ft

from ui.theme import BLUE, NAVY, WHITE, RED, RED_BG

FONT = "Comic Sans MS"
SUBTEXT = "#58739F"
MUTED = "#8AA0C0"
CARD_BORDER = "#D8EAFB"
PALE = "#E3F3FF"
TITLE_BG = "#B8D8FF"
GOLD = "#F4B83E"
GOLD_BG = "#FFF3D1"
GREEN = "#16A34A"
LOCKED_BG = "#EEF2F7"
LOCKED_FG = "#A3B1C6"


def _text(
    value,
    size,
    color=NAVY,
    bold=False,
    align=ft.TextAlign.LEFT,
    max_lines=1,
    italic=False,
):
    return ft.Text(
        str(value),
        size=size,
        color=color,
        font_family=FONT,
        weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
        italic=italic,
        text_align=align,
        max_lines=max_lines,
        overflow=ft.TextOverflow.ELLIPSIS,
    )


def _shadow(s, opacity=0.10, blur=14, y=4):
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(opacity, "#153C81"),
        blur_radius=blur * s,
        offset=ft.Offset(0, y * s),
    )


def card(content, s, padding=16, radius=26, color=WHITE):
    return ft.Container(
        bgcolor=color,
        padding=padding * s,
        border_radius=radius * s,
        border=ft.Border.all(max(1, 2 * s), CARD_BORDER),
        shadow=_shadow(s),
        content=content,
    )


def profile_title(title, subtitle, s):
    return ft.Column(
        spacing=6 * s,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                bgcolor=TITLE_BG,
                border_radius=18 * s,
                padding=ft.Padding.symmetric(
                    horizontal=28 * s,
                    vertical=8 * s,
                ),
                alignment=ft.Alignment.CENTER,
                content=_text(
                    title,
                    26 * s,
                    NAVY,
                    True,
                    ft.TextAlign.CENTER,
                    italic=True,
                ),
            ),
            _text(
                subtitle,
                13 * s,
                SUBTEXT,
                False,
                ft.TextAlign.CENTER,
            ),
        ],
    )


def section_title(title, s, trailing=None):
    controls = [_text(title, 19 * s, NAVY, True)]

    if trailing:
        controls.append(_text(trailing, 14 * s, SUBTEXT, True))

    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=controls,
    )


def avatar(initial, size, s):
    d = size * s

    return ft.Container(
        width=d,
        height=d,
        border_radius=d / 2,
        bgcolor=BLUE,
        border=ft.Border.all(max(2, 4 * s), WHITE),
        shadow=_shadow(s, 0.22, 10, 3),
        alignment=ft.Alignment.CENTER,
        content=_text(
            initial,
            d * 0.46,
            WHITE,
            True,
            ft.TextAlign.CENTER,
        ),
    )


def level_chip(level, s):
    return ft.Container(
        bgcolor=PALE,
        border_radius=14 * s,
        padding=ft.Padding.symmetric(
            horizontal=10 * s,
            vertical=3 * s,
        ),
        content=ft.Row(
            tight=True,
            spacing=4 * s,
            controls=[
                ft.Icon(
                    ft.Icons.MILITARY_TECH_ROUNDED,
                    size=16 * s,
                    color=BLUE,
                ),
                _text(f"Level {level}", 13 * s, BLUE, True),
            ],
        ),
    )


def profile_header(
    name,
    email,
    level,
    xp_in_level,
    xp_per_level,
    s,
    on_logout=None,
):
    initial = (name.strip()[:1] or "?").upper()

    progress = (
        min(1.0, xp_in_level / xp_per_level)
        if xp_per_level
        else 0
    )

    logout = (
        [logout_button(on_logout, s, height=40, font=15, icon=18)]
        if on_logout
        else []
    )

    return card(
        ft.Column(
            spacing=14 * s,
            controls=[
                ft.Row(
                    spacing=14 * s,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        avatar(initial, 76, s),
                        ft.Column(
                            expand=True,
                            spacing=3 * s,
                            tight=True,
                            controls=[
                                _text(name, 22 * s, NAVY, True),
                                (
                                    _text(email, 13 * s, SUBTEXT)
                                    if email
                                    else ft.Container(height=1)
                                ),
                                level_chip(level, s),
                            ],
                        ),
                    ],
                ),
                ft.Column(
                    spacing=5 * s,
                    controls=[
                        ft.ProgressBar(
                            value=progress,
                            color=BLUE,
                            bgcolor="#D6EAF8",
                            bar_height=10 * s,
                            border_radius=8 * s,
                        ),
                        _text(
                            f"{xp_in_level} / {xp_per_level} XP to Level {level + 1}",
                            12 * s,
                            SUBTEXT,
                            True,
                        ),
                    ],
                ),
                *logout,
            ],
        ),
        s,
    )


def stat_tile(icon, label, value, color, s):
    return ft.Container(
        expand=True,
        bgcolor=WHITE,
        padding=ft.Padding.symmetric(
            horizontal=6 * s,
            vertical=12 * s,
        ),
        border_radius=20 * s,
        border=ft.Border.all(max(1, 2 * s), CARD_BORDER),
        shadow=_shadow(s, 0.08, 10, 3),
        content=ft.Column(
            spacing=4 * s,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=26 * s, color=color),
                _text(
                    value,
                    21 * s,
                    NAVY,
                    True,
                    ft.TextAlign.CENTER,
                ),
                _text(
                    label,
                    12 * s,
                    SUBTEXT,
                    False,
                    ft.TextAlign.CENTER,
                ),
            ],
        ),
    )


def achievement_badge(
    icon,
    title,
    description,
    unlocked,
    width,
    s,
):
    fg = GOLD if unlocked else LOCKED_FG

    return ft.Container(
        width=width,
        padding=12 * s,
        bgcolor=GOLD_BG if unlocked else LOCKED_BG,
        border_radius=20 * s,
        border=ft.Border.all(
            max(1, 2 * s),
            GOLD if unlocked else "#DCE3EC",
        ),
        content=ft.Column(
            spacing=5 * s,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    icon if unlocked else ft.Icons.LOCK_OUTLINE,
                    size=30 * s,
                    color=fg,
                ),
                _text(
                    title,
                    14 * s,
                    NAVY if unlocked else LOCKED_FG,
                    True,
                    ft.TextAlign.CENTER,
                ),
                _text(
                    description,
                    11 * s,
                    SUBTEXT if unlocked else LOCKED_FG,
                    False,
                    ft.TextAlign.CENTER,
                    max_lines=2,
                ),
            ],
        ),
    )


def logout_button(on_click, s, height=50, font=17, icon=20):
    return ft.Container(
        height=height * s,
        bgcolor=RED_BG,
        border=ft.Border.all(max(1, 2 * s), RED),
        border_radius=(height / 2) * s,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=on_click,
        content=ft.Row(
            tight=True,
            spacing=8 * s,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Icon(
                    ft.Icons.LOGOUT_ROUNDED,
                    size=icon * s,
                    color=RED,
                ),
                _text("Log out", font * s, RED, True),
            ],
        ),
    )
