"""
Update system for LucasChess.
Enhanced with security, compression, backup, and logging features.
"""

import os
import shutil
import urllib.request
import urllib.error
from typing import Optional

import Code
from Code import Util
from Code.Board import Eboard
from Code.QT import QTMessages, SelectFiles

# Import new update system modules
from Code.Update import UpdateCompression
from Code.Update import UpdateSecurity
from Code.Update import UpdateLogger
from Code.Update import UpdateBackup


# Update server URLs
WEBUPDATES = "https://lucaschess.pythonanywhere.com/static/updater/updates_%s.txt" % (
    "win32" if Util.is_windows() else "linux"
)

WEBUPDATES_EBOARD_VERSION = "https://lucaschess.pythonanywhere.com/static/updater/version_eboards_%s.txt" % (
    "win32" if Util.is_windows() else "linux"
)

WEBUPDATES_EBOARD_ZIP = "https://lucaschess.pythonanywhere.com/static/updater/eboards_%s.zip" % (
    "win32" if Util.is_windows() else "linux"
)


class UpdateError(Exception):
    """Base exception for update errors."""

    pass


def update_file(titulo: str, urlfichero: str, tam: int, sha256: Optional[str] = None) -> bool:
    """
    Download and apply an update file.

    Args:
        titulo: Title for progress dialog
        urlfichero: URL of update file
        tam: Expected file size in bytes
        sha256: Optional SHA256 checksum for verification

    Returns:
        True if update successful, False otherwise
    """
    logger = UpdateLogger.get_logger()
    backup_path = None

    try:
        # Clean up and create actual folder
        shutil.rmtree("actual", ignore_errors=True)
        Util.create_folder("actual")

        # Check disk space for backup
        if not UpdateBackup.check_disk_space_for_backup():
            logger.error("Insufficient disk space for backup")
            QTMessages.message_error(None, _("Insufficient disk space to perform update"))
            return False

        # Download file with progress
        UpdateLogger.log_download_start(urlfichero, tam)

        global progreso, is_beginning
        progreso = QTMessages.ProgressBarSimple(None, titulo, _("Downloading..."), 100).mostrar()
        is_beginning = True

        def hook(bloques, tambloque, tamfichero):
            global progreso, is_beginning
            if is_beginning:
                total = tamfichero / tambloque
                if tambloque * total < tamfichero:
                    total += 1
                progreso.set_total(total)
                is_beginning = False
            progreso.inc()

        local_file = urlfichero.split("/")[-1]
        local_file = f"actual/{local_file}"

        try:
            urllib.request.urlretrieve(urlfichero, local_file, hook)
        except Exception as e:
            logger.error(f"Download failed: {e}")
            progreso.cerrar()
            return False

        _is_canceled = progreso.is_canceled()
        progreso.cerrar()

        if _is_canceled:
            logger.info("Update canceled by user")
            return False

        UpdateLogger.log_download_complete(local_file)

        # Verify file size
        actual_size = Util.filesize(local_file)
        if tam != actual_size:
            logger.error(f"Size mismatch: expected {tam}, got {actual_size}")
            QTMessages.message_error(None, _("Downloaded file size mismatch"))
            return False

        # Verify checksum if provided
        if sha256:
            try:
                UpdateLogger.log_checksum_verification(local_file, sha256)
                UpdateSecurity.verify_checksum(local_file, sha256)
                UpdateLogger.log_checksum_verified()
            except UpdateSecurity.ChecksumMismatchError as e:
                logger.error(f"Checksum verification failed: {e}")
                QTMessages.message_error(
                    None, _("Update file checksum verification failed.\nFile may be corrupted or tampered with.")
                )
                return False

        # Verify archive is valid
        if not UpdateCompression.is_valid_archive(local_file):
            logger.error(f"Invalid or corrupted archive: {local_file}")
            QTMessages.message_error(None, _("Downloaded file is corrupted"))
            return False

        # Create backup before proceeding
        try:
            current_version = Code.VERSION
            UpdateLogger.log_backup_created("creating...")
            backup_path = UpdateBackup.create_backup(current_version)
            UpdateLogger.log_backup_created(backup_path)
        except UpdateBackup.BackupError as e:
            logger.error(f"Backup creation failed: {e}")
            QTMessages.message_error(None, _("Failed to create backup before update"))
            return False

        # Extract archive
        try:
            archive_type = UpdateCompression.detect_archive_type(local_file)
            UpdateLogger.log_extraction_start(archive_type)

            progreso = QTMessages.one_moment_please(None, _("Extracting update..."))
            UpdateCompression.extract_archive(local_file, "actual")
            progreso.final()

            UpdateLogger.log_extraction_complete()
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            QTMessages.message_error(None, _("Failed to extract update file"))
            return False

        # Validate update script
        act_script = "actual/act.py"
        if not os.path.exists(act_script):
            logger.error("Update script not found in archive")
            QTMessages.message_error(None, _("Invalid update package: missing update script"))
            return False

        try:
            UpdateLogger.log_script_validation(act_script)
            UpdateSecurity.validate_update_script(act_script)
            UpdateLogger.log_script_validated()
        except UpdateSecurity.UnsafeScriptError as e:
            logger.error(f"Script validation failed: {e}")
            QTMessages.message_error(
                None, _("Update script failed security validation.\nUpdate package may be malicious.")
            )
            return False

        # Execute update script safely
        try:
            UpdateLogger.log_script_execution_start()
            UpdateSecurity.execute_update_script_safely(act_script)
            UpdateLogger.log_script_execution_complete()
        except Exception as e:
            logger.error(f"Script execution failed: {e}")

            # Attempt rollback
            if backup_path:
                try:
                    UpdateLogger.log_rollback_start(backup_path)
                    UpdateBackup.restore_backup(backup_path)
                    UpdateLogger.log_rollback_complete()
                    QTMessages.message_error(None, _("Update failed and was rolled back to previous version."))
                except UpdateBackup.RollbackError as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    QTMessages.message_error(
                        None, _("Update failed and rollback also failed.\nPlease reinstall the application.")
                    )
            else:
                QTMessages.message_error(None, _("Update failed"))

            return False

        # Cleanup old backups
        try:
            keep_backups = getattr(Code.configuration, 'x_update_keep_backups', 3)
            UpdateBackup.cleanup_old_backups(keep_count=keep_backups)
        except Exception as e:
            logger.warning(f"Backup cleanup failed: {e}")

        return True

    except Exception as e:
        logger.exception(f"Unexpected error during update: {e}")
        QTMessages.message_error(None, _("An unexpected error occurred during update"))
        return False


