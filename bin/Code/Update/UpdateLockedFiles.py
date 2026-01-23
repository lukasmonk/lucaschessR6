"""
Utilities for handling locked files during updates.
Windows locks .pyd, .dll, and .exe files when they are in use.
Linux/Unix typically allow replacing .so files even when loaded.
This module provides cross-platform strategies to safely update them.
"""

import os
import shutil
import platform
from typing import Optional, List


# Detect operating system
IS_WINDOWS = platform.system() == 'Windows'
IS_LINUX = platform.system() == 'Linux'


class LockedFileError(Exception):
    """Raised when a file is locked and cannot be updated."""

    pass


def is_file_locked(filepath: str) -> bool:
    """
    Check if a file is locked (cannot be written/deleted).

    Note: On Linux, files are rarely locked, so this mostly returns False.
    On Windows, .pyd/.dll files are locked when loaded.

    Args:
        filepath: Path to file to check

    Returns:
        True if file is locked, False otherwise
    """
    if not os.path.exists(filepath):
        return False

    try:
        # Try to open for exclusive writing
        with open(filepath, 'a'):
            pass
        return False  # Success = not locked
    except (IOError, OSError, PermissionError):
        return True  # Failure = locked


def safe_copy_file(source: str, dest: str, allow_pending: bool = True) -> str:
    """
    Safely copy a file, handling locked files.

    Strategy:
    - Linux/Unix: Direct copy (files typically don't lock)
    - Windows:
      1. Try direct copy (works if file is not locked)
      2. If locked, rename old file to .old and copy new one
      3. Old file will be deleted on next application start

    Args:
        source: Source file path
        dest: Destination file path
        allow_pending: If True, allow pending operations (rename .old) on Windows

    Returns:
        'copied' if direct copy succeeded
        'pending' if file was renamed and will be replaced on restart (Windows only)

    Raises:
        LockedFileError: If file cannot be updated even with rename strategy
    """
    # Ensure destination directory exists
    dest_dir = os.path.dirname(dest)
    if dest_dir and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    # On Linux, just try direct copy - files don't typically lock
    if not IS_WINDOWS:
        try:
            shutil.copy2(source, dest)
            return 'copied'
        except Exception as e:
            raise LockedFileError(f"Cannot copy {dest}: {e}") from e

    # Windows: Try direct copy first
    try:
        shutil.copy2(source, dest)
        return 'copied'
    except (IOError, OSError, PermissionError) as e:
        # File might be locked
        if not allow_pending:
            raise LockedFileError(f"Cannot copy {dest}: {e}") from e

        # Try rename strategy
        if not os.path.exists(dest):
            # Destination doesn't exist, try again
            try:
                shutil.copy2(source, dest)
                return 'copied'
            except Exception as e2:
                raise LockedFileError(f"Cannot copy {dest}: {e2}") from e2

        # Rename old file and copy new one
        try:
            old_file = dest + '.old'

            # If .old already exists, try to remove it
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except (IOError, OSError):
                    # .old file is also locked, try .old2, .old3, etc.
                    counter = 2
                    while os.path.exists(f"{old_file}{counter}"):
                        counter += 1
                    old_file = f"{old_file}{counter}"

            # Rename current file
            os.rename(dest, old_file)

            # Copy new file
            shutil.copy2(source, dest)

            return 'pending'

        except Exception as e:
            raise LockedFileError(f"Cannot update {dest}: file is locked and rename failed: {e}") from e


def cleanup_old_files(directory: str, recursive: bool = True) -> List[str]:
    """
    Clean up .old files from previous updates.
    Should be called at application startup.

    On Windows: Removes .old files from locked file updates
    On Linux: Usually no .old files, but cleans them anyway for consistency

    Args:
        directory: Directory to clean
        recursive: If True, clean subdirectories too

    Returns:
        List of files that were successfully deleted
    """
    deleted = []

    if recursive:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.old') or '.old' in filename:
                    filepath = os.path.join(root, filename)
                    try:
                        os.remove(filepath)
                        deleted.append(filepath)
                    except (IOError, OSError):
                        # Still locked or permission denied
                        pass
    else:
        # Just current directory
        for filename in os.listdir(directory):
            if filename.endswith('.old') or '.old' in filename:
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                        deleted.append(filepath)
                    except (IOError, OSError):
                        pass

    return deleted


