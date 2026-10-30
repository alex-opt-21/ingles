import asyncio
import struct
from pathlib import Path
import flet as ft

from services.ejercicios.ejercicio_service import QuizSession, format_time
from services.ejercicios.pronunciacion_service import listen_and_check
from ui.theme import (
    EXERCISE_BLUE as BLUE,
    EXERCISE_NAVY as NAVY,
    EXERCISE_SOFT_BLUE as SOFT_BLUE,
    EXERCISE_GREEN as GREEN,
    EXERCISE_RED as RED,
    EXERCISE_WHITE as WHITE,
    EXERCISE_FONT as FONT,
)

try:
    import flet_audio as fta
except ImportError:
    fta = None

# Paleta adicional (ajustable). Los colores principales vienen de ui.theme.
CREAM = "#FFFCF7"
PAPER = "#FFFFFF"
PALE_BLUE = "#EAF4FF"
BORDER_BLUE = "#A6CFFF"
PALE_BORDER = "#E9E5DF"
LOCKED_BG = "#D5DCE8"
LOCKED_FG = "#8A97B0"
SILVER = "#E9EDF4"

# Rutas RELATIVAS a src/assets/ (no incluir src/assets/ en src).
FONDO_NUBES = "imagenes/fondo_nubes.png"
HOJA_CENTRAL = "imagenes/hoja_central.png"

# Plantilla de diseño para colocar controles SOBRE la imagen de la hoja.
# Plantilla de posiciones para una hoja responsiva, sin scroll.
HOJA_BASE_W = 420
HOJA_BASE_H = 870
# Permite aprovechar mas alto de la pantalla sin ocultar el boton Continue.
# Puedes subirlo a 870 si la ventana es muy alta, o bajarlo a 820.
ALTURA_MAX_HOJA = 850
# Se deja sitio para el encabezado, los margenes y el area segura.
RESERVA_VERTICAL = 96
# Ajustes opcionales para alinear el diseño con un PNG diferente.
AJUSTE_X = 0
AJUSTE_Y = 0

# Proporcion de reserva cuando la hoja aun no se encuentra en disco.
# Se sustituye automaticamente por el ancho/alto REAL del PNG local.
HOJA_PROPORCION_RESERVA = 0.48


def _shadow(opacity=0.09, blur=12, y=3):
    return ft.BoxShadow(
        color=ft.Colors.with_opacity(opacity, "#153C81"),
        blur_radius=blur,
        offset=ft.Offset(0, y),
    )


