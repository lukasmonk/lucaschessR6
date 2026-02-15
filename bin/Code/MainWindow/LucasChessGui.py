import sys

from PySide6 import QtCore, QtWidgets

import Code
from Code.Z import XRun
from Code.Base.Constantes import ExitProgram
from Code.Config import Configuration, Usuarios
from Code.MainWindow import InitApp
from Code.QT import Colocacion, Controles, GarbageCollector, Iconos
from Code.Translations import SelectLanguage


def run_gui(procesador):
    main_config = Configuration.Configuration("")
    main_config.lee()
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True)

    app = QtWidgets.QApplication([])

    first_run = main_config.paths.is_first_time
    main_config.lee()  # Necesaria la doble lectura, para que _ permanezca como builting tras QApplication

    # Usuarios
    list_users = Usuarios.Usuarios().list_users
    if len(list_users) > 1:
        user = pide_usuario(list_users)
        if user == list_users[0]:
            user = None
    else:
        user = None

    procesador.start_with_user(user)
    configuration = Code.configuration

    nom_pieces_ori = configuration.dic_conf_boards_pk["BASE"]["o_base"]["x_nomPiezas"]
    Code.all_pieces.save_all_png(nom_pieces_ori, 30)

    if user:
        if not configuration.x_player:
            configuration.x_player = user.name
            configuration.graba()
        elif configuration.x_player != user.name:
            for usu in list_users:
                if usu.number == user.number:
                    usu.name = configuration.x_player
                    Usuarios.Usuarios().save_list(list_users)

    if first_run:
        if user:
            conf_main = Configuration.Configuration("")
            configuration.x_translator = conf_main.x_translator
            configuration.start()
            configuration.limpia(user.name)
            configuration.set_folders()
            configuration.graba()

        else:
            SelectLanguage.menu_select_language(None)

    translator = QtCore.QTranslator()
    translations_path = QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.LibraryPath.TranslationsPath)
    path_qm = f"qtbase_{configuration.x_translator}.qm"
    if translator.load(path_qm, translations_path):
        app.installTranslator(translator)

    InitApp.init_app_style(app, configuration)

    procesador.iniciar_gui()

    Code.garbage_collector = GarbageCollector.GarbageCollector()
    Code.garbage_collector.start()

    resp = app.exec()
    Code.garbage_collector.stop()

    if resp == ExitProgram.REINIT:
        XRun.run_lucas()

    return resp


class WPassword(QtWidgets.QDialog):
    def __init__(self, li_usuarios):
        QtWidgets.QDialog.__init__(self, None)

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.Dialog
            | QtCore.Qt.WindowType.WindowTitleHint
        )

        self.setWindowTitle(f"{Code.lucas_chess} {Code.VERSION}")
        self.setWindowIcon(Iconos.Aplicacion64())

        font = Controles.FontType(puntos=14)
        self.setFont(font)

        self.liUsuarios = li_usuarios

        li_options = [(usuario.name, nusuario) for nusuario, usuario in enumerate(li_usuarios)]
        lb_u = Controles.LB(self, f"{_('User')}:").set_font(font)
        self.cbU = Controles.CB(self, li_options, li_usuarios[0]).set_font(font)

        lb_p = Controles.LB(self, f"{_('Password')}:").set_font(font)
        self.edP = Controles.ED(self).password().set_font(font)

        btaceptar = Controles.PB(self, _("Accept"), rutina=self.accept, plano=False).set_font(font)
        btcancelar = Controles.PB(self, _("Cancel"), rutina=self.reject, plano=False).set_font(font)

        ly = Colocacion.G()
        ly.controld(lb_u, 0, 0).control(self.cbU, 0, 1)
        ly.controld(lb_p, 1, 0).control(self.edP, 1, 1)

        lybt = Colocacion.H().relleno().control(btaceptar).espacio(10).control(btcancelar)

        layout = Colocacion.V().otro(ly).espacio(10).otro(lybt).margen(10)

        self.setLayout(layout)
        self.edP.setFocus()

    def resultado(self):
        nusuario = self.cbU.valor()
        usuario = self.liUsuarios[nusuario]
        return usuario if self.edP.texto().strip() == usuario.password else None


def pide_usuario(li_usuarios):
    # Miramos si alguno tiene key, si es asi, lanzamos ventana
    si_pass = False
    for usuario in li_usuarios:
        if usuario.password:
            si_pass = True
    if si_pass:
        intentos = 3
        while True:
            w = WPassword(li_usuarios)
            if w.exec():
                usuario = w.resultado()
                if usuario:
                    break
            else:
                sys.exit()

            intentos -= 1
            if intentos == 0:
                sys.exit()
    else:
        if len(li_usuarios) <= 1:
            return None
        else:
            menu = Controles.Menu(None)  # No puede ser LCmenu, ya que todavia no existe la configuration
            menu.set_font(Controles.FontType(puntos=14))
            menu.opcion(None, _("Select your user"), Iconos.Usuarios())
            menu.separador()

            for usuario in li_usuarios:
                menu.opcion(
                    usuario,
                    usuario.name,
                    Iconos.Naranja() if usuario.number > 0 else Iconos.Verde(),
                )
                menu.separador()

            usuario = menu.lanza()

    return usuario
