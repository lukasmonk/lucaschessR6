from PySide6 import QtCore

import Code
from Code.Base.Constantes import ENG_INTERNAL
from Code.Engines import SelectEngines
from Code.QT import (
    Colocacion,
    Columnas,
    Controles,
    Delegados,
    Grid,
    Iconos,
    LCDialog,
    QTDialogs,
    QTMessages,
)
from Code.SQL import UtilSQL


class ConfigurationsPAE:
    def __init__(self):
        self.path_db = Code.configuration.paths.file_conf_play_engine()
        self.dic = self.read_dic()

    def read_dic(self) -> dict:
        with UtilSQL.DictSQL(self.path_db) as dbc:
            dbc.wrong_pickle(b"Code.Polyglots", b"Code.Books")
            dbc.wrong_pickle(b"OpeningStd", b"Opening")
            dic_resp = {}
            for k, dic in dbc.as_dictionary().items():
                dr = dic.get("RIVAL")
                if dr is None:
                    continue
                name_engine = dr.get("ENGINE")
                if name_engine is None:
                    continue
                tipo = dr.get("TYPE", ENG_INTERNAL)
                alias = dr.get("ALIAS")
                rival = SelectEngines.busca_engine(tipo, name_engine, alias)
                if rival is not None:
                    dic_resp[k] = dic
            return dic_resp

    def __setitem__(self, key, value):
        self.dic[key] = value

    def __getitem__(self, key):
        return self.dic.get(key)

    def __contains__(self, item):
        return item in self.dic

    def __delitem__(self, key):
        del self.dic[key]

    def values(self):
        return self.dic.values()

    def items(self):
        return self.dic.items()

    def list_visible(self) -> list:
        li_conf = [(key, dic.get("MNT_ORDER", 0), dic) for key, dic in self.dic.items() if dic.get("MNT_VISIBLE", True)]
        li_conf.sort(key=lambda x: x[1])
        return li_conf

    def save(self):
        with UtilSQL.DictSQL(self.path_db) as dbc:
            dbc.zap()
            for key, value in self.dic.items():
                dbc[key] = value