class QuizView:
    """Vista reemplazable; sigue usando la misma interfaz publica que la original."""

    def __init__(self, page: ft.Page, session: QuizSession, on_home):
        self.page = page
        self.session = session
        self.on_home = on_home
        self.mode = "quiz"       # quiz | paused | end | closed
        self._tick_id = 0
        self._player = None
        self.rec_state = "idle"
        self.rec_message = None
        self._width = 440
        self._height = 844
        self.timer_text = ft.Text("00:00")
        self.counter = ft.Text("1 / 16")
        self.shell = ft.Container()

    # ---------- Ciclo de vida ----------

    def show(self, resume=False):
        self.mode = "quiz"
        self._tick_id += 1
        if resume and self.session.has_progress:
            self.session.resume()
        else:
            self.session.start()
        self.rec_state = "idle"
        self.rec_message = None
        self.timer_text.value = format_time(self.session.time_now())
        self._mount()
        self.page.run_task(self._tick, self._tick_id)

    def close(self):
        self._tick_id += 1
        self.mode = "closed"
        self.page.on_resize = None

    def _mount(self):
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True,
                bgcolor=PALE_BLUE,
                alignment=ft.Alignment.TOP_CENTER,
                content=self.shell,
            )
        )
        self.page.on_resize = self._fit_card
        self._fit_card(force=True)

    def _fit_card(self, e=None, force=False):
        width = max(270, min(self.page.width or 440, 520))
        height = max(360, self.page.height or 844)
        if (
            force
            or abs(width - self._width) > 1
            or abs(height - self._height) > 1
            or self.shell.content is None
        ):
            self._width = width
            self._height = height
            self.render()

    async def _tick(self, token):
        while self._tick_id == token and self.mode == "quiz":
            self.timer_text.value = format_time(self.session.time_now())
            try:
                self.timer_text.update()
            except Exception:
                pass
            await asyncio.sleep(1)

    # ---------- Audio, mensajes y acciones de QuizSession ----------

    async def _speak(self, src):
        if fta is None or not src:
            return
        try:
            if self._player is not None and self._player in self.page.services:
                self.page.services.remove(self._player)
            new = fta.Audio(src=src, autoplay=True)
            self.page.services.append(new)
            self._player = new
            self.page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception as err:
            print(f"{message} ({err})")

    async def _choose(self, option):
        result = self.session.choose(option)
        if result == "ignored":
            return
        self.render()
        if result == "correct":
            await self._speak(self.session.current.get("audio"))

    def _on_back(self, e=None):
        self.rec_message = None
        if self.session.back():
            self.render()
        else:
            self._on_home()

    def _on_next(self, e=None):
        result = self.session.advance()
        if result == "blocked":
            if self.session.is_solved():
                self._toast("Say the word correctly to continue.")
            else:
                self._toast("First choose the correct answer.")
            return
        self.rec_message = None
        if result == "finished":
            self.mode = "end"
            self._tick_id += 1
        self.render()

    def _on_hint(self, e=None):
        if self.session.use_hint():
            self.render()

    def _on_skip(self, e=None):
        self.rec_message = None
        result = self.session.skip()
        if result == "finished":
            self.mode = "end"
            self._tick_id += 1
        self.render()

    async def _on_listen(self, e=None):
        ex = self.session.current
        if self.session.is_solved(ex):
            await self._speak(ex.get("audio"))
        else:
            self._toast("First choose the correct answer.")

    async def _on_mic(self, e=None):
        ex = self.session.current
        if not self.session.is_solved(ex):
            self._toast("First choose the correct answer.")
            return
        if self.rec_state != "idle":
            return
        self.rec_state = "recording"
        self.rec_message = None
        self.render()
        try:
            result = await asyncio.to_thread(listen_and_check, ex["answer"])
            self.rec_message = result
            if result[0]:
                self.session.mark_pronounced(ex)
        except Exception as err:
            print(f"Mic error: {err}")
            self._toast("Could not access the microphone.")
        finally:
            self.rec_state = "idle"
            if self.mode == "quiz":
                self.render()

    # ---------- Pausa y navegacion ----------

    def _on_pause(self, e=None):
        if self.mode != "quiz" or self.rec_state != "idle":
            return
        self.session.pause()
        self.mode = "paused"
        self._tick_id += 1
        self.render()

    def _on_resume(self, e=None):
        self.session.resume()
        self.mode = "quiz"
        self.render()
        self._tick_id += 1
        self.page.run_task(self._tick, self._tick_id)

    def _on_finish_now(self, e=None):
        self.session.finish_early()
        self._tick_id += 1
        self.mode = "end"
        self.render()

    def _on_save_exit(self, e=None):
        self.session.pause()
        self.close()
        self.on_home()

    def _on_restart(self, e=None):
        self.show()

    def _on_home(self, e=None):
        self.close()
        self.on_home()

    # ---------- Componentes visuales reutilizables ----------

    def _text(self, text, size=16, color=NAVY, bold=False, italic=False,
              align=ft.TextAlign.CENTER, max_lines=None):
        return ft.Text(
            str(text),
            size=size,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            color=color,
            italic=italic,
            font_family=FONT,
            text_align=align,
            max_lines=max_lines,
        )

    def _surface(self, content, padding=12, radius=22, color=PAPER,
                 border_color=PALE_BORDER):
        return ft.Container(
            bgcolor=color,
            padding=padding,
            border=ft.Border.all(1, border_color),
            border_radius=radius,
            shadow=_shadow(0.06, 10, 3),
            content=content,
        )

    def _letter_badge(self, scale=1.0):
        return ft.Container(
            width=46 * scale,
            height=48 * scale,
            bgcolor=BLUE,
            border_radius=15 * scale,
            border=ft.Border.all(max(1, 2 * scale), WHITE),
            shadow=_shadow(0.2, 7 * scale, 3 * scale),
            alignment=ft.Alignment.CENTER,
            content=self._text("A", 29 * scale, WHITE, bold=True, italic=True),
        )

    def _time_pill(self, scale=1.0):
        self.timer_text.size = 15 * scale
        self.timer_text.color = NAVY
        self.timer_text.weight = ft.FontWeight.BOLD
        self.timer_text.font_family = FONT
        return ft.Container(
            height=40 * scale,
            bgcolor=WHITE,
            border=ft.Border.all(max(1, 2 * scale), PALE_BLUE),
            border_radius=22 * scale,
            padding=ft.Padding.symmetric(horizontal=8 * scale),
            shadow=_shadow(0.09, 5 * scale, 2 * scale),
            ink=True,
            on_click=self._on_pause,
            tooltip="Pause practice",
            content=ft.Row(
                tight=True,
                spacing=3 * scale,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.PAUSE_CIRCLE_OUTLINE, size=16 * scale, color=BLUE),
                    self.timer_text,
                ],
            ),
        )

    def _counter_pill(self, scale=1.0):
        self.counter.value = f"{self.session.number} / {self.session.total}"
        self.counter.size = 15 * scale
        self.counter.weight = ft.FontWeight.BOLD
        self.counter.color = NAVY
        self.counter.font_family = FONT
        return ft.Container(
            height=40 * scale,
            bgcolor=WHITE,
            border_radius=22 * scale,
            padding=ft.Padding.symmetric(horizontal=10 * scale),
            border=ft.Border.all(max(1, 2 * scale), PALE_BLUE),
            shadow=_shadow(0.09, 5 * scale, 2 * scale),
            alignment=ft.Alignment.CENTER,
            content=self.counter,
        )

    def _header(self):
        """Una sola fila: logo/titulo a la izquierda, tiempo/progreso a la derecha."""
        scale = min(1.0, (self._width - 24) / 440)
        brand = ft.Row(
            tight=True,
            spacing=7 * scale,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self._letter_badge(scale),
                self._text("Action Practice", 17 * scale, bold=True, italic=True),
            ],
        )
        pills = ft.Row(
            tight=True,
            spacing=5 * scale,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._time_pill(scale), self._counter_pill(scale)],
        )
        return ft.Container(
            height=53 * scale,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=5 * scale,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[brand, pills],
            ),
        )

    def _section_heading(self, scale=1.0):
        return ft.Container(
            height=36 * scale,
            bgcolor="#B3D7FF",
            padding=ft.Padding.symmetric(horizontal=12 * scale),
            border_radius=12 * scale,
            alignment=ft.Alignment.CENTER,
            content=self._text("LOOK & CHOOSE", 18 * scale, bold=True, italic=True),
        )

    def _illustration(self, src, scale=1.0):
        """Ilustracion real del ejercicio; borde y sombra dibujados por Flet."""
        return ft.Container(
            width=274 * scale,
            height=274 * scale,
            padding=9 * scale,
            border_radius=34 * scale,
            bgcolor="#FFFDF8",
            border=ft.Border.all(max(1, 2 * scale), "#F0E9E0"),
            shadow=_shadow(0.07, 9 * scale, 3 * scale),
            content=ft.Container(
                border_radius=25 * scale,
                bgcolor=PALE_BLUE,
                alignment=ft.Alignment.CENTER,
                content=ft.Image(
                    src=src,
                    width=254 * scale,
                    height=254 * scale,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=self._text("Image not available", 14 * scale, SOFT_BLUE),
                ),
            ),
        )

    def _option_button(self, ex, option, scale=1.0):
        s = self.session
        picked = s.picked_for(ex)
        selected = picked == option
        correct = selected and option == ex["answer"]
        wrong = selected and not correct
        eliminated = s.hint_for(ex) == option and not selected
        solved = s.is_solved(ex)
        color = GREEN if correct else RED if wrong else SILVER if eliminated else BORDER_BLUE
        bg = "#E9F8ED" if correct else "#FFF0F0" if wrong else "#F4F5F8" if eliminated else WHITE
        fg = GREEN if correct else RED if wrong else LOCKED_FG if eliminated else NAVY

        async def choose(e):
            await self._choose(option)

        return ft.Container(
            height=49 * scale,
            bgcolor=bg,
            border=ft.Border.all(max(1, 2 * scale), color),
            border_radius=17 * scale,
            padding=ft.Padding.symmetric(horizontal=12 * scale),
            shadow=_shadow(0.06, 6 * scale, 2 * scale),
            ink=not (eliminated or solved),
            on_click=None if eliminated or solved else choose,
            content=ft.Row(
                spacing=12 * scale,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=25 * scale,
                        height=25 * scale,
                        border_radius=13 * scale,
                        alignment=ft.Alignment.CENTER,
                        border=ft.Border.all(max(1, 2 * scale), GREEN if correct else RED if wrong else "#9EADD0"),
                        bgcolor=GREEN if correct else RED if wrong else WHITE,
                        content=(
                            ft.Icon(ft.Icons.CHECK if correct else ft.Icons.CLOSE,
                                    size=17 * scale, color=WHITE)
                            if correct or wrong else None
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        alignment=ft.Alignment.CENTER_LEFT,
                        content=self._text(option, 20 * scale, fg, bold=True,
                                           italic=True, align=ft.TextAlign.LEFT, max_lines=1),
                    ),
                ],
            ),
        )

    def _small_button(self, label, icon, scale=1.0, on_click=None, enabled=True):
        color = BLUE if enabled else LOCKED_FG
        return ft.Container(
            width=104 * scale,
            height=50 * scale,
            bgcolor=WHITE if enabled else "#F4F6FA",
            border_radius=25 * scale,
            border=ft.Border.all(max(1, 1.5 * scale), BORDER_BLUE if enabled else SILVER),
            shadow=_shadow(0.08, 7 * scale, 3 * scale),
            ink=enabled,
            on_click=on_click if enabled else None,
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                tight=True,
                spacing=5 * scale,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=17 * scale, color=color),
                    self._text(label, 17 * scale, color, bold=True),
                ],
            ),
        )

    def _mic_button(self, scale=1.0):
        recording = self.rec_state == "recording"
        color = RED if recording else BLUE
        return ft.Container(
            width=66 * scale,
            height=66 * scale,
            border_radius=34 * scale,
            bgcolor=color,
            border=ft.Border.all(max(2, 5 * scale), "#CFE6FF"),
            shadow=_shadow(0.2, 13 * scale, 4 * scale),
            alignment=ft.Alignment.CENTER,
            ink=not recording,
            on_click=None if recording else self._on_mic,
            tooltip="Speak the answer",
            content=ft.Icon(
                ft.Icons.MIC if not recording else ft.Icons.GRAPHIC_EQ,
                color=WHITE,
                size=32 * scale,
            ),
        )

    def _continue_button(self, scale=1.0):
        enabled = self.session.can_continue()
        label = "Finish" if self.session.is_last else "Continue"
        return ft.Container(
            height=52 * scale,
            width=222 * scale,
            border_radius=28 * scale,
            bgcolor=GREEN if enabled else LOCKED_BG,
            border=ft.Border.all(max(1, 2 * scale), GREEN),
            shadow=_shadow(0.1, 9 * scale, 3 * scale),
            ink=enabled,
            on_click=self._on_next,  # explica el bloqueo si no se puede avanzar
            alignment=ft.Alignment.CENTER,
            content=ft.Row(
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5 * scale,
                controls=[
                    self._text(label, 20 * scale, WHITE if enabled else LOCKED_FG, bold=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT,
                            color=WHITE if enabled else LOCKED_FG, size=21 * scale),
                ],
            ),
        )

    def _feedback(self, scale=1.0):
        ex = self.session.current
        picked = self.session.picked_for(ex)
        if self.rec_message is not None and self.session.is_solved(ex):
            ok, heard = self.rec_message
            msg = "Great pronunciation!" if ok else f'I heard "{heard or "..."}". Try again.'
            color = GREEN if ok else RED
        elif self.session.is_solved(ex):
            msg, color = ("Correct!", GREEN) if self.session.is_pronounced(ex) else ("Correct! Now say it aloud.", GREEN)
        elif picked:
            msg, color = "Wrong. Try again.", RED
        else:
            return None
        return self._text(msg, 12 * scale, color, bold=True, max_lines=1)

    # ---------- Hoja con controles pegados a ella, SIN scroll ----------

    def _proporcion_hoja(self):
        """Lee el aspecto real del PNG para que la hoja nunca se deforme."""
        archivo = Path(__file__).resolve()
        for carpeta in archivo.parents:
            ruta = carpeta / "assets" / HOJA_CENTRAL
            if not ruta.is_file():
                continue
            try:
                with ruta.open("rb") as f:
                    header = f.read(24)
                if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
                    ancho, alto = struct.unpack(">II", header[16:24])
                    if ancho > 0 and alto > 0:
                        return ancho / alto
            except (OSError, ValueError, struct.error):
                pass
        return HOJA_PROPORCION_RESERVA

    def _build_quiz(self):
        """Hoja grande y fija, con controles de Flet pegados al fondo de papel.

        La hoja aprovecha mas altura sin recortar sus bordes. La imagen
        decorativa se ajusta ligeramente al rectangulo visible, mientras
        los controles reales permanecen fijos en sus posiciones relativas.
        """
        s = self.session
        ex = s.current

        # El contenedor exterior usa padding vertical 10 + SafeArea.
        # Evitamos que el encabezado + hoja superen la ventana.
        header_scale = min(1.0, (self._width - 24) / 440)
        header_h = 53 * header_scale
        espacio_para_hoja = self._height - 20 - header_h - 5 - 12
        paper_h = max(220, min(ALTURA_MAX_HOJA, espacio_para_hoja))
        paper_w = min(self._width - 24, 480)

        # Las posiciones X e Y se adaptan por separado. De esta forma la
        # hoja ocupa el ancho disponible y todo el contenido crece con ella.
        sx = paper_w / HOJA_BASE_W
        sy = paper_h / HOJA_BASE_H
        scale = min(sx, sy)

        def place(x, y, width, height, control, align=ft.Alignment.CENTER):
            return ft.Container(
                left=(x + AJUSTE_X) * sx,
                top=(y + AJUSTE_Y) * sy,
                width=width * sx,
                height=height * sy,
                alignment=align,
                content=control,
            )

        controls = [
            # Imagen decorativa SIN botones incluidos. FILL mantiene visibles
            # todos los bordes de papel, incluso si se amplia un poco en alto.
            ft.Image(
                src=HOJA_CENTRAL,
                left=0,
                top=0,
                width=paper_w,
                height=paper_h,
                fit=ft.BoxFit.FILL,
                error_content=self._text(
                    "No se encontro hoja_central.png", 13 * scale, RED
                ),
            ),
            place(36, 80, 348, 38, self._section_heading(scale)),
            place(23, 129, 374, 52,
                  self._text(ex["prompt"], 29 * scale, NAVY,
                             bold=True, max_lines=2)),
            place(39, 187, 342, 42,
                  self._text(ex["hint"], 14 * scale, SOFT_BLUE,
                             max_lines=2)),
            place(73, 237, 274, 274,
                  self._illustration(ex["image"], scale)),
        ]

        for i, option in enumerate(ex["options"][:3]):
            controls.append(
                place(40, 525 + i * 57, 340, 49,
                      self._option_button(ex, option, scale))
            )

        feedback = self._feedback(scale)
        if feedback is not None:
            controls.append(place(30, 691, 360, 17, feedback))

        controls.extend([
            place(38, 718, 104, 50,
                  self._small_button("Hint", ft.Icons.LIGHTBULB_OUTLINE,
                                     scale, on_click=self._on_hint,
                                     enabled=s.hint_available(ex))),
            place(177, 710, 66, 66, self._mic_button(scale)),
            place(278, 718, 104, 50,
                  self._small_button("Skip", ft.Icons.FAST_FORWARD,
                                     scale, on_click=self._on_skip)),
            place(110, 779, 200, 17,
                  self._text("Listening..." if self.rec_state == "recording"
                             else "Tap to speak", 12 * scale, SOFT_BLUE,
                             bold=True)),
            place(99, 800, 222, 52, self._continue_button(scale)),
        ])

        quiz_card = ft.Stack(
            width=paper_w,
            height=paper_h,
            controls=controls,
        )
        return ft.Column(
            expand=True,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._header(), quiz_card],
        )

    # ---------- Pantalla de pausa: botones reales ----------

    def _menu_button(self, text, on_click, primary=False):
        return ft.Container(
            bgcolor=BLUE if primary else WHITE,
            border=ft.Border.all(2, BLUE if primary else BORDER_BLUE),
            border_radius=24,
            height=55,
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=on_click,
            shadow=_shadow(0.07, 8, 3),
            content=self._text(text, 18, WHITE if primary else BLUE, bold=True),
        )

    def _build_paused(self):
        s = self.session
        return ft.Column(
            expand=True,
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    bgcolor=CREAM,
                    padding=26,
                    border_radius=30,
                    shadow=_shadow(0.09, 15, 3),
                    content=ft.Column(
                        spacing=18,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.PAUSE_CIRCLE_FILLED, color=BLUE, size=82),
                            self._text("Paused", 32, bold=True),
                            self._text(f"Question {s.number} / {s.total}", 18, SOFT_BLUE),
                            self._text(f"Time {format_time(s.time_now())}", 18, SOFT_BLUE),
                            self._menu_button("Resume", self._on_resume, primary=True),
                            self._menu_button("Finish now", self._on_finish_now),
                            self._menu_button("Save & exit", self._on_save_exit),
                        ],
                    ),
                ),
            ],
        )

    # ---------- Pantalla final: estadisticas como controles ----------

    def _stat(self, icon, label, value, color):
        return ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=ft.Border.all(1, PALE_BLUE),
            border_radius=18,
            padding=12,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
                controls=[
                    ft.Icon(icon, color=color, size=29),
                    self._text(value, 23, NAVY, bold=True),
                    self._text(label, 12, SOFT_BLUE),
                ],
            ),
        )

    def _summary_line(self, label, value, color=NAVY):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self._text(label, 16, NAVY, bold=True),
                self._text(value, 16, color, bold=True),
            ],
        )

    def _build_end(self):
        stats = self.session.summary()
        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Container(
                    bgcolor=CREAM,
                    padding=18,
                    border_radius=30,
                    shadow=_shadow(0.09, 14, 4),
                    content=ft.Column(
                        spacing=18,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.EMOJI_EVENTS, color=GREEN, size=72),
                            self._text("Practice Completed!", 27, bold=True),
                            self._text("Great job! You finished your practice.",
                                       15, SOFT_BLUE, max_lines=2),
                            ft.Row(spacing=10, controls=[
                                self._stat(ft.Icons.ACCESS_TIME, "Total Time",
                                           stats["time"], BLUE),
                                self._stat(ft.Icons.CHECK_CIRCLE_OUTLINE, "Completed",
                                           f'{stats["completed"]} / {stats["total"]}', GREEN),
                            ]),
                            ft.Row(spacing=10, controls=[
                                self._stat(ft.Icons.CANCEL_OUTLINED, "Wrong Answers",
                                           str(stats["errors"]), RED),
                                self._stat(ft.Icons.SKIP_NEXT, "Skips Used",
                                           str(stats["skips"]), SOFT_BLUE),
                            ]),
                            ft.Container(
                                padding=15,
                                bgcolor=WHITE,
                                border_radius=18,
                                content=ft.Column(spacing=13, controls=[
                                    self._summary_line("Correct on First Try",
                                                       f'{stats["first_try"]} / {stats["total"]}'),
                                    self._summary_line("XP Earned",
                                                       f'+{stats["xp_earned"]} XP', GREEN),
                                    self._summary_line("Total XP",
                                                       f'{stats["xp_total"]} XP'),
                                ]),
                            ),
                            self._menu_button("Practice Again", self._on_restart,
                                              primary=True),
                            ft.Container(
                                padding=8,
                                ink=True,
                                on_click=self._on_home,
                                content=self._text("Back to Home", 16, SOFT_BLUE,
                                                   bold=True),
                            ),
                        ],
                    ),
                ),
            ],
        )

    # ---------- Fondo exterior: imagen de nubes ----------

    def render(self):
        if self.mode == "closed":
            return
        self.timer_text.value = format_time(self.session.time_now())
        self.counter.value = f"{self.session.number} / {self.session.total}"

        builders = {
            "quiz": self._build_quiz,
            "paused": self._build_paused,
            "end": self._build_end,
        }
        content = builders[self.mode]()
        self.shell.width = self._width
        self.shell.height = self._height
        self.shell.content = ft.Stack(
            width=self._width,
            height=self._height,
            controls=[
                # Primera capa: fondo de nubes, detras de toda la vista.
                ft.Image(
                    src=FONDO_NUBES,
                    left=0,
                    top=0,
                    width=self._width,
                    height=self._height,
                    fit=ft.BoxFit.COVER,
                ),
                # Segunda capa: encabezado, hoja y controles interactivos.
                ft.Container(
                    left=0,
                    top=0,
                    width=self._width,
                    height=self._height,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    content=ft.SafeArea(content=content),
                ),
            ],
        )
        self.page.update()
