import os
import sys
import shutil


class Work:
    def __init__(self):
        self.path_r2 = os.path.abspath(os.path.join("..", "..", "lucaschessR2"))
        self.path_r6 = os.path.abspath(os.path.join("..", "..", "lucaschessR6"))
        self.pathcode_2 = os.path.join(self.path_r2, "bin", "Code")
        self.pathcode_6 = os.path.join(self.path_r6, "bin", "Code")

        self.st_add_gui = {"Controles.py", "MainWindow.py", "WBase.py", "WindowMemoria.py",
                           "WindowPuente.py", "WindowSonido.py", "Voyager.py"}

        self.li_changes = self.set_changes()

    @staticmethod
    def read_qtcore():
        li = []
        with open("QtCore.pyi", "rt") as f:
            for linea in f:
                if "Qt." in linea and " : " in linea and "..." in linea and "#" in linea:
                    linea = linea.strip()
                    x, y = linea.split(":")
                    x = x.strip()
                    y = y.strip().split("=")[0].strip()
                    li.append((f"Qt.{x}", f"{y}.{x}"))
        li.sort(key=lambda r: r[0], reverse=True)
        return li

    def set_changes(self):
        li_changes = []

        def add(xfrom1, xto1):
            li_changes.append((xfrom1, xto1))

        add("QtWidgets.QAction", "QtGui.QAction")
        add("QtWidgets.QShortcut", "QtGui.QShortcut")
        add("QTUtil.primary_screen().screenGeometry()", "QTUtil.primary_screen().availableGeometry()")
        add("self.NoDrag", "self.DragMode.NoDrag")
        add("self.NoAnchor", "self.ViewportAnchor.NoAnchor")
        add("self.escena.NoIndex", "self.escena.ItemIndexMethod.NoIndex")
        add("ly_abajo.SetFixedSize", "ly_abajo.SizeConstraint.SetFixedSize")
        add("QtCore.QRegExp", "QtCore.QRegularExpression")
        add("self.bfont.setWeight(75)", "self.bfont.setBold(True)")
        for pos in ("North", "South", "East", "West"):
            add(f"self.{pos}", f"self.TabPosition.{pos}")
        add(f"Qt.TextColorRole", f"Qt.ItemDataRole.ForegroundRole")
        add("square.tipo = QtCore.Qt.NoPen", "square.tipo = 0")
        add("cajon.tipo = QtCore.Qt.NoPen", "cajon.tipo = 0")
        add("self.bfont.setWeight(75)", "self.bfont.setBold(True)")
        add("int(event.modifiers())", "event.modifiers().value")
        add("& QtCore.Qt.ShiftModifier", "& QtCore.Qt.KeyboardModifier.ShiftModifier.value")
        add("& QtCore.Qt.AltModifier", "& QtCore.Qt.KeyboardModifier.AltModifier.value")
        add("& QtCore.Qt.ControlModifier", "& QtCore.Qt.KeyboardModifier.ControlModifier.value")
        add("event.delta()", "event.angleDelta().y()")
        add("resetMatrix", "resetTransform")
        add("FasterCode.get_pgn(from_sq, to_sq, promotion)",
            "FasterCode.get_pgn(from_sq, to_sq, '' if promotion is None else promotion)")
        add("Qt.transparent", "Qt.GlobalColor.transparent")
        add("painter.Antialiasing", "painter.RenderHint.Antialiasing")
        add("painter.SmoothPixmapTransform", "painter.RenderHint.SmoothPixmapTransform")
        add(".ScalableFonts", ".FontFilter.ScalableFonts")
        add("QtWidgets.QDesktopWidget().screenGeometry()", "QTUtil.primary_screen().availableGeometry()")
        add("QtWidgets.QDesktopWidget()", "QTUtil.primary_screen()")
        add("QtGui.QRegExpValidator(", "QtGui.QRegularExpressionValidator(")
        add("QLineEdit.Password", "QLineEdit.EchoMode.Password")
        add("self.NoInsert", "self.InsertPolicy.NoInsert")
        add("self.AdjustToMinimumContentsLengthWithIcon", "self.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon")
        add("QtGui.QTextOption.WordWrap", "QtGui.QTextOption.WrapMode.WordWrap")
        add("QtGui.QTextOption.NoWrap", "QtGui.QTextOption.WrapMode.NoWrap")

        liqt = self.read_qtcore()

        li_changes.extend(liqt)

        return li_changes

    def general_replace(self, basename, linea):
        if "PySide2" in linea:
            linea = linea.replace("PySide2", "PySide6")
            if basename in self.st_add_gui:
                if "QtGui" not in linea:
                    linea = linea.strip() + ", QtGui\n"
            return linea
        elif linea.startswith("VERSION ="):
            return "VERSION = \"R 6.0\"\n"

        for xfrom, xto in self.li_changes:
            if xfrom in linea:
                n = linea.index(xfrom)
                if not xfrom[-1].isalpha() or not linea[n + len(xfrom)].isalpha():
                    linea = linea.replace(xfrom, xto)

        return linea

    def copy_configuration(self, f2, q6):
        toolbutton = False
        for linea in f2:
            if linea.startswith("def int_toolbutton"):
                toolbutton = True

                q6.write("""def int_toolbutton(xint):
    for tbi in (Qt.ToolButtonStyle.ToolButtonIconOnly, Qt.ToolButtonStyle.ToolButtonTextOnly,
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon, Qt.ToolButtonStyle.ToolButtonTextUnderIcon):
        if xint == tbi.value:
            return tbi
    return Qt.ToolButtonStyle.ToolButtonTextUnderIcon


def toolbutton_int(qt_tbi):
    if qt_tbi in (Qt.ToolButtonStyle.ToolButtonIconOnly, Qt.ToolButtonStyle.ToolButtonTextOnly,
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon, Qt.ToolButtonStyle.ToolButtonTextUnderIcon):
        return qt_tbi.value
    return Qt.ToolButtonStyle.ToolButtonTextUnderIcon.value
""")

            elif linea.startswith("def active_folder"):
                toolbutton = False
            if toolbutton:
                continue
            linea = self.general_replace("Configuration.py", linea)
            q6.write(linea)

    def copy_lcdialog(self, f2, q6):
        remove = False
        for linea in f2:
            if "if QtWidgets.QDesktopWidget().screenCount() > 1:" in linea:
                remove = True
                continue
            if remove:
                if " QTUtil.desktop_size()" in linea:
                    remove = False
                    linea = linea[4:]
                    q6.write(linea)
                continue
            linea = self.general_replace("LCDialog.py", linea)
            q6.write(linea)

    def copy_sound(self, f2, q6):
        for linea in f2:
            if "QAudioDeviceInfo" in linea:
                if " import " in linea:
                    linea = linea.replace("QAudioDeviceInfo", "QMediaDevices")
                else:
                    linea = """        media_devices = QMediaDevices()
        device = media_devices.defaultAudioInput()\n"""
            if "QSound" in linea:
                if " import " in linea:
                    linea = linea.replace("QSound", "QSoundEffect")
                elif "self.qsound" in linea:
                    linea = "        self.qsound = QtMultimedia.QSoundEffect()\n" + \
                            "        self.qsound.setSource(QtCore.QUrl.fromLocalFile(path_wav))\n"
                else:
                    linea = "                qsound = QtMultimedia.QSoundEffect()\n" + \
                            "                qsound.setSource(QtCore.QUrl.fromLocalFile(path_wav))\n"
            if "not self.current.isFinished()" in linea:
                linea = linea.replace("not self.current.isFinished()", "self.current.isPlaying()")
            linea = self.general_replace("Sound.py", linea)
            q6.write(linea)

    def copy_qtutil(self, f2, q6):
        for linea in f2:
            if "PySide2" in linea:
                linea = linea.replace("PySide2", "PySide6")
            if linea.startswith("def desktop_size"):
                linea = """def primary_screen():
    app = QtWidgets.QApplication.instance()  # Get the QApplication instance
    if app is None:  # If there's no QApplication instance, create one
        app = QtWidgets.QApplication([])

    return app.primaryScreen()


def desktop_size():
"""
            elif "QtWidgets.QDesktopWidget().screenGeometry()" in linea:
                linea = linea.replace("QtWidgets.QDesktopWidget().screenGeometry()",
                                      "primary_screen().availableGeometry()")
            elif "QtWidgets.QDesktopWidget()" in linea:
                linea = linea.replace("QtWidgets.QDesktopWidget()", "primary_screen()")
            else:
                linea = self.general_replace("QTUtil.py", linea)
            q6.write(linea)

    def copy_scanner(self, f2, q6):
        for linea in f2:
            if linea.startswith("from Code.QT import Iconos"):
                linea = linea.strip() + ", QTUtil\n"
            else:
                linea = self.general_replace("Scanner.py", linea)
            q6.write(linea)

    def copy_code_file(self, path2):
        path6 = path2.replace("lucaschessR2", "lucaschessR6")

        with (open(path2, "rt", encoding="utf-8") as f2, open(path6, "wt", encoding="utf-8") as q6):
            basename = os.path.basename(path2)
            if basename == "Sound.py":
                self.copy_sound(f2, q6)
            elif basename == "Configuration.py":
                self.copy_configuration(f2, q6)
            elif basename == "QTUtil.py":
                self.copy_qtutil(f2, q6)
            elif basename == "LCDialog.py":
                self.copy_lcdialog(f2, q6)
            elif basename == "Scanner.py":
                self.copy_scanner(f2, q6)

            else:
                for linea in f2:
                    linea = self.general_replace(basename, linea)

                    q6.write(linea)

    def copy_code_folder(self, path2):
        print(path2)
        os.mkdir(path2.replace("lucaschessR2", "lucaschessR6"))
        entry: os.DirEntry
        for entry in os.scandir(path2):
            if entry.is_dir():
                if entry.name != "__pycache__":
                    self.copy_code_folder(entry.path)
            elif entry.name.endswith(".py"):
                self.copy_code_file(entry.path)

    def copy_code(self):
        if os.path.isdir(self.pathcode_6):
            shutil.rmtree(self.pathcode_6)
        self.copy_code_folder(self.pathcode_2)

    def remove_old(self):
        for folder in ("Resources", "bin"):
            path = os.path.abspath(os.path.join(self.path_r6, folder))
            if os.path.isdir(path):
                print("Deleting", folder)
                shutil.rmtree(path)

    def copy_resources(self):
        folder = "Resources"
        path_ori = os.path.abspath(os.path.join(self.path_r2, folder))
        path_dest = os.path.abspath(os.path.join(self.path_r6, folder))
        shutil.copytree(path_ori, path_dest)

    def copy_os(self):
        platform = sys.platform
        path_ori = os.path.abspath(os.path.join(self.path_r2, "bin", "OS", platform))
        path_dest = os.path.abspath(os.path.join(self.path_r6, "bin", "OS", platform))
        if os.path.exists(path_dest):
            try:
                shutil.rmtree(path_dest)
            except Exception as e:
                print(f"Error al intentar eliminar la carpeta: {str(e)}")

        shutil.copytree(path_ori, path_dest)

        if platform == "win32":
            path_fastercode37 = os.path.join(path_ori, "FasterCode.cp37-win32.pyd")
            path_fastercode312_ori = os.path.join(self.path_r6, "__Convert", "_fastercode", "source",
                                                  "FasterCode.cp312-win_amd64.pyd")
        else:
            path_fastercode37 = os.path.join(path_ori, "FasterCode.cpython-38-x86_64-linux-gnu.so")
            path_fastercode312_ori = os.path.join(self.path_r6, "__Convert", "_fastercode", "source",
                                                  "FasterCode.cpython-312-x86_64-linux-gnu.so")
        if os.path.isfile(path_fastercode37):
            os.remove(path_fastercode37)

        shutil.copy2(path_fastercode312_ori, path_dest)

    def copy_lucas(self):
        file = "LucasR.py"
        path_ori = os.path.abspath(os.path.join(self.path_r2, "bin", file))
        path_dest = os.path.abspath(os.path.join(self.path_r6, "bin", file))
        shutil.copy2(path_ori, path_dest)


w = Work()
w.remove_old()
w.copy_os()
w.copy_lucas()
w.copy_resources()
w.copy_code()
