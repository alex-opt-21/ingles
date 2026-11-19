
from dataclasses import dataclass
from pathlib import PurePath
import unicodedata
import re
import flet as ft

from ..core.exercise_common import exercise_text
from ..core.exercise_theme import (
    EXERCISE_FONT,
    EXERCISE_NAVY,
    EXERCISE_PALE_BLUE,
    EXERCISE_RED,
)


@dataclass(frozen=True)
class SceneSpec:
    ratio: float
    cx: float
    cy: float
    tw: float
    th: float


# Coordenadas normalizadas respecto a cada imagen cuadrada.
# cx, cy = centro del texto.
# tw, th = área segura para escribir dentro de la nube.

SCENES = {
    "cantar": SceneSpec(1.0, 0.28, 0.32, 0.40, 0.22),
    "cocina": SceneSpec(1.0, 0.72, 0.32, 0.38, 0.20),
    "construccion": SceneSpec(1.0, 0.72, 0.24, 0.39, 0.23),
    "doctora": SceneSpec(1.0, 0.72, 0.24, 0.39, 0.23),
    "estudiar": SceneSpec(1.0, 0.70, 0.36, 0.36, 0.23),
    "fiesta": SceneSpec(1.0, 0.70, 0.35, 0.37, 0.22),
    "futbol": SceneSpec(1.0, 0.73, 0.25, 0.31, 0.25),
    "jardin": SceneSpec(1.0, 0.72, 0.27, 0.34, 0.25),
    "nino": SceneSpec(1.0, 0.69, 0.36, 0.32, 0.22),
    "paisaje": SceneSpec(1.0, 0.70, 0.24, 0.39, 0.23),
    "pescar": SceneSpec(1.0, 0.70, 0.24, 0.39, 0.23),
    "pintar": SceneSpec(1.0, 0.28, 0.35, 0.38, 0.20),
    "playa": SceneSpec(1.0, 0.71, 0.23, 0.39, 0.23),
    "reposteria": SceneSpec(1.0, 0.70, 0.32, 0.39, 0.21),
}


def normalize_name(src: str) -> str:
    name = PurePath(str(src).replace("\\", "/")).stem.lower()
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", name)


def exercise_illustrated_question(
    *,
    src: str,
    question: str,
    scene: str | None = None,
    scale: float = 1.0,
    box: tuple[float, float] = (344, 253),
) -> ft.Stack:

    key = normalize_name(scene or src)

    # Buscar la configuración correspondiente.
    spec = SCENES.get(key)

    if spec is None:
        spec = next(
            (
                value for name, value in SCENES.items()
                if name in key
            ),
            SCENES["nino"],
        )

    max_w = box[0] * scale
    max_h = box[1] * scale

    iw = min(max_w, max_h * spec.ratio)
    ih = iw / spec.ratio

    question = str(question).strip()

    # Tamaño adaptable al contenido y al espacio de la nube.
    available_width = spec.tw * iw

    if len(question) <= 20:
        size = 14
    elif len(question) <= 32:
        size = 12
    elif len(question) <= 48:
        size = 10.5
    else:
        size = 9.5

    size *= scale

    return ft.Stack(
        width=iw,
        height=ih,
        controls=[
            ft.Image(
                src=src,
                left=0,
                top=0,
                width=iw,
                height=ih,
                fit=ft.BoxFit.CONTAIN,
                error_content=ft.Container(
                    bgcolor=EXERCISE_PALE_BLUE,
                    alignment=ft.Alignment.CENTER,
                    content=exercise_text(
                        "Missing image: " + str(src),
                        12 * scale,
                        EXERCISE_RED,
                    ),
                ),
            ),

            ft.Container(
                left=(spec.cx - spec.tw / 2) * iw,
                top=(spec.cy - spec.th / 2) * ih,
                width=available_width,
                height=spec.th * ih,
                padding=ft.Padding.symmetric(
                    horizontal=2 * scale,
                    vertical=2 * scale,
                ),
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    question,
                    size=size,
                    font_family=EXERCISE_FONT,
                    color=EXERCISE_NAVY,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=5,
                    overflow=ft.TextOverflow.CLIP,
                ),
            ),
        ],
    )
