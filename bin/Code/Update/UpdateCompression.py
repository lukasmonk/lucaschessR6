"""
Compression utilities for update system.
Supports both .zip and .7z formats with automatic detection.
Uses built-in modules: zipfile and lzma (no external dependencies).
"""

import os
import lzma
import tarfile
import zipfile
from typing import List


class UnsupportedArchiveFormat(Exception):
    """Raised when archive format is not supported."""

    pass


class ArchiveExtractionError(Exception):
    """Raised when archive extraction fails."""

    pass


def detect_archive_type(filepath: str) -> str:
    """
    Detect archive type by file extension.

    Args:
        filepath: Path to archive file

    Returns:
        'zip' or '7z'

    Raises:
        UnsupportedArchiveFormat: If file extension is not .zip or .7z
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.zip':
        return 'zip'
    elif ext in ('.7z', '.xz'):
        return '7z'
    else:
        raise UnsupportedArchiveFormat(f"Unsupported archive format: {ext}")


def extract_archive(filepath: str, destination: str) -> None:
    """
    Extract archive to destination folder.
    Automatically detects .zip or .7z format.

    Args:
        filepath: Path to archive file
        destination: Destination folder

    Raises:
        UnsupportedArchiveFormat: If format is not supported
        ArchiveExtractionError: If extraction fails
    """
    archive_type = detect_archive_type(filepath)

    try:
        if archive_type == 'zip':
            _extract_zip(filepath, destination)
        elif archive_type == '7z':
            _extract_7z_lzma(filepath, destination)
    except Exception as e:
        raise ArchiveExtractionError(f"Failed to extract {filepath}: {str(e)}") from e


def _extract_zip(filepath: str, destination: str) -> None:
    """Extract ZIP archive using zipfile."""
    with zipfile.ZipFile(filepath, 'r') as zf:
        zf.extractall(destination)


def _extract_7z_lzma(filepath: str, destination: str) -> None:
    """
    Extract .7z/.xz archive using lzma and tarfile.
    Works with .tar.xz and simple .7z files compressed with LZMA.
    """
    # Create destination if it doesn't exist
    os.makedirs(destination, exist_ok=True)

    # Try to extract as tar.xz first (most common .7z format for updates)
    try:
        with lzma.open(filepath, 'rb') as compressed_file:
            # Check if it's a tar archive
            compressed_file.seek(0)
            header = compressed_file.read(512)
            compressed_file.seek(0)

            # If it looks like a tar header, use tarfile
            if header[257:262] == b'ustar':
                with tarfile.open(fileobj=compressed_file, mode='r|') as tar:
                    tar.extractall(destination)
            else:
                # Single file compressed with LZMA
                # For update packages, we expect a tar archive
                # but fallback to direct extraction
                output_path = os.path.join(
                    destination, os.path.basename(filepath).replace('.7z', '').replace('.xz', '')
                )
                with open(output_path, 'wb') as out_file:
                    out_file.write(compressed_file.read())
    except Exception as e:
        raise ArchiveExtractionError(f"LZMA extraction failed: {str(e)}") from e


def get_archive_file_list(filepath: str) -> List[str]:
    """
    Get list of files in archive without extracting.

    Args:
        filepath: Path to archive file

    Returns:
        List of file paths in archive

    Raises:
        UnsupportedArchiveFormat: If format is not supported
    """
    archive_type = detect_archive_type(filepath)

    if archive_type == 'zip':
        with zipfile.ZipFile(filepath, 'r') as zf:
            return zf.namelist()
    elif archive_type == '7z':
        try:
            with lzma.open(filepath, 'rb') as compressed_file:
                # Check if it's a tar archive
                compressed_file.seek(0)
                header = compressed_file.read(512)
                compressed_file.seek(0)

                if header[257:262] == b'ustar':
                    with tarfile.open(fileobj=compressed_file, mode='r|') as tar:
                        return tar.getnames()
                else:
                    # Single file
                    return [os.path.basename(filepath).replace('.7z', '').replace('.xz', '')]
        except Exception:
            return []

    return []


def is_valid_archive(filepath: str) -> bool:
    """
    Check if archive file is valid and can be opened.

    Args:
        filepath: Path to archive file

    Returns:
        True if archive is valid, False otherwise
    """
    try:
        archive_type = detect_archive_type(filepath)

        if archive_type == 'zip':
            with zipfile.ZipFile(filepath, 'r') as zf:
                # Test archive integrity
                return zf.testzip() is None
        elif archive_type == '7z':
            # Try to open with lzma
            with lzma.open(filepath, 'rb') as compressed_file:
                # Try to read a bit to verify it's valid
                compressed_file.read(1024)
                return True

    except Exception:
        return False

    return False


def get_compression_info() -> dict:
    """
    Get information about available compression formats.

    Returns:
        Dictionary with supported formats and capabilities
    """
    return {
        'zip': {
            'supported': True,
            'library': 'zipfile (built-in)',
        },
        '7z': {
            'supported': True,
            'library': 'lzma + tarfile (built-in)',
        },
    }
