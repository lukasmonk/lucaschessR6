import os
import shutil
import sys
from pathlib import Path


class ProjectConverter:
    """
    A class to handle the conversion of a Python project from one version (PySide2/Qt5)
    to another (PySide6/Qt6).
    """

    def __init__(self, source_project_path: str):
        """
        Initializes the ProjectConverter with the path to the source project (R2).

        Args:
            source_project_path (str): The absolute path to the lucaschessR2 project.
        """
        self.source_path = Path(source_project_path)
        self.target_path = Path.cwd().parent.parent / "lucaschessR6"

        self.source_code_path = self.source_path / "bin" / "Code"
        self.target_code_path = self.target_path / "bin" / "Code"

        # Set of GUI files that might need QtGui import added if PySide2 is present
        self.gui_files_to_check = {
            "Controles.py", "MainWindow.py", "WBase.py", "WindowMemoria.py",
            "WindowPuente.py", "WindowSonido.py", "Voyager.py"
        }

        self.replacements = self._define_replacements()
        self.python_version = f"{sys.version_info.major}{sys.version_info.minor}"

    def _read_qtcore_replacements(self) -> list[tuple]:
        """
        Reads QtCore.pyi to extract Qt related replacements.
        """
        qt_replacements = []
        try:
            with open("QtCore.pyi", "rt", encoding="utf-8") as f:
                for line in f:
                    if "Qt." in line and " : " in line and "..." in line and "#" in line:
                        line = line.strip()
                        try:
                            x, y = line.split(":")
                            x = x.strip()
                            y = y.strip().split("=")[0].strip()
                            qt_replacements.append((f"Qt.{x}", f"{y}.{x}"))
                        except ValueError:
                            # Handle cases where split might fail if line format is unexpected
                            print(f"Warning: Could not parse QtCore.pyi line: {line.strip()}")
            qt_replacements.sort(key=lambda r: r[0], reverse=True)
        except FileNotFoundError:
            print("Error: QtCore.pyi not found. Cannot load QtCore replacements.")
        return qt_replacements

    def _define_replacements(self) -> list[tuple]:
        """
        Defines all the string replacements to be made during the conversion.
        """
        changes = []

        def add_change(old_str, new_str):
            changes.append((old_str, new_str))

        add_change("QtWidgets.QAction", "QtGui.QAction")
        add_change("QtWidgets.QShortcut", "QtGui.QShortcut")
        add_change("QTUtil.primary_screen().screenGeometry()", "QTUtil.primary_screen().availableGeometry()")
        add_change("self.NoDrag", "self.DragMode.NoDrag")
        add_change("self.NoAnchor", "self.ViewportAnchor.NoAnchor")
        add_change("self.escena.NoIndex", "self.escena.ItemIndexMethod.NoIndex")
        add_change("ly_abajo.SetFixedSize", "ly_abajo.SizeConstraint.SetFixedSize")
        add_change("QtCore.QRegExp", "QtCore.QRegularExpression")
        add_change("self.bfont.setWeight(75)", "self.bfont.setBold(True)") # This line was duplicated in original
        for pos in ("North", "South", "East", "West"):
            add_change(f"self.{pos}", f"self.TabPosition.{pos}")
        add_change(f"Qt.TextColorRole", f"Qt.ItemDataRole.ForegroundRole")
        add_change("square.tipo = QtCore.Qt.NoPen", "square.tipo = 0")
        add_change("cajon.tipo = QtCore.Qt.NoPen", "cajon.tipo = 0")
        add_change("int(event.modifiers())", "event.modifiers().value")
        add_change("& QtCore.Qt.ShiftModifier", "& QtCore.Qt.KeyboardModifier.ShiftModifier.value")
        add_change("& QtCore.Qt.AltModifier", "& QtCore.Qt.KeyboardModifier.AltModifier.value")
        add_change("& QtCore.Qt.ControlModifier", "& QtCore.Qt.KeyboardModifier.ControlModifier.value")
        add_change("event.delta()", "event.angleDelta().y()")
        add_change("resetMatrix", "resetTransform")
        add_change("FasterCode.get_pgn(from_sq, to_sq, promotion)",
                   "FasterCode.get_pgn(from_sq, to_sq, '' if promotion is None else promotion)")
        add_change("Qt.transparent", "Qt.GlobalColor.transparent")
        add_change("painter.Antialiasing", "painter.RenderHint.Antialiasing")
        add_change("painter.SmoothPixmapTransform", "painter.RenderHint.SmoothPixmapTransform")
        add_change(".ScalableFonts", ".FontFilter.ScalableFonts")
        add_change("QtWidgets.QDesktopWidget().screenGeometry()", "QTUtil.primary_screen().availableGeometry()")
        add_change("QtWidgets.QDesktopWidget()", "QTUtil.primary_screen()")
        add_change("QtGui.QRegExpValidator(", "QtGui.QRegularExpressionValidator(")
        add_change("QLineEdit.Password", "QLineEdit.EchoMode.Password")
        add_change("self.NoInsert", "self.InsertPolicy.NoInsert")
        add_change("self.AdjustToMinimumContentsLengthWithIcon", "self.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon")
        add_change("QtGui.QTextOption.WordWrap", "QtGui.QTextOption.WrapMode.WordWrap")
        add_change("QtGui.QTextOption.NoWrap", "QtGui.QTextOption.WrapMode.NoWrap")
        add_change("self.taller.mic_start(self)", "self.taller.mic_start()")

        changes.extend(self._read_qtcore_replacements())
        return changes

    def _apply_general_replacements(self, filename: str, line: str) -> str:
        """
        Applies general string replacements to a given line.
        """
        if "PySide2" in line:
            line = line.replace("PySide2", "PySide6")
            if filename in self.gui_files_to_check and "QtGui" not in line:
                # This logic assumes the import is on the same line.
                # A more robust solution might involve parsing imports more carefully.
                if line.strip().endswith("\n") or not line.strip(): # Check if line ends with newline or is empty
                    line = line.strip() + ", QtGui\n"
                else:
                    line = line.strip() + ", QtGui" + "\n" # Ensure newline
            return line
        elif line.startswith("VERSION ="):
            return "VERSION = \"R 6.0\"\n"

        for old_str, new_str in self.replacements:
            if old_str in line:
                n = line.index(old_str)
                # Ensure we don't replace substrings that are part of larger words
                if not old_str[-1].isalpha() or n + len(old_str) >= len(line) or not line[n + len(old_str)].isalpha():
                    line = line.replace(old_str, new_str)
        return line

    def _handle_configuration_file(self, lines: list[str], output_file):
        """
        Handles specific replacements for 'Configuration.py'.
        """
        toolbutton_section = False
        for line in lines:
            if line.strip().startswith("def int_toolbutton"):
                toolbutton_section = True
                output_file.write("""def int_toolbutton(xint):
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
                continue
            elif line.strip().startswith("def active_folder"):
                toolbutton_section = False
            if toolbutton_section:
                continue
            output_file.write(self._apply_general_replacements("Configuration.py", line))

    def _handle_lcdialog_file(self, lines: list[str], output_file):
        """
        Handles specific replacements for 'LCDialog.py'.
        """
        remove_lines = False
        for line in lines:
            if "if QtWidgets.QDesktopWidget().screenCount() > 1:" in line:
                remove_lines = True
                continue
            if remove_lines:
                if " QTUtil.desktop_size()" in line:
                    remove_lines = False
                    line = line[4:]  # Remove indentation
                    output_file.write(line)
                continue
            output_file.write(self._apply_general_replacements("LCDialog.py", line))

    def _handle_sound_file(self, output_file):
        """
        Copies 'Sound.py' directly as it needs no specific transformations.
        """
        try:
            with open("Sound.py", "rt", encoding="utf-8") as f:
                output_file.write(f.read())
        except FileNotFoundError:
            print(f"Error: Sound.py not found at {self.source_code_path / 'Sound.py'}")

    def _handle_qtutil_file(self, lines: list[str], output_file):
        """
        Handles specific replacements for 'QTUtil.py'.
        """
        for line in lines:
            if "PySide2" in line:
                line = line.replace("PySide2", "PySide6")
            if line.strip().startswith("def desktop_size"):
                # Insert primary_screen function before desktop_size
                output_file.write("""def primary_screen():
    app = QtWidgets.QApplication.instance()  # Get the QApplication instance
    if app is None:  # If there's no QApplication instance, create one
        app = QtWidgets.QApplication([])

    return app.primaryScreen()


def desktop_size():
""")
                # The original line "def desktop_size" itself will be skipped by the next conditions
                # or handled by general_replace if it contains other keywords.
                # However, this specific replacement effectively overwrites it.
                continue # Skip the original line
            elif "QtWidgets.QDesktopWidget().screenGeometry()" in line:
                line = line.replace("QtWidgets.QDesktopWidget().screenGeometry()",
                                    "primary_screen().availableGeometry()")
            elif "QtWidgets.QDesktopWidget()" in line:
                line = line.replace("QtWidgets.QDesktopWidget()", "primary_screen()")
            else:
                line = self._apply_general_replacements("QTUtil.py", line)
            output_file.write(line)

    def _handle_scanner_file(self, lines: list[str], output_file):
        """
        Handles specific replacements for 'Scanner.py'.
        """
        for line in lines:
            if line.strip().startswith("from Code.QT import Iconos"):
                line = line.strip() + ", QTUtil\n"
            else:
                line = self._apply_general_replacements("Scanner.py", line)
            output_file.write(line)

    def _convert_single_file(self, file_path: Path):
        """
        Converts a single Python file by applying defined replacements.
        """
        try:
            with open(file_path, "rt", encoding="utf-8") as f_old:
                lines = f_old.readlines()

            # Ensure the parent directory exists for the target file
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wt", encoding="utf-8") as f_new:
                filename = file_path.name
                if filename == "Sound.py":
                    self._handle_sound_file(f_new)
                elif filename == "Configuration.py":
                    self._handle_configuration_file(lines, f_new)
                elif filename == "QTUtil.py":
                    self._handle_qtutil_file(lines, f_new)
                elif filename == "LCDialog.py":
                    self._handle_lcdialog_file(lines, f_new)
                elif filename == "Scanner.py":
                    self._handle_scanner_file(lines, f_new)
                else:
                    for line in lines:
                        f_new.write(self._apply_general_replacements(filename, line))
        except Exception as e:
            print(f"Error converting file {file_path}: {e}")

    def convert_code_files(self):
        """
        Converts all Python files in the 'Code' directory.
        """
        print("Converting Code files...")

        def _walk_and_convert(folder: Path):
            for entry in folder.iterdir():
                if entry.is_file() and entry.suffix == ".py":
                    self._convert_single_file(entry)
                elif entry.is_dir():
                    _walk_and_convert(entry)

        _walk_and_convert(self.target_code_path)
        print("Code conversion complete.")

    def copy_code_directory(self):
        """
        Copies the entire 'Code' directory from R2 to R6.
        """
        print(f"Copying Code from {self.source_code_path} to {self.target_code_path}...")
        if self.target_code_path.exists():
            try:
                shutil.rmtree(self.target_code_path)
            except OSError as e:
                print(f"Error deleting old Code directory: {e}")
                return False
        try:
            shutil.copytree(self.source_code_path, self.target_code_path)
            print("Code directory copied.")
            return True
        except OSError as e:
            print(f"Error copying Code directory: {e}")
            return False

    def remove_pycache(self):
        """
        Removes all '__pycache__' directories from the target Code path.
        """
        print("Removing __pycache__ directories...")

        def _clean_folder(folder: Path):
            for entry in folder.iterdir():
                if entry.is_dir():
                    if entry.name == "__pycache__":
                        try:
                            shutil.rmtree(entry)
                        except OSError as e:
                            print(f"Error removing {entry}: {e}")
                    else:
                        _clean_folder(entry)

        _clean_folder(self.target_code_path)

    def remove_old_target_folders(self):
        """
        Removes old 'Resources' and 'bin' folders from the target R6 path.
        """
        print("Removing old target folders (Resources, bin)...")
        for folder_name in ("Resources", "bin"):
            path_to_remove = self.target_path / folder_name
            if path_to_remove.is_dir():
                try:
                    print(f"Deleting {path_to_remove}")
                    shutil.rmtree(path_to_remove)
                except OSError as e:
                    print(f"Error deleting {path_to_remove}: {e}")
        print("Old target folders removed.")

    def copy_resources(self):
        """
        Copies the 'Resources' folder from R2 to R6.
        """
        print("Copying Resources...")
        source_resources_path = self.source_path / "Resources"
        target_resources_path = self.target_path / "Resources"
        try:
            shutil.copytree(source_resources_path, target_resources_path)
            print("Resources copied.")
            return True
        except OSError as e:
            print(f"Error copying Resources: {e}")
            return False

    def copy_os_specific_engines(self):
        """
        Copies OS-specific engine files from R2 to R6.
        """
        print("Copying engines (OS-specific)...")
        platform_dir = sys.platform
        source_os_path = self.source_path / "bin" / "OS" / platform_dir
        target_os_path = self.target_path / "bin" / "OS" / platform_dir

        if target_os_path.exists():
            try:
                shutil.rmtree(target_os_path)
            except OSError as e:
                print(f"Error deleting old OS-specific engine folder: {e}")
                return False
        try:
            shutil.copytree(source_os_path, target_os_path)
            print("OS-specific engines copied.")
            return True
        except OSError as e:
            print(f"Error copying OS-specific engines: {e}")
            return False

    def copy_lucas_file(self):
        """
        Copies 'LucasR.py' from R2 to R6.
        """
        print("Copying LucasR.py...")
        file_name = "LucasR.py"
        source_file = self.source_path / "bin" / file_name
        target_file = self.target_path / "bin" / file_name
        try:
            shutil.copy2(source_file, target_file)
            print("LucasR.py copied.")
            return True
        except FileNotFoundError:
            print(f"Error: {source_file} not found.")
            return False
        except OSError as e:
            print(f"Error copying LucasR.py: {e}")
            return False

    def copy_fastercode_module(self):
        """
        Copies the compiled FasterCode module to the OS-specific directory.
        """
        print("Copying FasterCode module...")
        platform_dir = sys.platform
        fastercode_source_folder = self.target_path / "__Convert" / "_fastercode" / "source"

        if platform_dir == "win32":
            fastercode_filename = f"FasterCode.cp{self.python_version}-win_amd64.pyd"
        else: # Assuming Linux or other Unix-like for '.so'
            fastercode_filename = f"FasterCode.cpython-{self.python_version}-x86_64-linux-gnu.so"

        source_fastercode_path = fastercode_source_folder / fastercode_filename
        target_os_folder = self.target_path / "bin" / "OS" / platform_dir

        if not source_fastercode_path.is_file():
            print(f"Error: FasterCode module not found at {source_fastercode_path}. "
                  "Please ensure it is built first.")
            return False

        # Remove existing FasterCode files and __pycache__ in the target OS folder
        for entry in target_os_folder.iterdir():
            if entry.name.startswith("FasterCode"):
                try:
                    os.remove(entry)
                except OSError as e:
                    print(f"Error removing old FasterCode file {entry}: {e}")
            elif entry.name == "__pycache__":
                try:
                    shutil.rmtree(entry)
                except OSError as e:
                    print(f"Error removing __pycache__ in OS folder {entry}: {e}")

        try:
            shutil.copy2(source_fastercode_path, target_os_folder)
            print(f"FasterCode ({fastercode_filename}) copied to {target_os_folder}.")
            return True
        except OSError as e:
            print(f"Error copying FasterCode module: {e}")
            return False

    def check_fastercode_exists(self):
        """
        Checks if the compiled FasterCode module exists.
        """
        platform_dir = sys.platform
        fastercode_path = self.target_path / "__Convert" / "_fastercode" / "source"

        if platform_dir == "win32":
            fastercode_file = fastercode_path / f"FasterCode.cp{self.python_version}-win_amd64.pyd"
        else:
            fastercode_file = fastercode_path / f"FasterCode.cpython-{self.python_version}-x86_64-linux-gnu.so"

        if not fastercode_file.is_file():
            input(f"\nFasterCode must be created from __Convert/_fastercode\n\n"
                  f"File to be created: {fastercode_file}\n\nPress enter to finish")

    def run_conversion(self):
        """
        Executes the full conversion process.
        """
        print("Starting conversion process...")

        # Step 1: Initial cleanup of target R6 project
        self.remove_old_target_folders()

        # Step 2: Copy essential components
        if not self.copy_os_specific_engines(): return
        if not self.copy_lucas_file(): return
        if not self.copy_resources(): return
        if not self.copy_fastercode_module(): return

        # Step 3: Copy and convert 'Code' directory
        if not self.copy_code_directory(): return
        self.remove_pycache() # Remove __pycache__ from newly copied code
        self.convert_code_files() # Apply transformations to copied code

        print("\nConversion Done!")

        self.check_fastercode_exists()


if __name__ == "__main__":
    while True:
        source_project_base_path = input("Folder with version 2 of the programme: ")

        if not source_project_base_path:
            sys.exit(1)

        path_py = os.path.join(source_project_base_path, "bin", "LucasR.py")
        if not os.path.isfile(path_py):
            print(f"There is not file: {path_py}")
        else:
            break

    converter = ProjectConverter(source_project_base_path)
    converter.run_conversion()

