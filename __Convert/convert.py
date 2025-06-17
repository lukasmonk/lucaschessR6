import os
import shutil
import sys


class Work:
    def __init__(self, path_lcr2):
        self.path_r2 = path_lcr2
        self.path_r6 = os.path.abspath(os.path.join("..", "..", "lucaschessR6"))
        self.pathcode_2 = os.path.join(self.path_r2, "bin", "Code")
        self.pathcode_6 = os.path.join(self.path_r6, "bin", "Code")

        self.st_add_gui = {"Controles.py", "MainWindow.py", "WBase.py", "WindowMemoria.py",
                           "WindowPuente.py", "WindowSonido.py", "Voyager.py"}

        self.li_changes = self.set_changes()

        self.python_version = f"{sys.version_info.major}{sys.version_info.minor}"

    @staticmethod
    def read_qtcore():
        li = []
        with open("QtCore.pyi", "rt") as f:
            for line in f:
                if "Qt." in line and " : " in line and "..." in line and "#" in line:
                    line = line.strip()
                    x, y = line.split(":")
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
        add("self.taller.mic_start(self)", "self.taller.mic_start()")

        liqt = self.read_qtcore()

        li_changes.extend(liqt)

        return li_changes

    def general_replace(self, basename, line_py):
        if "PySide2" in line_py:
            line_py = line_py.replace("PySide2", "PySide6")
            if basename in self.st_add_gui:
                if "QtGui" not in line_py:
                    line_py = line_py.strip() + ", QtGui\n"
            return line_py
        elif line_py.startswith("VERSION ="):
            return "VERSION = \"R 6.0\"\n"

        for xfrom, xto in self.li_changes:
            if xfrom in line_py:
                n = line_py.index(xfrom)
                if not xfrom[-1].isalpha() or not line_py[n + len(xfrom)].isalpha():
                    line_py = line_py.replace(xfrom, xto)

        return line_py

    def copy_configuration(self, lines_py, q6):
        toolbutton = False
        for line in lines_py:
            if line.startswith("def int_toolbutton"):
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

            elif line.startswith("def active_folder"):
                toolbutton = False
            if toolbutton:
                continue
            line = self.general_replace("Configuration.py", line)
            q6.write(line)

    def copy_lcdialog(self, lines_py, q6):
        remove = False
        for line in lines_py:
            if "if QtWidgets.QDesktopWidget().screenCount() > 1:" in line:
                remove = True
                continue
            if remove:
                if " QTUtil.desktop_size()" in line:
                    remove = False
                    line = line[4:]
                    q6.write(line)
                continue
            line = self.general_replace("LCDialog.py", line)
            q6.write(line)

    @staticmethod
    def copy_sound(q6):
        with open("Sound.py", "rt", encoding="utf-8") as f:
            q6.write(f.read())

    def copy_qtutil(self, lines_py, q6):
        for line in lines_py:
            if "PySide2" in line:
                line = line.replace("PySide2", "PySide6")
            if line.startswith("def desktop_size"):
                line = """def primary_screen():
    app = QtWidgets.QApplication.instance()  # Get the QApplication instance
    if app is None:  # If there's no QApplication instance, create one
        app = QtWidgets.QApplication([])

    return app.primaryScreen()


def desktop_size():
"""
            elif "QtWidgets.QDesktopWidget().screenGeometry()" in line:
                line = line.replace("QtWidgets.QDesktopWidget().screenGeometry()",
                                    "primary_screen().availableGeometry()")
            elif "QtWidgets.QDesktopWidget()" in line:
                line = line.replace("QtWidgets.QDesktopWidget()", "primary_screen()")
            else:
                line = self.general_replace("QTUtil.py", line)
            q6.write(line)

    def copy_scanner(self, lines_py, q6):
        for line in lines_py:
            if line.startswith("from Code.QT import Iconos"):
                line = line.strip() + ", QTUtil\n"
            else:
                line = self.general_replace("Scanner.py", line)
            q6.write(line)

    def convert_file(self, path6):
        with open(path6, "rt", encoding="utf-8") as f6_old:
            lines = [line for line in f6_old]

        with open(path6, "wt", encoding="utf-8") as q6:
            basename = os.path.basename(path6)
            if basename == "Sound.py":
                self.copy_sound(q6)
            elif basename == "Configuration.py":
                self.copy_configuration(lines, q6)
            elif basename == "QTUtil.py":
                self.copy_qtutil(lines, q6)
            elif basename == "LCDialog.py":
                self.copy_lcdialog(lines, q6)
            elif basename == "Scanner.py":
                self.copy_scanner(lines, q6)

            else:
                for line in lines:
                    line = self.general_replace(basename, line)

                    q6.write(line)

    def convert_code(self):
        print("Converting Code")

        def convert_code_folder(folder):
            entry: os.DirEntry
            for entry in os.scandir(folder):
                if entry.is_file():
                    self.convert_file(entry.path)
                elif entry.is_dir():
                    convert_code_folder(entry.path)

        convert_code_folder(self.pathcode_6)

    def copy_code(self):
        print("Copying Code")
        if os.path.isdir(self.pathcode_6):
            shutil.rmtree(self.pathcode_6)

        shutil.copytree(self.pathcode_2, self.pathcode_6)

    def remove_pycache(self):
        def limpia(folder):
            for entry in os.scandir(folder):
                if entry.is_dir():
                    if entry.name == "__pycache__":
                        shutil.rmtree(entry.path)
                    else:
                        limpia(entry.path)

        limpia(self.pathcode_6)

    def remove_old(self):
        for folder in ("Resources", "bin"):
            path = os.path.abspath(os.path.join(self.path_r6, folder))
            if os.path.isdir(path):
                print("Deleting", folder)
                shutil.rmtree(path)

    def copy_resources(self):
        folder = "Resources"
        print("Copying Resources")
        path_ori = os.path.abspath(os.path.join(self.path_r2, folder))
        path_dest = os.path.abspath(os.path.join(self.path_r6, folder))
        shutil.copytree(path_ori, path_dest)

    def copy_os(self):
        print("Copying engines")
        platform = sys.platform
        path_ori = os.path.abspath(os.path.join(self.path_r2, "bin", "OS", platform))
        path_dest = os.path.abspath(os.path.join(self.path_r6, "bin", "OS", platform))
        if os.path.exists(path_dest):
            try:
                shutil.rmtree(path_dest)
            except Exception as e:
                print(f"Error al intentar eliminar la carpeta: {str(e)}")

        shutil.copytree(path_ori, path_dest)

    def copy_lucas(self):
        file = "LucasR.py"
        path_ori = os.path.abspath(os.path.join(self.path_r2, "bin", file))
        path_dest = os.path.abspath(os.path.join(self.path_r6, "bin", file))
        shutil.copy2(path_ori, path_dest)

    def copy_fastercode(self):
        path_fastercode = os.path.join(self.path_r6, "__Convert", "_fastercode", "source",
                                       f"FasterCode.cp{self.python_version}-win_amd64.pyd")
        platform = sys.platform
        path_folder_os = os.path.join(self.path_r6, "bin", "OS", platform)
        for entry in os.scandir(path_folder_os):
            if entry.name.startswith("FasterCode"):
                os.remove(entry.path)
            elif entry.name == "__pycache__":
                shutil.rmtree(entry.path)

        shutil.copy2(path_fastercode, path_folder_os)

    def check_fastercode(self):
        platform = sys.platform
        if platform == "win32":
            path_fastercode_new = os.path.join(self.path_r6, "__Convert", "_fastercode", "source",
                                               f"FasterCode.cp{self.python_version}-win_amd64.pyd")
        else:
            path_fastercode_new = os.path.join(self.path_r6, "__Convert", "_fastercode", "source",
                                               f"FasterCode.cpython-{self.python_version}-x86_64-linux-gnu.so")

        if not os.path.isfile(path_fastercode_new):
            input("\nFasterCode must be created first from __Convert/_fastercode\n\n"
                  f"File to be created: {path_fastercode_new}\n\nPress enter to finish")
            return False
        return True


path_r2 = r"h:\pyLCR2"

w = Work(path_r2)
if w.check_fastercode():
    w.remove_old()
    w.copy_os()
    w.copy_lucas()
    w.copy_resources()
    w.copy_fastercode()
    w.copy_code()
    w.remove_pycache()
    w.convert_code()

    print("Done")
