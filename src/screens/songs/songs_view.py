from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path

import flet as ft

from services.songs.songs_pronunciacion_service import (
    MAX_RECORD_SECONDS,
    listen_and_check,
    preload as preload_songs_model,
)

# AJUSTA esta ruta a donde pusiste la carpeta `exercises` (ej. ui/exercises).
from ui.exercises.core.exercise_screen import ExerciseScreen
from ui.exercises.components.exercise_microphone import exercise_microphone
from ui.exercises.overlays.pause_overlay import pause_overlay
from ui.exercises.overlays.results_overlay import results_screen
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

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "songs.json"
PALE_BLUE = "#ECF7FF"
PALE_YELLOW = "#FFF7DC"
MUTED = "#8194AE"

# Margen al reproducir una línea para no comerse el inicio/final de la frase.
LINE_PAD_BEFORE_MS = 150
LINE_PAD_AFTER_MS = 350

# Tiempo para que el control de audio exista en el cliente antes del primer play().
PLAYER_MOUNT_DELAY = 0.3
PLAY_RETRIES = 3

# Alto (sin escalar) de cada fila de la hoja de letra.
LYRIC_ROW_HEIGHT = 47
LYRIC_MAX_VISIBLE_ROWS = 5


def load_songs(path: Path = CATALOG_PATH) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        songs = data.get("songs", []) if isinstance(data, dict) else data
        return [
            s for s in songs
            if isinstance(s, dict)
            and (s.get("audio") or s.get("lines"))
        ]
    except (OSError, ValueError, TypeError) as exc:
        print(f"No se pudo cargar el catálogo Songs: {exc}")
        return []


# ---------- Pasos de práctica: líneas + párrafos + canción completa ----------

def _merged_step(kind: str, raw_lines: list[dict], indices: list[int], label: str) -> dict:
    """Crea un paso que une varias líneas (párrafo o canción completa)."""
    first, last = raw_lines[indices[0]], raw_lines[indices[-1]]
    start, end = first.get("start_ms"), last.get("end_ms")
    seconds = (end - start) / 1000 if start is not None and end is not None else 60
    return {
        "kind": kind,
        "label": label,
        "text": " ".join(raw_lines[i].get("text", "") for i in indices),
        "start_ms": start,
        "end_ms": end,
        "line_indices": list(indices),
        "max_seconds": max(15, min(seconds + 10, 300)),  # margen extra
    }


def build_steps(song: dict) -> list[dict]:
    """Líneas + párrafo al terminar cada grupo + canción completa al final.

    Agrupa líneas consecutivas con el mismo campo "group". Si un grupo tiene
    una sola línea no se crea paso de párrafo.
    """
    raw = [
        l if isinstance(l, dict) else {"text": str(l)}
        for l in song.get("lines", [])
    ]

    blocks: list[dict] = []
    for i, line in enumerate(raw):
        g = line.get("group")
        if blocks and g and blocks[-1]["group"] == g:
            blocks[-1]["indices"].append(i)
        else:
            blocks.append({"group": g, "indices": [i]})

    steps: list[dict] = []
    for block in blocks:
        for i in block["indices"]:
            steps.append({
                **raw[i],
                "kind": "line",
                "label": block["group"] or "Line",
                "line_indices": [i],
            })
        if block["group"] and len(block["indices"]) > 1:
            steps.append(_merged_step("group", raw, block["indices"], block["group"]))

    if len(raw) > 1:
        steps.append(_merged_step("song", raw, list(range(len(raw))), "Full song"))
    return steps


# Archivo donde se guarda el avance de cada canción (junto a songs.json).
PROGRESS_PATH = CATALOG_PATH.with_name("songs_progress.json")


