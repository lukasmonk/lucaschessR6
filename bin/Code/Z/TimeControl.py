import time
from enum import Enum, auto

from Code.Base.Constantes import INFINITE


class TimeMode(Enum):
    """
    Modos estándar de control de tiempo en ajedrez.

    SUDDEN_DEATH   : Tiempo fijo, sin incremento. Se acaba → pierde.
                     Ej: 5min, 10min, 30min
    FISCHER        : Tiempo base + incremento por jugada (ya implementado como seconds_per_move).
                     Ej: 5min + 3s/mov  (el más común en online)
    BRONSTEIN      : El incremento solo se devuelve si no se usó todo el tiempo del turno.
                     A diferencia de Fischer, el reloj nunca supera el tiempo inicial del turno.
                     Ej: 5min + 3s Bronstein
    DELAY_SIMPLE   : Cuenta atrás se retrasa N segundos antes de empezar a correr.
                     Usado en torneos OTB (over the board) americanos.
                     Ej: 30min + 5s delay
    HOURGLASS      : El tiempo que gasta un jugador se añade al reloj del rival.
                     Ej: ambos con 5min, se transfiere segundo a segundo.
    MOVES_IN_TIME  : N movimientos en X tiempo, luego se añade tiempo extra (time bonus).
                     Ej: 40 movimientos en 90min, luego +30min para el resto.
                     El más usado en torneos clásicos FIDE.
    HANDICAP       : Tiempos distintos para cada bando (ver HANDICAPS).
    """

    SUDDEN_DEATH = auto()
    FISCHER = auto()
    BRONSTEIN = auto()
    DELAY_SIMPLE = auto()
    HOURGLASS = auto()
    MOVES_IN_TIME = auto()
    HANDICAP = auto()


