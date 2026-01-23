from typing import Any, List, Optional, Tuple

import Code
from Code.Base.Constantes import GT_AGAINST_ENGINE_LEAGUE, GT_AGAINST_ENGINE_SWISS
from Code.QT import QTMessages
from Code.SQL import UtilSQL
from Code.Z import Util


class Adjournments:
    def __init__(self):
        self.file = Code.configuration.paths.file_adjournments()

    def open(self):
        return UtilSQL.DictSQL(self.file)

    @staticmethod
    def create_key(tp: int, label_menu: str) -> str:
        now = Util.today()
        return "%d|%d|%d|%d|%d|%d|%d|%s" % (
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            tp,
            label_menu,
        )

    @staticmethod
    def key_crash(tp: int, label_menu: str) -> str:
        return Adjournments.create_key(tp, label_menu)

    def add_crash(self, key_crash: str, dic: dict):
        with self.open() as db:
            db[key_crash] = dic

    def rem_crash(self, key_crash: str):
        self.remove(key_crash)

    def add(self, tp: int, dic: dict, label_menu: str):
        with self.open() as db:
            key = self.create_key(tp, label_menu)
            db[key] = dic

    def get(self, key: str) -> Any:
        with self.open() as db:
            return db[key]

    def remove(self, key: str):
        with self.open() as db:
            del db[key]
            num_elem = len(db)
        if num_elem == 0:
            Util.remove_file(self.file)

    def list_menu(self) -> Optional[List[Tuple[str, str, int]]]:
        try:
            with self.open() as db:
                li = db.keys(True)
                li_resp = []
                for key in li:
                    year, month, day, hour, minute, second, tp, label_menu = key.split("|")
                    label = "%d-%02d-%02d %02d:%02d:%02d " % (
                        int(year),
                        int(month),
                        int(day),
                        int(hour),
                        int(minute),
                        int(second),
                    )
                    tp = int(tp)
                    li_resp.append((key, label + label_menu, tp))
                return li_resp
        except:
            Util.remove_file(self.file)
            return None

    def __len__(self) -> int:
        if Util.exist_file(self.file):
            try:
                with self.open() as db:
                    return len(db)
            except:
                Util.remove_file(self.file)
        return 0

    @staticmethod
    def si_seguimos(manager) -> bool:
        if QTMessages.pregunta(manager.main_window, _("Do you want to exit Lucas Chess?")):
            manager.main_window.accept()
            return False
        else:
            manager.main_window.active_game(False, False)
            manager.remove_captures()
            manager.procesador.start()
            return True

    def _key_match(self, xmatch, game_type: int) -> Optional[Tuple[str, dict]]:
        with self.open() as db:
            li = db.keys(True)
            for key in li:
                parts = key.split("|")
                if len(parts) >= 7:
                    tp = parts[6]
                    if int(tp) == game_type:
                        dic = db[key]
                        saved_match = dic.get("match_saved")
                        if saved_match and saved_match.get("XID") == xmatch.xid:
                            return key, dic
        return None

    def key_match_league(self, xmatch) -> Optional[Tuple[str, dict]]:
        return self._key_match(xmatch, GT_AGAINST_ENGINE_LEAGUE)

    def key_match_swiss(self, xmatch) -> Optional[Tuple[str, dict]]:
        return self._key_match(xmatch, GT_AGAINST_ENGINE_SWISS)

    def __enter__(self):
        return self

    def __exit__(self, xtype, value, traceback):
        pass
