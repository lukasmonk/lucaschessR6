import os
import queue
import time
import wave
from io import BytesIO

from PySide6 import QtCore, QtMultimedia, QtWidgets
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

import Code
from Code.QT import QTUtils, FormLayout, Iconos
from Code.SQL import UtilSQL
from Code.Translations import TrListas
from Code.Z import Util

DATABASE = "D"
PLAY_ESPERA = "P"
PLAY_SINESPERA = "N"
STOP = "S"
TERMINAR = "T"


class RunSound:
    """
    Reproduce el modelo de reproducción de Lichess a nivel de arquitectura:
    los WAV se cargan/preparan una vez, pero cada reproducción usa una nueva
    instancia de QSoundEffect. Así, una instancia cuyo estado interno quede
    atascado no puede bloquear futuras reproducciones del mismo sonido.
    """

    MAX_PENDING_SOUNDS = 64
    MAX_WATCHDOG_MS = 5000

    def __init__(self):
        Code.runSound = self
        self.replay = None
        self.replayBeep = None
        self.replayError = None
        self.dic_sounds = {}
        self.queue = queue.Queue(maxsize=self.MAX_PENDING_SOUNDS)
        self.current = None
        self.current_started_at = None
        self.playback_generation = 0
        self.working = False
        self.move_sounds_preloaded = False
        self._active_effects = set()

    def preload_move_sounds(self):
        if self.move_sounds_preloaded:
            return
        with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db:
            keys = "abcdefgh12345678KQRBNP"
            keys += "x+#="
            for key in keys:
                self._load_sound(key, db)
            for key in ("O-O", "O-O-O"):
                self._load_sound(key, db)
            self._load_sound("MC", db)
        self.move_sounds_preloaded = True

    def _load_sound(self, key, db=None):
        if key in self.dic_sounds:
            return self.dic_sounds[key]

        if db is None:
            with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db:
                wav = db.get(key)
        else:
            wav = db[key]

        if not wav:
            self.dic_sounds[key] = None, 0
            return None, 0

        with wave.open(BytesIO(wav)) as wf:
            try:
                mseconds = 1000.0 * wf.getnframes() / wf.getframerate()
            except (ZeroDivisionError, wave.Error):
                mseconds = 0

        if mseconds <= 0:
            self.dic_sounds[key] = None, 0
            return None, 0

        folder_sounds = Code.configuration.paths.folder_sounds()
        Util.create_folder(folder_sounds)
        path_wav = self.path_wav(key)
        with open(path_wav, "wb") as q:
            q.write(wav)

        # Se conserva una instancia preparada como marcador/cache de que el
        # sonido existe. No se reutiliza para reproducirlo: cada play crea una
        # instancia independiente, como un AudioBufferSource de Web Audio.
        template = QtMultimedia.QSoundEffect(self._qt_parent())
        template.setSource(QtCore.QUrl.fromLocalFile(path_wav))
        self.dic_sounds[key] = (template, mseconds)
        return self.dic_sounds[key]

    def _new_effect(self, key):
        template, mseconds = self._load_sound(key)
        if template is None or mseconds <= 0:
            return None, 0

        effect = QtMultimedia.QSoundEffect(self._qt_parent())
        effect.setSource(template.source())
        effect.setVolume(template.volume())
        self._active_effects.add(effect)
        return effect, mseconds

    @staticmethod
    def _qt_parent():
        app = QtWidgets.QApplication.instance()
        return app

    def _finish_playback(self, effect, stop=False):
        if effect is not self.current:
            self._active_effects.discard(effect)
            effect.deleteLater()
            return

        self.current = None
        self.current_started_at = None
        if stop:
            try:
                effect.stop()
            except RuntimeError:
                pass
        self._active_effects.discard(effect)
        effect.deleteLater()
        self.siguiente()

    def _sound_status_changed(self, key, effect):
        if effect.status() == QtMultimedia.QSoundEffect.Status.Error:
            self._finish_playback(effect, stop=True)

    def _sound_playing_changed(self, key, effect):
        if effect is self.current and not effect.isPlaying():
            self._finish_playback(effect)

    def siguiente(self):
        if self.current is not None:
            return

        while True:
            try:
                key = self.queue.get_nowait()
            except queue.Empty:
                self.working = False
                return

            try:
                effect, mseconds = self._new_effect(key)
            except Exception:
                continue

            if effect is None or mseconds <= 0:
                continue

            self.current = effect
            self.current_started_at = time.monotonic()
            self.playback_generation += 1
            generation = self.playback_generation
            effect.statusChanged.connect(
                lambda k=key, e=effect: self._sound_status_changed(k, e))
            effect.playingChanged.connect(
                lambda k=key, e=effect: self._sound_playing_changed(k, e))

            try:
                effect.play()
            except Exception:
                self._finish_playback(effect, stop=True)
                return

            timeout_ms = min(int(mseconds) + 1000, self.MAX_WATCHDOG_MS)
            QtCore.QTimer.singleShot(
                timeout_ms,
                lambda e=effect, g=generation: self._watchdog(e, g))
            return

    def _watchdog(self, effect, generation):
        if self.current is effect and self.playback_generation == generation:
            # Detener también el efecto antiguo antes de liberar la cola.
            # Aunque su señal de fin no llegue, la siguiente reproducción
            # utiliza otra instancia y no hereda su estado.
            self._finish_playback(effect, stop=True)

    def play_key(self, key, start=True):
        app = QtWidgets.QApplication.instance()
        if app is not None and QtCore.QThread.currentThread() is not app.thread():
            QtCore.QMetaObject.invokeMethod(
                app,
                lambda k=key, s=start: self.play_key(k, s),
                QtCore.Qt.ConnectionType.QueuedConnection)
            return True

        effect, mseconds = self._load_sound(key)
        if effect is not None and mseconds > 0:
            try:
                self.queue.put_nowait(key)
            except queue.Full:
                return False
            if start:
                self.working = True
                self.siguiente()
            return True
        return False

    def save_wav(self, key, wav):
        self.dic_sounds.pop(key, None)
        folder_sounds = Code.configuration.paths.folder_sounds()
        Util.create_folder(folder_sounds)
        path_wav = self.path_wav(key)
        with open(path_wav, "wb") as q:
            q.write(wav)

    def sync_wavs_with_database(self):
        folder_sounds = Code.configuration.paths.folder_sounds()
        Util.create_folder(folder_sounds)
        expected_files = set()

        with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db:
            for key in db.keys():
                wav = db[key]
                if not wav:
                    continue
                path_wav = self.path_wav(key)
                expected_files.add(os.path.basename(path_wav))
                with open(path_wav, "wb") as q:
                    q.write(wav)

        for entry in os.scandir(folder_sounds):
            if entry.is_file() and entry.name.lower().endswith(".wav") and entry.name not in expected_files:
                os.remove(entry.path)

    def remove_wav(self, key):
        self.dic_sounds.pop(key, None)
        Util.remove_file(self.path_wav(key))

    def path_wav(self, key):
        folder_sounds = Code.configuration.paths.folder_sounds()
        return Util.opj(folder_sounds, f"{self.relations[key]['WAV_KEY']}.wav")

    def reset(self):
        self.working = False
        self.queue = queue.Queue(maxsize=self.MAX_PENDING_SOUNDS)
        effect = self.current
        self.current = None
        self.current_started_at = None
        for active in list(self._active_effects):
            try:
                active.stop()
            except RuntimeError:
                pass
            active.deleteLater()
        self._active_effects.clear()
        if effect:
            try:
                effect.stop()
            except RuntimeError:
                pass

    def play_list(self, li):
        for key in li:
            self.play_key(key, False)
        if not self.queue.empty():
            self.working = True
            self.siguiente()
            return True
        return False

    def play_list_seconds(self, li):
        secs = 0.0
        for key in li:
            self.play_key(key, False)
            secs += self.dic_sounds.get(key, (None, 0))[1]
        if not self.queue.empty():
            self.working = True
            self.siguiente()
            return secs
        return 0.0

    def play_zeitnot(self):
        self.play_key("ZEITNOT")

    def play_error(self):
        self.play_key("ERROR")
        if self.dic_sounds.get("ERROR", (None, 0))[0] is None:
            QtWidgets.QApplication.beep()

    def play_beep(self):
        self.play_key("MC")
        if self.dic_sounds.get("MC", (None, 0))[0] is None:
            QtWidgets.QApplication.beep()

    @property
    def relations(self):
        dic = {}

        def add(key, txt, wav_key):
            dic[key] = {"NAME": txt, "WAV_KEY": key if wav_key is None else wav_key}

        add("MC", _("Beep after move"), "BEEP")
        add("ERROR", _("Error"), "ERROR")
        add("ZEITNOT", _("Zeitnot"), "ZEITNOT")
        add("GANAMOS", _("You win"), "WIN")
        add("GANARIVAL", _("Opponent wins"), "LOST")
        add("TABLAS", _("Stalemate"), "STALEMATE")
        add("TABLASREPETICION", _("Draw by threefold repetition"), "DRAW_THREEFOLD")
        add("TABLAS50", _("Draw by fifty-move rule"), "DRAW_FIFTYRULE")
        add("TABLASFALTAMATERIAL", _("Draw by insufficient material"), "DRAW_MATERIAL")
        add("GANAMOSTIEMPO", _("You win on time"), "WIN_TIME")
        add("GANARIVALTIEMPO", _("Opponent has won on time"), "LOST_TIME")
        add("OFRECETABLAS", _("Opponent offers draw"), "OFFERS_DRAW")
        add("OFRECERESIGNAR", _("Opponent offers resignation"), "OFFERS_RESIGN")

        for c in "abcdefgh12345678":
            add(c, c, f"COORD_{c}")

        d = TrListas.dic_nom_pieces()
        for c in "KQRBNP":
            add(c, d[c], f"PIECE_{c}")

        add("O-O", _("Short castling"), "SHORT_CASTLING")
        add("O-O-O", _("Long castling"), "LONG_CASTLING")
        add("=", _("Promote to"), "PROMOTE_TO")
        add("x", _("Capture"), "CAPTURE")
        add("+", _("Check"), "CHECK")
        add("#", _("Checkmate"), "CHECKMATE")
        return dic

