from __future__ import annotations

import asyncio
import json
from pathlib import Path

import flet as ft

from services.songs.songs_pronunciacion_service import (
    RECORD_SECONDS as SONG_RECORD_SECONDS,
    listen_and_check,
    preload as preload_songs_model,
)
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

ASSET_BACKGROUND = "imagenes/fondo_nubes.png"
CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "songs.json"
PALE_BLUE = "#ECF7FF"
PALE_YELLOW = "#FFF7DC"
MUTED = "#8194AE"


def load_songs(path: Path = CATALOG_PATH) -> list[dict]:
    """Lee el catálogo; admite canciones sin letra para escuchar el MP3."""
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


class SongsView:
    def __init__(self, page: ft.Page, on_home, songs=None):
        self.page = page
        self.on_home = on_home
        self.songs = songs if songs is not None else load_songs()
        self.song = None
        self.index = 0
        self.completed: set[int] = set()
        self.skipped: set[int] = set()
        self.recognizing = False
        self.feedback: tuple[str, str] | None = None
        self.stage = "catalog"  # catalog | practice | finished | closed
        self._width = 440
        self._height = 844
        self.shell = ft.Container()
        self.player = None
        self.player_src = None
        self.playing = False
        self.audio_end_ms = None
        self._audio_token = 0

    def close(self):
        """Ciclo de vida compatible con close_current() de src/main.py.

        Detiene el audio y desconecta el listener de resize al salir.
        """
        if self.stage == "closed":
            return
        self.stage = "closed"
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

    def _header(self, title, subtitle=None):
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
                ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color=BLUE,
                        size=31 * self.scale),
            ],
        )

    def _back(self, e=None):
        self.page.run_task(self._navigate_back)

    async def _navigate_back(self):
        await self._dispose_player()
        if self.stage == "practice" or self.stage == "finished":
            self.stage = "catalog"
            self.song = None
            self.render()
        elif self.stage == "catalog":
            self.close()
            self.on_home()

    def _toast(self, message):
        try:
            self.page.show_dialog(ft.SnackBar(content=ft.Text(message)))
        except Exception:
            print(message)

    def _select_song(self, song):
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
        self.song = song
        self.index = 0
        self.completed.clear()
        self.skipped.clear()
        self.feedback = None
        self.recognizing = False
        self.stage = "practice"
        self.render()

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
            practice_button = self._button(
                "Practice lines" if has_lines else "Lyrics pending",
                ft.Icons.MIC_ROUNDED if has_lines else ft.Icons.LOCK_OUTLINE,
                lambda e, s=item: self._select_song(s),
                primary=has_lines,
                enabled=has_lines,
            )

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
                            ft.Row(controls=[practice_button]),
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
        # Un fragmento de hasta cinco líneas, manteniendo visible la actual.
        start = min(max(0, self.index - 2), max(0, len(lines) - 5))
        return list(enumerate(lines[start:start + 5], start=start))

    def _lyric_sheet(self):
        pieces = []
        for idx, raw in self._visible_lines():
            text = raw.get("text", "") if isinstance(raw, dict) else str(raw)
            is_active = idx == self.index
            done = idx in self.completed
            skipped = idx in self.skipped
            pieces.append(ft.Container(
                height=47 * self.scale,
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
        return self._surface(
            ft.Column(spacing=1 * self.scale, controls=pieces),
            color="#FCFEFF", padding=10,
        )

    @property
    def line(self):
        raw = self.song["lines"][self.index]
        return raw if isinstance(raw, dict) else {"text": str(raw)}

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
        self._audio_token += 1
        play_token = self._audio_token
        self.audio_end_ms = end_ms
        self.playing = True
        self.render()
        try:
            await self.player.play(position=ft.Duration(milliseconds=int(start_ms)))
            if end_ms is not None:
                # on_position_change se dispara cada ~1s. Este vigilante consulta
                # la posición cada 0.15s para detener la frase con más precisión.
                self.page.run_task(self._watch_segment, play_token, self.player, int(end_ms))
        except Exception as exc:
            self.playing = False
            self.render()
            print(f"Could not play {src}: {exc}")
            self._toast("Could not play this audio file. Check its path.")

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
        line = self.line
        clip = line.get("clip", "")
        if clip:
            await self._play(clip)
            return
        song_audio = self.song.get("audio", "")
        start, end = line.get("start_ms"), line.get("end_ms")
        if song_audio and start is not None and end is not None and end > start:
            await self._play(song_audio, start, end)
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

    async def _on_mic(self, e=None):
        if self.recognizing or self.index in self.completed or self.index in self.skipped:
            return
        # No grabar mientras la canción suena: evita que el reconocimiento
        # transcriba la música en lugar de la voz del estudiante.
        await self._pause_audio()
        recorded_index = self.index
        recorded_song = self.song
        self.recognizing = True
        self.feedback = ("busy", f"Listening to your voice... ({SONG_RECORD_SECONDS} s)")
        self.render()
        try:
            result = await asyncio.to_thread(listen_and_check, self.line["text"])
            success, recognized = result
            if self.stage != "practice" or self.song is not recorded_song or self.index != recorded_index:
                return
            if success:
                self.completed.add(self.index)
                self.feedback = ("ok", "Great pronunciation! You can continue.")
            else:
                heard = recognized or "nothing clearly"
                self.feedback = ("error", f'I heard: "{heard}". Try again!')
        except Exception as exc:
            print(f"Song microphone error: {exc}")
            if self.stage == "practice" and self.song is recorded_song:
                self.feedback = ("error", "Microphone unavailable. Check permissions.")
        finally:
            self.recognizing = False
            if self.stage == "practice" and self.song is recorded_song:
                self.render()

    async def _skip_line(self, e=None):
        if self.recognizing:
            return
        await self._pause_audio()
        self.skipped.add(self.index)
        self.feedback = ("skip", "Line skipped. It won't count as completed.")
        self.render()

    async def _continue(self, e=None):
        if self.recognizing or (self.index not in self.completed and
                                self.index not in self.skipped):
            self._toast("First practice this line using the microphone.")
            return
        await self._dispose_player()
        self.feedback = None
        if self.index + 1 == len(self.song["lines"]):
            self.stage = "finished"
        else:
            self.index += 1
        self.render()

    def _practice(self):
        lines = self.song["lines"]
        total = len(lines)
        active = self.line["text"]
        can_advance = self.index in self.completed or self.index in self.skipped
        status = self.feedback
        status_color = GREEN if status and status[0] == "ok" else (
            RED if status and status[0] == "error" else SOFT_BLUE)
        status_text = status[1] if status else "Tap Listen, then repeat the line aloud."
        return ft.Column(
            expand=True,
            spacing=11 * self.scale,
            controls=[
                self._header(self.song.get("title", "Songs"),
                             f"Line {self.index + 1} of {total}  •  Speaking"),
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
                        self._txt("YOUR LINE", 12, True, BLUE, centered=True),
                        ft.Container(
                            height=72 * self.scale,
                            alignment=ft.Alignment.CENTER,
                            content=self._txt(active, 22, True, NAVY,
                                              centered=True, max_lines=3),
                        ),
                        ft.Row(spacing=9 * self.scale, controls=[
                            self._button("Listen line", ft.Icons.VOLUME_UP_ROUNDED,
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
                                content=ft.Container(
                                    width=67 * self.scale,
                                    height=67 * self.scale,
                                    bgcolor=RED if self.recognizing else BLUE,
                                    border_radius=40 * self.scale,
                                    alignment=ft.Alignment.CENTER,
                                    ink=not (self.recognizing or can_advance),
                                    on_click=None if (self.recognizing or can_advance)
                                    else self._on_mic,
                                    content=ft.Icon(ft.Icons.MIC_ROUNDED,
                                                    color=WHITE, size=34 * self.scale),
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
        total = len(self.song["lines"])
        return ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16 * self.scale,
            controls=[
                ft.Icon(ft.Icons.EMOJI_EVENTS_ROUNDED, color="#F4B83E",
                        size=95 * self.scale),
                self._txt("Song practice finished!", 26, True, centered=True),
                self._surface(ft.Column(
                    spacing=13 * self.scale,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._txt(self.song.get("title", "Song"), 21, True,
                                  centered=True),
                        self._txt(f"{len(self.completed)} / {total} lines completed",
                                  20, True, GREEN, centered=True),
                        self._txt(f"{len(self.skipped)} skipped lines",
                                  15, color=SOFT_BLUE),
                    ],
                )),
                ft.Row(spacing=10, controls=[
                    self._button("Song list", ft.Icons.LIST,
                                 self._back),
                    self._button("Try again", ft.Icons.REPLAY_ROUNDED,
                                 lambda e: self._select_song(self.song), primary=True),
                ]),
            ],
        )

    def render(self):
        if self.stage == "closed":
            return
        self.shell.width = self._width
        self.shell.height = self._height
        content = {
            "catalog": self._catalog,
            "practice": self._practice,
            "finished": self._finished,
        }[self.stage]()
        self.shell.content = ft.Stack(
            width=self._width, height=self._height,
            controls=[
                ft.Image(src=ASSET_BACKGROUND, fit=ft.BoxFit.COVER,
                         width=self._width, height=self._height,
                         left=0, top=0),
                ft.Container(
                    left=0, top=0,
                    width=self._width, height=self._height,
                    padding=ft.Padding.symmetric(horizontal=17 * self.scale,
                                                 vertical=15 * self.scale),
                    content=ft.SafeArea(content=content),
                ),
            ],
        )
        self.page.update()