def update_eboard(main_window):
    """
    Update electronic board drivers.

    Args:
        main_window: Main window for dialogs
    """
    logger = UpdateLogger.get_logger()

    try:
        version_local = Eboard.version()

        ftxt = Code.configuration.temporary_file("txt")
        ok = Util.urlretrieve(WEBUPDATES_EBOARD_VERSION, ftxt)

        if not ok:
            logger.warning("Could not retrieve eboard version info")
            return

        with open(ftxt, "rt") as f:
            version_remote = f.read().strip()

        if version_local == version_remote:
            logger.info(f"Eboard drivers already up to date: {version_local}")
            return

        logger.info(f"Updating eboard drivers: {version_local} -> {version_remote}")

        with QTMessages.one_moment_please(main_window, _("Downloading eboards drivers")):
            fzip = Code.configuration.temporary_file("zip")
            ok = Util.urlretrieve(WEBUPDATES_EBOARD_ZIP, fzip)

        if ok:
            # Extract drivers
            UpdateCompression.extract_archive(fzip, Code.configuration.temporary_folder())

            # Copy files
            import zipfile

            zfobj = zipfile.ZipFile(fzip)
            for name in zfobj.namelist():
                path_dll = Util.opj(Code.folder_os, "DigitalBoards", name)
                with open(path_dll, "wb") as outfile:
                    outfile.write(zfobj.read(name))
            zfobj.close()

            # Read news
            news_file = Util.opj(Code.folder_os, "DigitalBoards", "news")
            if os.path.exists(news_file):
                with open(news_file, "rt", encoding="utf-8") as f:
                    news = f.read().strip()
            else:
                news = ""

            logger.info(f"Eboard drivers updated to {version_remote}")
            QTMessages.message(
                main_window,
                f"{_('Updated the eboards drivers')}\n {_('Version')}: {version_remote}\n{news}",
            )
        else:
            logger.error("Failed to download eboard drivers")
            QTMessages.message_error(main_window, _("It has not been possible to update the eboards drivers"))

    except Exception as e:
        logger.exception(f"Eboard update failed: {e}")
        QTMessages.message_error(main_window, _("It has not been possible to update the eboards drivers"))


