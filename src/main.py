import json
import os
import time
from pathlib import Path

import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None

BASE_DIR = Path(__file__).parent
EXERCISES_FILE = BASE_DIR / "data" / "acciones.json"
ASSETS_DIR = BASE_DIR / "assets"

STORAGE_DIR = Path(os.getenv("FLET_APP_STORAGE_DATA") or BASE_DIR / "storage")
PROGRESS_FILE = STORAGE_DIR / "progress.json"

XP_PER_EXERCISE = 10


def load_exercises() -> list[dict]:
    with open(EXERCISES_FILE, encoding="utf-8") as f:
        exercises = json.load(f)["exercises"]
    for ex in exercises:
        ruta = ASSETS_DIR / ex["image"]
        if not ruta.exists():
            print(f"[!] No encuentro la imagen: {ruta}")
    return exercises


def load_progress() -> dict:
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"xp": 0, "completed": []}


def save_progress(progress: dict) -> None:
    try:
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    except OSError as err:
        print(f"No se pudo guardar el progreso: {err}")


def format_time(seconds: float) -> str:
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


BLUE = "#2F6FED"
NAVY = "#141B34"
GREY = "#6B7280"
LINE = "#E5E7EB"
WHITE = "#FFFFFF"
GREEN = "#16A34A"
GREEN_DARK = "#15803D"
GREEN_BG = "#ECFDF3"
RED = "#DC2626"
RED_BG = "#FEF2F2"
BG_TOP = "#F4F6FC"
BG_BOTTOM = "#E6EAF6"


