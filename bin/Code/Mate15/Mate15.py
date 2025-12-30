import ast
import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import Code
from Code.SQL import UtilSQL


@dataclass
class Mate15:
    """Data container for Mate15 training positions."""

    fen: str = ""
    date: datetime.datetime = field(default_factory=datetime.datetime.now)
    info: str = ""
    move: str = ""
    resp: Dict[str, Any] = field(default_factory=dict)
    tries: List[int] = field(default_factory=list)  # List of times taken (int?)
    pos: int = 0

    def result(self) -> Optional[int]:
        """Return the best (minimum) time from tries, or None if no tries."""
        if not self.tries:
            return None
        return min(self.tries)

    def num_tries(self) -> int:
        return len(self.tries)

    def append_try(self, tm: int) -> None:
        self.tries.append(tm)

    def save(self) -> Dict[str, Any]:
        """Return a dictionary representation of the object for storage."""
        # We use asdict but we might need to ensure compatibility with the specific keys
        # expected by the existing restore/DB logic if they differ from field names.
        # The original save method returned exactly these keys:
        return {
            "date": self.date,
            "pos": self.pos,
            "fen": self.fen,
            "info": self.info,
            "move": self.move,
            "resp": self.resp,
            "tries": self.tries,
        }

    def restore(self, dic: Dict[str, Any]) -> None:
        """Update object state from a dictionary."""
        self.date = dic["date"]
        self.pos = dic["pos"]
        self.fen = dic["fen"]
        self.info = dic["info"]
        self.move = dic["move"]
        self.resp = dic["resp"]
        self.tries = dic["tries"]

    def copy(self) -> "Mate15":
        """Return a copy of the object with updated date."""
        # Create a new instance with current data
        new_obj = Mate15(
            fen=self.fen,
            date=datetime.datetime.now(),
            info=self.info,
            move=self.move,
            resp=self.resp.copy(),  # Shallow copy of dict
            tries=self.tries[:],  # Shallow copy of list
            pos=self.pos,
        )
        return new_obj


class DBMate15:
    def __init__(self, path: str):
        self.path = path
        self.li_data: List[Mate15] = []

        with self.db() as db:
            li_dates = db.keys(True, True)
            dic_data = db.as_dictionary()
            for date in li_dates:
                mate15 = Mate15()
                mate15.restore(dic_data[date])
                self.li_data.append(mate15)

    def db(self) -> UtilSQL.DictSQL:
        return UtilSQL.DictSQL(self.path)

    def db_config(self) -> UtilSQL.DictSQL:
        return UtilSQL.DictSQL(self.path, tabla="config")

    def __len__(self) -> int:
        return len(self.li_data)

    def last(self) -> Optional[Mate15]:
        if self.li_data:
            return self.li_data[0]
        return None

    def create_new(self) -> Mate15:
        with open(Code.path_resource("IntFiles", "mate.15"), "rt", encoding="utf-8") as f:
            li = [linea.strip() for linea in f if linea.strip()]

        with self.db_config() as dbc:
            siguiente = dbc["NEXT"]
            if siguiente is None:
                siguiente = 0
            if siguiente >= len(li):
                siguiente = 0
            linea = li[siguiente]
            dbc["NEXT"] = siguiente + 1

        # Format: 8/4K1P1/...|Info|Move|Dict
        # Example: ...|Shahmat besteciliyi,2006,...|g1e1|{'e5f4': 'e1g3', ...}
        fen, info, move1, cdic = linea.split("|")

        m15 = Mate15()
        m15.fen = fen
        m15.pos = siguiente
        m15.info = info
        m15.move = move1
        try:
            m15.resp = ast.literal_eval(cdic)
        except (ValueError, SyntaxError):
            m15.resp = {}  # Fallback to empty dict if parsing fails

        with self.db() as db:
            db[str(m15.date)] = m15.save()
            self.li_data.insert(0, m15)

        return m15

    def repeat(self, base_15: Mate15) -> None:
        m15 = base_15.copy()
        m15.tries = []

        with self.db() as db:
            db[str(m15.date)] = m15.save()
            self.li_data.insert(0, m15)

    def remove_mate15(self, li_recno: List[int]) -> None:
        with self.db() as db:
            li_recno.sort(reverse=True)
            for recno in li_recno:
                mate15 = self.li_data[recno]
                del db[str(mate15.date)]
                del self.li_data[recno]
            db.pack()

    def save(self, mate15: Mate15) -> None:
        with self.db() as db:
            db[str(mate15.date)] = mate15.save()

    def mate15(self, recno: int) -> Mate15:
        return self.li_data[recno]
