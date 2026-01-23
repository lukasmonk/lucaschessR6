from PySide6 import QtGui

import Code
from Code.QT import Colocacion, Controles, Iconos, LCDialog, QTMessages


class WAlbum(LCDialog.LCDialog):
    def __init__(self, wowner, album):

        self.album = album
        titulo = album.name

        LCDialog.LCDialog.__init__(self, wowner, titulo, album.icono(), "albumes")

        self.configuration = Code.configuration

        ncromos = len(album)
        dic_t = {
            6: 3,
            8: 4,
            10: 5,
            12: 6,
            14: 7,
            16: 8,
            18: 6,
            20: 5,
            24: 6,
            28: 7,
            32: 8,
            40: 8,
        }
        divisor = dic_t.get(ncromos, 6)

        layout = Colocacion.G()

        pte = False

        ico_caracol = Iconos.Caracol()

        for pos in range(ncromos):
            cromo = album.get_cromo(pos)
            if not cromo.hecho:
                pte = True

            pb = Controles.PB(self, "", rutina=self.pulsado, plano=False)
            pb.setFixedSize(110, 110)
            pb.key = cromo

            if cromo.hecho:
                icono = cromo.icono()
                pixmap = icono.pixmap(64, 64)
                icono.addPixmap(pixmap, QtGui.QIcon.Mode.Disabled)
                pb.setEnabled(False)
            else:
                icono = ico_caracol

            pb.set_icono(icono, 64)

            lb = Controles.LB(self, cromo.name)
            lb.set_font_type(puntos=10, peso=75)
            row = pos // divisor
            col = pos % divisor
            layout.controlc(pb, row * 2, col)
            layout.controlc(lb, row * 2 + 1, col)

        mensaje = _("Select a slot to play against and get its image if you win") if pte else ""
        lb = Controles.LB(self, mensaje)

        pb_exit = Controles.PB(self, _("Close"), self.quit, plano=False).set_icono(Iconos.MainMenu())
        ly_p = Colocacion.H().relleno().control(lb).relleno().control(pb_exit)
        if not pte:
            pb_rebuild = Controles.PB(self, _("Rebuild this album"), self.rebuild, plano=False).set_icono(
                Iconos.Delete()
            )
            ly_p.control(pb_rebuild)

        ly_t = Colocacion.V().otro(layout).otro(ly_p)

        self.setLayout(ly_t)

        self.restore_video(with_tam=False)

        self.resultado = None, None

    def finalize(self):
        self.save_video()

    def closeEvent(self, event):
        self.finalize()

    def quit(self):
        self.finalize()
        self.reject()

    def rebuild(self):
        if QTMessages.pregunta(self, _("Do you want to remove this album and create a new one?")):
            self.album.reset()
            self.finalize()
            self.resultado = None, True
            self.reject()

    def pulsado(self):
        cromo = self.sender().key
        self.resultado = cromo, False
        self.accept()


def elige_cromo(wowner, album):
    w = WAlbum(wowner, album)
    w.exec()
    return w.resultado
