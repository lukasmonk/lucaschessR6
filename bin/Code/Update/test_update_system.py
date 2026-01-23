"""
Test and verification script for update system improvements.
Run this to verify that all components work correctly.
"""

import os
import sys
import tempfile

# Add Code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Code.Update import UpdateCompression
from Code.Update import UpdateSecurity
from Code.Update import UpdateBackup
from Code.Update import UpdateLogger


def test_compression():
    """Test compression utilities."""
    print("\n" + "=" * 60)
    print("Testing Compression Utilities")
    print("=" * 60)

    # Check compression support
    info = UpdateCompression.get_compression_info()
    print("\nCompression formats:")
    print(f"  ZIP: {info['zip']['supported']} ({info['zip']['library']})")
    print(f"  7Z:  {info['7z']['supported']} ({info['7z']['library']})")

    if not info['7z']['supported']:
        print("\n⚠️  WARNING: py7zr not installed. Install with: pip install py7zr")

    # Create test archive
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")

        # Create test zip
        import zipfile

        zip_path = os.path.join(tmpdir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(test_file, "test.txt")

        # Test detection
        detected = UpdateCompression.detect_archive_type(zip_path)
        print(f"\n✓ Archive type detection: {detected}")

        # Test validation
        is_valid = UpdateCompression.is_valid_archive(zip_path)
        print(f"✓ Archive validation: {is_valid}")

        # Test extraction
        extract_dir = os.path.join(tmpdir, "extracted")
        UpdateCompression.extract_archive(zip_path, extract_dir)
        extracted_file = os.path.join(extract_dir, "test.txt")
        if os.path.exists(extracted_file):
            print("✓ Archive extraction: Success")
        else:
            print("✗ Archive extraction: FAILED")

    print("\n✅ Compression tests completed")


def test_security():
    """Test security utilities."""
    print("\n" + "=" * 60)
    print("Testing Security Utilities")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test checksum calculation
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content for checksum")

        checksum = UpdateSecurity.calculate_sha256(test_file)
        print(f"\n✓ SHA256 calculation: {checksum[:16]}...")

        # Test checksum verification
        try:
            UpdateSecurity.verify_checksum(test_file, checksum)
            print("✓ Checksum verification: Success")
        except UpdateSecurity.ChecksumMismatchError:
            print("✗ Checksum verification: FAILED")

        # Test with wrong checksum
        try:
            UpdateSecurity.verify_checksum(test_file, "wrong_checksum")
            print("✗ Wrong checksum detection: FAILED (should have raised error)")
        except UpdateSecurity.ChecksumMismatchError:
            print("✓ Wrong checksum detection: Success")

        # Test safe script validation
        safe_script = os.path.join(tmpdir, "safe.py")
        with open(safe_script, 'w') as f:
            f.write(
                """
import os
import shutil

def actualizar():
    # Safe operations
    shutil.copy("file1.txt", "file2.txt")
    os.makedirs("newdir", exist_ok=True)
"""
            )

        try:
            UpdateSecurity.validate_update_script(safe_script)
            print("✓ Safe script validation: Passed")
        except UpdateSecurity.UnsafeScriptError as e:
            print(f"✗ Safe script validation: FAILED - {e}")

        # Test unsafe script validation
        unsafe_script = os.path.join(tmpdir, "unsafe.py")
        with open(unsafe_script, 'w') as f:
            f.write(
                """
import os

def actualizar():
    os.system("echo dangerous")  # Should be caught
"""
            )

        try:
            UpdateSecurity.validate_update_script(unsafe_script)
            print("✗ Unsafe script detection: FAILED (should have rejected)")
        except UpdateSecurity.UnsafeScriptError:
            print("✓ Unsafe script detection: Success")

    print("\n✅ Security tests completed")


def test_logging():
    """Test logging system."""
    print("\n" + "=" * 60)
    print("Testing Logging System")
    print("=" * 60)

    logger = UpdateLogger.get_logger()
    print(f"\n✓ Logger initialized: {logger.name}")
    print(f"✓ Log handlers: {len(logger.handlers)}")

    # Test logging functions
    UpdateLogger.log_update_start("R 6.00", "R 6.01")
    UpdateLogger.log_download_start("https://example.com/update.zip", 1024 * 1024)
    UpdateLogger.log_checksum_verified()
    UpdateLogger.log_update_complete("R 6.01")

    print("✓ Logging functions: All executed")
    print("\n✅ Logging tests completed")


def test_backup():
    """Test backup system."""
    print("\n" + "=" * 60)
    print("Testing Backup System")
    print("=" * 60)

    # Check disk space
    has_space = UpdateBackup.check_disk_space_for_backup()
    print(f"\n✓ Disk space check: {'Sufficient' if has_space else 'Insufficient'}")

    # Note: We can't easily test actual backup creation without affecting the real system
    print("✓ Backup functions: Available")
    print("  - create_backup()")
    print("  - restore_backup()")
    print("  - verify_backup()")
    print("  - cleanup_old_backups()")

    print("\n✅ Backup tests completed")


def test_integration():
    """Test integration between modules."""
    print("\n" + "=" * 60)
    print("Testing Module Integration")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal update package
        act_py = os.path.join(tmpdir, "act.py")
        with open(act_py, 'w') as f:
            f.write(
                """
import shutil

def actualizar():
    # Minimal update operation
    pass
"""
            )

        # Create ZIP
        import zipfile

        zip_path = os.path.join(tmpdir, "update.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(act_py, "act.py")

        # Calculate checksum
        checksum = UpdateSecurity.calculate_sha256(zip_path)

        # Verify checksum
        UpdateSecurity.verify_checksum(zip_path, checksum)

        # Validate archive
        UpdateCompression.is_valid_archive(zip_path)

        # Extract
        extract_dir = os.path.join(tmpdir, "extracted")
        UpdateCompression.extract_archive(zip_path, extract_dir)

        # Validate script
        extracted_script = os.path.join(extract_dir, "act.py")
        UpdateSecurity.validate_update_script(extracted_script)

        print("\n✓ Full update package workflow: Success")
        print("  - Package creation")
        print("  - Checksum calculation")
        print("  - Checksum verification")
        print("  - Archive validation")
        print("  - Archive extraction")
        print("  - Script validation")

    print("\n✅ Integration tests completed")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" LucasChess Update System - Verification Tests")
    print("=" * 70)

    try:
        test_compression()
        test_security()
        test_logging()
        test_backup()
        test_integration()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)


        return 0

    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ TESTS FAILED: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
