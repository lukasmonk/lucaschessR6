from PySide6 import QtCore, QtWidgets


class V(QtWidgets.QVBoxLayout):
    def control(self, control: QtWidgets.QWidget) -> "V":
        self.addWidget(control)
        return self

    def controlc(self, control: QtWidgets.QWidget) -> "V":
        self.addWidget(control)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        return self

    def controld(self, control: QtWidgets.QWidget) -> "V":
        self.addWidget(control)
        self.setAlignment(control, QtCore.Qt.AlignmentFlag.AlignRight)
        return self

    def controli(self, control: QtWidgets.QWidget) -> "V":
        self.addWidget(control)
        self.setAlignment(control, QtCore.Qt.AlignmentFlag.AlignLeft)
        return self

    def otro(self, layout: QtWidgets.QLayout) -> "V":
        self.addLayout(layout)
        return self

    def espacio(self, espacio: int) -> "V":
        self.addSpacing(espacio)
        return self

    def margen(self, n: int) -> "V":
        self.setContentsMargins(n, n, n, n)
        return self

    def relleno(self, factor: int = 1) -> "V":
        self.addStretch(factor)
        return self


class H(QtWidgets.QHBoxLayout):
    def control(self, control: QtWidgets.QWidget, stretch: int = 0) -> "H":
        self.addWidget(control, stretch)
        return self

    def controld(self, control: QtWidgets.QWidget) -> "H":
        self.addWidget(control)
        self.setAlignment(control, QtCore.Qt.AlignmentFlag.AlignRight)
        return self

    def controli(self, control: QtWidgets.QWidget) -> "H":
        self.addWidget(control)
        self.setAlignment(control, QtCore.Qt.AlignmentFlag.AlignLeft)
        return self

    def otro(self, layout: QtWidgets.QLayout) -> "H":
        self.addLayout(layout)
        return self

    def otroi(self, layout: QtWidgets.QLayout) -> "H":
        self.addLayout(layout)
        self.setAlignment(layout, QtCore.Qt.AlignmentFlag.AlignLeft)
        return self

    def otroc(self, layout: QtWidgets.QLayout) -> "H":
        self.addLayout(layout)
        self.setAlignment(layout, QtCore.Qt.AlignmentFlag.AlignCenter)
        return self

    def espacio(self, espacio: int) -> "H":
        self.addSpacing(espacio)
        return self

    def set_separation(self, tam: int) -> "H":
        self.setSpacing(tam)
        return self

    def margen(self, n: int) -> "H":
        self.setContentsMargins(n, n, n, n)
        return self

    def relleno(self, factor: int = 1) -> "H":
        self.addStretch(factor)
        return self


class G(QtWidgets.QGridLayout):
    dicAlineacion = {
        None: QtCore.Qt.AlignmentFlag.AlignLeft,
        "d": QtCore.Qt.AlignmentFlag.AlignRight,
        "c": QtCore.Qt.AlignmentFlag.AlignCenter,
    }

    def control(
        self,
        control: QtWidgets.QWidget,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
        alineacion: str | None = None,
    ) -> "G":
        self.addWidget(control, row, column, num_rows, num_columns, self.dicAlineacion[alineacion])
        return self

    def controld(
        self,
        control: QtWidgets.QWidget,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
    ) -> "G":
        self.addWidget(control, row, column, num_rows, num_columns, self.dicAlineacion["d"])
        return self

    def controlc(
        self,
        control: QtWidgets.QWidget,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
    ) -> "G":
        self.addWidget(control, row, column, num_rows, num_columns, self.dicAlineacion["c"])
        return self

    def otro(
        self,
        layout: QtWidgets.QLayout,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
        alineacion: str | None = None,
    ) -> "G":
        self.addLayout(layout, row, column, num_rows, num_columns, self.dicAlineacion[alineacion])
        return self

    def otroc(
        self,
        layout: QtWidgets.QLayout,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
    ) -> "G":
        self.addLayout(layout, row, column, num_rows, num_columns, self.dicAlineacion["c"])
        return self

    def otrod(
        self,
        layout: QtWidgets.QLayout,
        row: int,
        column: int,
        num_rows: int = 1,
        num_columns: int = 1,
    ) -> "G":
        self.addLayout(layout, row, column, num_rows, num_columns, self.dicAlineacion["d"])
        return self

    def margen(self, n: int) -> "G":
        self.setContentsMargins(n, n, n, n)
        return self

    def relleno_column(self, col: int, factor: int) -> "G":
        self.setColumnStretch(col, factor)
        return self

    def empty_column(self, column: int, min_size: int) -> "G":
        self.setColumnMinimumWidth(column, min_size)
        return self

    def empty_row(self, row: int, min_size: int) -> "G":
        self.setRowMinimumHeight(row, min_size)
        return self


# def juntaH(control1: QtWidgets.QWidget, control2: QtWidgets.QWidget) -> H:
#     return H().control(control1).control(control2).relleno()