def update(main_window):
    """
    Check for and apply application updates.

    Args:
        main_window: Main window for dialogs

    Returns:
        True if update was applied, False otherwise
    """
    logger = UpdateLogger.get_logger()

    # Update eboard drivers if configured
    if Code.configuration.x_digital_board:
        if Code.eboard:
            Code.eboard.deactivate()
        update_eboard(main_window)

    # Parse version: "R 1.01" -> "R01.01" -> "0101" -> bytes
    current_version = Code.VERSION.replace(" ", "0").replace(".", "")[1:].encode()
    base_version = Code.BASE_VERSION.encode()
    mens_error = None
    done_update = False

    try:
        logger.info("Checking for updates...")
        logger.info(f"Current version: {Code.VERSION}")
        logger.info(f"Base version: {Code.BASE_VERSION}")

        f = urllib.request.urlopen(WEBUPDATES)
        for blinea in f:
            act = blinea.strip()
            if act and not act.startswith(b"#"):  # Skip comments
                li = act.split(b" ")

                # Support both old format (4 fields) and new format (5 fields with SHA256)
                if len(li) >= 4 and li[3].isdigit():
                    base = li[0]
                    version = li[1]
                    urlfichero = li[2]
                    tam = li[3]
                    sha256 = li[4].decode() if len(li) >= 5 else None

                    if base == base_version:
                        if current_version < version:
                            version_str = version.decode()
                            logger.info(f"Update available: {version_str}")

                            if sha256:
                                logger.info(f"Update includes SHA256 checksum: {sha256[:16]}...")
                            else:
                                logger.warning("Update does not include SHA256 checksum")

                            UpdateLogger.log_update_start(Code.VERSION, version_str)

                            if not update_file(
                                _X(_("version %1"), version_str),
                                urlfichero.decode(),
                                int(tam),
                                sha256,
                            ):
                                mens_error = _X(
                                    _("An error has occurred during the upgrade to version %1"),
                                    version_str,
                                )
                                UpdateLogger.log_update_failed(version_str, Exception(mens_error))
                            else:
                                done_update = True
                                UpdateLogger.log_update_complete(version_str)

        f.close()

    except urllib.error.URLError as e:
        logger.error(f"Network error while checking updates: {e}")
        mens_error = _("Encountered a network problem, cannot access the Internet")
    except Exception as e:
        logger.exception(f"Unexpected error while checking updates: {e}")
        mens_error = _("An unexpected error occurred while checking for updates")

    if mens_error:
        QTMessages.message_error(main_window, mens_error)
        return False

    if not done_update:
        logger.info("No updates available")
        QTMessages.message_bold(main_window, _("There are no pending updates"))
        return False

    return True


