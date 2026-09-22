import time

import FasterCode
from PySide6 import QtWidgets, QtCore

from Code.Base import Position
from Code.Databases import DBgames, WDB_Games
from Code.QT import Colocacion


class InfoMoveReplace:
    def __init__(self, owner):
        self.tab_database = owner
        self.board = self.tab_database.tabs_analysis.wlines.pboard.board

    @staticmethod
    def game_mode(_x, _y):
        return True


class TabDatabase(QtWidgets.QWidget):
    position: Position.Position

    def __init__(self, tabs_analysis, path_db):
        QtWidgets.QWidget.__init__(self)

        self.tabs_analysis = tabs_analysis
        self.is_temporary = False

        self.pv = tabs_analysis.dbop.basePV

        self.db = DBgames.DBgames(path_db)
        self.last_refresh = time.monotonic()

        self.wgames = WDB_Games.WGames(self, self.db, None, False)
        self.wgames.tbWork.hide()
        self.wgames.status.hide()
        self.wgames.infoMove = InfoMoveReplace(self)

        layout = Colocacion.H().control(self.wgames)
        self.setLayout(layout)

    def tw_terminar(self):
        self.db.close()
        return

    def set_data(self, position, pv):
        self.position = position
        self.set_pv(pv)

    def set_pv(self, pv):
        self.pv = pv

    def start(self):
        self.wgames.grid.hide()
        self.db.filter_pv(self.pv)
        self.db.rowidReader.finished_reading.connect(self.tw_refresh_end)
        self.db.rowidReader.rowids_received.connect(self.tw_refresh)

    @QtCore.Slot()
    def tw_refresh_end(self):
        self.wgames.grid.show()
        self.wgames.grid.refresh()

    @QtCore.Slot()
    def tw_refresh(self):
        if time.monotonic() - self.last_refresh < 1.0:
            return
        self.last_refresh = time.monotonic()
        self.wgames.grid.show()
        self.wgames.grid.refresh()

    def stop(self):
        self.db.close()
