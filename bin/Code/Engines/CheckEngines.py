import os
import shutil
from typing import List, Set, Optional

import cpuinfo

import Code
from Code.Z import Util


class StockfishManager:
    """
    Manage Stockfish engine selection based on CPU capabilities.
    """

    STOCKFISH_KEY = "STOCKFISH17.1"

    REQUIREMENTS = [
        ("vnni512", {"avx512f", "avx512vl", "avx512vnni", "avx512dq", "avx512bw"}),
        ("avx512", {"avx512f", "avx512bw", "avx512dq"}),
        ("vnni256", {"avx2", "avxvnni"}),
        ("avxvnni", {"avx2", "avxvnni"}),
        ("bmi2", {"bmi2"}),
        ("avx2", {"avx2"}),
        ("sse41-popcnt", {"sse4_1", "popcnt"}),
        ("ssse3", {"ssse3"}),
        ("sse3-popcnt", {"sse3", "popcnt"}),
        ("x86-64", set()),
    ]

    def __init__(self) -> None:
        self._cpu_flags = None

    # =========================
    # Public API
    # =========================
    @property
    def cpu_flags(self):
        if self._cpu_flags is None:
            self._cpu_flags = self._get_cpu_flags()
        return self._cpu_flags

    def check(self, check_again: bool = False) -> bool:
        conf = self._get_stockfish_config()
        if not conf:
            return True

        if saved_name := self._read_saved_name():
            conf.name = saved_name
            if not check_again:
                return True

        versions = self._read_versions(conf)
        if not versions:
            return True

        best = self._select_best_version(versions)
        if not best:
            return True

        self._apply_version(conf, best)
        return True

    def current_name(self) -> str:
        return self._read_saved_name() or "stockfish"

    # =========================
    # Internal helpers
    # =========================

    @staticmethod
    def _get_stockfish_config():
        return Code.configuration.engines.dic_engines().get("stockfish")

    def _read_saved_name(self) -> Optional[str]:
        data = Code.configuration.read_variables(self.STOCKFISH_KEY)
        return data.get("NAME")

    # -------- CPU --------

    def _get_cpu_flags(self) -> Set[str]:
        try:
            info = cpuinfo.get_cpu_info()
            flags = {f.lower() for f in info.get("flags", [])}
            self._normalize_flags(flags)
            return flags
        except Exception:
            return set()

    @staticmethod
    def _normalize_flags(flags: Set[str]) -> None:
        if "sse4.1" in flags:
            flags.add("sse4_1")
        if "sse4.2" in flags:
            flags.add("sse4_2")

    # -------- Versions --------

    @staticmethod
    def _read_versions(conf) -> List[str]:
        folder = os.path.dirname(conf.path_exe)
        path = Util.opj(folder, "versions.txt")

        with open(path, "rt") as f:
            return [line.strip() for line in f if "x86-64" in line]

    def _select_best_version(self, versions: List[str]) -> Optional[str]:
        if compatible := [(self._version_score(v), v) for v in versions if self._is_compatible(v)]:
            compatible.sort(reverse=True)
            return compatible[0][1]

        return next(
            (v for v in versions if v.endswith("x86-64.exe")),
            versions[0] if versions else None,
        )

    def _is_compatible(self, version: str) -> bool:
        required = set()

        for substring, flags in self.REQUIREMENTS:
            if substring in version:
                required |= flags

        return required.issubset(self.cpu_flags)

    def _version_score(self, version: str) -> int:
        return next(
            (
                len(self.REQUIREMENTS) - index
                for index, (substring, _) in enumerate(self.REQUIREMENTS)
                if substring in version
            ),
            0,
        )

    # -------- Apply --------

    def _apply_version(self, conf, version: str) -> None:
        folder = os.path.dirname(conf.path_exe)
        source = Util.opj(folder, version)
        target = conf.path_exe

        Util.remove_file(target)
        shutil.copy(source, target)

        conf.name = version.replace(".exe", "")
        Code.configuration.write_variables(
            self.STOCKFISH_KEY,
            {"NAME": conf.name},
        )


# =========================
# Backward-compatible API
# =========================


def check_stockfish(check_again: bool) -> bool:
    _manager = StockfishManager()
    return _manager.check(check_again)


def check_engines(_window) -> None:
    if not Code.engines_has_been_checked:
        _manager = StockfishManager()
        _manager.check(False)
        Code.engines_has_been_checked = True


def current_stockfish() -> str:
    _manager = StockfishManager()
    return _manager.current_name()
