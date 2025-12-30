import os
import queue
import time
import wave
from io import BytesIO

from PySide6 import QtCore, QtMultimedia, QtWidgets
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

import Code
from Code import Util
from Code.QT import QTUtils
from Code.SQL import UtilSQL
from Code.Translations import TrListas

DATABASE = "D"
PLAY_ESPERA = "P"
PLAY_SINESPERA = "N"
STOP = "S"
TERMINAR = "T"


class RunSound:
    def __init__(self):
        Code.runSound = self
        self.replay = None
        self.replayBeep = None
        self.replayError = None
        self.dic_sounds = {}

        self.queue = queue.Queue()
        self.current = None

        self.working = False

    def siguiente(self):
        if not self.queue.empty():
            if self.current and self.current.isPlaying():
                QtCore.QTimer.singleShot(50, self.siguiente)
                return
            key = self.queue.get()
            self.current, mseconds = self.dic_sounds[key]
            self.current.play()
            if not self.queue.empty():
                QtCore.QTimer.singleShot(mseconds, self.siguiente)
                return

    def play_key(self, key, start=True):
        played = False
        if key not in self.dic_sounds:
            name_wav = self.relations[key]["WAV_KEY"] + ".wav"
            path_wav = Util.opj(Code.configuration.paths.folder_sounds(), name_wav)
            if os.path.isfile(path_wav):
                wf = wave.open(path_wav)
                seconds = 1000.0 * wf.getnframes() / wf.getframerate()
                wf.close()
                qsound = QtMultimedia.QSoundEffect()
                qsound.setSource(QtCore.QUrl.fromLocalFile(path_wav))
                self.dic_sounds[key] = (qsound, seconds)
                played = True
            else:
                self.dic_sounds[key] = (None, 0)
                return False
        else:
            seconds = self.dic_sounds[key][1]

        if seconds > 0:
            self.queue.put(key)
            if start:
                self.siguiente()
        return played

    def write_sounds(self):
        configuration = Code.configuration
        folder_sounds = configuration.paths.folder_sounds()

        Util.create_folder(folder_sounds)

        for entry in os.scandir(folder_sounds):
            os.remove(entry.path)

        with UtilSQL.DictSQL(configuration.paths.file_sounds(), "general") as db:
            for key in db.keys():
                wav = self.relations[key]["WAV_KEY"] + ".wav"
                path_wav = Util.opj(folder_sounds, wav)
                with open(path_wav, "wb") as q:
                    q.write(db[key])

    def save_wav(self, key, wav):
        folder_sounds = Code.configuration.paths.folder_sounds()
        path_wav = Util.opj(folder_sounds, self.relations[key]["WAV_KEY"] + ".wav")
        with open(path_wav, "wb") as q:
            q.write(wav)

    def remove_wav(self, key):
        folder_sounds = Code.configuration.paths.folder_sounds()
        path_wav = Util.opj(folder_sounds, self.relations[key]["WAV_KEY"] + ".wav")
        Util.remove_file(path_wav)

    def path_wav(self, key):
        folder_sounds = Code.configuration.paths.folder_sounds()
        return Util.opj(folder_sounds, self.relations[key]["WAV_KEY"] + ".wav")

    def read_sounds(self):
        configuration = Code.configuration
        folder_sounds = configuration.paths.folder_sounds()

        if not os.path.isdir(folder_sounds):
            self.write_sounds()

    def close(self):
        self.working = False
        if self.current:
            self.current.stop()
        self.queue = queue.Queue()

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
            secs += self.dic_sounds[key][1]
        if not self.queue.empty():
            self.working = True
            self.siguiente()
            return secs
        return 0.0

    def play_zeinot(self):
        self.play_key("ZEITNOT")

    def playError(self):
        self.play_key("ERROR")
        if self.dic_sounds["ERROR"][0] is None:
            QtWidgets.QApplication.beep()

    def playBeep(self):
        self.play_key("MC")
        if self.dic_sounds["MC"][0] is None:
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

        for c in "abcdefgh12345678":
            add(c, c, "COORD_" + c)

        d = TrListas.dic_nom_pieces()
        for c in "KQRBNP":
            add(c, d[c], "PIECE_" + c)

        add("O-O", _("Short castling"), "SHORT_CASTLING")
        add("O-O-O", _("Long castling"), "LONG_CASTLING")
        add("=", _("Promote to"), "PROMOTE_TO")
        add("x", _("Capture"), "CAPTURE")
        add("+", _("Check"), "CHECK")
        add("#", _("Checkmate"), "CHECKMATE")

        return dic


def msc(centesimas):
    t = centesimas
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

        if not wav:
            self.centesimas = 0
        else:
            f = BytesIO(self.wav)

            wf = wave.open(f)
            self.centesimas = int(round(100.0 * wf.getnframes() / wf.getframerate(), 0))
            wf.close()

    def with_data(self):
        return self.wav is not None

    def reset_to_0(self):
        self.wav = None
        self.centesimas = 0

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

    def lin2alaw(self, data: bytes, width: int) -> bytes:
        """
        Convierte PCM lineal (signed) a A-Law.
        width: ancho en bytes de cada muestra (normalmente 2).
        """
        if width != 2:
            raise ValueError("Solo se soporta width=2 (16-bit PCM)")
        out = bytearray()
        for i in range(0, len(data), width):
            sample = int.from_bytes(data[i : i + 2], "little", signed=True)
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

        if pcm_val > clip:
            pcm_val = clip

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
        self.datos.append(self.io_device.readAll())

    def mic_end(self):
        self.audio_input.stop()

        resp = b"".join(self.datos)
        tx = self.lin2alaw(resp, 2)
        frames = self.alaw2lin(tx, 2)
        io = BytesIO()
        wf = wave.open(io, "wb")
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.FORMAT // 8)
        wf.setframerate(self.SAMPLE_RATE)
        wf.writeframes(frames)
        self.wav = io.getvalue()
        self.centesimas = round(100.0 * wf.getnframes() / wf.getframerate(), 0)
        wf.close()

    def read_wav_from_disk(self, file):
        try:
            wf = wave.open(file, "rb")
            self.centesimas = round(100.0 * wf.getnframes() / wf.getframerate(), 0)
            wf.close()
            f = open(file, "rb")
            self.wav = f.read()
            f.close()
            return True
        except:
            self.wav = None
            self.centesimas = 0
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
        self.ini_time = time.time()
        self.playing()

    def playing(self):
        if self.owner.is_canceled:
            return
        t1 = time.time()
        centesimas = (t1 - self.ini_time) * 100 + self.cent_desde
        try:
            if centesimas >= self.cent_hasta:
                centesimas = self.cent_desde
            self.owner.mesa.ponCentesimasActual(centesimas)
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
        self.centesimas = cent_hasta - cent_desde
