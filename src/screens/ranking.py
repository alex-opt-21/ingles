
import flet as ft
from services.admin import admin_service


def construir_ranking(page, width, height):

    BLUE = "#168BFF"
    NAVY = "#183568"
    GRAY = "#58739F"
    BG = "#EFF7FF"
    WHITE = "#FFFFFF"

    GOLD_DARK = "#A96D00"
    GOLD_BG = "#FFF1BE"
    SILVER_BG = "#E9F0FA"
    SILVER = "#8198B8"
    BRONZE_BG = "#F8E5D8"
    BRONZE = "#B9794C"

    # Espacio disponible para el contenido.
    area_height = max(height - 85, 300)
    card_width = max(width - 38, 220)

    lista = ft.Column(spacing=10)

    def short_name(name):
        name = (name or "Student").strip()
        return name.split()[0] if name else "Student"

    def get_xp(student):
        try:
            return int(student.get("xp", 0) or 0)
        except (ValueError, TypeError):
            return 0

    def soft_shadow():
        return ft.BoxShadow(
            blur_radius=10,
            color="#2584BCE0",
            offset=ft.Offset(0, 3),
        )

    # XP
    def xp_badge(value, size=20, gold=False):
        return ft.Container(
            padding=8,
            bgcolor=WHITE,
            border_radius=30,
            border=ft.Border.all(
                2,
                "#FFD36D" if gold else "#B9DFFF",
            ),
            content=ft.Text(
                f"{value} XP",
                size=size,
                color=BLUE,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            ),
        )

    # ENCABEZADO
    def build_header():
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("🏆", size=32),
                ft.Text(
                    "Leaderboard",
                    size=26,
                    color=NAVY,
                    weight=ft.FontWeight.BOLD,
                    font_family="Comic Sans MS",
                ),
                ft.Container(expand=True),
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=30,
                    bgcolor=WHITE,
                    alignment=ft.Alignment.CENTER,
                    shadow=soft_shadow(),
                    content=ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_color=BLUE,
                        icon_size=23,
                        tooltip="Refresh leaderboard",
                        on_click=load_ranking,
                    ),
                ),
            ],
        )

    # PRESENTACIÓN
    def build_intro():
        return ft.Container(
            padding=12,
            bgcolor="#EFFAFF",
            border_radius=25,
            border=ft.Border.all(3, WHITE),
            shadow=soft_shadow(),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=4,
                        controls=[
                            ft.Row(
                                spacing=7,
                                controls=[
                                    ft.Text("🏆", size=23),
                                    ft.Text(
                                        "Top Students",
                                        size=21,
                                        color=NAVY,
                                        weight=ft.FontWeight.BOLD,
                                        font_family="Comic Sans MS",
                                    ),
                                ],
                            ),
                            ft.Text(
                                "Learn, practice and reach the top!",
                                size=12,
                                color=GRAY,
                                font_family="Comic Sans MS",
                            ),
                        ],
                    ),
                    ft.Text("🎓", size=34),
                ],
            ),
        )

    # DECORACIÓN DEL CAMPEÓN
    def champion_decoration():
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Text("⭐", size=18),
                        ft.Text("🏆", size=49),
                        ft.Text("⭐", size=18),
                    ],
                ),
                ft.Container(
                    padding=7,
                    bgcolor="#F47A24",
                    border_radius=12,
                    content=ft.Text(
                        "#1 CHAMPION",
                        size=14,
                        color=WHITE,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
            ],
        )

    # PRIMER PUESTO
    def champion_card(student):
        return ft.Container(
            width=card_width,
            padding=8,
            bgcolor=GOLD_BG,
            border_radius=29,
            border=ft.Border.all(3, WHITE),
            shadow=soft_shadow(),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5,
                controls=[
                    champion_decoration(),

                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text("👑", size=16),
                            ft.Text(
                                "LEADERBOARD CHAMPION",
                                size=11,
                                color=GOLD_DARK,
                                weight=ft.FontWeight.BOLD,
                                font_family="Comic Sans MS",
                            ),
                            ft.Text("👑", size=16),
                        ],
                    ),

                    ft.Text(
                        short_name(student.get("name")),
                        size=29,
                        color=NAVY,
                        weight=ft.FontWeight.BOLD,
                        font_family="Comic Sans MS",
                        text_align=ft.TextAlign.CENTER,
                    ),

                    xp_badge(get_xp(student), 21, True),

                    ft.Text(
                        "✨  Keep being number one!  ✨",
                        size=11,
                        color=GOLD_DARK,
                        font_family="Comic Sans MS",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    # SEGUNDO Y TERCER PUESTO
    def podium_card(student, place):

        if place == 2:
            medal = "🥈"
            title = "SECOND PLACE"
            background = SILVER_BG
            accent = SILVER
            decoration = "⭐"
        else:
            medal = "🥉"
            title = "THIRD PLACE"
            background = BRONZE_BG
            accent = BRONZE
            decoration = "✨"

        return ft.Container(
            width=card_width,
            padding=9,
            bgcolor=background,
            border_radius=25,
            border=ft.Border.all(3, WHITE),
            shadow=soft_shadow(),
            content=ft.Row(
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=60,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                ft.Text(medal, size=39),
                                ft.Text(
                                    f"#{place}",
                                    size=11,
                                    color=accent,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),
                    ),

                    ft.Container(
                        width=2,
                        height=72,
                        bgcolor="#CAD9EE",
                    ),

                    ft.Column(
                        expand=True,
                        spacing=3,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                title,
                                size=11,
                                color=accent,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                short_name(student.get("name")),
                                size=19,
                                color=NAVY,
                                weight=ft.FontWeight.BOLD,
                                font_family="Comic Sans MS",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            xp_badge(get_xp(student), 16),
                        ],
                    ),

                    ft.Text(decoration, size=19),
                ],
            ),
        )

    # RESTO DE ESTUDIANTES
    def student_row(student, place):
        return ft.Container(
            padding=11,
            bgcolor=WHITE,
            border_radius=18,
            border=ft.Border.all(2, "#DCEBFA"),
            shadow=soft_shadow(),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=35,
                        height=35,
                        border_radius=12,
                        bgcolor="#EAF3FF",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            str(place),
                            color=BLUE,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                short_name(student.get("name")),
                                color=NAVY,
                                size=14,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Bright English Student",
                                color=GRAY,
                                size=10,
                            ),
                        ],
                    ),
                    ft.Text(
                        f"{get_xp(student)} XP",
                        color=BLUE,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
            ),
        )

    # RANKING VACÍO
    def empty_card():
        return ft.Container(
            padding=22,
            bgcolor=WHITE,
            border_radius=25,
            border=ft.Border.all(2, "#DCEBFA"),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Text("🏆", size=42),
                    ft.Text(
                        "The leaderboard is waiting!",
                        color=NAVY,
                        size=17,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Complete exercises to appear here.",
                        color=GRAY,
                        size=12,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    # ACTUALIZAR RANKING
    def load_ranking(e=None):
        lista.controls.clear()

        try:
            students = admin_service.get_student_ranking() or []

            students = sorted(
                students,
                key=get_xp,
                reverse=True,
            )[:10]

        except Exception as error:
            print("Leaderboard error:", error)
            students = []

        if not students:
            lista.controls.append(empty_card())

        else:
            lista.controls.append(champion_card(students[0]))

            if len(students) >= 2:
                lista.controls.append(
                    podium_card(students[1], 2)
                )

            if len(students) >= 3:
                lista.controls.append(
                    podium_card(students[2], 3)
                )

            if len(students) > 3:
                lista.controls.append(
                    ft.Text(
                        "MORE STUDENTS",
                        size=15,
                        color=NAVY,
                        weight=ft.FontWeight.BOLD,
                        font_family="Comic Sans MS",
                    )
                )

                for place, student in enumerate(students[3:], start=4):
                    lista.controls.append(
                        student_row(student, place)
                    )

        page.update()

    # CONTENIDO DESPLAZABLE
    contenido = ft.Column(
        spacing=8,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            build_header(),
            build_intro(),
            lista,
            ft.Container(height=15),
        ],
    )

    # FONDO: AHORA CUBRE TODA LA PANTALLA
    # El contenido termina antes para dejar espacio a la navegación.
    contenedor = ft.Container(
        left=0,
        top=0,
        width=width,
        height=height,
        bgcolor=BG,
        content=ft.Stack(
            width=width,
            height=height,
            controls=[
                ft.Image(
                    src="imagenes/home/fondo.png",
                    width=width,
                    height=height,
                    fit=ft.BoxFit.FILL,
                    error_content=ft.Container(
                        bgcolor=BG,
                    ),
                ),

                ft.Container(
                    left=0,
                    top=0,
                    width=width,
                    height=area_height,
                    padding=12,
                    content=contenido,
                ),
            ],
        ),
    )

    load_ranking()

    return contenedor