class WConfigurationsPAE(LCDialog.LCDialog):
    korder = "MNT_ORDER"
    kvisible = "MNT_VISIBLE"

    def __init__(self, w_parent):
        LCDialog.LCDialog.__init__(self, w_parent, _("Save configuration"), Iconos.Calculo(), "play_save")

        self.configurations_pae = ConfigurationsPAE()
        self.w_parent = w_parent
        self.li_data = []
        self.read_data()

        tb = QTDialogs.LCTB(self)
        tb.new(_("Close"), Iconos.MainMenu(), self.terminate)
        tb.new(_("Save"), Iconos.SaveAs(), self.saveas)
        tb.new(_("Up"), Iconos.Arriba(), self.up, sep=False)
        tb.new(_("Down"), Iconos.Abajo(), self.down)
        tb.new(_("Remove"), Iconos.Borrar(), self.remove)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("KEY", _("Name"), 360, edicion=Delegados.LineaTextoUTF8())
        o_columns.nueva(
            "VISIBLE",
            _("Visible"),
            100,
            align_center=True,
            is_editable=True,
            is_checked=True,
        )

        self.grid = Grid.Grid(self, o_columns, is_editable=True)
        font = Controles.FontType(puntos=Code.configuration.x_font_points)
        self.grid.set_font(font)
        self.register_grid(self.grid)

        lb_info = Controles.LB(self, _("Double click to change the label"))

        ly = Colocacion.V().control(tb).control(self.grid).control(lb_info)
        self.setLayout(ly)
        self.restore_video(default_width=520, default_height=360)

    def terminate(self):
        self.configurations_pae.save()
        self.save_video()
        self.accept()

    def closeEvent(self, event):
        self.configurations_pae.save()
        self.save_video()

    def last_order(self):
        the_last_order = 0
        for dicv in self.configurations_pae.values():
            norder = dicv[self.korder]
            if norder > the_last_order:
                the_last_order = norder
        return the_last_order

    def refresh_gui(self):
        self.read_data()
        self.grid.refresh()

    def read_data(self):
        order = 0
        for key, dicv in self.configurations_pae.items():
            if self.korder not in dicv:
                order += 1
                dicv[self.korder] = order
                dicv[self.kvisible] = True
                self.configurations_pae[key] = dicv

        li = [
            (key, dicv.get(self.kvisible, True), dicv.get(self.korder, 0))
            for key, dicv in self.configurations_pae.items()
        ]
        li.sort(key=lambda x: x[2])
        self.li_data = li

    def grid_num_datos(self, _grid):
        return len(self.li_data)

    def grid_dato(self, _grid, row, obj_column):
        col = obj_column.key

        if col == "KEY":
            return self.li_data[row][0]
        if col == "VISIBLE":
            return self.li_data[row][1]
        return None

    def grid_setvalue(self, _grid, nfila, obj_column, value):
        col = obj_column.key
        key = self.li_data[nfila][0]
        if col == "KEY":
            if key != value and value:
                if value not in self.configurations_pae:
                    dic = self.configurations_pae[key]
                    del self.configurations_pae[key]
                    self.configurations_pae[value] = dic
                    self.refresh_gui()
        elif col == "VISIBLE":
            dic = self.configurations_pae[key]
            dic[self.kvisible] = value
            self.configurations_pae[key] = dic
            self.refresh_gui()

    def grid_right_button(self, grid, row, obj_column, _modif):
        col = obj_column.key
        if col == "KEY":
            key = self.li_data[row][0]
            result = QTMessages.read_simple(self, _("Maintenance"), _("Name"), key)
            if result:
                self.grid_setvalue(grid, row, obj_column, result)

    def grid_tecla_control(self, _grid, k, _is_shift, _is_control, _is_alt):
        if k in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            self.remove()

    def remove(self):
        recno = self.grid.recno()
        if recno >= 0:
            key = self.li_data[recno][0]
            if QTMessages.pregunta(self, _X(_("Delete %1?"), key)):
                del self.configurations_pae[key]
                self.refresh_gui()

    def up(self):
        recno = self.grid.recno()
        if recno < 1:
            return
        key_act = self.li_data[recno][0]
        key_otr = self.li_data[recno - 1][0]
        dic_act = self.configurations_pae[key_act]
        dic_otr = self.configurations_pae[key_otr]
        dic_act[self.korder], dic_otr[self.korder] = (
            dic_otr[self.korder],
            dic_act[self.korder],
        )
        self.configurations_pae[key_act] = dic_act
        self.configurations_pae[key_otr] = dic_otr
        self.refresh_gui()
        self.grid.goto(recno - 1, 0)

    def down(self):
        recno = self.grid.recno()
        if recno < 0 or recno >= len(self.li_data) - 1:
            return
        key_act = self.li_data[recno][0]
        key_otr = self.li_data[recno + 1][0]
        dic_act = self.configurations_pae[key_act]
        dic_otr = self.configurations_pae[key_otr]
        dic_act[self.korder], dic_otr[self.korder] = (
            dic_otr[self.korder],
            dic_act[self.korder],
        )
        self.configurations_pae[key_act] = dic_act
        self.configurations_pae[key_otr] = dic_otr
        self.refresh_gui()
        self.grid.goto(recno + 1, 0)

    def saveas(self):
        li_values = [x[0] for x in self.li_data]
        value = self.w_parent.bt_rival.text().strip()
        result = QTMessages.read_simple(
            self,
            _("Save current configuration"),
            _("Name"),
            value,
            width=360,
            li_values=li_values,
        )
        if result:
            dicn = self.w_parent.save_dic()
            if result in self.configurations_pae:
                dicant = self.configurations_pae[result]
                dicn[self.korder] = dicant[self.korder]
                dicn[self.kvisible] = dicant[self.kvisible]
            else:
                dicn[self.korder] = self.last_order() + 1
                dicn[self.kvisible] = True
            self.configurations_pae[result] = dicn
            self.refresh_gui()
            for pos, reg in enumerate(self.li_data):
                if reg[0] == result:
                    self.grid.goto(pos, 0)
                    return
