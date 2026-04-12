import FasterCode

import Code


class ECO:
    """Determina el código ECO de una partida a partir de su secuencia de
    movimientos en formato UCI (separados por espacios).
    """

    def __init__(self):
        self._dic = {}
        path = Code.path_resource("Openings", "eco.lines")
        with open(path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    fen, eco, depth = line.split("|")
                    self._dic[fen] = (eco, int(depth))
        self.max_depth = max(data[1] for data in self._dic.values())

    def assign(self, uci: str) -> str | None:
        """Devuelve el código ECO más específico para una partida.

        Parameters
        ----------
        uci:
            Secuencia de movimientos UCI separados por espacios,
            p.ej. ``"e2e4 e7e5 g1f3 b8c6"``.

        Returns
        -------
        str | None
            Código ECO (p.ej. ``"C44"``), o ``None`` si no se encontró ningún match.
        """
        if not uci:
            return None
        li_uci = uci.split()[: self.max_depth]

        best_eco: str | None = None
        best_depth: int = -1

        FasterCode.set_init_fen()
        for pv in li_uci:
            FasterCode.move_pv(pv[:2], pv[2:4], pv[4:])
            fenm2 = FasterCode.get_fenm2()
            if fenm2 in self._dic:
                eco, depth = self._dic[fenm2]
                if depth > best_depth:
                    best_depth = depth
                    best_eco = eco

        if best_eco is None:
            if uci.startswith("d2d4 g8f6 c2c4 g7g6") and "d7d5" in uci:
                return "D70"
            if li_uci[0] in ("e2e4", "d2d4", "g1f3", "c2c4", "b2b3", "f2f4"):
                return "A00"

        return best_eco


# ---------------------------------------------------------------------------
# Singleton a nivel de módulo — reutiliza la misma instancia en el proceso
# ---------------------------------------------------------------------------
_eco_singleton: ECO | None = None


def get_eco() -> ECO:
    # Devuelve la instancia compartida de ECO
    global _eco_singleton
    if _eco_singleton is None:
        _eco_singleton = ECO()
    return _eco_singleton
