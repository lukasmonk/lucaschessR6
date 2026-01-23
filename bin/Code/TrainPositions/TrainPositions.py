import os
import random
from typing import Optional

import Code
from Code.Z import Util
from Code.QT import Controles, FormLayout, Iconos, QTDialogs, QTMessages
from Code.SQL import UtilSQL
from Code.TrainPositions import ManagerTrainPositions
from Code.Translations import TrListas


class TrainPositions:
    """Manages training positions functionality including parameter configuration and training execution."""

    def __init__(self, wparent) -> None:
        """Initialize the TrainPositions manager.

        Args:
            wparent: Parent widget for dialogs and UI elements.
        """
        self.wparent = wparent

    def params_training_position(
        self,
        titulo: str,
        n_fen: int,
        pos: int,
        salta: bool,
        tutor_active: bool,
        tipo: str,
        remove_solutions: bool,
        show_comments: bool,
        advanced: bool,
    ) -> Optional[tuple[int, str, bool, bool, bool, bool, bool]]:
        """Display dialog to configure training position parameters.

        Args:
            titulo: Title for the dialog.
            n_fen: Total number of positions available.
            pos: Current position number.
            salta: Whether to jump to next position after solving.
            tutor_active: Whether tutor is initially active.
            tipo: Type of position selection (sequential/random).
            remove_solutions: Whether to remove pre-defined solutions.
            show_comments: Whether to show comments.
            advanced: Whether advanced mode is enabled.

        Returns:
            Tuple of (position, tipo, tutor_active, jump, remove_solutions, show_comments, advanced)
            or None if dialog was cancelled.
        """
        form = FormLayout.FormLayout(self.wparent, titulo, Iconos.Entrenamiento(), minimum_width=200)

        form.separador()
        label = f"{_("Select position")} (1..{n_fen})"
        form.spinbox(label, 1, n_fen, 70, pos)

        form.separador()
        li = [
            (_("Sequential"), "s"),
            (_("Random"), "r"),
            (_("Random with same sequence based on position"), "rk"),
        ]
        form.combobox(_("Type"), li, tipo)

        form.separador()
        form.checkbox(_("Tutor initially active"), tutor_active)

        form.separador()
        form.checkbox(_("Jump to the next after solving"), salta)

        form.separador()
        form.checkbox(_("Remove pre-defined solutions"), remove_solutions)

        form.separador()
        form.checkbox(_("Show comments"), show_comments)

        form.separador()
        form.checkbox(_("Advanced mode"), advanced)

        form.apart_simple_np(_("This advanced mode applies only to positions<br>with a solution included in the file"))

        resultado = form.run()
        if resultado:
            (
                position,
                tipo,
                tutor_active,
                jump,
                remove_solutions,
                show_comments,
                advanced,
            ) = resultado[1]
            if remove_solutions:
                advanced = False
            return (
                position,
                tipo,
                tutor_active,
                jump,
                remove_solutions,
                show_comments,
                advanced,
            )
        else:
            return None

    def train_position(self, training: str) -> None:
        """Execute training for a specific training file.

        Args:
            training: Path to the training file (.fns).
        """
        with QTMessages.one_moment_please(self.wparent):
            txt = os.path.basename(training)[:-4]
            tittraining = TrListas.dic_training().get(txt, txt)
            with Util.OpenCodec(training) as f:
                todo = f.read().strip()
            li_entrenamientos = [(linea, pos) for pos, linea in enumerate(todo.split("\n"), 1)]
            n_posiciones = len(li_entrenamientos)
        if n_posiciones == 0:
            return
        with UtilSQL.DictSQL(Code.configuration.paths.file_trainings()) as db:
            data = db[training]
            if not isinstance(data, dict):
                data = {}
            pos_ultimo = data.get("POSULTIMO", 1)
            jump = data.get("SALTA", False)
            tipo = data.get("TYPE", "s")
            advanced = data.get("ADVANCED", False)
            tutor_active = data.get("TUTOR_ACTIVE", True)
            remove_solutions = data.get("REMOVE_SOLUTIONS", False)
            show_comments = data.get("SHOW_COMMENTS", True)

            response = self.params_training_position(
                tittraining,
                n_posiciones,
                pos_ultimo,
                jump,
                tutor_active,
                tipo,
                remove_solutions,
                show_comments,
                advanced,
            )
            if response is None:
                return
            pos, tipo, tutor_active, jump, remove_solutions, show_comments, advanced = response
            db[training] = {
                "POSULTIMO": pos,
                "SALTA": jump,
                "TYPE": tipo,
                "ADVANCED": advanced,
                "REMOVE_SOLUTIONS": remove_solutions,
                "SHOW_COMMENTS": show_comments,
                "TUTOR_ACTIVE": tutor_active,
            }
        if tipo.startswith("r"):
            if tipo == "rk":
                random.seed(pos)
            random.shuffle(li_entrenamientos)
            pos = 1

        Code.procesador.manager = ManagerTrainPositions.ManagerTrainPositions(Code.procesador)
        Code.procesador.manager.set_training(training)
        Code.procesador.manager.start(
            pos,
            n_posiciones,
            tittraining,
            li_entrenamientos,
            tutor_active,
            jump,
            remove_solutions,
            show_comments,
            advanced,
        )


