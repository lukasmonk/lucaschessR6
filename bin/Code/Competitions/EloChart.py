import datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QSplineSeries

import Code
from Code.Base import Game
from Code.Base.Constantes import CMP_ELO, RS_WIN_PLAYER, RS_WIN_OPPONENT, RS_DRAW
from Code.Competitions import History
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, LCDialog, FormLayout, QTMessages
from Code.SQL import UtilSQL
from Code.Z import Util


class EloChartDialog(LCDialog.LCDialog):
    def __init__(self, w_parent):
        titulo = _("Elo Progress Charts")
        icono = Iconos.DailyTest()

        extparam = "elochartv4"
        LCDialog.LCDialog.__init__(self, w_parent, titulo, icono, extparam)

        self.history = History.History(CMP_ELO)

        # Datos normalizados (ver _build_rows). Deben existir antes de crear el grid.
        self.all_rows = []  # todos los registros, del más antiguo al más reciente
        self.rows = []  # la ventana visible (como máximo sp_games partidas)
        self.rows_reversed = []  # lo mismo, del más reciente al más antiguo (para el grid)
        self.rows_by_number = {}
        self.offset = 0  # partidas más recientes que quedan fuera de la ventana (0 = las últimas)

        self.cb_option = Controles.CB(self, self.history.get_combo(), CMP_ELO).capture_changes(self.change_mode)

        self.sp_games = Controles.SB(self, 50, 10, 1000).capture_changes(self.refresh)
        self.sp_games.setSuffix(f" {_('Games')}")

        self.bt_back = Controles.PB(self, "◀", rutina=self.page_back, plano=False)
        self.bt_back.set_pordefecto(False)
        self.bt_forward = Controles.PB(self, "▶", rutina=self.page_forward, plano=False)
        self.bt_forward.set_pordefecto(False)
        self.lb_range = Controles.LB(self, "")

        self.chart_view = QChartView(self)
        self.chart_view.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMGAME", _("Game"), 80, align_center=True)
        o_columns.nueva("DATE", _("Date"), 100, align_center=True)
        o_columns.nueva("RIVAL", _("Opponent"), 110, align_center=True)
        o_columns.nueva("RELO", f'{_("Opponent")}-{_("Elo")}', 110, align_center=True)
        o_columns.nueva("SIDE", _("Side"), 80, align_center=True)
        o_columns.nueva("MOVES", _("Movements"), 100, align_center=True)
        o_columns.nueva("RESULTADO", _("Result"), 80, align_center=True)
        o_columns.nueva("ELO", _("Elo"), 120, align_center=True)

        self.grid = Grid.Grid(self, o_columns, complete_row_select=True)
        self.register_grid(self.grid)

        self.bt_reset = Controles.PB(self, _("Remove"), rutina=self.reset_history, plano=False)
        self.bt_reset.set_pordefecto(False)
        self.bt_close = Controles.PB(self, _("Close"), rutina=self.terminar, plano=False)
        self.bt_close.set_pordefecto(False)

        ly_top = Colocacion.H()
        ly_top.control(self.cb_option).relleno().control(self.sp_games)

        ly_nav = Colocacion.H()
        ly_nav.control(self.bt_back).relleno().control(self.lb_range).relleno().control(self.bt_forward)

        ly_bottom = Colocacion.H()
        ly_bottom.control(self.bt_reset).relleno().control(self.bt_close)

        layout = Colocacion.V()
        layout.otro(ly_top)
        layout.control(self.chart_view)
        layout.otro(ly_nav)
        layout.control(self.grid)
        layout.otro(ly_bottom)

        self.setLayout(layout)

        self.restore_video(default_width=950, default_height=720)

        self.refresh()

    def terminar(self):
        self.save_video()
        self.accept()

    # ------------------------------------------------------------------ datos

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_date(value):
        if isinstance(value, (datetime.datetime, datetime.date)):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10] if value else ""

    @staticmethod
    def _format_side(side):
        if side is True:
            return _("White")
        if side is False:
            return _("Black")
        return "" if side is None else str(side)

    @staticmethod
    def _format_result(result):
        if result == RS_WIN_PLAYER:
            c = _("W ||Games won")
        elif result == RS_WIN_OPPONENT:
            c = _("L ||Games lost")
        elif result == RS_DRAW:
            c = _("D ||Games drawn")
        else:
            c = ""
        return c

    @staticmethod
    def _format_elo(ant_elo, new_elo):
        if ant_elo == new_elo:
            return f"{new_elo}"
        elif ant_elo > new_elo:
            symbol = "↙"
        else:
            symbol = "↗"
        return f"{ant_elo} {symbol} {new_elo}"

    def _build_rows(self):
        """Convierte los registros de History (claves FECHA, RIVAL, RELO, NELO...) en filas
        con las claves que usan el grid y el gráfico. Devuelve la lista del más antiguo al más reciente."""
        records = self.history.read_all_records()  # [(history_pos, record)], del más reciente al más antiguo

        valid = []
        for history_pos, record in reversed(records):
            elo = self._to_int(record.get("NELO"))
            if elo is not None:
                valid.append((history_pos, record, elo))

        rows = []
        for number, (history_pos, record, elo) in enumerate(valid, start=1):
            plies = self._to_int(record.get("PLYCOUNT"))
            rows.append(
                {
                    "NUMGAME": number,
                    "DATE": self._format_date(record.get("FECHA")),
                    "SIDE": self._format_side(record.get("SIDE")),
                    "MOVES": str(plies) if plies is not None else "",
                    "RIVAL": record.get("RIVAL", ""),
                    "RELO": self._to_int(record.get("RELO")),
                    "RELO_ESTIMATED": record.get("RELO_ESTIMATED"),
                    "ELO": self._format_elo(record["AELO"], record["NELO"]),
                    "NELO": record["NELO"],
                    "AELO": record["AELO"],
                    "RESULTADO": self._format_result(record.get("RESULTADO")),
                    "game_save": record.get("GAME_SAVE"),
                    "history_pos": history_pos,
                }
            )

        return rows

    # ------------------------------------------------------------------ navegación

    def change_mode(self, *_args):
        self.offset = 0
        self.refresh()

    def page_back(self):
        """Ventana anterior (partidas más antiguas)."""
        self.offset += self.sp_games.value()
        self.refresh()

    def page_forward(self):
        """Ventana siguiente (partidas más recientes)."""
        self.offset -= self.sp_games.value()
        self.refresh()

    def refresh(self, *_args):
        self.history.set_mode(self.cb_option.valor())

        self.all_rows = self._build_rows()
        total = len(self.all_rows)
        size = self.sp_games.value()

        self.offset = min(max(self.offset, 0), max(total - size, 0))
        end = total - self.offset
        start = max(end - size, 0)

        self.rows = self.all_rows[start:end]
        self.rows_reversed = self.rows[::-1]
        self.rows_by_number = {row["NUMGAME"]: row for row in self.rows}

        self.bt_back.setEnabled(start > 0)
        self.bt_forward.setEnabled(self.offset > 0)
        self.lb_range.setText(self._range_text(total))

        self.chart_view.setChart(self._build_chart())
        self.grid.refresh()

    def _range_text(self, total):
        if not self.rows:
            return ""
        first, last = self.rows[0], self.rows[-1]
        return f"{first['DATE']}  →  {last['DATE']}    ({first['NUMGAME']}-{last['NUMGAME']} / {total})"

    # ------------------------------------------------------------------ gráfico

    def _build_chart(self):
        chart = QChart()
        chart.setTitle(self.cb_option.currentText())
        chart.legend().setVisible(True)

        player_series = QLineSeries()
        player_series.setName(_("Elo"))
        player_series.setPointsVisible(True)
        rival_series = QLineSeries()
        rival_series.setName(f'{_("Opponent")}-{_("Elo")}')
        rival_series.setPointsVisible(True)

        ratings = []
        for row in self.rows:
            number = row["NUMGAME"]
            player_series.append(number, row["NELO"])
            ratings.append(row["NELO"])
            if row["RELO"] is not None:
                rival_series.append(number, row["RELO"])
                ratings.append(row["RELO"])

        chart.addSeries(player_series)
        chart.addSeries(rival_series)

        first = self.rows[0]["NUMGAME"] if self.rows else 1
        last = self.rows[-1]["NUMGAME"] if self.rows else 2
        if last == first:
            last = first + 1

        axis_x = QValueAxis()
        title_x = _("Game")
        axis_x.setTitleText(title_x)
        axis_x.setLabelFormat("%d")
        axis_x.setRange(first, last)

        span = last - first
        max_lines = max(1, min(len(self.rows) // 2, 16))
        grid_step = max(1, -(-span // max_lines))  # paso entre líneas de rejilla (ceil)
        label_step = max(grid_step, -(-span // 14))  # ~14 etiquetas como máximo
        label_step = -(-label_step // grid_step) * grid_step  # múltiplo del paso de rejilla

        axis_x.setTickType(QValueAxis.TickType.TicksDynamic)
        axis_x.setTickAnchor(first)
        axis_x.setTickInterval(label_step)
        axis_x.setMinorTickCount(label_step // grid_step - 1)
        axis_x.setMinorGridLineVisible(True)

        axis_y = QValueAxis()
        axis_y.setTitleText(_("Elo"))
        axis_y.setLabelFormat("%d")
        low = min(ratings, default=0)
        high = max(ratings, default=100)
        padding = max(20, (high - low) // 10)
        axis_y.setRange(max(0, low - padding), high + padding)

        chart.addAxis(axis_x, QtCore.Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, QtCore.Qt.AlignmentFlag.AlignLeft)
        for series in (player_series, rival_series):
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            series.hovered.connect(self.show_tooltip)

        return chart

    def show_tooltip(self, point, active):
        if not active:
            QtWidgets.QToolTip.hideText()
            return
        row = self.rows_by_number.get(round(point.x()))
        if row is None:
            return
        rival_elo = row["RELO"]
        if rival_elo is None:
            label_elo = "?"
        else:
            label_elo = f"~{rival_elo}" if row["RELO_ESTIMATED"] else str(rival_elo)
        text = f"{row['DATE']}\n{row['RIVAL']} ({label_elo})\n{_('Elo')}: {row['ELO']}"
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), text, self.chart_view)

    # ------------------------------------------------------------------ grid

    def grid_num_datos(self, _grid):
        return len(self.rows_reversed)

    def grid_dato(self, _grid, row, obj_column):
        key = obj_column.key
        record = self.rows_reversed[row]
        value = record.get(key)
        if value is None:
            return ""
        if key == "RELO" and record.get("RELO_ESTIMATED"):
            return f"~{value}"
        return str(value)

    def grid_doble_click(self, _grid, row, _obj_column):
        self.edit_game(row)

    def grid_bold(self, _grid, row, _obj_column):
        record: dict = self.rows_reversed[row]
        return record["NELO"] > record["AELO"]

    def edit_game(self, grid_row):
        if not 0 <= grid_row < len(self.rows_reversed):
            return

        record: dict = self.rows_reversed[grid_row]
        game_save = record["game_save"]
        if not game_save:
            return

        path = self.history.get_path()
        history_pos = record["history_pos"]

        game = Game.Game()
        game.restore(game_save)
        game.recno = history_pos

        def save_game(recno, edited_game):
            with UtilSQL.ListSQL(path) as dbhistory:
                drecord = dbhistory[history_pos]
                if not isinstance(drecord, dict):
                    drecord = {}
                drecord["GAME_SAVE"] = edited_game.save()
                dbhistory[history_pos] = drecord
            response = Util.Record()
            response.ok = True
            response.recno = recno
            return response

        Code.procesador.manager_game(self, game, True, False, None, save_routine=save_game)
        self.refresh()

    # ------------------------------------------------------------------ reset

    def reset_history(self):

        form = FormLayout.FormLayout(self, _("Remove"), Iconos.Delete())
        form.separador()
        form.spinbox(_("From"), 1, len(self.rows), 80, 1)
        form.separador()
        form.spinbox(_("To"), 1, len(self.rows), 80, 1)
        form.separador()
        resultado = form.run()
        if resultado is None:
            return False

        accion, li_resp = resultado
        first_game, last_game = li_resp
        # first_game, last_game = int(first_game), int(last_game)
        if first_game > last_game:
            first_game, last_game = last_game, first_game

        if not QTMessages.pregunta(self,
                                   _("Are you sure you want to remove %s?").replace("%s", f"{first_game}-{last_game}")):
            return False

        # NUMGAME es el orden mostrado; hay que borrar por la posición real en la BD, de mayor a menor
        positions = sorted(
            (row["history_pos"] for row in self.all_rows if first_game <= row["NUMGAME"] <= last_game),
            reverse=True,
        )
        with UtilSQL.ListSQL(self.history.get_path()) as history:
            for history_pos in positions:
                del history[history_pos]

        self.refresh()

        return True
