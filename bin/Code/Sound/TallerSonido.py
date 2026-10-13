import time
import wave
from io import BytesIO

from PySide6 import QtCore, QtMultimedia
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

import Code
from Code.QT import QTUtils, FormLayout, Iconos


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
