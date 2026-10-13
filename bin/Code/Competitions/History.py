import datetime
import re

import Code
from Code.Base.Constantes import CMP_ELO, CMP_MICELO, CMP_WICKER, CMP_FICS, CMP_FIDE, CMP_LICHESS, CMP_MAIA
from Code.Base.Constantes import RS_WIN_PLAYER, RS_DRAW, RS_WIN_OPPONENT
from Code.SQL import UtilSQL


class History:
    def __init__(self, cmp_mode: int = -1):
        self.cmp_mode: int = cmp_mode
        self.dic_control: dict = self._get_dic_control()
        self.current_records: list = []

    # ----------------------------------------------------------------------------------- API

    def num_records(self) -> int:
        return len(self.current_records)

    def label(self):
        return self.dic_control[self.cmp_mode][1]

    def set_mode(self, cmp_mode: int):
        self.cmp_mode = cmp_mode

    def get_path(self) -> str:
        return self.dic_control[self.cmp_mode][0]()

    def save_history(self, name_opponent, elo_opponent, result, elo_before, elo_new, game, side):
        dic = {
            "FECHA": datetime.datetime.now(),
            "RIVAL": name_opponent,
            "RELO": elo_opponent,
            "RESULTADO": result,
            "AELO": elo_before,
            "NELO": elo_new,
            "GAME_SAVE": game.save(),
            "SIDE": side,
            "PLYCOUNT": len(game)
        }
        with UtilSQL.ListSQL(self.get_path()) as list_db:
            list_db.append(dic)

    def read_all_records(self):
        with UtilSQL.ListSQL(self.get_path()) as history:
            records = [(index, record) for index, record in enumerate(history) if isinstance(record, dict)]

        self._check_old(records)
        records.sort(key=lambda x: x[0], reverse=True)
        self.current_records = records
        return records

    def get_combo(self) -> list:
        return [(eti, key) for key, (path, eti) in self.dic_control.items()]

    # -----------------------------------------------------------------------------------------------------

    @staticmethod
    def _get_dic_control() -> dict:
        paths = Code.configuration.paths
        return {
            CMP_ELO: (paths.file_estad_elo, _("Lucas-Elo")),
            CMP_MICELO: (paths.file_estad_mic_elo, _("Tourney-Elo")),
            CMP_WICKER: (paths.file_estad_wicker_elo, _("The Wicker Park Tourney")),
            CMP_FICS: (paths.file_estad_fics_elo, _("Fics-Elo")),
            CMP_FIDE: (paths.file_estad_fide_elo, _("Fide-Elo")),
            CMP_LICHESS: (paths.file_estad_lichess_elo, _("Lichess-Elo")),
            CMP_MAIA: (paths.file_estad_maia_elo, _("Maia Ladder")),
        }

    def _current_engine_elos(self):
        if self.cmp_mode == CMP_MICELO:
            from Code.Engines import EnginesMicElo

            engines = EnginesMicElo.all_engines()
            saved = Code.configuration.read_variables("DicMicElos")
        elif self.cmp_mode == CMP_WICKER:
            from Code.Engines import EnginesWicker

            engines = EnginesWicker.read_wicker_engines()
            saved = Code.configuration.read_variables("DicWickerElos")
        else:
            return {}
        return {engine.name.casefold(): saved.get(engine.key, engine.elo) for engine in engines}

    def _check_old(self, records):
        is_mic_wicker = self.cmp_mode in (CMP_MICELO, CMP_WICKER)
        is_elo = self.cmp_mode == CMP_ELO

        engine_elos = self._current_engine_elos() if is_mic_wicker else {}
        for pos, record in records:
            if record.get("RESULTADO") is None:
                delta = int(record["NELO"]) - int(record["AELO"])
                if delta < 0:
                    record["RESULTADO"] = RS_WIN_OPPONENT
                elif delta > 0:
                    record["RESULTADO"] = RS_WIN_PLAYER
                else:
                    record["RESULTADO"] = RS_DRAW

            relo = record.get("RELO")
            if is_mic_wicker:

                if isinstance(relo, (int, str)) and str(relo).lstrip("-").isdigit():
                    record["RELO"] = int(relo)
                    record["RELO_ESTIMATED"] = False
                else:
                    current_elo = engine_elos.get(record["RIVAL"].casefold())
                    if current_elo is not None:
                        record["RELO"] = int(current_elo)
                        record["RELO_ESTIMATED"] = True

            elif relo is None:
                if is_elo:
                    rival_name = record.get("RIVAL", "")
                    if "(" in rival_name:
                        match = re.search(r"\((\d+)\)\s*$", rival_name)
                        record["RELO"] = int(match.group(1)) if match else None
                elif "LEVEL" in record:
                    record["RELO"] = int(record["LEVEL"]) * 100 + 50
                    record["RELO_ESTIMATED"] = True
            if is_elo:
                record["RIVAL"] = record.get("RIVAL", "").split("(")[0].strip()

