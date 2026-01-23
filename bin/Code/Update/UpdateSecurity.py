"""
Security utilities for update system.
Handles checksum verification, script validation, and sandboxed execution.
"""

import hashlib
import os
import re
from typing import Dict, Any


class ChecksumMismatchError(Exception):
    """Raised when file checksum doesn't match expected value."""

    pass


class UnsafeScriptError(Exception):
    """Raised when update script contains dangerous operations."""

    pass


def calculate_sha256(filepath: str, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        filepath: Path to file
        chunk_size: Size of chunks to read (default 8KB)

    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def verify_checksum(filepath: str, expected_hash: str) -> bool:
    """
    Verify file checksum against expected SHA256 hash.

    Args:
        filepath: Path to file
        expected_hash: Expected SHA256 hash (hexadecimal)

    Returns:
        True if checksums match

    Raises:
        ChecksumMismatchError: If checksums don't match
    """
    actual_hash = calculate_sha256(filepath)

    if actual_hash.lower() != expected_hash.lower():
        raise ChecksumMismatchError(
            f"Checksum mismatch for {filepath}:\n" f"  Expected: {expected_hash}\n" f"  Got:      {actual_hash}"
        )

    return True


# Dangerous patterns that should not appear in update scripts
DANGEROUS_PATTERNS = [
    r'__import__\s*\(',  # Dynamic imports
    r'\beval\s*\(',  # Code evaluation
    r'\bexec\s*\(',  # Code execution (except our controlled exec)
    r'\bcompile\s*\(',  # Code compilation
    r'\bexecfile\s*\(',  # File execution (Python 2)
    r'open\s*\([^)]*["\']w["\']',  # Writing files (too broad, will refine)
    r'subprocess\.',  # Subprocess execution
    r'os\.system\s*\(',  # System commands
    r'os\.exec[lv]',  # Exec family
    r'os\.spawn',  # Spawn processes
    r'os\.popen',  # Popen
    r'socket\.',  # Network operations
    r'urllib\.request\.urlopen',  # URL opening (except in our code)
    r'requests\.',  # HTTP requests
]


# Required patterns that must appear in update scripts
REQUIRED_PATTERNS = [
    r'def\s+actualizar\s*\(',  # Must define actualizar() function
]


def validate_update_script(script_path: str) -> None:
    """
    Validate that update script is safe to execute.

    Checks for:
    - Dangerous function calls (eval, exec, __import__, etc)
    - System operations (os.system, subprocess, etc)
    - Network operations
    - Required structure (actualizar() function)

    Args:
        script_path: Path to act.py script

    Raises:
        UnsafeScriptError: If script contains dangerous operations or missing structure
    """
    if not os.path.exists(script_path):
        raise UnsafeScriptError(f"Script not found: {script_path}")

    with open(script_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, script_content, re.IGNORECASE):
            raise UnsafeScriptError(
                f"Unsafe pattern detected in {script_path}: {pattern}\n"
                f"Update script contains potentially dangerous operations."
            )

    # Check for required patterns
    for pattern in REQUIRED_PATTERNS:
        if not re.search(pattern, script_content):
            raise UnsafeScriptError(
                f"Required pattern missing in {script_path}: {pattern}\n"
                f"Update script must define actualizar() function."
            )


def create_restricted_namespace() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Create restricted namespace for exec() execution.

    Returns:
        Tuple of (globals, locals) dictionaries with limited functionality
    """
    import shutil
    import os

    # Very restricted builtins
    safe_builtins = {
        'print': print,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'len': len,
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'True': True,
        'False': False,
        'None': None,
    }

    # Safe modules (read-only operations mostly)
    safe_globals = {
        '__builtins__': safe_builtins,
        'os': os,  # Needed for file operations
        'shutil': shutil,  # Needed for copying files
    }

    safe_locals = {}

    return safe_globals, safe_locals


def execute_update_script_safely(script_path: str) -> None:
    """
    Execute update script in restricted namespace.

    Args:
        script_path: Path to validated act.py script

    Raises:
        UnsafeScriptError: If script validation fails
        Exception: If script execution fails
    """
    # First validate
    validate_update_script(script_path)

    # Read script
    with open(script_path, 'r', encoding='utf-8') as f:
        script_content = f.read()

    # Create restricted namespace
    safe_globals, safe_locals = create_restricted_namespace()

    # Execute in restricted environment
    try:
        exec(script_content, safe_globals, safe_locals)

        # Call actualizar() function if it exists in locals
        if 'actualizar' in safe_locals:
            safe_locals['actualizar']()
        else:
            raise UnsafeScriptError("actualizar() function not found after execution")

    except Exception as e:
        raise Exception(f"Update script execution failed: {str(e)}") from e