class TimeControl:
    def __init__(self, window, game, side):
        self.window = window
        self.game = game
        self.side = side

        self.total_time = 0.0
        self.pending_time = 0.0
        self.seconds_per_move = 0.0  # incremento Fischer / Bronstein / delay
        self.zeitnot_marker = 0.0

        self.time_init = None
        self.show_clock = False
        self.time_paused = 0.0
        self.time_previous = 0.0

        self.pending_time_initial = 0

        self.set_clock_side = window.set_clock_white if side else window.set_clock_black
        self.is_displayed = True

        # -- Modo de tiempo
        self.time_mode = TimeMode.SUDDEN_DEATH

        # -- Bronstein: guarda el tiempo al inicio del turno
        self._bronstein_turn_start = 0.0

        # -- Delay simple: retardo antes de que corra el reloj
        self._delay_remaining = 0.0
        self._delay_active = False

        # -- Moves in time (control por fases FIDE)
        self.moves_in_time_phases = []  # lista de (num_moves, secs, bonus_secs)
        self._current_phase = 0
        self._moves_in_phase = 0  # movimientos jugados en la fase actual

        # -- Hourglass: referencia al reloj del rival --------------------------
        self._opponent_clock = None  # se asigna desde fuera con set_opponent

    # -- Configuración ---------------------------------------------------------

    def set_displayed(self, is_displayed):
        self.is_displayed = is_displayed

    def set_opponent(self, opponent_clock):
        """Necesario solo para el modo Hourglass."""
        self._opponent_clock = opponent_clock

    def config_clock(self, total_time, seconds_per_move, zeinot_marker, secs_extra):
        """Configuración base (compatibilidad con código existente)."""
        self.pending_time = self.total_time = total_time + secs_extra
        self.seconds_per_move = seconds_per_move if seconds_per_move else 0
        self.zeitnot_marker = zeinot_marker if zeinot_marker else 0
        self.show_clock = total_time > 0.0
        self.time_mode = TimeMode.FISCHER if seconds_per_move else TimeMode.SUDDEN_DEATH

    def config_fischer(self, base_secs, increment_secs, zeitnot=0):
        """
        Tiempo base + incremento por jugada (Bobby Fischer, 1988).
        El incremento se suma AL PARAR el reloj, antes de pasarlo al rival.
        Ej: config_fischer(300, 3)  →  5min + 3s/mov
        """
        self.time_mode = TimeMode.FISCHER
        self.pending_time = self.total_time = float(base_secs)
        self.seconds_per_move = float(increment_secs)
        self.zeitnot_marker = zeitnot
        self.show_clock = True

    def config_bronstein(self, base_secs, delay_secs, zeitnot=0):
        """
        Tiempo base + delay Bronstein (David Bronstein, 1989).
        El tiempo del turno se descuenta solo si superas el delay.
        El reloj nunca sube por encima del tiempo al inicio del turno.
        Ej: config_bronstein(300, 5)  →  5min + 5s Bronstein
        """
        self.time_mode = TimeMode.BRONSTEIN
        self.pending_time = self.total_time = float(base_secs)
        self.seconds_per_move = float(delay_secs)
        self.zeitnot_marker = zeitnot
        self.show_clock = True

    def config_delay(self, base_secs, delay_secs, zeitnot=0):
        """
        Delay simple (US Chess Federation).
        El reloj no corre durante los primeros delay_secs de cada turno.
        A diferencia de Bronstein, el tiempo no consumido en el delay
        NO se acumula: simplemente no descuenta.
        Ej: config_delay(1800, 5)  →  30min + 5s delay
        """
        self.time_mode = TimeMode.DELAY_SIMPLE
        self.pending_time = self.total_time = float(base_secs)
        self.seconds_per_move = float(delay_secs)
        self._delay_remaining = float(delay_secs)
        self.zeitnot_marker = zeitnot
        self.show_clock = True

    def config_hourglass(self, base_secs):
        """
        Reloj de arena: el tiempo que usa un jugador se transfiere al rival.
        Requiere llamar a set_opponent() con el TimeControl del rival.
        Ej: config_hourglass(300)  →  5min cada uno
        """
        self.time_mode = TimeMode.HOURGLASS
        self.pending_time = self.total_time = float(base_secs)
        self.seconds_per_move = 0
        self.show_clock = True

    def config_moves_in_time(self, phases, zeitnot=0):
        """
        Control por fases (estándar FIDE torneos clásicos).
        phases: lista de tuplas (num_moves, base_secs, bonus_secs)
          - num_moves=0 significa "el resto de la partida"
          - bonus_secs se añade al pasar de fase
        Ej FIDE clásico:
          config_moves_in_time([(40, 5400, 0), (20, 1800, 0), (0, 900, 30)])
          → 40 mov en 90min | 20 mov en 30min | resto en 15min + 30s/mov
        Ej rápido:
          config_moves_in_time([(0, 900, 10)])
          → 15min + 10s/mov (fase única)
        """
        self.time_mode = TimeMode.MOVES_IN_TIME
        self.moves_in_time_phases = phases
        self._current_phase = 0
        self._moves_in_phase = 0
        if phases:
            _, base_secs, self.seconds_per_move = phases[0]
            self.pending_time = self.total_time = float(base_secs)
        self.zeitnot_marker = zeitnot
        self.show_clock = True

    def config_as_time_keeper(self):
        self.config_clock(INFINITE, 0, 0, 0)
        self.is_displayed = False

    # -- Utilidades de formato -------------------------------------------------

    @staticmethod
    def text(segs):
        if segs <= 0.0:
            segs = 0.0
        tp = round(segs)
        txt = "%02d:%02d" % (int(tp / 60), tp % 60)
        return txt

    @staticmethod
    def text_with_hours(segs):
        """Formato H:MM:SS para partidas largas."""
        if segs <= 0.0:
            segs = 0.0
        tp = round(segs)
        hh = tp // 3600
        mm = (tp % 3600) // 60
        ss = tp % 60
        if hh:
            return "%d:%02d:%02d" % (hh, mm, ss)
        return "%02d:%02d" % (mm, ss)

    def phase_label(self):
        """Etiqueta de fase para moves_in_time."""
        if self.time_mode == TimeMode.MOVES_IN_TIME and self.moves_in_time_phases:
            num_moves, __, __ = self.moves_in_time_phases[self._current_phase]
            if num_moves:
                remaining = num_moves - self._moves_in_phase
                return f"⌖{remaining}"
        return ""

    # -- Consulta de tiempo ----------------------------------------------------

    def get_seconds(self):
        if self.time_init:
            elapsed = time.time() - self.time_init
            if self.time_mode == TimeMode.DELAY_SIMPLE:
                elapsed = max(0.0, elapsed - self._delay_remaining)
            tp = self.pending_time - elapsed
        else:
            tp = self.pending_time
        return round(tp)

    def label(self):
        return self.text(self.get_seconds())

    def get_seconds2(self):
        if self.time_init:
            tp2 = time.time() - self.time_init
            elapsed = tp2
            if self.time_mode == TimeMode.DELAY_SIMPLE:
                elapsed = max(0.0, elapsed - self._delay_remaining)
            tp = self.pending_time - elapsed
        else:
            tp = self.pending_time - self.time_paused
            tp2 = self.time_paused
        if tp <= 0.0:
            tp = 0
        return tp, tp2 + self.time_previous

    # -- Ciclo start / stop / pause --------------------------------------------

    def start(self):
        if self.time_paused:
            self.pending_time -= self.time_paused
            self.time_previous += self.time_paused
        else:
            self.time_previous = 0
            self.pending_time_initial = self.pending_time

        self.time_init = time.time()
        self.time_paused = 0.0

        # Bronstein: guarda tiempo al inicio del turno
        if self.time_mode == TimeMode.BRONSTEIN:
            self._bronstein_turn_start = self.pending_time

        # Delay: reinicia el delay al inicio de cada turno
        if self.time_mode == TimeMode.DELAY_SIMPLE:
            self._delay_remaining = self.seconds_per_move
            self._delay_active = True

    def stop(self):
        """
        Para el reloj al final del turno y aplica el incremento
        correspondiente al modo activo.
        """
        if self.time_init:
            t_used = time.time() - self.time_init
            self.time_init = None
            self.time_previous = 0

            if self.time_mode == TimeMode.FISCHER:
                self.pending_time -= t_used - self.seconds_per_move

            elif self.time_mode == TimeMode.BRONSTEIN:
                # Solo se recupera el tiempo si el turno duró menos que el delay
                recovered = min(t_used, self.seconds_per_move)
                self.pending_time = self._bronstein_turn_start - t_used + recovered

            elif self.time_mode == TimeMode.DELAY_SIMPLE:
                effective = max(0.0, t_used - self.seconds_per_move)
                self.pending_time -= effective

            elif self.time_mode == TimeMode.HOURGLASS:
                self.pending_time -= t_used
                if self._opponent_clock:
                    self._opponent_clock.pending_time += t_used

            elif self.time_mode == TimeMode.MOVES_IN_TIME:
                self.pending_time -= t_used - self.seconds_per_move
                self._advance_moves_in_time_phase()

            else:  # SUDDEN_DEATH
                self.pending_time -= t_used

            if self.time_is_consumed():
                self.pending_time = 0.0

            return t_used
        else:
            tp = self.time_paused
            self.pending_time -= tp
            self.time_paused = 0
            self.time_previous = 0
            return tp

    def _advance_moves_in_time_phase(self):
        """Comprueba si hay que avanzar de fase en moves_in_time."""
        if not self.moves_in_time_phases:
            return
        self._moves_in_phase += 1
        num_moves, __, __ = self.moves_in_time_phases[self._current_phase]
        if num_moves and self._moves_in_phase >= num_moves:
            # Avanzar a la siguiente fase si existe
            next_phase = self._current_phase + 1
            if next_phase < len(self.moves_in_time_phases):
                self._current_phase = next_phase
                self._moves_in_phase = 0
                __, extra_secs, __ = self.moves_in_time_phases[next_phase]
                self.pending_time += extra_secs
                self.total_time += extra_secs

    def pause(self):
        if self.time_init:
            t_used = time.time() - self.time_init
            self.time_init = None
            self.time_paused = t_used

    def reset(self):
        self.time_init = None
        self.time_paused = 0
        self.time_previous = 0
        self.pending_time = self.pending_time_initial
        self._delay_remaining = self.seconds_per_move
        self._moves_in_phase = 0
        self._current_phase = 0

    def restart(self):
        self.time_init = time.time() - self.time_paused
        self.time_paused = 0
        self.set_labels()

    # -- Display ---------------------------------------------------------------

    def set_labels(self):
        if self.is_displayed:
            tp, tp2 = self.get_seconds2()
            eti = self.text(tp)
            eti2 = self.text(tp2)
            if eti:
                if self.time_mode == TimeMode.MOVES_IN_TIME:
                    eti2 += self.phase_label()

                self.set_clock_side(eti, eti2)

    def label_dgt(self):
        segs = self.get_seconds()
        mins = segs // 60
        segs -= mins * 60
        hors = mins // 60
        mins -= hors * 60
        return "%d:%02d:%02d" % (hors, mins, segs)

    # -- Comprobaciones de estado ----------------------------------------------

    def time_is_consumed(self):
        if self.time_init:
            elapsed = time.time() - self.time_init
            if self.time_mode == TimeMode.DELAY_SIMPLE:
                elapsed = max(0.0, elapsed - self._delay_remaining)
            return (self.pending_time - elapsed) <= 0.0
        return self.pending_time <= 0.0

    def is_zeitnot(self):
        if self.zeitnot_marker:
            if self.time_init:
                t = self.pending_time - (time.time() - self.time_init)
            else:
                t = self.pending_time
            if t > 0:
                resp = t < self.zeitnot_marker
                if resp:
                    self.zeitnot_marker = None
                return resp
        return False

    # -- Extras ----------------------------------------------------------------

    def set_zeinot(self, segs):
        self.zeitnot_marker = segs

    def add_extra_seconds(self, secs):
        self.pending_time += secs
        self.total_time += secs

    # -- Serialización ---------------------------------------------------------

    def save(self):
        return (
            self.total_time,
            self.pending_time,
            self.zeitnot_marker,
            self.time_paused,
            self.time_mode,
            self._current_phase,
            self._moves_in_phase,
        )

    def restore(self, tvar):
        (
            self.total_time,
            self.pending_time,
            self.zeitnot_marker,
            self.time_paused,
            self.time_mode,
            self._current_phase,
            self._moves_in_phase,
        ) = tvar
        self.time_init = None
