import flet as ft

from ui.profile_components import (
    BLUE, GREEN, GOLD, NAVY,
    achievement_badge, activity_row, card,
    profile_header, profile_title, section_title, stat_tile,
)

XP_PER_LEVEL = 100

# Pon True para volver a mostrar la seccion de logros.
SHOW_ACHIEVEMENTS = False

# Se muestran SIEMPRE todas las actividades en "Your progress".
# (clave en user["progress"], icono, titulo)
ACTIVITIES = [
    ("sentences", ft.Icons.EDIT_NOTE_ROUNDED, "Sentences"),
    ("questions", ft.Icons.QUESTION_ANSWER_ROUNDED, "Questions"),
    ("phrases", ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED, "Phrases"),
    ("songs", ft.Icons.MUSIC_NOTE_ROUNDED, "Songs"),
]

# (id, icono, titulo, descripcion, condicion(xp, hechos, total))
ACHIEVEMENTS = [
    ("first", ft.Icons.FLAG_ROUNDED, "First step", "Complete 1 flashcard",
     lambda xp, d, t: d >= 1),
    ("ten", ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, "On fire", "Complete 10 flashcards",
     lambda xp, d, t: d >= 10),
    ("half", ft.Icons.TRENDING_UP_ROUNDED, "Halfway there", "Finish half the course",
     lambda xp, d, t: t > 0 and d * 2 >= t),
    ("all", ft.Icons.EMOJI_EVENTS_ROUNDED, "Course complete", "Finish every exercise",
     lambda xp, d, t: t > 0 and d >= t),
    ("xp100", ft.Icons.STAR_ROUNDED, "100 XP", "Earn 100 XP",
     lambda xp, d, t: xp >= 100),
    ("xp500", ft.Icons.WORKSPACE_PREMIUM_ROUNDED, "500 XP", "Earn 500 XP",
     lambda xp, d, t: xp >= 500),
]


def _int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def construir_perfil(user, total, width, height, on_logout, bottom_space=0):
    """Devuelve el contenido del perfil (columna con scroll, ancho adaptable).

    ``bottom_space``: espacio libre al final para que el navbar flotante no
    tape el ultimo elemento (el contenido puede scrollear hasta quedar encima).
    """
    s = max(0.7, min(1.15, width / 440))
    pad = 16 * s
    content_w = min(width, 520)
    inner_w = content_w - 2 * pad

    name = (user.get("name") or "").strip() or "Student"
    email = (user.get("email") or "").strip()
    xp = _int(user.get("xp"))
    done = min(len(user.get("completed", [])), max(total, 0))
    level = xp // XP_PER_LEVEL + 1
    xp_in_level = xp % XP_PER_LEVEL

    # --- Progreso por actividad (siempre se muestran todas) ---
    rows = [activity_row(ft.Icons.STYLE_ROUNDED, "Flashcards", done, total, BLUE, s)]
    extra = user.get("progress") or {}
    for key, icon, title in ACTIVITIES:
        data = extra.get(key)
        data = data if isinstance(data, dict) else {}
        rows.append(activity_row(icon, title, _int(data.get("done")),
                                 _int(data.get("total")), BLUE, s))

    controls = [
        profile_title("My Profile", "Here is your learning progress!", s),
        profile_header(name, email, level, xp_in_level, XP_PER_LEVEL, s,
                       on_logout=on_logout),
        ft.Row(spacing=10 * s, controls=[
            stat_tile(ft.Icons.STAR_ROUNDED, "Total XP", str(xp), GOLD, s),
            stat_tile(ft.Icons.MILITARY_TECH_ROUNDED, "Level", str(level), BLUE, s),
            stat_tile(ft.Icons.CHECK_CIRCLE_ROUNDED, "Completed",
                      f"{done}/{total}", GREEN, s),
        ]),
        card(ft.Column(spacing=14 * s, controls=[
            section_title("Your progress", s),
            *rows,
        ]), s),
    ]

    # --- Logros (ocultos por ahora) ---
    if SHOW_ACHIEVEMENTS:
        unlocked = [bool(cond(xp, done, total)) for *_, cond in ACHIEVEMENTS]
        gap = 10 * s
        badge_w = (inner_w - gap) / 2
        badges = ft.Row(
            wrap=True, spacing=gap, run_spacing=gap,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                achievement_badge(icon, title, desc, ok, badge_w, s)
                for (_, icon, title, desc, _), ok in zip(ACHIEVEMENTS, unlocked)
            ],
        )
        controls.append(card(ft.Column(spacing=12 * s, controls=[
            section_title("Achievements", s,
                          f"{sum(unlocked)} / {len(ACHIEVEMENTS)}"),
            badges,
        ]), s))

    body = ft.Column(spacing=16 * s, controls=controls)

    return ft.Column(
        width=width, height=height,
        scroll=ft.ScrollMode.AUTO,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[ft.Container(
            width=content_w,
            # bottom_space deja libre la zona del navbar para poder llegar
            # al ultimo boton haciendo scroll.
            padding=ft.Padding(left=pad, right=pad, top=14 * s,
                               bottom=bottom_space + 12 * s),
            content=body,
        )],
    )