import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None


class SoundEffects:
    CORRECT = "audio/effects/correct_answer.wav"
    WRONG = "audio/effects/wrong_answer.wav"
    FINISH = "audio/effects/finish.wav"

    def __init__(self, page: ft.Page, enabled: bool = True):
        self.page = page
        self.enabled = enabled
        self._players = {"fx": None, "voice": None}

    # ---------- Metodos simples (los que usaras en los ejercicios) ----------

    def correct(self):
        self._play("fx", self.CORRECT)

    def wrong(self):
        self._play("fx", self.WRONG)

    def finish(self):
        self._play("fx", self.FINISH)

    def voice(self, src):
        """Audio de la palabra u otro audio hablado."""
        self._play("voice", src)

    def stop(self):
        """Quita ambos reproductores (llamar al cerrar el ejercicio)."""
        for channel in self._players:
            self._remove(channel)

    # ---------- Internos ----------

    def _remove(self, channel):
        player = self._players.get(channel)
        if player is not None:
            try:
                if player in self.page.services:
                    self.page.services.remove(player)
            except Exception:
                pass
            self._players[channel] = None

    def _play(self, channel, src):
        if not self.enabled or fta is None or not src:
            return
        try:
            self._remove(channel)
            player = fta.Audio(src=src, autoplay=True)
            self.page.services.append(player)
            self._players[channel] = player
            self.page.update()
        except Exception as err:
            print(f"No se pudo reproducir {src}: {err}")