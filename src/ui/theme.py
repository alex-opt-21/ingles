
import flet as ft

# INFORMACION GENERAL
APP_NAME = "Saylo"
APP_TAGLINE = "Learn English"
LOGO = "imagenes/logos/logo.png"

# COLORES GENERALES
BLUE = "#007AFF"
BLUE_SOFT = "#E3EFFF"
NAVY = "#1C1C1E"
GREY = "#8E8E93"
LINE = "#D6E4F7"
TRACK = "#D5E3F7"
WHITE = "#FFFFFF"
GREEN = "#34C759"
GREEN_DARK = "#248A3D"
GREEN_BG = "#E9F9EE"
RED = "#FF3B30"
RED_BG = "#FFE9E8"
BG_TOP = "#EAF3FF"
BG_BOTTOM = "#F8FBFF"
RADIO_IDLE = "#B9C6DB"
ICON_IDLE = "#7FA6D6"
DISABLED_BG = "#DCE6F5"
DISABLED_TEXT = "#9AB0CE"

# COLORES DE ACTION PRACTICE
EXERCISE_BLUE = "#087CFA"
EXERCISE_NAVY = "#08256E"
EXERCISE_SOFT_BLUE = "#6185BD"
EXERCISE_GREEN = "#129946"
EXERCISE_RED = "#E84245"
EXERCISE_WHITE = "#FFFFFF"
EXERCISE_FONT = "Comic Sans MS"

# ICONOS DE LOS VERBOS
OPTION_ICONS = {
    "eat": "RESTAURANT",
    "drink": "LOCAL_DRINK",
    "sleep": "BED",
    "swim": "POOL",
    "run": "DIRECTIONS_RUN",
    "walk": "DIRECTIONS_WALK",
    "read": "MENU_BOOK",
    "write": "EDIT",
    "sing": "MUSIC_NOTE",
    "dance": "MUSIC_NOTE",
    "fly": "FLIGHT",
    "play": "SPORTS_ESPORTS",
    "cook": "OUTDOOR_GRILL",
    "study": "SCHOOL",
    "drive": "DIRECTIONS_CAR",
}

def glass(opacity: float = 0.85) -> str:
    return ft.Colors.with_opacity(opacity, WHITE)
