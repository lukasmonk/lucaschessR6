import os
from pathlib import Path
from typing import Union

from PySide6 import QtWidgets

import Code
from Code.Z import Util


def select_pgn(wowner):
    configuration = Code.configuration
    path = read_file(wowner, configuration.pgn_folder(), "pgn")
    if path:
        carpeta, file = os.path.split(path)
        configuration.save_pgn_folder(carpeta)
    return path


def select_pgns(wowner):
    configuration = Code.configuration
    files = read_files(wowner, configuration.pgn_folder(), "pgn")
    if files:
        carpeta = os.path.dirname(files[0])
        configuration.save_pgn_folder(carpeta)
    return files


def get_existing_directory(owner, carpeta, titulo=None):
    carpeta = str(carpeta) if carpeta is not None else ""
    if titulo is None:
        titulo = _("Open Directory")
    options = QtWidgets.QFileDialog.Option.ShowDirsOnly
    options |= QtWidgets.QFileDialog.Option.DontResolveSymlinks
    if Code.configuration.x_mode_select_lc:
        options |= QtWidgets.QFileDialog.Option.DontUseNativeDialog
    return QtWidgets.QFileDialog.getExistingDirectory(owner, titulo, carpeta, options=options)


def _lf_title_filter(extension, titulo):
    if titulo is None:
        titulo = _("File")
    if " " in extension:
        filtro = extension
    else:
        pathext = f"*.{extension}"
        if extension == "*" and Util.is_linux():
            pathext = "*"
        filtro = f"{_('File')} {extension} ({pathext})"
    return titulo, filtro


def read_file(owner, carpeta, extension, titulo=None):
    carpeta = str(carpeta) if carpeta is not None else ""
    options = (
        QtWidgets.QFileDialog.Option.DontUseNativeDialog
        if Code.configuration.x_mode_select_lc
        else QtWidgets.QFileDialog.Option(0)
    )

    titulo, filtro = _lf_title_filter(extension, titulo)
    resp = QtWidgets.QFileDialog.getOpenFileName(owner, titulo, carpeta, filtro, options=options)
    return resp[0] if resp else None


def read_files(owner, carpeta, extension, titulo=None):
    carpeta = str(carpeta) if carpeta is not None else ""
    options = (
        QtWidgets.QFileDialog.Option.DontUseNativeDialog
        if Code.configuration.x_mode_select_lc
        else QtWidgets.QFileDialog.Option(0)
    )

    titulo, filtro = _lf_title_filter(extension, titulo)
    resp = QtWidgets.QFileDialog.getOpenFileNames(
        owner, titulo, carpeta, filtro, options=options
    )
    return resp[0] if resp else None


def read_or_create_file(owner, carpeta, extension, titulo=None):
    carpeta = str(carpeta) if carpeta is not None else ""
    options = QtWidgets.QFileDialog.Option.DontConfirmOverwrite
    if Code.configuration.x_mode_select_lc:
        options |= QtWidgets.QFileDialog.Option.DontUseNativeDialog
    titulo, filtro = _lf_title_filter(extension, titulo)
    resp = QtWidgets.QFileDialog.getSaveFileName(owner, titulo, carpeta, filtro, options=options)
    return resp[0] if resp else None


def save_file(
        main_window: QtWidgets.QWidget | None,
        titulo: str,
        carpeta: Union[str, Path, None],
        extension: str,
        confirm_overwrite: bool = True
) -> str:
    titulo, filtro = _lf_title_filter(extension, titulo)
    carpeta = str(carpeta) if carpeta is not None else ""

    options = QtWidgets.QFileDialog.Option(0)
    if Code.configuration.x_mode_select_lc:
        options |= QtWidgets.QFileDialog.Option.DontUseNativeDialog
    if not confirm_overwrite:
        options |= QtWidgets.QFileDialog.Option.DontConfirmOverwrite

    resp, _ = QtWidgets.QFileDialog.getSaveFileName(main_window, titulo, carpeta, filtro, options=options)
    return resp or ""