def msc(hundreds_of_second):
    t = hundreds_of_second
    cent = t % 100
    t //= 100
    mins = t // 60
    t -= mins * 60
    seg = t
    return mins, seg, cent


class TallerSonido:
    FORMAT = 16
    CHANNELS = 2
    SAMPLE_RATE = 22500
    audio_input = None
    datos: list
    io_device = None
    qsound: QtMultimedia.QSoundEffect
    cent_desde: int
    cent_hasta: int
    ini_time: float

    def __init__(self, owner, wav):
        self.wav = wav

        self.owner = owner
        self.datos = []

        if not wav:
            self.hundreds_of_second = 0
        else:
            f = BytesIO(self.wav)

            wf = wave.open(f)
            self.hundreds_of_second = int(round(100.0 * wf.getnframes() / wf.getframerate(), 0))
            wf.close()

    def with_data(self):
        return self.wav is not None

    def reset_to_0(self):
        self.wav = None
        self.hundreds_of_second = 0

    def mic_start(self):
        format_audio = QAudioFormat()
        format_audio.setSampleRate(self.SAMPLE_RATE)
        format_audio.setChannelCount(self.CHANNELS)
        format_audio.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        input_devices = QMediaDevices.audioInputs()
        if not input_devices:
            return False
        device = input_devices[0]
        self.audio_input = QAudioSource(device, format_audio, self.owner)
        self.datos = []
        self.io_device = self.audio_input.start()
        self.io_device.readyRead.connect(self.mic_record)
        return True

    def lin2alaw(self, data: bytes, width: int) -> bytes:
        """
        Convierte PCM lineal (signed) a A-Law.
        width: ancho en bytes de cada muestra (normalmente 2).
        """
        if width != 2:
            raise ValueError("Solo se soporta width=2 (16-bit PCM)")
        out = bytearray()
        for i in range(0, len(data), width):
            sample = int.from_bytes(data[i: i + 2], "little", signed=True)
            out.append(self._linear2alaw_sample(sample))
        return bytes(out)

    def alaw2lin(self, data: bytes, width: int) -> bytes:
        """
        Convierte A-Law a PCM lineal (signed).
        width: ancho en bytes de cada muestra de salida (normalmente 2).
        """
        if width != 2:
            raise ValueError("Solo se soporta width=2 (16-bit PCM)")
        out = bytearray()
        for code in data:
            sample = self._alaw2linear_sample(code)
            out += sample.to_bytes(2, "little", signed=True)
        return bytes(out)

    @staticmethod
    def _linear2alaw_sample(sample: int) -> int:
        """Convierte un entero PCM16 a un byte A-Law."""
        clip = 32635

        sign = 0x00
        pcm_val = sample
        if pcm_val >= 0:
            sign = 0x80
        else:
            pcm_val = -pcm_val - 1

        pcm_val = min(pcm_val, clip)

        if pcm_val >= 256:

            def _search(val: int) -> int:
                """Devuelve la posición del bit más significativo."""
                for i in range(7):
                    if val <= (0x1F << i):
                        return i
                return 7

            exponent = _search(pcm_val >> 8)
            mantissa = (pcm_val >> (exponent + 3)) & 0x0F
            compressed_val = (exponent << 4) | mantissa
        else:
            compressed_val = pcm_val >> 4

        compressed_val ^= 0x55
        return compressed_val | sign

    @staticmethod
    def _alaw2linear_sample(a_val: int) -> int:
        """Convierte un byte A-Law a un entero PCM16."""
        a_val ^= 0x55
        sign = a_val & 0x80
        exponent = (a_val & 0x70) >> 4
        mantissa = a_val & 0x0F

        if exponent == 0:
            sample = (mantissa << 4) + 8
        else:
            sample = ((mantissa << 4) + 0x108) << (exponent - 1)

        return sample if sign else -sample

    def mic_record(self):
        self.datos.append(bytes(self.io_device.readAll()))

    def mic_end(self):
        self.audio_input.stop()

        frames = b"".join(self.datos)
        io = BytesIO()
        wf = wave.open(io, "wb")
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.FORMAT // 8)
        wf.setframerate(self.SAMPLE_RATE)
        wf.writeframes(frames)
        self.wav = io.getvalue()
        self.hundreds_of_second = round(100.0 * wf.getnframes() / wf.getframerate(), 0)
        wf.close()

    def read_wav_from_disk(self, file):
        try:
            wf = wave.open(file, "rb")
            self.hundreds_of_second = round(100.0 * wf.getnframes() / wf.getframerate(), 0)
            wf.close()
            f = open(file, "rb")
            self.wav = f.read()
            f.close()
            return True
        except:
            self.wav = None
            self.hundreds_of_second = 0
            return False

    def play(self, cent_desde, cent_hasta):
        io_wav = self.io_wav(cent_desde, cent_hasta)
        path_wav = Code.configuration.temporary_file("wav")
        with open(path_wav, "wb") as q:
            q.write(io_wav)
        self.qsound = QtMultimedia.QSoundEffect()
        self.qsound.setSource(QtCore.QUrl.fromLocalFile(path_wav))
        self.qsound.play()

        self.cent_desde = cent_desde
        self.cent_hasta = cent_hasta
        self.ini_time = time.monotonic()
        self.playing()

    def playing(self):
        if self.owner.is_canceled():
            return
        t1 = time.monotonic()
        hundreds_of_second = (t1 - self.ini_time) * 100 + self.cent_desde
        try:
            if hundreds_of_second >= self.cent_hasta:
                hundreds_of_second = self.cent_desde
            self.owner.mesa.pon_centesimas_actual(hundreds_of_second)
            QTUtils.refresh_gui()
            if not self.owner.siPlay:
                self.qsound.stop()
            elif self.qsound.isPlaying():
                QtCore.QTimer.singleShot(100, self.playing)
        except RuntimeError:
            self.qsound.stop()

    def io_wav(self, cent_desde, cent_hasta):
        f = BytesIO(self.wav)

        wf = wave.open(f, "rb")
        nchannels, sampwidth, framerate, nframes, comptype, compname = wf.getparams()

        kfc = 1.0 * wf.getframerate() / 100.0  # n. de frames por cada centesima
        min_frame = int(kfc * cent_desde)
        max_frame = int(kfc * cent_hasta)

        wf.setpos(min_frame)
        frames = wf.readframes(max_frame - min_frame)
        wf.close()

        io = BytesIO()
        wf = wave.open(io, "wb")
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(frames)
        data = io.getvalue()
        wf.close()

        return data

    def recorta(self, cent_desde, cent_hasta):
        self.wav = self.io_wav(cent_desde, cent_hasta)
        self.hundreds_of_second = cent_hasta - cent_desde


def config_sonido(owner):
    configuration = Code.configuration
    form = FormLayout.FormLayout(owner, _("Configuration"), Iconos.S_Play(), minimum_width=440)
    form.separador()
    form.apart(_("After each opponent move"))
    form.checkbox(_("Sound a beep"), configuration.x_sound_beep)
    form.checkbox(_("Play customised sounds"), configuration.x_sound_move)
    form.separador()
    form.checkbox(_("The same for player moves"), configuration.x_sound_our)
    form.separador()
    form.checkbox(_("Tournaments between engines"), configuration.x_sound_tournements)
    form.separador()
    form.apart(_("When finishing the game"))
    form.checkbox(_("Play customised sounds for the result"), configuration.x_sound_results)
    form.separador()
    form.separador()
    form.apart(_("Others"))
    form.checkbox(_("Play a beep when there is an error in tactic trainings"), configuration.x_sound_error)
    form.separador()
    form.add_tab(_("Sounds"))
    resultado = form.run()
    if resultado:
        (
            configuration.x_sound_beep,
            configuration.x_sound_move,
            configuration.x_sound_our,
            configuration.x_sound_tournements,
            configuration.x_sound_results,
            configuration.x_sound_error,
        ) = resultado[1][0]
        configuration.graba()
