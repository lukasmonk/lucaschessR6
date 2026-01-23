"""
Backup and rollback utilities for update system.
Handles creating/restoring backups and cleanup of old backups.
"""

import os
import shutil
from datetime import datetime
from typing import List

import Code
from Code import Util


class BackupError(Exception):
    """Raised when backup operations fail."""

    pass


class RollbackError(Exception):
    """Raised when rollback operations fail."""

    pass


def get_backup_dir() -> str:
    """
    Get the directory for storing backups.

    Returns:
        Path to backup directory
    """
    backup_dir = os.path.join(Code.folder_root, "bin", "backups")
    Util.create_folder(backup_dir)
    return backup_dir


def create_backup(version: str) -> str:
    """
    Create backup of current installation before update.

    Args:
        version: Current version being backed up

    Returns:
        Path to backup directory

    Raises:
        BackupError: If backup fails
    """
    try:
        backup_dir = get_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{version}_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)

        # Check if backup already exists
        if os.path.exists(backup_path):
            raise BackupError(f"Backup already exists: {backup_path}")

        # Create backup directory
        Util.create_folder(backup_path)

        # Critical paths to backup
        bin_dir = os.path.join(Code.folder_root, "bin")
        critical_items = [
            "Code",  # Main application code
            "OS",  # OS-specific files
            "Resources",  # Resources
            "LucasR.py",  # Main entry point
        ]

        # Copy each critical item
        for item in critical_items:
            source = os.path.join(bin_dir, item)
            if not os.path.exists(source):
                continue  # Skip if doesn't exist

            dest = os.path.join(backup_path, item)

            try:
                if os.path.isdir(source):
                    shutil.copytree(source, dest, symlinks=True, ignore_dangling_symlinks=True)
                else:
                    shutil.copy2(source, dest)
            except Exception as e:
                # Clean up partial backup
                if os.path.exists(backup_path):
                    shutil.rmtree(backup_path, ignore_errors=True)
                raise BackupError(f"Failed to backup {item}: {str(e)}") from e

        # Create backup metadata file
        metadata_file = os.path.join(backup_path, "_backup_info.txt")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            f.write(f"Version: {version}\n")
            f.write(f"Date: {timestamp}\n")
            f.write(f"Path: {backup_path}\n")

        return backup_path

    except Exception as e:
        raise BackupError(f"Backup creation failed: {str(e)}") from e


def restore_backup(backup_path: str) -> None:
    """
    Restore from backup (rollback).

    Args:
        backup_path: Path to backup directory

    Raises:
        RollbackError: If restore fails
    """
    try:
        if not os.path.exists(backup_path):
            raise RollbackError(f"Backup not found: {backup_path}")

        # Verify backup
        if not verify_backup(backup_path):
            raise RollbackError(f"Backup verification failed: {backup_path}")

        bin_dir = os.path.join(Code.folder_root, "bin")

        # List items in backup
        backup_items = [item for item in os.listdir(backup_path) if item != "_backup_info.txt"]

        # Restore each item
        for item in backup_items:
            source = os.path.join(backup_path, item)
            dest = os.path.join(bin_dir, item)

            try:
                # Remove existing item
                if os.path.exists(dest):
                    if os.path.isdir(dest):
                        shutil.rmtree(dest)
                    else:
                        os.remove(dest)

                # Restore from backup
                if os.path.isdir(source):
                    shutil.copytree(source, dest, symlinks=True)
                else:
                    shutil.copy2(source, dest)

            except Exception as e:
                raise RollbackError(f"Failed to restore {item}: {str(e)}") from e

    except Exception as e:
        raise RollbackError(f"Rollback failed: {str(e)}") from e


def verify_backup(backup_path: str) -> bool:
    """
    Verify that backup is valid and has critical files.

    Args:
        backup_path: Path to backup directory

    Returns:
        True if backup is valid, False otherwise
    """
    if not os.path.exists(backup_path):
        return False

    # Check for metadata file
    metadata_file = os.path.join(backup_path, "_backup_info.txt")
    if not os.path.exists(metadata_file):
        return False

    # Check for at least Code directory
    code_dir = os.path.join(backup_path, "Code")
    if not os.path.exists(code_dir):
        return False

    return True


def get_available_backups() -> List[str]:
    """
    Get list of available backups, sorted by date (newest first).

    Returns:
        List of backup directory paths
    """
    backup_dir = get_backup_dir()

    if not os.path.exists(backup_dir):
        return []

    backups = []
    for item in os.listdir(backup_dir):
        item_path = os.path.join(backup_dir, item)
        if os.path.isdir(item_path) and item.startswith("backup_"):
            if verify_backup(item_path):
                backups.append(item_path)

    # Sort by modification time (newest first)
    backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    return backups


def cleanup_old_backups(keep_count: int = 3) -> None:
    """
    Clean up old backups, keeping only the most recent ones.

    Args:
        keep_count: Number of backups to keep (default: 3)
    """
    backups = get_available_backups()

    # Remove old backups beyond keep_count
    for backup_path in backups[keep_count:]:
        try:
            shutil.rmtree(backup_path, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors


def get_backup_size(backup_path: str) -> int:
    """
    Get total size of backup in bytes.

    Args:
        backup_path: Path to backup directory

    Returns:
        Total size in bytes
    """
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(backup_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)

    return total_size


def check_disk_space_for_backup() -> bool:
    """
    Check if there's enough disk space for creating a backup.

    Returns:
        True if enough space available, False otherwise
    """
    try:
        bin_dir = os.path.join(Code.folder_root, "bin")

        # Estimate required space (approximately 2x current bin size)
        required_space = 0
        for dirpath, dirnames, filenames in os.walk(bin_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    required_space += os.path.getsize(filepath)

        required_space *= 2  # Safety margin

        # Check available space
        if hasattr(shutil, 'disk_usage'):
            stat = shutil.disk_usage(Code.folder_root)
            available_space = stat.free
            return available_space > required_space

        # Fallback: assume we have enough space
        return True

    except Exception:
        # If we can't check, assume we have enough
        return True
