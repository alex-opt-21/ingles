from dataclasses import dataclass
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
    ratio: float   # ancho / alto del PNG
    cx: float      # centro X del globo (fraccion del ancho)
    cy: float      # centro Y del globo (fraccion del alto)
    tw: float      # ancho seguro del texto (fraccion)
    th: float      # alto seguro del texto (fraccion)


SCENES: dict[str, SceneSpec] = {
    "fiesta": SceneSpec(1448 / 1086, 0.70, 0.34, 0.36, 0.28),
    "nino": SceneSpec(1403 / 1121, 0.68, 0.39, 0.34, 0.25),
}


def exercise_illustrated_question(
    *,
    src: str,
    question: str,
    scene: str | None = None,
    scale: float = 1.0,
    box: tuple[float, float] = (344, 253),
) -> ft.Stack:
    key = str(scene or "").lower()
    if key not in SCENES:
        key = "fiesta" if "fiesta" in (src or "").lower() else "nino"
    spec = SCENES[key]

    max_w, max_h = box[0] * scale, box[1] * scale
    iw = min(max_w, max_h * spec.ratio)
    ih = iw / spec.ratio

    question = str(question)
    size = (16 if len(question) <= 24 else 14 if len(question) <= 38 else 12.5) * scale

    return ft.Stack(
        width=iw,
        height=ih,
        controls=[
            ft.Image(
                src=src,
                left=0, top=0,
                width=iw, height=ih,
                fit=ft.BoxFit.CONTAIN,
                error_content=ft.Container(
                    bgcolor=EXERCISE_PALE_BLUE,
                    alignment=ft.Alignment.CENTER,
                    content=exercise_text("Missing image: " + str(src), 12 * scale, EXERCISE_RED),
                ),
            ),
            ft.Container(
                left=(spec.cx - spec.tw / 2) * iw,
                top=(spec.cy - spec.th / 2) * ih,
                width=spec.tw * iw,
                height=spec.th * ih,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    question,
                    size=size,
                    font_family=EXERCISE_FONT,
                    color=EXERCISE_NAVY,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=5,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ),
        ],
    )