def load_progress(path: Path = PROGRESS_PATH) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_progress(progress: dict, path: Path = PROGRESS_PATH) -> None:
    try:
        path.write_text(
            json.dumps(progress, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"No se pudo guardar el progreso de Songs: {exc}")


class SongsView:
    def __init__(self, page: ft.Page, on_home, songs=None, achievements=None):
        self.page = page
        self.on_home = on_home
        self.songs = songs if songs is not None else load_songs()
        self.song = None
        self.steps: list[dict] = []
        self.line_step_of: dict[int, int] = {}  # índice de línea -> índice de paso
        self.index = 0  # índice del PASO actual
        self.completed: set[int] = set()  # índices de pasos
        self.skipped: set[int] = set()    # índices de pasos
        self.rec_state = "idle"  # idle | recording | processing
        self._stop_event = threading.Event()
        self._elapsed = 0.0
        self._t0: float | None = None
        self.feedback: tuple[str, str] | None = None
        # catalog | practice | paused | finished | closed
        self.stage = "catalog"
        self._width = 440
        self._height = 844
        self.shell = ft.Container()
        self.player = None
        self.player_src = None
        self.playing = False
        self.audio_end_ms = None
        self._audio_token = 0
        self.achievements = achievements
        self.progress: dict = load_progress()

    # ---------- Progreso guardado ----------

    @staticmethod
    def _song_id(song) -> str:
        return str(song.get("id") or song.get("title") or "song")

    def _saved_for(self, song):
        """Devuelve el avance guardado de la canción, o None si no hay uno válido."""
        saved = self.progress.get(self._song_id(song))
        if not isinstance(saved, dict):
            return None
        total = len(build_steps(song))
        # Un avance guardado con otra cantidad de pasos (formato viejo) se ignora.
        if saved.get("total") != total:
            return None
        try:
            index = int(saved.get("index", 0))
        except (TypeError, ValueError):
            return None
        if not 0 <= index < total:
            return None
        return {
            "index": index,
            "completed": {i for i in saved.get("completed", []) if 0 <= i < total},
            "skipped": {i for i in saved.get("skipped", []) if 0 <= i < total},
            "elapsed": float(saved.get("elapsed", 0.0) or 0.0),
        }

    def _save_progress(self):
        if not self.song:
            return
        self.progress[self._song_id(self.song)] = {
            "total": len(self.steps),
            "index": self.index,
            "completed": sorted(self.completed),
            "skipped": sorted(self.skipped),
            "elapsed": round(self._time_now(), 1),
        }
        write_progress(self.progress)

    def _clear_progress(self, song):
        if self.progress.pop(self._song_id(song), None) is not None:
            write_progress(self.progress)

    # ---------- Estado auxiliar ----------

    @property
    def recognizing(self) -> bool:
        return self.rec_state != "idle"

    def _time_now(self) -> float:
        return self._elapsed + (time.monotonic() - self._t0 if self._t0 else 0.0)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        s = int(seconds)
        return f"{s // 60:02d}:{s % 60:02d}"

    # ---------- Ciclo de vida ----------

    def close(self):
        """Ciclo de vida compatible con close_current() de src/main.py.

        Detiene el audio y el micrófono, y desconecta el listener de resize.
        """
        if self.stage == "closed":
            return
        self.stage = "closed"
        self._stop_event.set()  # no dejar el micrófono abierto
        self.page.on_resize = None
        self.page.run_task(self._dispose_player)

    def show(self):
        self.stage = "catalog"
        self.page.clean()
        self.page.add(
            ft.Container(
                expand=True, bgcolor=PALE_BLUE,
                alignment=ft.Alignment.TOP_CENTER, content=self.shell,
            )
        )
        self.page.on_resize = self._fit
        self._fit(force=True)
        # Preparar Whisper antes de la primera grabación, sin bloquear Flet.
        preload_songs_model()

    def _fit(self, e=None, force=False):
        width = min(self.page.width or 440, 520)
        height = self.page.height or 844
        if (force or abs(width - self._width) > 1 or
                abs(height - self._height) > 1 or self.shell.content is None):
            self._width, self._height = width, height
            self.render()

    @property
    def scale(self):
        return max(0.58, min(1.0, self._width / 440, self._height / 844))

    # ---------- Componentes visuales ----------

    def _txt(self, value, size=16, bold=False, color=NAVY, centered=False,
             max_lines=None):
        return ft.Text(
            str(value), size=size * self.scale, color=color,
            weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            font_family=FONT, max_lines=max_lines,
            text_align=ft.TextAlign.CENTER if centered else ft.TextAlign.LEFT,
        )

    def _surface(self, content, color=WHITE, padding=15, radius=23):
        return ft.Container(
            bgcolor=color, border_radius=radius * self.scale,
            padding=padding * self.scale,
            border=ft.Border.all(1.5, "#D8EAFB"),
            shadow=ft.BoxShadow(
                blur_radius=9 * self.scale,
                offset=ft.Offset(0, 2 * self.scale), color="#142B77AE"),
            content=content,
        )

    def _button(self, label, icon, callback, primary=False, enabled=True,
                color=None):
        active_bg = color or (BLUE if primary else WHITE)
        fg = WHITE if primary or color else BLUE
        return ft.Container(
            height=49 * self.scale, expand=True,
            border_radius=16 * self.scale,
            alignment=ft.Alignment.CENTER,
            bgcolor=active_bg if enabled else "#E0E7F0",
            border=ft.Border.all(1, BLUE if enabled else "#CCD5E0"),
            ink=enabled, on_click=callback if enabled else None,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5 * self.scale,
                controls=[
                    ft.Icon(icon, size=19 * self.scale,
                            color=fg if enabled else MUTED),
                    self._txt(label, 15, True,
                              fg if enabled else MUTED),
                ],
            ),
        )

    def _header(self, title, subtitle=None, on_pause=None):
        right = (
            ft.Container(
                width=43 * self.scale, height=43 * self.scale,
                bgcolor=WHITE, border_radius=14 * self.scale,
                alignment=ft.Alignment.CENTER, ink=True, on_click=on_pause,
                content=ft.Icon(ft.Icons.PAUSE_ROUNDED, color=BLUE,
                                size=22 * self.scale),
            )
            if on_pause else
            ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color=BLUE,
                    size=31 * self.scale)
        )
        return ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10 * self.scale,
            controls=[
                ft.Container(
                    width=43 * self.scale, height=43 * self.scale,
                    bgcolor=WHITE, border_radius=14 * self.scale,
                    alignment=ft.Alignment.CENTER, ink=True,
                    on_click=self._back,
                    content=ft.Icon(ft.Icons.ARROW_BACK_ROUNDED,
                                    color=BLUE, size=22 * self.scale),
                ),
                ft.Column(
                    expand=True, spacing=1,
                    controls=[
                        self._txt(title, 22, True),
                        self._txt(subtitle, 12, False, SOFT_BLUE)
                        if subtitle else ft.Container(height=1),
                    ],
                ),
                right,
            ],
        )

    # ---------- Navegación ----------

    def _back(self, e=None):
        self.page.run_task(self._navigate_back)

    async def _navigate_back(self):
        self._stop_event.set()  # corta cualquier grabación en curso
        await self._dispose_player()
        if self.stage in ("practice", "paused", "finished"):
            self.stage = "catalog"
            self.song = None
            self.steps = []
            self.line_step_of = {}
            self.render()
        elif self.stage == "catalog":
            self.close()
            self.on_home()

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception:
            print(message)

    def _select_song(self, song, resume=False):
        # Al entrar a la práctica se detiene la vista previa completa.
        self.page.run_task(self._pause_audio)
        lines = song.get("lines", [])
        if not lines or not any(
            (isinstance(line, str) and line.strip()) or
            (isinstance(line, dict) and str(line.get("text", "")).strip())
            for line in lines
        ):
            self._toast("Add the song lyrics and line timings in src/data/songs.json to practice speaking.")
            return
        saved = self._saved_for(song) if resume else None
        self.song = song
        # Construir los pasos: líneas, párrafos y canción completa.
        self.steps = build_steps(song)
        self.line_step_of = {
            s["line_indices"][0]: n
            for n, s in enumerate(self.steps) if s["kind"] == "line"
        }
        self.completed.clear()
        self.skipped.clear()
        if saved:
            self.index = saved["index"]
            self.completed.update(saved["completed"])
            self.skipped.update(saved["skipped"])
            self._elapsed = saved["elapsed"]
        else:
            self.index = 0
            self._elapsed = 0.0
            self._clear_progress(song)  # empezar de cero borra el avance anterior
        self.feedback = None
        self.rec_state = "idle"
        self._t0 = time.monotonic()
        self.stage = "practice"
        self.render()
        # Reproduce automáticamente el primer paso al entrar a la práctica.
        # (Si no lo quieres, borra la siguiente línea.)
        self.page.run_task(self._on_listen_line)

    # ---------- Pantallas ----------

    def _catalog(self):
        song_cards = []
        for item in self.songs:
            has_lines = bool(item.get("lines"))
            has_audio = bool(item.get("audio"))
            info = (
                f'{len(item["lines"])} lines to practice'
                if has_lines else "Audio ready · lyrics not configured yet"
            )

            # La tarjeta de práctica y el reproductor son controles separados.
            # Esto evita entrar a una práctica con lista de líneas vacía.
            preview_button = self._button(
                "Play song" if has_audio else "No audio",
                ft.Icons.PLAY_CIRCLE_ROUNDED,
                lambda e, s=item: self.page.run_task(
                    self._play, s.get("audio", "")
                ),
                enabled=has_audio,
            )
            pause_button = self._button(
                "Pause", ft.Icons.PAUSE_CIRCLE_ROUNDED,
                self._pause_audio, enabled=has_audio,
            )
            saved = self._saved_for(item) if has_lines else None
            if saved:
                practice_label = f"Resume (step {saved['index'] + 1})"
            else:
                practice_label = "Practice lines" if has_lines else "Lyrics pending"
            practice_button = self._button(
                practice_label,
                ft.Icons.MIC_ROUNDED if has_lines else ft.Icons.LOCK_OUTLINE,
                lambda e, s=item: self._select_song(s, resume=True),
                primary=has_lines,
                enabled=has_lines,
            )
            restart_button = self._button(
                "Restart", ft.Icons.REPLAY_ROUNDED,
                lambda e, s=item: self._select_song(s),
            ) if saved else None

            song_cards.append(
                self._surface(
                    ft.Column(
                        spacing=11 * self.scale,
                        controls=[
                            ft.Row(
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(
                                        width=64 * self.scale,
                                        height=64 * self.scale,
                                        border_radius=18 * self.scale,
                                        bgcolor=PALE_YELLOW,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.HEADPHONES,
                                            color=BLUE, size=31 * self.scale,
                                        ),
                                    ),
                                    ft.Column(
                                        expand=True, spacing=4,
                                        controls=[
                                            self._txt(item.get("title", "Song"), 17, True),
                                            self._txt(item.get("artist", ""), 12, color=SOFT_BLUE),
                                            self._txt(info, 12, color=SOFT_BLUE,
                                                      max_lines=2),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Row(spacing=7 * self.scale, controls=[
                                preview_button, pause_button,
                            ]),
                            ft.Row(
                                spacing=7 * self.scale,
                                controls=[practice_button, restart_button]
                                if restart_button else [practice_button],
                            ),
                        ],
                    ),
                )
            )

        if not song_cards:
            song_cards = [self._surface(self._txt(
                "No songs found. Add songs to src/data/songs.json.",
                15, centered=True, max_lines=3,
            ))]

        return ft.Column(
            expand=True, spacing=15 * self.scale,
            controls=[
                self._header("Songs", "Choose a song to practice"),
                self._surface(ft.Column(spacing=6, controls=[
                    self._txt("Learn English with music", 20, True),
                    self._txt("Listen, repeat a line, and continue when you are ready.",
                              14, color=SOFT_BLUE, max_lines=3),
                ]), PALE_YELLOW),
                ft.Column(
                    expand=True, scroll=ft.ScrollMode.AUTO,
                    spacing=12 * self.scale, controls=song_cards,
                ),
            ],
        )

    def _visible_lines(self):
        lines = self.song["lines"]
        step = self.line
        if step["kind"] == "song":
            return list(enumerate(lines))  # todas (con scroll)
        if step["kind"] == "group":
            return [(i, lines[i]) for i in step["line_indices"]]
        # Una línea: un fragmento de hasta cinco, manteniendo visible la actual.
        cur = step["line_indices"][0]
        start = min(max(0, cur - 2), max(0, len(lines) - 5))
        return list(enumerate(lines[start:start + 5], start=start))

    def _lyric_sheet(self):
        step = self.line
        kind = step["kind"]
        visible = self._visible_lines()
        pieces = []
        for idx, raw in visible:
            text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
            # En la canción completa no se resalta ninguna línea en particular.
            is_active = kind != "song" and idx in step["line_indices"]
            sidx = self.line_step_of.get(idx)
            done = sidx in self.completed
            skipped = sidx in self.skipped
            pieces.append(ft.Container(
                height=LYRIC_ROW_HEIGHT * self.scale,
                bgcolor="#DBF0FF" if is_active else "#FFFFFF00",
                border_radius=13 * self.scale,
                padding=ft.Padding.symmetric(horizontal=10 * self.scale),
                alignment=ft.Alignment.CENTER_LEFT,
                content=ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=7 * self.scale,
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if done else
                            ft.Icons.SKIP_NEXT if skipped else
                            ft.Icons.MUSIC_NOTE if is_active else
                            ft.Icons.CIRCLE_OUTLINED,
                            color=GREEN if done else BLUE if is_active else MUTED,
                            size=18 * self.scale,
                        ),
                        ft.Container(expand=True, content=self._txt(
                            text, 14 if is_active else 12,
                            bold=is_active, color=NAVY if is_active else
                            GREEN if done else MUTED,
                            max_lines=2,
                        )),
                    ],
                ),
            ))

        column = ft.Column(spacing=1 * self.scale, controls=pieces)
        if kind != "line":
            # Párrafo / canción: alto fijo y scroll si hay más de 5 líneas.
            column.scroll = ft.ScrollMode.AUTO
            rows = min(len(pieces), LYRIC_MAX_VISIBLE_ROWS)
            column.height = rows * (LYRIC_ROW_HEIGHT + 1) * self.scale
        return self._surface(column, color="#FCFEFF", padding=10)

    @property
    def line(self):
        """Paso actual (línea, párrafo o canción completa)."""
        return self.steps[self.index]

    # ---------- Audio ----------

    async def _dispose_player(self):
        self._audio_token += 1  # cancela cualquier vigilante de segmento
        self.playing = False
        self.audio_end_ms = None
        player = self.player
        self.player = None
        self.player_src = None
        if player is not None:
            try:
                await player.pause()
                await player.release()
            except Exception as exc:
                print(f"Error al detener audio: {exc}")
            try:
                self.page.services.remove(player)
            except (ValueError, AttributeError):
                pass
            if self.stage != "closed":
                self.page.update()

    async def _play(self, src: str, start_ms=0, end_ms=None):
        if fta is None:
            self._toast("Install the audio plugin: uv add flet-audio")
            return
        if self.recognizing:
            return
        if not src:
            self._toast("Add your song audio path to songs.json first.")
            return

        if self.player is None or src != self.player_src:
            await self._dispose_player()
            self.player = fta.Audio(
                src=src, autoplay=False,
                release_mode=fta.ReleaseMode.STOP,
                on_position_change=self._on_audio_position,
                on_state_change=self._on_audio_state,
            )
            self.player_src = src
            self.page.services.append(self.player)
            self.page.update()
            # El control debe existir en el cliente antes del primer play().
            # Sin esta espera el primer click no suena y hay que pulsar dos veces.
            await asyncio.sleep(PLAYER_MOUNT_DELAY)

        player = self.player
        if player is None or self.stage == "closed":
            return

        self._audio_token += 1
        play_token = self._audio_token
        self.audio_end_ms = end_ms
        self.playing = True
        self.render()

        last_exc = None
        for _ in range(PLAY_RETRIES):  # reintenta por si el control aún no está listo
            try:
                await player.play(position=ft.Duration(milliseconds=int(start_ms)))
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                await asyncio.sleep(0.25)

        if last_exc is not None:
            self.playing = False
            self.render()
            print(f"Could not play {src}: {last_exc}")
            self._toast("Could not play this audio file. Check its path.")
            return

        if end_ms is not None:
            # on_position_change se dispara cada ~1s. Este vigilante consulta
            # la posición cada 0.15s para detener la frase con más precisión.
            self.page.run_task(self._watch_segment, play_token, player, int(end_ms))

    async def _watch_segment(self, token, player, end_ms):
        while token == self._audio_token and self.playing and self.player is player:
            await asyncio.sleep(0.15)
            try:
                pos = await player.get_current_position()
                if pos is None:
                    continue
                ms = int(pos.in_milliseconds)
                if ms >= end_ms:
                    self._audio_token += 1
                    self.playing = False
                    self.audio_end_ms = None
                    await player.pause()
                    if self.stage != "closed":
                        self.render()
                    break
            except Exception as exc:
                # Si el backend no permite consultar posición, el callback de
                # audio (aprox. 1s) sigue siendo la alternativa.
                print(f"Segment watcher: {exc}")
                break

    async def _on_audio_position(self, e):
        if not self.playing or self.audio_end_ms is None or self.player is None:
            return
        # La actualización de la posición llega aprox. cada segundo. Para cortes
        # exactos se recomiendan clips separados (propiedad 'clip').
        if int(e.position) >= self.audio_end_ms:
            self.playing = False
            try:
                await self.player.pause()
            except Exception:
                pass
            if self.stage != "closed":
                self.render()

    def _on_audio_state(self, e):
        # El fin natural de un clip requiere volver a habilitar Play.
        state_name = str(e.state).lower()
        if "completed" in state_name and self.playing:
            self.playing = False
            if self.stage != "closed":
                self.render()

    async def _on_listen_line(self, e=None):
        if self.song is None or self.stage not in ("practice", "paused"):
            return
        step = self.line
        # Las líneas pueden tener un clip propio; párrafos y canción no.
        clip = step.get("clip", "")
        if clip:
            await self._play(clip)
            return
        song_audio = self.song.get("audio", "")
        start, end = step.get("start_ms"), step.get("end_ms")
        if song_audio and start is not None and end is not None and end > start:
            await self._play(
                song_audio,
                max(0, start - LINE_PAD_BEFORE_MS),
                end + LINE_PAD_AFTER_MS,
            )
        else:
            self._toast("Configure a line clip or start_ms/end_ms in songs.json.")

    async def _on_full_song(self, e=None):
        await self._play(self.song.get("audio", ""))

    async def _pause_audio(self, e=None):
        if self.player is not None and self.playing:
            self._audio_token += 1
            self.playing = False
            try:
                await self.player.pause()
            except Exception:
                pass
            self.render()

    # ---------- Micrófono ----------

    async def _on_mic(self, e=None):
        if self.index in self.completed or self.index in self.skipped:
            return

        # Segundo toque: detener la grabación y procesar.
        if self.rec_state == "recording":
            self._stop_event.set()
            self.rec_state = "processing"
            self.feedback = ("busy", "Checking your pronunciation...")
            self.render()
            return

        # Ignorar toques mientras procesa.
        if self.rec_state != "idle":
            return

        # No grabar mientras la canción suena: evita que el reconocimiento
        # transcriba la música en lugar de la voz del estudiante.
        await self._pause_audio()
        recorded_index = self.index
        recorded_song = self.song
        step = self.line

        self._stop_event = threading.Event()
        self.rec_state = "recording"
        self.feedback = ("busy", "Recording... tap the microphone again when you finish.")
        self.render()
        try:
            success, recognized = await asyncio.to_thread(
                listen_and_check, step["text"], self._stop_event,
                step.get("max_seconds", MAX_RECORD_SECONDS), step["kind"],
            )
            if (self.stage not in ("practice", "paused")
                    or self.song is not recorded_song
                    or self.index != recorded_index):
                return
            if success:
                self.completed.add(self.index)
                self.feedback = ("ok", "Great pronunciation! You can continue.")
            else:
                heard = recognized or "nothing clearly"
                if len(heard) > 90:  # en párrafos/canción el texto puede ser largo
                    heard = heard[:90] + "..."
                self.feedback = ("error", f'I heard: "{heard}". Try again!')
        except Exception as exc:
            print(f"Song microphone error: {exc}")
            if self.stage == "practice" and self.song is recorded_song:
                self.feedback = ("error", "Microphone unavailable. Check permissions.")
        finally:
            self.rec_state = "idle"
            if self.stage == "practice" and self.song is recorded_song:
                self.render()

    # ---------- Acciones de práctica ----------

    async def _skip_line(self, e=None):
        if self.recognizing:
            return
        await self._pause_audio()
        self.skipped.add(self.index)
        self.feedback = ("skip", "Step skipped. It won't count as completed.")
        self._save_progress()
        self.render()

    async def _continue(self, e=None):
        if self.recognizing or (self.index not in self.completed and
                                self.index not in self.skipped):
            self._toast("First practice this step using the microphone.")
            return
        await self._dispose_player()
        self.feedback = None
        if self.index + 1 == len(self.steps):
            self._clear_progress(self.song)  # canción terminada: sin avance pendiente
            self.stage = "finished"
            self.render()
            return
        self.index += 1
        self._save_progress()
        self.render()                 # muestra primero el nuevo paso
        await self._on_listen_line()  # y reproduce su audio automáticamente

    # ---------- Pausa ----------

    async def _on_pause(self, e=None):
        if self.stage != "practice" or self.rec_state != "idle":
            return
        await self._pause_audio()
        self._elapsed = self._time_now()
        self._t0 = None
        self.stage = "paused"
        self.render()

    def _on_resume(self, e=None):
        self._t0 = time.monotonic()
        self.stage = "practice"
        self.render()

    def _on_finish_now(self, e=None):
        self._clear_progress(self.song)
        self.stage = "finished"
        self.render()

    def _on_save_exit(self, e=None):
        # Guarda el avance y vuelve al catálogo.
        self._save_progress()
        self._back()

    # ---------- Pantalla de práctica ----------

    def _practice(self):
        total = len(self.steps)
        step = self.line
        kind = step["kind"]

        if kind == "line":
            active, tag, size = step["text"], "YOUR LINE", 22
            listen_label = "Listen line"
        elif kind == "group":
            active = f'{step["label"]} · {len(step["line_indices"])} lines'
            tag, size, listen_label = "NOW THE WHOLE PARAGRAPH", 20, "Listen paragraph"
        else:
            active, tag, size = "Sing the full song!", "FINAL CHALLENGE", 20
            listen_label = "Listen song"

        can_advance = self.index in self.completed or self.index in self.skipped
        status = self.feedback
        status_color = GREEN if status and status[0] == "ok" else (
            RED if status and status[0] == "error" else SOFT_BLUE)
        if status:
            status_text = status[1]
        elif kind == "line":
            status_text = "Tap Listen, then tap the microphone, repeat the line and tap again."
        elif kind == "group":
            status_text = "Now say the whole paragraph in one go. Tap the microphone to start and again to finish."
        else:
            status_text = "Last challenge: say or sing the whole song. Tap the microphone to start and again to finish."

        return ft.Column(
            expand=True,
            spacing=11 * self.scale,
            controls=[
                self._header(self.song.get("title", "Songs"),
                             f"{step['label']}  •  Step {self.index + 1} of {total}",
                             on_pause=self._on_pause),
                ft.ProgressBar(
                    value=len(self.completed | self.skipped) / total,
                    color=BLUE, bgcolor="#D6EAF8",
                    bar_height=8 * self.scale,
                    border_radius=6 * self.scale,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        self._txt("LYRICS · FOLLOW ALONG", 13, True, SOFT_BLUE),
                        self._txt(f"{len(self.completed)} correct", 13, True, GREEN),
                    ],
                ),
                self._lyric_sheet(),
                self._surface(ft.Column(
                    spacing=9 * self.scale,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._txt(tag, 12, True, BLUE, centered=True),
                        ft.Container(
                            height=72 * self.scale,
                            alignment=ft.Alignment.CENTER,
                            content=self._txt(active, size, True, NAVY,
                                              centered=True, max_lines=3),
                        ),
                        ft.Row(spacing=9 * self.scale, controls=[
                            self._button(listen_label, ft.Icons.VOLUME_UP_ROUNDED,
                                         self._on_listen_line, enabled=not self.recognizing),
                            self._button("Play song" if not self.playing else "Pause",
                                         ft.Icons.PLAY_CIRCLE if not self.playing else
                                         ft.Icons.PAUSE_CIRCLE,
                                         self._on_full_song if not self.playing else
                                         self._pause_audio,
                                         enabled=not self.recognizing),
                        ]),
                    ],
                ), color=PALE_YELLOW),
                ft.Container(
                    height=48 * self.scale,
                    alignment=ft.Alignment.CENTER,
                    content=self._txt(status_text, 13, True, status_color,
                                      centered=True, max_lines=2),
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.BOTTOM_CENTER,
                    content=ft.Column(
                        tight=True,
                        spacing=10 * self.scale,
                        controls=[
                            ft.Container(
                                height=67 * self.scale,
                                alignment=ft.Alignment.CENTER,
                                # Micrófono compartido con los demás ejercicios.
                                content=exercise_microphone(
                                    None if can_advance else self._on_mic,
                                    recording=self.rec_state == "recording",
                                    scale=self.scale,
                                    size=67,
                                ),
                            ),
                            ft.Row(spacing=10 * self.scale, controls=[
                                self._button("Skip", ft.Icons.SKIP_NEXT,
                                             self._skip_line,
                                             enabled=not (self.recognizing or can_advance)),
                                self._button("Finish" if self.index + 1 == total
                                             else "Continue",
                                             ft.Icons.CHEVRON_RIGHT,
                                             self._continue, primary=True,
                                             enabled=can_advance and not self.recognizing),
                            ]),
                        ],
                    ),
                ),
            ],
        )

    def _finished(self):
        """Pantalla final compartida (misma que los demás ejercicios)."""
        def indices(kind):
            return [i for i, s in enumerate(self.steps) if s["kind"] == kind]

        def done(kind):
            return sum(1 for i in indices(kind) if i in self.completed)

        lines_total = len(indices("line"))
        groups_total = len(indices("group"))
        song_idx = indices("song")
        if not song_idx:
            song_value = "—"
        elif song_idx[0] in self.completed:
            song_value = "Done"
        else:
            song_value = "Skipped"

        return results_screen(
            title="Song practice finished!",
            subtitle=self.song.get("title", "Song"),
            stats=[
                (ft.Icons.CHECK_CIRCLE_OUTLINE, "Lines completed",
                 f"{done('line')} / {lines_total}", GREEN),
                (ft.Icons.LIBRARY_MUSIC, "Paragraphs completed",
                 f"{done('group')} / {groups_total}", GREEN),
                (ft.Icons.EMOJI_EVENTS, "Full song", song_value, SOFT_BLUE),
                (ft.Icons.SKIP_NEXT, "Skipped steps",
                 str(len(self.skipped)), SOFT_BLUE),
            ],
            retry_label="Try again",
            exit_label="Song list",
            on_retry=lambda e: self._select_song(self.song),
            on_exit=self._back,
            width=self._width,
            height=self._height,
        )

    # ---------- Render ----------

    def _screen(self, content):
        return ExerciseScreen(
            content,
            width=self._width,
            height=self._height,
            padding=ft.Padding.symmetric(horizontal=17 * self.scale,
                                         vertical=15 * self.scale),
        )

    def render(self):
        if self.stage == "closed":
            return
        self.shell.width = self._width
        self.shell.height = self._height
        if self.stage == "finished":
            # results_screen ya trae fondo y área segura.
            self.shell.content = self._finished()
        elif self.stage == "catalog":
            self.shell.content = self._screen(self._catalog())
        else:  # practice | paused
            screen = self._screen(self._practice())
            if self.stage == "paused":
                screen = ft.Stack(
                    width=self._width,
                    height=self._height,
                    controls=[screen, pause_overlay(
                        question_text=f"Step {self.index + 1} / {len(self.steps)}",
                        time_text=self._fmt_time(self._time_now()),
                        on_resume=self._on_resume,
                        on_finish=self._on_finish_now,
                        on_save_exit=self._on_save_exit,
                        width=self._width,
                        height=self._height,
                    )],
                )
            self.shell.content = screen
        self.page.update()