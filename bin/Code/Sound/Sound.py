import collections
import functools
import os
import threading
import time
import wave
from io import BytesIO

from PySide6 import QtCore, QtMultimedia, QtWidgets

import Code
from Code.SQL import UtilSQL
from Code.Translations import TrListas
from Code.Z import Util

_Status = QtMultimedia.QSoundEffect.Status


class SoundDispatcher(QtCore.QObject):
    """Objeto auxiliar para redirigir llamadas desde hilos secundarios al hilo GUI."""

    sig_play_key = QtCore.Signal(str, bool)
    sig_play_list = QtCore.Signal(list)
    sig_reset = QtCore.Signal()
    sig_beep = QtCore.Signal()
    sig_invalidate = QtCore.Signal(str)  # "" = todas las claves


class RunSound(QtCore.QObject):
    """Reproductor de sonidos.

    Diseño:
    - Un QSoundEffect por clave (pool LRU de MAX_EFFECTS), con la fuente cargada una sola vez.
      Un fichero problemático solo afecta a su propia clave.
    """

    MAX_PENDING_SOUNDS = 16
    MAX_ABSOLUTE_SOUND_MS = 15000
    WATCHDOG_OFFSET_MS = 1000
    MAX_EFFECTS = 32

    def __init__(self):
        super().__init__()

        # Garantiza que el objeto (y sus hijos) viven en el hilo GUI
        app = QtWidgets.QApplication.instance()
        if app is not None and self.thread() is not app.thread():
            self.moveToThread(app.thread())

        # Caché: clave -> (bytes, duración_ms). Protegida por lock (accesible desde cualquier hilo)
        self.dic_sounds = {}
        self._missing = set()  # claves sin sonido en la BD (caché negativa)
        self._cache_lock = threading.RLock()
        self._relations = None
        self.move_sounds_preloaded = False

        # Estado del hilo GUI
        self._pending = collections.deque(maxlen=self.MAX_PENDING_SOUNDS)
        self._effects = collections.OrderedDict()  # clave -> QSoundEffect (LRU)
        self._bad_keys = set()  # claves cuyo efecto dio Error
        self._warmup = collections.deque()

        self._current_effect = None
        self._current_key = None
        self._current_started_at = None
        self._seen_playing = False  # hemos visto isPlaying() == True para el sonido actual
        self._waiting_ready = False  # play() pendiente de que el efecto esté Ready

        self._watchdog = QtCore.QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog)

        # Redirección thread-safe
        self._dispatcher = SoundDispatcher(self)
        queued = QtCore.Qt.ConnectionType.QueuedConnection
        self._dispatcher.sig_play_key.connect(self._slot_play_key, queued)
        self._dispatcher.sig_play_list.connect(self._slot_play_list, queued)
        self._dispatcher.sig_reset.connect(self._slot_reset, queued)
        self._dispatcher.sig_beep.connect(self._slot_beep, queued)
        self._dispatcher.sig_invalidate.connect(self._slot_invalidate, queued)

        # Cambios en los dispositivos de audio (auriculares, bluetooth, suspensión...)
        self._media_devices = None
        try:
            self._media_devices = QtMultimedia.QMediaDevices(self)
            self._media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)
        except Exception:
            pass

        # Se publica al final, cuando el objeto está completamente construido
        Code.runSound = self

    # ------------------------------------------------------------------ utilidades

    def _in_gui_thread(self):
        return QtCore.QThread.currentThread() == self.thread()

    @property
    def current(self):
        """Compatibilidad: efecto que está sonando (o None)."""
        return self._current_effect

    @classmethod
    def _wav_info(cls, wav):
        """Devuelve (duración_ms, canales, sampwidth, framerate) o None si el WAV no es válido."""
        try:
            with wave.open(BytesIO(wav)) as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                channels = wf.getnchannels()
                width = wf.getsampwidth()
        except Exception:
            return None
        if frames <= 0 or rate <= 0:
            return None
        mseconds = min(1000.0 * frames / rate, cls.MAX_ABSOLUTE_SOUND_MS)
        return mseconds, channels, width, rate

    @staticmethod
    def _write_atomic(path, data):
        """Escritura atómica: un corte no deja un fichero truncado."""
        Util.create_folder(os.path.dirname(path))
        tmp = f"{path}.tmp"
        with open(tmp, "wb") as q:
            q.write(data)
        os.replace(tmp, path)

    @staticmethod
    def _same_content(path, data):
        try:
            if os.path.getsize(path) != len(data):
                return False
            with open(path, "rb") as q:
                return q.read() == data
        except OSError:
            return False

    @staticmethod
    def _default_output_name():
        try:
            return QtMultimedia.QMediaDevices.defaultAudioOutput().description()
        except Exception:
            return "?"

    # ------------------------------------------------------------------ caché de sonidos

    def preload_move_sounds(self):
        """Precarga los sonidos de movimiento estándar (bytes) y, si estamos en el hilo GUI,
        va creando los efectos de forma escalonada para no penalizar el arranque."""
        if self.move_sounds_preloaded:
            return
        keys = list("abcdefgh12345678KQRBNP") + ["x", "+", "#", "=", "O-O", "O-O-O", "MC"]
        with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db:
            for key in keys:
                self._load_sound(key, db)
        self.move_sounds_preloaded = True

        if self._in_gui_thread():
            self._warmup.extend(keys)
            self._warmup_step()

    def _warmup_step(self):
        if not self._warmup:
            return
        key = self._warmup.popleft()
        if len(self._effects) < self.MAX_EFFECTS:
            self._get_effect(key)
        if self._warmup:
            QtCore.QTimer.singleShot(0, self._warmup_step)

    def _load_sound(self, key, db=None):
        """Carga un sonido desde la BD a la caché. Seguro desde cualquier hilo.
        Devuelve (bytes, duración_ms) o (None, 0)."""
        with self._cache_lock:
            cached = self.dic_sounds.get(key)
            if cached is not None:
                return cached
            if key in self._missing:
                return None, 0

            try:
                if db is None:
                    with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db_:
                        wav = db_.get(key)
                else:
                    wav = db.get(key)
            except Exception:
                # Error transitorio (BD bloqueada...): no se cachea para reintentar
                # log.exception("Error leyendo el sonido %r de la BD", key)
                return None, 0

            if not wav:
                self._missing.add(key)
                return None, 0

            info = self._wav_info(wav)
            if info is None:
                # log.warning("WAV inválido para la clave %r (%d bytes)", key, len(wav))
                self._missing.add(key)
                return None, 0

            self.dic_sounds[key] = (wav, info[0])
            return self.dic_sounds[key]

    def clear_cache(self):
        """Olvida la caché (bytes, claves ausentes, claves con error) y recrea los efectos."""
        with self._cache_lock:
            self.dic_sounds.clear()
            self._missing.clear()
        self._invalidate("")

    # ------------------------------------------------------------------ pool de efectos (hilo GUI)

    def _get_effect(self, key):
        """Devuelve el QSoundEffect de la clave (creándolo si hace falta) o None."""
        effect = self._effects.get(key)
        if effect is not None:
            self._effects.move_to_end(key)
            return effect
        if key in self._bad_keys:
            return None

        wav, _ = self._load_sound(key)
        if not wav:
            return None

        path = self._ensure_file(key, wav)
        if path is None:
            return None

        effect = QtMultimedia.QSoundEffect(self)
        effect.playingChanged.connect(functools.partial(self._on_playing_changed, effect))
        effect.statusChanged.connect(functools.partial(self._on_status_changed, effect, key))
        effect.setSource(QtCore.QUrl.fromLocalFile(path))
        self._effects[key] = effect
        self._trim_effects()
        return effect

    def _ensure_file(self, key, wav):
        """Garantiza que el WAV está en disco y coincide (en tamaño) con la BD."""
        path = self.path_wav(key)
        if path is None:
            return None
        try:
            if not (os.path.isfile(path) and os.path.getsize(path) == len(wav)):
                self._write_atomic(path, wav)
            return path
        except OSError:
            # log.exception("No se pudo escribir %s", path)
            return None

    def _trim_effects(self):
        while len(self._effects) > self.MAX_EFFECTS:
            for key, effect in self._effects.items():
                if effect is not self._current_effect:
                    self._discard_effect(key)
                    break
            else:
                break

    def _discard_effect(self, key):
        effect = self._effects.pop(key, None)
        if effect is not None:
            self._dispose(effect)

    def _discard_all_effects(self):
        effects = list(self._effects.values())
        self._effects.clear()
        self._cleanup_current()
        for effect in effects:
            self._dispose(effect)

    def _dispose(self, effect):
        if effect is self._current_effect:
            self._cleanup_current()
        try:
            effect.stop()
        except Exception:
            pass
        effect.deleteLater()

    def _mark_bad(self, key, effect):
        """Marca la clave como defectuosa y descarta su efecto."""
        self._bad_keys.add(key)
        if self._effects.get(key) is effect:
            del self._effects[key]
        self._dispose(effect)

    # ------------------------------------------------------------------ máquina de reproducción (hilo GUI)

    @QtCore.Slot()
    def siguiente(self):
        """Procesa el siguiente sonido de la cola. Seguro desde cualquier hilo."""
        if not self._in_gui_thread():
            QtCore.QMetaObject.invokeMethod(self, "siguiente", QtCore.Qt.ConnectionType.QueuedConnection)
            return

        if self._current_effect is not None:
            return

        while self._pending:
            key = self._pending.popleft()
            effect = self._get_effect(key)
            if effect is None:
                continue
            if self._start(key, effect):
                return
            self._beep()

    def _schedule_next(self):
        """Evita llamar a siguiente() dentro de la emisión de una señal del propio efecto."""
        QtCore.QTimer.singleShot(0, self.siguiente)

    def _start(self, key, effect):
        status = effect.status()
        if status == _Status.Error:
            # log.warning("Efecto en Error al iniciar %r", key)
            self._mark_bad(key, effect)
            return False

        self._current_effect = effect
        self._current_key = key
        self._current_started_at = time.monotonic()
        self._seen_playing = False
        self._waiting_ready = status != _Status.Ready  # Loading / Null: play() cuando esté Ready

        mseconds = self.dic_sounds.get(key, (None, self.MAX_ABSOLUTE_SOUND_MS))[1]
        self._watchdog.start(int(mseconds) + self.WATCHDOG_OFFSET_MS)

        if not self._waiting_ready:
            effect.play()
        return True

    def _cleanup_current(self):
        self._watchdog.stop()
        self._current_effect = None
        self._current_key = None
        self._current_started_at = None
        self._seen_playing = False
        self._waiting_ready = False

    def _finish_current(self):
        self._cleanup_current()
        self._schedule_next()

    def _on_playing_changed(self, effect):
        # Señales de efectos que no son el actual (obsoletos, descartados) se ignoran
        if effect is not self._current_effect:
            return
        if effect.isPlaying():
            self._seen_playing = True
        elif self._seen_playing:
            # Solo damos por terminado si antes lo vimos sonando (evita falsos fines)
            self._finish_current()

    def _on_status_changed(self, effect, key):
        status = effect.status()
        if effect is not self._current_effect:
            if status == _Status.Error:
                # log.warning("Efecto en Error (no activo): %r", key)
                self._mark_bad(key, effect)
            return

        if status == _Status.Ready and self._waiting_ready:
            self._waiting_ready = False
            effect.play()
        elif status == _Status.Error:
            # log.warning("Efecto en Error durante la reproducción: %r", key)
            self._mark_bad(key, effect)
            self._beep()
            self._schedule_next()

    def _on_watchdog(self):
        """La reproducción actual no terminó a tiempo: el backend se considera colgado.
        No se mira isPlaying(): justo en ese caso es cuando hay que actuar."""
        if self._current_effect is None:
            return
        # elapsed = time.monotonic() - (self._current_started_at or time.monotonic())
        # log.warning(
        #     "Watchdog: clave=%r estado=%s isPlaying=%s visto_sonando=%s esperando_ready=%s "
        #     "transcurrido=%.2fs salida=%s",
        #     self._current_key,
        #     effect.status(),
        #     effect.isPlaying(),
        #     self._seen_playing,
        #     self._waiting_ready,
        #     elapsed,
        #     self._default_output_name(),
        # )
        self._discard_all_effects()
        self._schedule_next()

    def _on_audio_outputs_changed(self):
        # log.info("Dispositivos de salida cambiados; salida por defecto: %s", self._default_output_name())
        self._bad_keys.clear()
        self._discard_all_effects()
        if self._pending:
            self._schedule_next()

    @staticmethod
    def _beep():
        QtWidgets.QApplication.beep()

    # ------------------------------------------------------------------ slots de despacho (hilo GUI)

    def _enqueue(self, key):
        """Encola; si la cola está llena, la deque descarta el elemento más antiguo."""
        self._pending.append(key)

    @QtCore.Slot(str, bool)
    def _slot_play_key(self, key, start):
        wav, _ = self._load_sound(key)
        if not wav:
            return False
        self._enqueue(key)
        if start:
            self.siguiente()
        return True

    @QtCore.Slot(list)
    def _slot_play_list(self, keys):
        for key in keys:
            self._enqueue(key)
        if self._pending:
            self.siguiente()

    @QtCore.Slot()
    def _slot_reset(self):
        self._pending.clear()
        effect = self._current_effect
        self._cleanup_current()  # antes de stop(): así playingChanged(False) se ignora
        if effect is not None:
            try:
                effect.stop()
            except Exception:
                pass

    @QtCore.Slot()
    def _slot_beep(self):
        self._beep()

    @QtCore.Slot(str)
    def _slot_invalidate(self, key):
        if key:
            self._bad_keys.discard(key)
            self._discard_effect(key)
        else:
            self._bad_keys.clear()
            self._discard_all_effects()

    def _invalidate(self, key):
        if self._in_gui_thread():
            self._slot_invalidate(key)
        else:
            self._dispatcher.sig_invalidate.emit(key)

    # ------------------------------------------------------------------ API pública (cualquier hilo)

    def play_key(self, key, start=True):
        """Reproduce un sonido por su clave. Desde hilos secundarios devuelve True si se despachó."""
        if not self._in_gui_thread():
            self._dispatcher.sig_play_key.emit(key, start)
            return True
        return self._slot_play_key(key, start)

    def play_list(self, li):
        """Encola y reproduce secuencialmente una lista de claves. True si hay algo que sonar."""
        keys = [key for key in li if self._load_sound(key)[0]]
        if not keys:
            return False
        if self._in_gui_thread():
            self._slot_play_list(keys)
        else:
            self._dispatcher.sig_play_list.emit(keys)
        return True

    def play_list_seconds(self, li):
        """Como play_list, pero devuelve la duración total estimada en segundos (0.0 si no hay nada)."""
        keys = [key for key in li if self._load_sound(key)[0]]
        if not keys:
            return 0.0
        secs = sum(self._load_sound(key)[1] for key in keys) / 1000.0
        self.play_list(keys)
        return secs

    def reset(self):
        """Vacía la cola y detiene el sonido actual."""
        if self._in_gui_thread():
            self._slot_reset()
        else:
            self._dispatcher.sig_reset.emit()

    def beep(self):
        if self._in_gui_thread():
            self._beep()
        else:
            self._dispatcher.sig_beep.emit()

    def _play_or_beep(self, key):
        if self._load_sound(key)[0]:
            self.play_key(key)
        else:
            self.beep()

    def play_zeitnot(self):
        self.play_key("ZEITNOT")

    def play_error(self):
        self._play_or_beep("ERROR")

    def play_beep(self):
        self._play_or_beep("MC")

    # ------------------------------------------------------------------ gestión de ficheros

    def save_wav(self, key, wav):
        """Guarda o actualiza un WAV en disco. Devuelve False si el WAV no es válido."""
        valid = self._wav_info(wav) is not None
        # if not valid:
        #     log.warning("save_wav: WAV inválido para la clave %r", key)
        with self._cache_lock:
            self.dic_sounds.pop(key, None)
            self._missing.discard(key)
        path = self.path_wav(key)
        if path:
            self._write_atomic(path, wav)
        self._invalidate(key)
        return valid

    def remove_wav(self, key):
        """Elimina la caché, el efecto y el archivo físico de un sonido."""
        with self._cache_lock:
            self.dic_sounds.pop(key, None)
            self._missing.discard(key)
        path = self.path_wav(key)
        if path is not None:
            Util.remove_file(path)
        self._invalidate(key)

    def sync_wavs_with_database(self):
        """Sincroniza los archivos del disco con el contenido de la base de datos."""
        folder_sounds = Code.configuration.paths.folder_sounds()
        Util.create_folder(folder_sounds)
        expected_files = set()

        with UtilSQL.DictSQL(Code.configuration.paths.file_sounds(), "general") as db:
            for key in db.keys():
                try:
                    wav = db[key]
                except Exception:
                    # log.exception("Error leyendo %r de la BD", key)
                    continue
                if not wav:
                    continue
                path_wav = self.path_wav(key)
                if path_wav is None:
                    continue
                expected_files.add(os.path.basename(path_wav))
                try:
                    if not (os.path.isfile(path_wav) and self._same_content(path_wav, wav)):
                        self._write_atomic(path_wav, wav)
                except OSError:
                    # log.exception("No se pudo sincronizar %s", path_wav)
                    pass

        try:
            with os.scandir(folder_sounds) as it:
                entries = [e for e in it if e.is_file()]
        except OSError:
            entries = []

        for entry in entries:
            name = entry.name.lower()
            stale_wav = name.endswith(".wav") and entry.name not in expected_files
            if stale_wav or name.endswith(".wav.tmp"):
                try:
                    os.remove(entry.path)
                except OSError:
                    # log.exception("No se pudo borrar %s", entry.path)
                    pass

        self.clear_cache()

    def path_wav(self, key):
        """Obtiene la ruta local completa a partir de la relación."""
        rel = self.relations.get(key)
        if rel is None:
            return None
        folder_sounds = Code.configuration.paths.folder_sounds()
        return Util.opj(folder_sounds, f"{rel['WAV_KEY']}.wav")

    @property
    def relations(self):
        if self._relations is None:
            self._relations = self._build_relations()
        return self._relations

    @staticmethod
    def _build_relations():
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