def update_pyd_file(source: str, dest: str) -> dict:
    """
    Update a binary extension file safely (.pyd on Windows, .so on Linux).

    Windows: .pyd files are locked when imported, uses rename strategy
    Linux: .so files typically don't lock, direct copy works

    Args:
        source: Source file (.pyd or .so)
        dest: Destination file

    Returns:
        Dictionary with update status:
        {
            'status': 'copied' | 'pending' | 'failed',
            'message': str,
            'requires_restart': bool
        }
    """
    result = {'status': 'failed', 'message': '', 'requires_restart': False}

    try:
        # Check if file is locked
        is_locked = is_file_locked(dest) if os.path.exists(dest) else False

        if is_locked:
            basename = os.path.basename(dest)
            result['message'] = f"{basename} is currently in use"

        # Try to copy
        copy_status = safe_copy_file(source, dest, allow_pending=True)

        basename = os.path.basename(dest)

        if copy_status == 'copied':
            result['status'] = 'copied'
            result['message'] = f"Updated {basename} successfully"
            # On Linux, even if copied, recommend restart for safety
            # (old .so is in memory, new one on disk)
            result['requires_restart'] = is_locked
        elif copy_status == 'pending':
            result['status'] = 'pending'
            result['message'] = f"{basename} will be updated on next restart"
            result['requires_restart'] = True

        return result

    except LockedFileError as e:
        result['status'] = 'failed'
        result['message'] = str(e)
        result['requires_restart'] = False
        return result


def batch_update_files(file_mapping: dict, file_types: Optional[List[str]] = None) -> dict:
    """
    Update multiple files, handling locked files appropriately.

    Args:
        file_mapping: Dictionary of {source: dest} paths
        file_types: Optional list of file extensions to handle specially
                   Default: ['.pyd', '.dll', '.exe'] on Windows
                            ['.so'] on Linux

    Returns:
        Dictionary with results:
        {
            'copied': [list of files],
            'pending': [list of files],
            'failed': [list of files],
            'requires_restart': bool
        }
    """
    if file_types is None:
        # Platform-specific defaults
        if IS_WINDOWS:
            file_types = ['.pyd', '.dll', '.exe']
        elif IS_LINUX:
            file_types = ['.so']
        else:
            file_types = ['.so']  # Other Unix-like systems

    results = {'copied': [], 'pending': [], 'failed': [], 'requires_restart': False}

    for source, dest in file_mapping.items():
        ext = os.path.splitext(dest)[1].lower()

        # Check if this is a potentially locked file type
        if ext in file_types:
            update_result = update_pyd_file(source, dest)

            if update_result['status'] == 'copied':
                results['copied'].append(dest)
                if update_result['requires_restart']:
                    results['requires_restart'] = True
            elif update_result['status'] == 'pending':
                results['pending'].append(dest)
                results['requires_restart'] = True
            else:
                results['failed'].append(dest)
        else:
            # Regular file, use simple copy
            try:
                shutil.copy2(source, dest)
                results['copied'].append(dest)
            except Exception:
                results['failed'].append(dest)

    return results


def get_locked_files_report(directory: str) -> List[str]:
    """
    Get a list of binary extension files that are currently locked.
    Useful for diagnostics.

    Windows: Checks .pyd, .dll files
    Linux: Checks .so files (though they typically don't lock)

    Args:
        directory: Directory to scan

    Returns:
        List of locked file paths
    """
    locked = []

    if IS_WINDOWS:
        extensions = ['.pyd', '.dll']
    elif IS_LINUX:
        extensions = ['.so']
    else:
        extensions = ['.so']

    for root, dirs, files in os.walk(directory):
        for filename in files:
            if any(filename.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)
                if is_file_locked(filepath):
                    locked.append(filepath)

    return locked