def main(page: ft.Page):
    page.title = "Action Practice"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BG_TOP
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH  # el fondo ocupa todo el ancho

    # Al probar en la PC, la ventana imita un celular (en el cel real no hace nada)
    try:
        if page.platform in (
            ft.PagePlatform.WINDOWS,
            ft.PagePlatform.MACOS,
            ft.PagePlatform.LINUX,
        ):
            page.window.width = 390
            page.window.height = 844
    except Exception as err:
        print(f"No se pudo ajustar la ventana: {err}")

    exercises = load_exercises()
    progress = load_progress()

    # screen: "start" | "quiz" | "end"
    state = {
        "screen": "start",
        "index": 0,
        "picked": {},       # id -> última opción elegida
        "errors": 0,        # intentos fallidos en esta ronda
        "t0": 0.0,          # momento en que se pulsó "Empezar"
        "elapsed": 0.0,     # tiempo total al terminar
    }

    # Se crea un Audio nuevo con autoplay en cada reproducción
    # (evita el timeout de audio.play(), que hace un seek internamente)
    player = {"ctrl": None}

    async def speak(src: str):
        if fta is None:
            return
        try:
            old = player["ctrl"]
            if old is not None and old in page.services:
                page.services.remove(old)
            new = fta.Audio(src=src, autoplay=True)
            page.services.append(new)
            player["ctrl"] = new
            page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def speaker_button(src: str, color: str, size: int = 18) -> ft.IconButton:
        async def on_click(e):
            await speak(src)

        return ft.IconButton(
            icon=ft.Icons.VOLUME_UP,
            icon_color=color,
            icon_size=size,
            on_click=on_click,
        )

    def primary_button(label: str, on_click) -> ft.Container:
        return ft.Container(
            content=ft.Text(label, size=16, weight=ft.FontWeight.BOLD, color=WHITE),
            alignment=ft.Alignment.CENTER,
            height=50,
            border_radius=16,
            bgcolor=BLUE,
            shadow=ft.BoxShadow(blur_radius=14, color="#2F6FED55", offset=ft.Offset(0, 5)),
            on_click=on_click,
        )

    def current() -> dict:
        return exercises[state["index"]]

    def is_solved(ex: dict) -> bool:
        return state["picked"].get(ex["id"]) == ex["answer"]

    # ---------- acciones ----------

    def start(e=None):
        state["screen"] = "quiz"
        state["index"] = 0
        state["picked"] = {}
        state["errors"] = 0
        state["t0"] = time.perf_counter()  # arranca el cronómetro
        render()

    def finish(e=None):
        state["elapsed"] = time.perf_counter() - state["t0"]  # detiene el cronómetro
        state["screen"] = "end"
        render()

    async def choose(option: str):
        ex = current()
        if is_solved(ex):
            return
        state["picked"][ex["id"]] = option
        if option == ex["answer"]:
            if ex["id"] not in progress["completed"]:
                progress["completed"].append(ex["id"])
                progress["xp"] += XP_PER_EXERCISE
                save_progress(progress)
            render()
            await speak(ex["audio"])  # acertó: se reproduce el verbo
        else:
            state["errors"] += 1
            render()

    def go(step: int):
        new_index = state["index"] + step
        if not (0 <= new_index < len(exercises)):
            return
        # Para avanzar hay que haber acertado el ejercicio actual.
        if step > 0 and not is_solved(current()):
            return
        state["index"] = new_index
        render()

    # ---------- piezas de UI ----------

    def option_tile(ex: dict, option: str) -> ft.Container:
        selected = state["picked"].get(ex["id"]) == option
        correct = selected and option == ex["answer"]
        wrong = selected and not correct

        if correct:
            border, bg, marker_color = GREEN, GREEN_BG, GREEN
            marker = ft.Icon(ft.Icons.CHECK, size=14, color=WHITE)
        elif wrong:
            border, bg, marker_color = RED, RED_BG, RED
            marker = ft.Icon(ft.Icons.CLOSE, size=14, color=WHITE)
        else:
            border, bg, marker_color = LINE, WHITE, None
            marker = None

        circle = ft.Container(
            width=22,
            height=22,
            border_radius=11,
            alignment=ft.Alignment.CENTER,
            bgcolor=marker_color,
            border=ft.Border.all(1.5, marker_color or "#CBD5E1"),
            content=marker,
        )

        row = [circle, ft.Text(option, size=15, weight=ft.FontWeight.W_600, color=NAVY, expand=True)]
        if correct:
            row.append(speaker_button(ex["audio"], GREEN, size=16))

        async def handler(e):
            await choose(option)

        return ft.Container(
            content=ft.Row(row, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=14,
            bgcolor=bg,
            border=ft.Border.all(1.5, border),
            on_click=handler,
        )

    def picture(ex: dict) -> ft.Container:
        return ft.Container(
            height=230,
            bgcolor="#EEF2FA",
            border_radius=20,
            border=ft.Border.all(4, WHITE),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=ft.BoxShadow(blur_radius=18, color="#1F2A5533", offset=ft.Offset(0, 6)),
            content=ft.Stack(
                controls=[
                    ft.Image(
                        src=ex["image"],
                        fit=ft.BoxFit.CONTAIN,
                        left=0, top=0, right=0, bottom=0,
                        error_content=ft.Container(
                            bgcolor=LINE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.IMAGE_OUTLINED, size=48, color=GREY),
                        ),
                    ),
                    ft.Container(
                        content=ft.Text(ex.get("image_credit", ""), size=9, color=WHITE),
                        right=10,
                        bottom=8,
                    ),
                ]
            ),
        )

    def navigation() -> ft.Row:
        last = state["index"] == len(exercises) - 1
        solved = is_solved(current())
        dots = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Container(
                    width=8 if i == state["index"] else 6,
                    height=8 if i == state["index"] else 6,
                    border_radius=4,
                    bgcolor=BLUE if i == state["index"] else "#CBD5E1",
                )
                for i in range(len(exercises))
            ],
        )
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                # Atrás: se habilita desde el 2.º ejercicio
                ft.IconButton(
                    ft.Icons.CHEVRON_LEFT,
                    icon_color=NAVY,
                    disabled=state["index"] == 0,
                    on_click=lambda e: go(-1),
                ),
                dots,
                # Adelante: solo si ya acertó (y no es el último)
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT,
                    icon_color=NAVY,
                    disabled=(not solved) or last,
                    on_click=lambda e: go(1),
                ),
            ],
        )

    def feedback(ex: dict) -> ft.Control:
        picked = state["picked"].get(ex["id"])
        if picked is None:
            return ft.Text("Tap an option to answer.", size=13, color=GREY)
        if picked == ex["answer"]:
            return ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                wrap=True,
                spacing=4,
                controls=[
                    ft.Text("That's right!", size=13, weight=ft.FontWeight.BOLD, color=GREEN_DARK),
                    ft.Text("Listen and repeat:", size=13, color=GREEN_DARK),
                    ft.Text(
                        ex["answer"].lower(),
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=GREEN_DARK,
                        style=ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                    ),
                    speaker_button(ex["audio"], GREEN_DARK, size=16),
                ],
            )
        return ft.Text("Not quite. Try again.", size=13, weight=ft.FontWeight.W_600, color=RED)

    # ---------- contenedores ----------

    counter = ft.Text()
    card_content = ft.Column(spacing=14)

    counter_pill = ft.Container(
        content=counter,
        padding=ft.Padding.symmetric(horizontal=14, vertical=6),
        border_radius=20,
        bgcolor=WHITE,
        border=ft.Border.all(1, LINE),
    )

    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(
                        width=36,
                        height=36,
                        border_radius=10,
                        bgcolor=BLUE,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text("A", size=20, weight=ft.FontWeight.BOLD, color=WHITE),
                    ),
                    ft.Text(
                        spans=[
                            ft.TextSpan("Action ", ft.TextStyle(color=GREY)),
                            ft.TextSpan("Practice", ft.TextStyle(color=NAVY, weight=ft.FontWeight.BOLD)),
                        ],
                        size=14,
                    ),
                ],
            ),
            counter_pill,
        ],
    )

    header_box = ft.Container(content=header, width=380, padding=ft.Padding.only(top=12))

    card = ft.Container(
        width=380,
        padding=20,
        border_radius=28,
        bgcolor=WHITE,
        shadow=ft.BoxShadow(blur_radius=30, color="#1F2A5522", offset=ft.Offset(0, 10)),
        content=card_content,
    )

    # ---------- pantallas ----------

    def build_start() -> list[ft.Control]:
        return [
            ft.Container(height=10),
            ft.Container(
                width=84,
                height=84,
                border_radius=24,
                bgcolor=BLUE,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.RECORD_VOICE_OVER, size=44, color=WHITE),
            ),
            ft.Text(
                "Action Practice",
                size=28,
                weight=ft.FontWeight.W_800,
                color=NAVY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                f"{len(exercises)} verbos para practicar.\nMira la imagen, elige el verbo correcto y escúchalo.",
                size=14,
                color=GREY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=6),
            primary_button("Empezar", start),
            ft.Container(height=6),
        ]

    def build_quiz() -> list[ft.Control]:
        ex = current()
        last = state["index"] == len(exercises) - 1
        controls: list[ft.Control] = [
            ft.Text(
                "LOOK & CHOOSE",
                size=10,
                weight=ft.FontWeight.BOLD,
                color=BLUE,
                text_align=ft.TextAlign.CENTER,
                style=ft.TextStyle(letter_spacing=1.6),
            ),
            ft.Text(
                ex["prompt"],
                size=26,
                weight=ft.FontWeight.W_800,
                color=NAVY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(ex["hint"], size=12, color=GREY, text_align=ft.TextAlign.CENTER),
            picture(ex),
            navigation(),
            *[option_tile(ex, opt) for opt in ex["options"]],
            ft.Container(content=feedback(ex), alignment=ft.Alignment.CENTER, height=32),
        ]
        # En el último ejercicio, al acertar aparece el botón para terminar
        if last and is_solved(ex):
            controls.append(primary_button("Terminar", finish))
        return controls

    def build_end() -> list[ft.Control]:
        errors = state["errors"]
        return [
            ft.Container(height=6),
            ft.Container(
                width=84,
                height=84,
                border_radius=42,
                bgcolor=GREEN_BG,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.EMOJI_EVENTS, size=44, color=GREEN),
            ),
            ft.Text(
                "¡Terminaste!",
                size=28,
                weight=ft.FontWeight.W_800,
                color=NAVY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text("Tu tiempo total", size=13, color=GREY, text_align=ft.TextAlign.CENTER),
            ft.Text(
                format_time(state["elapsed"]),
                size=48,
                weight=ft.FontWeight.W_800,
                color=BLUE,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Sin errores, perfecto." if errors == 0 else f"Intentos fallidos: {errors}",
                size=13,
                color=GREY,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(f"XP total: {progress['xp']}", size=13, color=GREY, text_align=ft.TextAlign.CENTER),
            ft.Container(height=6),
            primary_button("Practicar de nuevo", start),
            ft.Container(height=6),
        ]

    def render():
        screen = state["screen"]

        # El contador solo se ve durante el quiz
        counter_pill.visible = screen == "quiz"
        if screen == "quiz":
            counter.spans = [
                ft.TextSpan(str(state["index"] + 1), ft.TextStyle(weight=ft.FontWeight.BOLD, color=NAVY)),
                ft.TextSpan(f" / {len(exercises)}", ft.TextStyle(color=GREY)),
            ]
            counter.size = 12

        if screen == "start":
            card_content.controls = build_start()
        elif screen == "quiz":
            card_content.controls = build_quiz()
        else:
            card_content.controls = build_end()

        card_content.horizontal_alignment = (
            ft.CrossAxisAlignment.STRETCH if screen == "quiz" else ft.CrossAxisAlignment.CENTER
        )
        page.update()

    def fit_card(e=None):
        if page.width:
            card.width = header_box.width = min(page.width - 32, 440)
            page.update()

    page.on_resize = fit_card

    page.add(
        ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,  # centra el contenido horizontalmente
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[BG_TOP, BG_BOTTOM],
            ),
            content=ft.SafeArea(
                expand=True,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[header_box, card],
                ),
            ),
        )
    )
    fit_card()
    render()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ASSETS_DIR))