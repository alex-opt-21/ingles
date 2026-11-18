from ui.theme import (
    EXERCISE_BLUE,
    EXERCISE_NAVY,
    EXERCISE_SOFT_BLUE,   # OJO: es color de TEXTO secundario (azul grisaceo)
    EXERCISE_GREEN,
    EXERCISE_RED,
    EXERCISE_WHITE,
    EXERCISE_FONT,
)

# ---- Colores auxiliares ----
EXERCISE_CREAM = "#FFFCF7"         # fondo de tarjetas de pausa / resultados
EXERCISE_PAPER = "#FFFFFF"
EXERCISE_PALE_BLUE = "#EAF4FF"     # fondo de ilustracion, bordes de pills
EXERCISE_BORDER_BLUE = "#A6CFFF"   # borde de opciones y botones
EXERCISE_PALE_BORDER = "#E9E5DF"
EXERCISE_HEADING_BG = "#B3D7FF"    # barra "LOOK & CHOOSE"
EXERCISE_LOCKED_BG = "#D5DCE8"     # boton deshabilitado
EXERCISE_LOCKED_FG = "#8A97B0"
EXERCISE_SILVER = "#E9EDF4"
EXERCISE_YELLOW = "#FFD54A"       # tarjeta de situacion (Phrases)
EXERCISE_YELLOW_BG = "#FFF6CC"

# ---- Dimensiones de diseno de la hoja (todo se escala a partir de aqui) ----
SHEET_WIDTH = 420
SHEET_HEIGHT = 870
SHEET_MAX_HEIGHT = 850
# Margen vertical que se descuenta del alto de pantalla:
# padding exterior (10 + 10) + separacion header/hoja (5) + holgura (12)
SHEET_VERTICAL_RESERVE = 37
# Ajuste fino por si cambias el PNG de la hoja (en unidades de diseno)
SHEET_ADJUST_X = 0
SHEET_ADJUST_Y = 0

# ---- Recursos compartidos (rutas relativas a src/assets/) ----
BACKGROUND_IMAGE = "imagenes/fondo_e.png"
SHEET_IMAGE = "imagenes/hoja_centra.png"
