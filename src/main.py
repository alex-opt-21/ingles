import json
import os
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

    exercises = load_exercises()
    progress = load_progress()
    state = {"index": 0, "picked": {}}

    audio = None
    if fta is not None:
        audio = fta.Audio()
        page.services.append(audio)

    async def speak(src: str):
        if audio is None:
            return
        try:
            audio.src = src
            audio.update()
            await audio.play()
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

    def current() -> dict:
        return exercises[state["index"]]

    def is_solved(ex: dict) -> bool:
        return state["picked"].get(ex["id"]) == ex["answer"]

    def choose(option: str):
        ex = current()
        if is_solved(ex):
            return
        state["picked"][ex["id"]] = option
        if option == ex["answer"] and ex["id"] not in progress["completed"]:
            progress["completed"].append(ex["id"])
            progress["xp"] += XP_PER_EXERCISE
            save_progress(progress)
        render()

    def go(step: int):
        new_index = state["index"] + step
        if 0 <= new_index < len(exercises):
            state["index"] = new_index
            render()

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

        def handler(e):
            choose(option)

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
                ft.IconButton(
                    ft.Icons.CHEVRON_LEFT,
                    icon_color=NAVY,
                    disabled=state["index"] == 0,
                    on_click=lambda e: go(-1),
                ),
                dots,
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT,
                    icon_color=NAVY,
                    disabled=state["index"] == len(exercises) - 1,
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

    counter = ft.Text()
    card_content = ft.Column(spacing=14)

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
            ft.Container(
                content=counter,
                padding=ft.Padding.symmetric(horizontal=14, vertical=6),
                border_radius=20,
                bgcolor=WHITE,
                border=ft.Border.all(1, LINE),
            ),
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

    def render():
        ex = current()
        total = len(exercises)

        counter.spans = [
            ft.TextSpan(str(state["index"] + 1), ft.TextStyle(weight=ft.FontWeight.BOLD, color=NAVY)),
            ft.TextSpan(f" / {total}", ft.TextStyle(color=GREY)),
        ]
        counter.size = 12

        card_content.controls = [
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
        page.update()

    def fit_card(e=None):
        if page.width:
            card.width = header_box.width = min(page.width - 32, 440)
            page.update()

    page.on_resize = fit_card

    page.add(
        ft.Container(
            expand=True,
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