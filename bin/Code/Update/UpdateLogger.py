"""
Logging configuration for update system.
Centralized logging with file rotation and console output.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

import Code


# Global logger instance
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get or create the update system logger."""
    global _logger

    if _logger is None:
        _logger = setup_logger()

    return _logger


def setup_logger(log_dir: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration for update system.

    Args:
        log_dir: Directory for log files (default: user data folder)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('LucasChess.Update')
    logger.setLevel(logging.DEBUG)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    # Determine log directory
    if log_dir is None:
        try:
            log_dir = Code.configuration.folder_userdata()
        except (AttributeError, TypeError):
            # Fallback if configuration not initialized
            import tempfile

            log_dir = tempfile.gettempdir()

    log_file = os.path.join(log_dir, 'updates.log')

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter('%(levelname)s: %(message)s')

    # File handler with rotation (keep 5 files of 1MB each)
    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')  # 1MB
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, continue without it
        print(f"Warning: Could not setup file logging: {e}")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def log_update_start(current_version: str, target_version: str) -> None:
    """Log the start of an update operation."""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info(f"Starting update: {current_version} -> {target_version}")
    logger.info("=" * 60)


def log_update_complete(version: str) -> None:
    """Log successful update completion."""
    logger = get_logger()
    logger.info("=" * 60)
    logger.info(f"Update to {version} completed successfully")
    logger.info("=" * 60)


def log_update_failed(version: str, error: Exception) -> None:
    """Log update failure."""
    logger = get_logger()
    logger.error("=" * 60)
    logger.error(f"Update to {version} FAILED: {str(error)}")
    logger.exception(error)
    logger.error("=" * 60)


def log_download_start(url: str, size: int) -> None:
    """Log download start."""
    logger = get_logger()
    size_mb = size / (1024 * 1024)
    logger.info(f"Downloading: {url}")
    logger.info(f"Size: {size_mb:.2f} MB")


def log_download_complete(filepath: str) -> None:
    """Log download completion."""
    logger = get_logger()
    logger.info(f"Download complete: {filepath}")


def log_checksum_verification(filepath: str, expected: str) -> None:
    """Log checksum verification."""
    logger = get_logger()
    logger.info(f"Verifying checksum for {os.path.basename(filepath)}")
    logger.debug(f"Expected SHA256: {expected}")


def log_checksum_verified() -> None:
    """Log successful checksum verification."""
    logger = get_logger()
    logger.info("Checksum verified successfully")


def log_extraction_start(archive_type: str) -> None:
    """Log archive extraction start."""
    logger = get_logger()
    logger.info(f"Extracting {archive_type} archive...")


def log_extraction_complete() -> None:
    """Log archive extraction completion."""
    logger = get_logger()
    logger.info("Extraction complete")


def log_backup_created(backup_path: str) -> None:
    """Log backup creation."""
    logger = get_logger()
    logger.info(f"Backup created: {backup_path}")


def log_rollback_start(backup_path: str) -> None:
    """Log rollback start."""
    logger = get_logger()
    logger.warning(f"Rolling back from backup: {backup_path}")


def log_rollback_complete() -> None:
    """Log rollback completion."""
    logger = get_logger()
    logger.info("Rollback completed successfully")


def log_script_validation(script_path: str) -> None:
    """Log script validation."""
    logger = get_logger()
    logger.info(f"Validating update script: {script_path}")


def log_script_validated() -> None:
    """Log successful script validation."""
    logger = get_logger()
    logger.info("Update script validated successfully")


def log_script_execution_start() -> None:
    """Log script execution start."""
    logger = get_logger()
    logger.info("Executing update script...")


def log_script_execution_complete() -> None:
    """Log script execution completion."""
    logger = get_logger()
    logger.info("Update script executed successfully")