class TrainingFNS:
    """Represents a training file (.fns) with its path and display name."""

    def __init__(self, path: str, name: str) -> None:
        """Initialize a training file reference.

        Args:
            path: Absolute path to the training file.
            name: Display name for the training file.
        """
        self.name = name
        self.path = path


class TrainingDir:
    """Represents a directory containing training files and subdirectories."""

    folders: list["TrainingDir"]
    files: list[TrainingFNS]

    def __init__(self, carpeta: str) -> None:
        """Initialize a training directory.

        Args:
            carpeta: Path to the directory to scan for training files.
        """
        dic_training = TrListas.dic_training()

        def tr_training(txt):
            return dic_training.get(txt, txt)

        self.tr = tr_training

        if Util.same_path(carpeta, Code.configuration.paths.folder_tactics()):
            self.name = _("Personal tactics")
        else:
            self.name = tr_training(os.path.basename(carpeta))
        self.read(carpeta)

    def read(self, carpeta: str) -> None:
        """Scan directory and populate folders and files lists.

        Args:
            carpeta: Path to the directory to scan.
        """
        folders = []
        files = []
        for elem in os.scandir(carpeta):
            if elem.is_dir():
                folders.append(TrainingDir(elem.path))
            elif elem.name.endswith(".fns"):
                name = self.tr(elem.name[:-4])
                files.append(TrainingFNS(elem.path, name))
        self.folders = sorted(folders, key=lambda td: td.name)
        self.files = sorted(files, key=lambda td: td.name)

    def add_other_folder(self, folder: str) -> "TrainingDir":
        """Add another folder to this training directory.

        Args:
            folder: Path to the folder to add.

        Returns:
            The newly created TrainingDir instance.
        """
        tf = TrainingDir(folder)
        self.folders.append(tf)
        return tf

    def vacio(self) -> bool:
        """Check if this directory is empty (no folders or files).

        Returns:
            True if empty, False otherwise.
        """
        return (len(self.folders) + len(self.files)) == 0

    def reduce(self) -> None:
        """Recursively remove empty subdirectories."""
        li_borrar = []
        for n, folder in enumerate(self.folders):
            folder.reduce()
            if folder.vacio():
                li_borrar.append(n)
        if li_borrar:
            for n in range(len(li_borrar) - 1, -1, -1):
                del self.folders[li_borrar[n]]

    def menu(self, bmenu, add_menu_option) -> None:
        """Recursively build menu structure for training files.

        Args:
            bmenu: Menu object to populate.
            add_menu_option: Callback function to add menu options.
        """
        ico_op = Iconos.PuntoNaranja()
        ico_dr = Iconos.Carpeta()
        for folder in self.folders:
            submenu1 = bmenu.submenu(_F(folder.name), ico_dr)
            folder.menu(submenu1, add_menu_option)
        for training_file in self.files:
            add_menu_option(bmenu, f"ep_{training_file.path}", _F(training_file.name), ico_op)


def select_one_fns(owner) -> Optional[str]:
    """Display menu to select a training file.

    Args:
        owner: Parent widget for the menu.

    Returns:
        Relative path to selected training file, or None if cancelled.
    """
    tpirat = Controles.FontType("Chess Merida", Code.configuration.x_font_points + 4)

    def add_menu_option(menu, key: str, texto: str, icono, is_disabled: bool = False) -> None:
        if "KP" in texto:
            k2 = texto.index("K", 2)
            texto = texto[:k2] + texto[k2:].lower()
            menu.opcion(key, texto, icono, is_disabled, font_type=tpirat)
        else:
            menu.opcion(key, texto, icono, is_disabled)

    menu = QTDialogs.LCMenu(owner)
    td = TrainingDir(Code.path_resource("Trainings"))
    td.add_other_folder(Code.configuration.paths.folder_personal_trainings())
    td.add_other_folder(Code.configuration.paths.folder_tactics())
    td.reduce()
    td.menu(menu, add_menu_option)
    resp = menu.lanza()
    return resp if resp is None else Util.relative_path(resp[3:])
