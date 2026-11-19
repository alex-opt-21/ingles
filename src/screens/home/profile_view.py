import flet as ft

from ui.profile_components import (
    BLUE,
    GOLD,
    NAVY,
    SUBTEXT,
    _text,
    achievement_icon,
    card,
    profile_header,
    profile_title,
    stat_tile,
)

XP_PER_LEVEL = 100

# Rutas relativas a src/assets/ (la carpeta se llama "My profile", con espacio).
ASSET_PROFILE = "imagenes/My profile/"
IMG_XP = ASSET_PROFILE + "XP.png"
IMG_LV = ASSET_PROFILE + "LV.png"

# Imagenes de logros (campo "icon" de achievements.json).
ASSET_ACHIEVEMENTS = "imagenes/achievements/"

# Iconos de respaldo para logros que aun no tienen imagen.
ACHIEVEMENT_ICONS = {
    "1": ft.Icons.FLAG_ROUNDED,
    "2": ft.Icons.PSYCHOLOGY_ROUNDED,
    "3": ft.Icons.EDIT_NOTE_ROUNDED,
    "4": ft.Icons.LIGHTBULB_ROUNDED,
    "5": ft.Icons.CHAT_ROUNDED,
    "6": ft.Icons.MUSIC_NOTE_ROUNDED,
    "7": ft.Icons.STAR_ROUNDED,
    "8": ft.Icons.WORKSPACE_PREMIUM_ROUNDED,
    "9": ft.Icons.MILITARY_TECH_ROUNDED,
    "10": ft.Icons.EXPLORE_ROUNDED,
    "11": ft.Icons.BOOKMARKS_ROUNDED,
    "12": ft.Icons.EMOJI_EVENTS_ROUNDED,
}

ICONS_PER_ROW = 3  # cuantos iconos por fila


def _int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _achievement_image(achievement):
    """Ruta (relativa a assets) de la imagen del logro, o None si no tiene."""
    icon_file = achievement.get("icon")
    return ASSET_ACHIEVEMENTS + icon_file if icon_file else None


def construir_perfil(
    user,
    total,
    width,
    height,
    on_logout,
    bottom_space=0,
    achievement_definitions=None,
):
    """Construye el perfil con estadísticas y logros del usuario."""

    s = max(0.7, min(1.15, width / 440))
    pad = 16 * s

    content_w = min(width, 520)
    inner_w = content_w - 2 * pad

    name = (user.get("name") or "").strip() or "Student"
    email = (user.get("email") or "").strip()

    xp = _int(user.get("xp"))

    level = xp // XP_PER_LEVEL + 1
    xp_in_level = xp % XP_PER_LEVEL

    # Logros guardados por AchievementService.
    achievement_data = user.get("achievements") or {}

    unlocked_ids = {
        str(value)
        for value in achievement_data.get("unlocked", [])
    }

    definitions = achievement_definitions or []

    unlocked_count = sum(
        1
        for achievement in definitions
        if str(achievement.get("id")) in unlocked_ids
    )

    # Ancho interno de la tarjeta (se descuenta padding y borde).
    gap = 14 * s
    card_inner_w = inner_w - 36 * s

    # Tamano de cada icono: ICONS_PER_ROW por fila, con tope de 92*s.
    icon_size = min(
        92 * s,
        (card_inner_w - gap * (ICONS_PER_ROW - 1)) / ICONS_PER_ROW - 1,
    )
    icon_size = max(56, icon_size)

    achievement_controls = [
        achievement_icon(
            icon=ACHIEVEMENT_ICONS.get(
                str(achievement.get("id")),
                ft.Icons.EMOJI_EVENTS_ROUNDED,
            ),
            title=achievement.get("name", "Achievement"),
            unlocked=str(achievement.get("id")) in unlocked_ids,
            size=icon_size,
            s=s,
            image_src=_achievement_image(achievement),
        )
        for achievement in definitions
    ]

    if not achievement_controls:
        achievement_controls.append(
            ft.Container(
                padding=16 * s,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    "No achievements available yet.",
                    size=13 * s,
                    color="#8AA0C0",
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )

    badges = ft.Row(
        wrap=True,
        spacing=gap,
        run_spacing=12 * s,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=achievement_controls,
    )

    achievements_title = ft.Column(
        spacing=2 * s,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            _text(
                "My Achievements",
                19 * s,
                NAVY,
                True,
                ft.TextAlign.CENTER,
            ),
            _text(
                f"{unlocked_count} / {len(definitions)}",
                13 * s,
                SUBTEXT,
                True,
                ft.TextAlign.CENTER,
            ),
        ],
    )

    controls = [
        profile_title(
            "My Profile",
            "Here are your achievements!",
            s,
            inner_w,
        ),

        profile_header(
            name,
            email,
            level,
            xp_in_level,
            XP_PER_LEVEL,
            s,
            on_logout=on_logout,
        ),

        ft.Row(
            spacing=12 * s,
            controls=[
                stat_tile(
                    IMG_XP,
                    "Total XP",
                    str(xp),
                    s,
                    ft.Icons.STAR_ROUNDED,
                    GOLD,
                ),
                stat_tile(
                    IMG_LV,
                    "Level",
                    str(level),
                    s,
                    ft.Icons.MILITARY_TECH_ROUNDED,
                    BLUE,
                ),
            ],
        ),

        card(
            ft.Column(
                width=card_inner_w,  # <- hace que la tarjeta ocupe todo el ancho
                spacing=16 * s,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    achievements_title,
                    badges,
                ],
            ),
            s,
        ),
    ]

    body = ft.Column(
        spacing=16 * s,
        controls=controls,
    )

    return ft.Column(
        width=width,
        height=height,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=content_w,
                padding=ft.Padding(
                    left=pad,
                    right=pad,
                    top=14 * s,
                    bottom=bottom_space + 12 * s,
                ),
                content=body,
            )
        ],
    )