def test_update(procesador):
    """
    Test for available updates and prompt user.
    Called periodically to check for updates.

    Args:
        procesador: Main processor instance
    """
    logger = UpdateLogger.get_logger()

    current_version = Code.VERSION.replace(" ", "0").replace(".", "")[1:].encode()
    base_version = Code.BASE_VERSION.encode()
    nresp = 0

    try:
        f = urllib.request.urlopen(WEBUPDATES)
        for blinea in f:
            act = blinea.strip()
            if act and not act.startswith(b"#"):  # Skip comments
                li = act.split(b" ")
                if len(li) >= 4 and li[3].isdigit():
                    base = li[0]
                    version = li[1]
                    # urlfichero = li[2]
                    # tam = li[3]

                    if base == base_version:
                        if current_version < version:
                            version_str = version.decode()
                            logger.info(f"Update available: {version_str}")

                            nresp = QTMessages.question_withcancel_123(
                                procesador.main_window,
                                _("Update"),
                                _("Version %s is ready to update") % version_str,
                                _("Update now"),
                                _("Do not do anything"),
                                _("Don't ask again"),
                            )
                            break
        f.close()

    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        pass

    if nresp == 1:
        procesador.actualiza()
    elif nresp == 3:
        Code.configuration.x_check_for_update = False
        Code.configuration.graba()


def update_manual(main_window):
    """
    Manually install an update from a local file.

    Args:
        main_window: Main window for dialogs

    Returns:
        True if update successful, False otherwise
    """
    logger = UpdateLogger.get_logger()

    config = Code.configuration
    dic = config.read_variables("MANUAL_UPDATE")
    folder = dic.get("FOLDER", config.folder_userdata())

    # Allow both .zip and .7z files
    compression_info = UpdateCompression.get_compression_info()
    extensions = ["zip"]
    if compression_info['7z']['supported']:
        extensions.append("7z")

    # For now, use simple file dialog (could be enhanced to support multiple extensions)
    path_archive = SelectFiles.leeFichero(main_window, folder, "zip")
    if not path_archive or not Util.exist_file(path_archive):
        return False

    # Check if it's a supported archive
    try:
        archive_type = UpdateCompression.detect_archive_type(path_archive)
    except UpdateCompression.UnsupportedArchiveFormat as e:
        logger.error(f"Unsupported archive format: {e}")
        QTMessages.message_error(main_window, str(e))
        return False

    dic["FOLDER"] = os.path.dirname(path_archive)
    config.write_variables("MANUAL_UPDATE", dic)

    logger.info(f"Manual update from: {path_archive}")

    # Prepare actual folder
    folder_actual = Util.opj(Code.folder_root, "bin", "actual")
    shutil.rmtree(folder_actual, ignore_errors=True)
    Util.create_folder(folder_actual)

    # Copy archive to actual folder
    shutil.copy(path_archive, folder_actual)
    local_file = Util.opj(folder_actual, os.path.basename(path_archive))

    try:
        # Verify archive
        if not UpdateCompression.is_valid_archive(local_file):
            logger.error("Invalid archive file")
            QTMessages.message_error(main_window, _("Archive file is corrupted or invalid"))
            return False

        # Extract
        UpdateLogger.log_extraction_start(archive_type)
        with QTMessages.one_moment_please(main_window, _("Extracting...")):
            UpdateCompression.extract_archive(local_file, folder_actual)
        UpdateLogger.log_extraction_complete()

        # Validate and execute act.py
        path_act_py = Util.opj(folder_actual, "act.py")

        if not os.path.exists(path_act_py):
            logger.error("Update script not found")
            QTMessages.message_error(main_window, _("Invalid update package: missing act.py"))
            return False

        try:
            UpdateLogger.log_script_validation(path_act_py)
            UpdateSecurity.validate_update_script(path_act_py)
            UpdateLogger.log_script_validated()
        except UpdateSecurity.UnsafeScriptError as e:
            logger.error(f"Script validation failed: {e}")
            QTMessages.message_error(main_window, _("Update script failed security validation"))
            return False

        # Execute
        UpdateLogger.log_script_execution_start()
        UpdateSecurity.execute_update_script_safely(path_act_py)
        UpdateLogger.log_script_execution_complete()

        logger.info("Manual update completed successfully")
        return True

    except Exception as e:
        logger.exception(f"Manual update failed: {e}")
        QTMessages.message_error(main_window, _("Manual update failed"))
        return False
