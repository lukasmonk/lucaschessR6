"""
Update system for LucasChess.
Provides secure and reliable application updates with backup, rollback, and verification.
"""

# Import main update functions
from Code.Update.Update import update, update_manual, test_update, update_eboard

# Import utilities for use in update scripts
from Code.Update.UpdateLockedFiles import (
    update_pyd_file,
    batch_update_files,
    safe_copy_file,
    cleanup_old_files,
)

from Code.Update.UpdateCompression import (
    extract_archive,
    detect_archive_type,
    is_valid_archive,
    get_compression_info,
)

from Code.Update.UpdateSecurity import (
    calculate_sha256,
    verify_checksum,
    validate_update_script,
)

from Code.Update.UpdateLogger import get_logger

from Code.Update.UpdateBackup import (
    create_backup,
    restore_backup,
    cleanup_old_backups,
)


__all__ = [
    # Main functions
    'update',
    'update_manual',
    'test_update',
    'update_eboard',
    # Locked files
    'update_pyd_file',
    'batch_update_files',
    'safe_copy_file',
    'cleanup_old_files',
    # Compression
    'extract_archive',
    'detect_archive_type',
    'is_valid_archive',
    'get_compression_info',
    # Security
    'calculate_sha256',
    'verify_checksum',
    'validate_update_script',
    # Logging
    'get_logger',
    # Backup
    'create_backup',
    'restore_backup',
    'cleanup_old_backups',
]
