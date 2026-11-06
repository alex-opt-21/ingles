
import flet as ft
from services.admin import admin_service


def mostrar_ranking(page, volver):

    AZUL = "#1677E8"
    AZUL_OSCURO = "#183568"
    FONDO = "#F1F6FD"
    BLANCO = "#FFFFFF"
    GRIS = "#64748B"

    page.clean()

    def nombre_corto(nombre):
        nombre = (nombre or "Estudiante").strip()
        return nombre.split()[0]

    def obtener_xp(alumno):
        try:
            return int(alumno.get("xp", 0) or 0)
        except (ValueError, TypeError):
            return 0

    lista = ft.Column(spacing=12)

    def tarjeta_podio(alumno, puesto):
        colores = {
            1: ("#FFF1BD", "#D99A00", "🥇", "PRIMER LUGAR"),
            2: ("#E8EDF5", "#8293A9", "🥈", "SEGUNDO LUGAR"),
            3: ("#F8E2D2", "#B97849", "🥉", "TERCER LUGAR"),
        }

        fondo, color, medalla, titulo = colores[puesto]

        return ft.Container(
            expand=True,
            padding=15,
            border_radius=22,
            bgcolor=fondo,
            content=ft.Column(
                [
                    ft.Text(medalla, size=38),
                    ft.Text(
                        titulo,
                        size=10,
                        color=color,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        nombre_corto(alumno["name"]),
                        size=17,
                        color=AZUL_OSCURO,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        f'{obtener_xp(alumno)} XP',
                        size=20,
                        color=AZUL,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=7,
            ),
        )

    def fila_estudiante(alumno, puesto):
        return ft.Container(
            padding=14,
            border_radius=17,
            bgcolor=BLANCO,
            content=ft.Row(
                [
                    ft.Container(
                        width=38,
                        height=38,
                        border_radius=12,
                        bgcolor="#EAF2FF",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            str(puesto),
                            color=AZUL,
                            weight=ft.FontWeight.BOLD,
                            size=16,
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                nombre_corto(alumno["name"]),
                                color=AZUL_OSCURO,
                                weight=ft.FontWeight.BOLD,
                                size=15,
                            ),
                            ft.Text(
                                "Estudiante Bright English",
                                color=GRIS,
                                size=11,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(
                        f'{obtener_xp(alumno)} XP',
                        color=AZUL,
                        weight=ft.FontWeight.BOLD,
                        size=15,
                    ),
                ],
            ),
        )

    def cargar_ranking(e=None):
        lista.controls.clear()

        try:
            estudiantes = admin_service.get_student_ranking()
            estudiantes = estudiantes or []

            estudiantes = sorted(
                estudiantes,
                key=lambda alumno: obtener_xp(alumno),
                reverse=True,
            )[:10]

        except Exception as error:
            print("Error al cargar ranking:", error)
            estudiantes = []

        if not estudiantes:
            lista.controls.append(
                ft.Container(
                    padding=30,
                    bgcolor=BLANCO,
                    border_radius=20,
                    content=ft.Column(
                        [
                            ft.Text("🏆", size=45),
                            ft.Text(
                                "¡El ranking está esperando!",
                                color=AZUL_OSCURO,
                                weight=ft.FontWeight.BOLD,
                                size=17,
                            ),
                            ft.Text(
                                "Completa ejercicios para aparecer aquí.",
                                color=GRIS,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
            page.update()
            return

        # PRIMER PUESTO
        primero = estudiantes[0]

        lista.controls.append(
            ft.Container(
                padding=18,
                border_radius=22,
                bgcolor="#FFF1BD",
                content=ft.Column(
                    [
                        ft.Text("🏆", size=42),
                        ft.Text(
                            "LÍDER DEL RANKING",
                            color="#A66D00",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            nombre_corto(primero["name"]),
                            color=AZUL_OSCURO,
                            size=25,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f'{obtener_xp(primero)} XP',
                            color=AZUL,
                            size=26,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "¡Sigue siendo el número uno!",
                            color="#8A6B24",
                            size=12,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                ),
            )
        )

        # SEGUNDO Y TERCER PUESTO
        if len(estudiantes) > 1:
            podio = []

            for puesto in (2, 3):
                if len(estudiantes) >= puesto:
                    podio.append(
                        tarjeta_podio(estudiantes[puesto - 1], puesto)
                    )

            lista.controls.append(
                ft.Row(
                    controls=podio,
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )

        # RESTO DE LOS ESTUDIANTES
        if len(estudiantes) > 3:
            lista.controls.append(
                ft.Text(
                    "CLASIFICACIÓN GENERAL",
                    color=AZUL_OSCURO,
                    size=15,
                    weight=ft.FontWeight.BOLD,
                )
            )

            for puesto, alumno in enumerate(estudiantes[3:], start=4):
                lista.controls.append(
                    fila_estudiante(alumno, puesto)
                )

        page.update()

    encabezado = ft.Row(
        [
            ft.IconButton(
                icon=ft.Icons.ARROW_BACK_ROUNDED,
                icon_color=AZUL_OSCURO,
                on_click=lambda e: volver(),
            ),
            ft.Text(
                "Ranking",
                size=27,
                color=AZUL_OSCURO,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.REFRESH_ROUNDED,
                icon_color=AZUL,
                tooltip="Actualizar puntuaciones",
                on_click=cargar_ranking,
            ),
        ],
    )

    contenido = ft.Column(
        [
            encabezado,

            ft.Container(
                padding=15,
                border_radius=20,
                bgcolor=BLANCO,
                content=ft.Column(
                    [
                        ft.Text(
                            "🏆 Los mejores estudiantes",
                            size=19,
                            color=AZUL_OSCURO,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "¡Aprende, practica y conquista el primer lugar!",
                            color=GRIS,
                            size=12,
                        ),
                    ],
                    spacing=6,
                ),
            ),

            lista,
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    page.add(
        ft.Container(
            expand=True,
            padding=16,
            bgcolor=FONDO,
            content=contenido,
        )
    )

    cargar_ranking()
