
import flet as ft

from services.admin import admin_service


def admin_dashboard(page, admin_user, on_logout):
    page.clean()

    azul = "#1E3A70"
    azul_oscuro = "#172D55"
    fondo = "#F2F6FC"
    blanco = "#FFFFFF"

    tabla = ft.Column(spacing=10)
    ranking = ft.Column(spacing=8)
    mensaje = ft.Text("", size=13)

    busqueda = ft.TextField(
        hint_text="Buscar por nombre o correo",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=12,
        expand=True,
    )

    total_texto = ft.Text(
        "0", size=25, weight=ft.FontWeight.BOLD, color=azul
    )

    activos_texto = ft.Text(
        "0", size=25, weight=ft.FontWeight.BOLD, color=azul
    )

    inactivos_texto = ft.Text(
        "0", size=25, weight=ft.FontWeight.BOLD, color=azul
    )

    # ---------------- MENSAJES ----------------

    def aviso(texto):
        mensaje.value = texto
        page.update()

    # ---------------- CONTAR EJERCICIOS ----------------

    def contar_ejercicios(completed):
        if isinstance(completed, (list, tuple, set)):
            return len(completed)

        try:
            return int(completed or 0)
        except (ValueError, TypeError):
            return 0

    # ---------------- TARJETAS ----------------

    def tarjeta(titulo, valor):
        return ft.Container(
            expand=True,
            padding=14,
            border_radius=14,
            bgcolor=blanco,
            content=ft.Column(
                [
                    ft.Text(
                        titulo,
                        size=12,
                        color="#64748B",
                    ),
                    valor,
                ],
                spacing=5,
            ),
        )

    # ---------------- RANKING ----------------

    def actualizar_ranking():
        ranking.controls.clear()

        mejores = admin_service.get_student_ranking()

        for puesto, estudiante in enumerate(mejores, start=1):

            medalla = {
                1: "🥇",
                2: "🥈",
                3: "🥉",
            }.get(puesto, f"{puesto}.")

            ejercicios = contar_ejercicios(
                estudiante.get("completed", 0)
            )

            ranking.controls.append(
                ft.Container(
                    padding=12,
                    border_radius=12,
                    bgcolor=blanco,
                    content=ft.Row(
                        [
                            ft.Text(
                                medalla,
                                size=22,
                            ),

                            ft.Column(
                                [
                                    ft.Text(
                                        estudiante.get(
                                            "name",
                                            "Estudiante",
                                        ),
                                        size=14,
                                        weight=ft.FontWeight.BOLD,
                                        color=azul_oscuro,
                                    ),

                                    ft.Text(
                                        f"{ejercicios} ejercicios completados",
                                        size=11,
                                        color="#64748B",
                                    ),
                                ],
                                expand=True,
                                spacing=3,
                            ),

                            ft.Text(
                                f'{int(estudiante.get("xp", 0) or 0)} XP',
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=azul,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

        if not mejores:
            ranking.controls.append(
                ft.Text(
                    "Todavía no hay estudiantes en el ranking.",
                    color="#64748B",
                )
            )

    # ---------------- ACTUALIZAR USUARIOS ----------------

    def actualizar(e=None):
        usuarios = admin_service.list_users()

        actualizar_ranking()

        termino = (busqueda.value or "").strip().lower()

        total = len(usuarios)

        activos = sum(
            1 for u in usuarios if u["active"]
        )

        inactivos = total - activos

        total_texto.value = str(total)
        activos_texto.value = str(activos)
        inactivos_texto.value = str(inactivos)

        tabla.controls.clear()

        filtrados = [
            u for u in usuarios
            if termino in u["name"].lower()
            or termino in u["email"].lower()
        ]

        for usuario in filtrados:

            email = usuario["email"]
            es_admin = usuario["role"] == "admin"
            activo = usuario["active"]

            def cambiar_estado(
                e,
                correo=email,
                estado=activo,
            ):
                ok, resultado = admin_service.set_user_active(
                    correo,
                    not estado,
                )

                aviso(resultado)
                actualizar()

            def editar(
                e,
                correo=email,
                nombre=usuario["name"],
            ):
                abrir_edicion(correo, nombre)

            def eliminar(
                e,
                correo=email,
                nombre=usuario["name"],
            ):
                confirmar_eliminacion(correo, nombre)

            ejercicios = contar_ejercicios(
                usuario.get("completed", 0)
            )

            controles = [
                ft.Text(
                    usuario["name"],
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=azul_oscuro,
                ),

                ft.Text(
                    email,
                    size=12,
                    color="#64748B",
                ),

                ft.Text(
                    f'Rol: {usuario["role"]} | '
                    f'XP: {usuario["xp"]} | '
                    f'Ejercicios: {ejercicios}',
                    size=11,
                    color="#64748B",
                ),

                ft.Text(
                    "Activo" if activo else "Desactivado",
                    color="#15803D" if activo else "#DC2626",
                    size=12,
                ),
            ]

            acciones = [
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    tooltip="Editar nombre",
                    on_click=editar,
                ),

                ft.IconButton(
                    icon=(
                        ft.Icons.BLOCK
                        if activo
                        else ft.Icons.CHECK_CIRCLE
                    ),
                    tooltip="Desactivar o activar",
                    disabled=es_admin,
                    on_click=cambiar_estado,
                ),

                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Eliminar usuario",
                    disabled=es_admin,
                    on_click=eliminar,
                ),
            ]

            tabla.controls.append(
                ft.Container(
                    padding=14,
                    border_radius=14,
                    bgcolor=blanco,
                    content=ft.Row(
                        [
                            ft.Column(
                                controles,
                                spacing=4,
                                expand=True,
                            ),

                            ft.Row(
                                acciones,
                                spacing=0,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

        if not filtrados:
            tabla.controls.append(
                ft.Text(
                    "No se encontraron usuarios.",
                    color="#64748B",
                )
            )

        page.update()

    # ---------------- CREAR USUARIO ----------------

    def abrir_crear(e=None):

        nombre = ft.TextField(
            label="Nombre completo"
        )

        correo = ft.TextField(
            label="Correo electrónico",
            keyboard_type=ft.KeyboardType.EMAIL,
        )

        clave = ft.TextField(
            label="Contraseña inicial",
            password=True,
            can_reveal_password=True,
        )

        error = ft.Text(
            "",
            color="#DC2626",
        )

        def guardar(ev):

            ok, resultado = admin_service.create_user(
                nombre.value,
                correo.value,
                clave.value,
            )

            if not ok:
                error.value = resultado
                page.update()
                return

            page.pop_dialog()

            aviso("Usuario creado correctamente.")
            actualizar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Crear usuario"),

                content=ft.Column(
                    [
                        nombre,
                        correo,
                        clave,
                        error,
                    ],
                    tight=True,
                    width=320,
                ),

                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda ev: page.pop_dialog(),
                    ),

                    ft.Button(
                        "Guardar",
                        on_click=guardar,
                    ),
                ],
            )
        )

    # ---------------- EDITAR USUARIO ----------------

    def abrir_edicion(email, nombre_actual):

        nombre = ft.TextField(
            label="Nombre completo",
            value=nombre_actual,
        )

        error = ft.Text(
            "",
            color="#DC2626",
        )

        def guardar(ev):

            ok, resultado = admin_service.update_user(
                email,
                nombre.value,
            )

            if not ok:
                error.value = resultado
                page.update()
                return

            page.pop_dialog()

            aviso(resultado)
            actualizar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Editar usuario"),

                content=ft.Column(
                    [
                        ft.Text(email, size=12),
                        nombre,
                        error,
                    ],
                    tight=True,
                    width=320,
                ),

                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda ev: page.pop_dialog(),
                    ),

                    ft.Button(
                        "Guardar cambios",
                        on_click=guardar,
                    ),
                ],
            )
        )

    # ---------------- ELIMINAR USUARIO ----------------

    def confirmar_eliminacion(email, nombre):

        def eliminar_confirmado(e):

            ok, resultado = admin_service.delete_user(email)

            page.pop_dialog()

            aviso(resultado)
            actualizar()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar usuario"),

                content=ft.Text(
                    f"¿Quieres eliminar la cuenta de {nombre} "
                    f"({email})? Esta operación no se puede deshacer."
                ),

                actions=[
                    ft.TextButton(
                        "Cancelar",
                        on_click=lambda e: page.pop_dialog(),
                    ),

                    ft.Button(
                        "Eliminar definitivamente",
                        on_click=eliminar_confirmado,
                        style=ft.ButtonStyle(
                            bgcolor="#DC2626",
                            color=blanco,
                        ),
                    ),
                ],
            )
        )

    # ---------------- ENCABEZADO ----------------

    encabezado = ft.Row(
        [
            ft.Column(
                [
                    ft.Text(
                        "Administración",
                        size=25,
                        weight=ft.FontWeight.BOLD,
                        color=azul_oscuro,
                    ),

                    ft.Text(
                        f'Bienvenida, {admin_user.get("name", "Administradora")}',
                        color="#64748B",
                    ),
                ],
                spacing=4,
                expand=True,
            ),

            ft.IconButton(
                icon=ft.Icons.LOGOUT,
                tooltip="Cerrar sesión",
                on_click=lambda e: on_logout(),
            ),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ---------------- CONTENIDO ----------------

    contenido = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,

        controls=[
            encabezado,

            ft.Text(
                "🏆 Ranking de estudiantes",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=azul_oscuro,
            ),

            ranking,

            ft.Row(
                [
                    tarjeta("Total", total_texto),
                    tarjeta("Activos", activos_texto),
                    tarjeta("Inactivos", inactivos_texto),
                ],
                spacing=8,
            ),

            ft.Row(
                [
                    busqueda,

                    ft.IconButton(
                        icon=ft.Icons.SEARCH,
                        tooltip="Buscar",
                        on_click=actualizar,
                    ),
                ]
            ),

            ft.Row(
                [
                    ft.Text(
                        "Usuarios registrados",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=azul_oscuro,
                    ),

                    ft.Button(
                        "Crear usuario",
                        icon=ft.Icons.PERSON_ADD,
                        on_click=abrir_crear,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),

            mensaje,
            tabla,
        ],
    )

    page.add(
        ft.Container(
            expand=True,
            padding=20,
            bgcolor=fondo,
            content=contenido,
        )
    )

    actualizar()
