import re
from functools import lru_cache
from pathlib import Path

import flet as ft

from ui.theme import BLUE, NAVY, WHITE, RED, RED_BG

# AJUSTA esta ruta a donde tengas tu BlueBanner.
from ui.exercises.components.blue_banner import BlueBanner

FONT = "Comic Sans MS"
SUBTEXT = "#58739F"
MUTED = "#8AA0C0"
CARD_BORDER = "#D8EAFB"
PALE = "#E3F3FF"
BANNER_SRC = "imagenes/My profile/banner_azul.svg"   # relativa a src/assets/
BANNER_WIDTH_FACTOR = 0.8     # 1.0 = ancho completo; menor = banner mas chico y centrado
BANNER_ASPECT_FALLBACK = 600 / 230   # solo si no se puede leer el SVG
BANNER_TEXT = NAVY            # pon WHITE si tu banner es de azul oscuro          # pon WHITE si tu banner es de azul oscuro
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


@lru_cache(maxsize=None)
def banner_aspect():
    """Proporcion (ancho / alto) REAL del SVG, leida de su viewBox.

    Usar la proporcion exacta evita que el banner se deforme o quede
    desalineado con el texto. Si no se puede leer, usa el valor de respaldo.
    """
    for folder in Path(__file__).resolve().parents:
        path = folder / "assets" / BANNER_SRC
        if not path.is_file():
            continue
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            break
        tag = re.search(r"<svg\b[^>]*>", head, flags=re.S)
        tag = tag.group(0) if tag else head
        box = re.search(r'viewBox\s*=\s*"([^"]+)"', tag)
        if box:
            nums = re.findall(r"-?\d+(?:\.\d+)?", box.group(1))
            if len(nums) == 4 and float(nums[3]) > 0:
                return float(nums[2]) / float(nums[3])
        w = re.search(r'(?<![-\w])width\s*=\s*"([\d.]+)', tag)
        h = re.search(r'(?<![-\w])height\s*=\s*"([\d.]+)', tag)
        if w and h and float(h.group(1)) > 0:
            return float(w.group(1)) / float(h.group(1))
        break
    return BANNER_ASPECT_FALLBACK


def profile_title(title, subtitle, s, width):
    """Titulo sobre el banner, centrado. El banner mide `width * BANNER_WIDTH_FACTOR`
    y su alto sale de la proporcion real del SVG (sin deformarlo)."""
    banner_w = width * BANNER_WIDTH_FACTOR
    banner_h = banner_w / banner_aspect()

    banner = BlueBanner(
        width=banner_w,
        height=banner_h,
        padding=6 * s,
        svg_src=BANNER_SRC,
        content=ft.Column(
            tight=True,
            spacing=2 * s,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _text(
                    title,
                    26 * s,
                    BANNER_TEXT,
                    True,
                    ft.TextAlign.CENTER,
                    italic=True,
                ),
                _text(
                    subtitle,
                    12 * s,
                    BANNER_TEXT,
                    False,
                    ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    # El contenedor ocupa todo el ancho y centra el banner dentro.
    return ft.Container(
        width=width,
        alignment=ft.Alignment.CENTER,
        content=banner,
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


def logout_icon_button(on_click, s, size=40):
    """Boton circular solo con icono (cerrar sesion)."""
    d = size * s

    return ft.Container(
        width=d,
        height=d,
        border_radius=d / 2,
        bgcolor=RED_BG,
        border=ft.Border.all(max(1, 2 * s), RED),
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=on_click,
        tooltip="Log out",
        content=ft.Icon(
            ft.Icons.LOGOUT_ROUNDED,
            size=(size * 0.5) * s,
            color=RED,
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

    top_row = [
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
    ]

    if on_logout:
        top_row.append(logout_icon_button(on_logout, s))

    return card(
        ft.Column(
            spacing=14 * s,
            controls=[
                ft.Row(
                    spacing=14 * s,
                    # START = icono arriba a la derecha.
                    # Cambialo a CENTER si lo quieres a la mitad.
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=top_row,
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
            ],
        ),
        s,
    )


def stat_tile(
    image_src,
    label,
    value,
    s,
    fallback_icon=ft.Icons.STAR_ROUNDED,
    fallback_color=GOLD,
):
    """Tarjeta con imagen a la izquierda, etiqueta arriba y valor grande abajo.

    Si la imagen no se encuentra, muestra `fallback_icon` para no romper el diseno.
    """
    img = 50 * s

    return ft.Container(
        expand=True,
        bgcolor=WHITE,
        padding=ft.Padding.symmetric(
            horizontal=10 * s,
            vertical=10 * s,
        ),
        border_radius=22 * s,
        border=ft.Border.all(max(1, 2 * s), CARD_BORDER),
        shadow=_shadow(s, 0.08, 10, 3),
        content=ft.Row(
            spacing=8 * s,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Image(
                    src=image_src,
                    width=img,
                    height=img,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Icon(
                        fallback_icon,
                        size=img * 0.8,
                        color=fallback_color,
                    ),
                ),
                ft.Column(
                    expand=True,
                    spacing=2 * s,
                    tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        _text(
                            label,
                            12 * s,
                            NAVY,
                            True,
                            ft.TextAlign.CENTER,
                        ),
                        _text(
                            value,
                            24 * s,
                            NAVY,
                            True,
                            ft.TextAlign.CENTER,
                        ),
                    ],
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