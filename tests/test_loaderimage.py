"""
Tests for loaderimage pack/unpack functionality.
"""

import struct
import tempfile
from pathlib import Path

import pytest

from rkpyimg.tools.loaderimage import (
    HEADER_SIZE,
    RK_UBOOT_MAGIC,
    RK_TRUST_MAGIC,
    SecondLoaderHeader,
    pack_loader_image,
    pack_uboot,
    pack_trust,
    unpack_loader_image,
    get_loader_info,
    _calculate_sha256,
    _align_size,
)


class TestSecondLoaderHeader:
    """Tests for SecondLoaderHeader class."""

    def test_default_values(self):
        """Test default header values."""
        header = SecondLoaderHeader()
        assert header.magic == RK_UBOOT_MAGIC
        assert header.version == 0
        assert header.loader_load_addr == 0x200000
        assert header.loader_load_size == 0
        assert header.hash_len == 32

    def test_to_bytes_size(self):
        """Test that header serializes to exactly 2048 bytes."""
        header = SecondLoaderHeader()
        data = header.to_bytes()
        assert len(data) == HEADER_SIZE

    def test_to_bytes_magic(self):
        """Test magic number in serialized header."""
        header = SecondLoaderHeader(magic=RK_UBOOT_MAGIC)
        data = header.to_bytes()
        assert data[:8] == b"LOADER  "

        header_trust = SecondLoaderHeader(magic=RK_TRUST_MAGIC)
        data_trust = header_trust.to_bytes()
        assert data_trust[:8] == b"TOS     "

    def test_to_bytes_fields(self):
        """Test field values in serialized header."""
        header = SecondLoaderHeader(
            magic=RK_UBOOT_MAGIC,
            version=5,
            loader_load_addr=0x200000,
            loader_load_size=0x10000,
            crc32=0x12345678,
            hash_len=32,
        )
        data = header.to_bytes()

        # Parse back the values
        magic, version, reserved0, load_addr, load_size, crc32, hash_len = struct.unpack(
            "<8sIIIIII", data[:32]
        )

        assert magic == b"LOADER  "
        assert version == 5
        assert load_addr == 0x200000
        assert load_size == 0x10000
        assert crc32 == 0x12345678
        assert hash_len == 32

    def test_from_bytes_roundtrip(self):
        """Test that from_bytes(to_bytes()) preserves values."""
        original = SecondLoaderHeader(
            magic=RK_UBOOT_MAGIC,
            version=10,
            loader_load_addr=0x400000,
            loader_load_size=0x80000,
            crc32=0xAABBCCDD,
            hash_len=32,
            hash=b"\x01\x02\x03" + bytes(29),
        )

        data = original.to_bytes()
        parsed = SecondLoaderHeader.from_bytes(data)

        assert parsed.magic == original.magic
        assert parsed.version == original.version
        assert parsed.loader_load_addr == original.loader_load_addr
        assert parsed.loader_load_size == original.loader_load_size
        assert parsed.crc32 == original.crc32
        assert parsed.hash_len == original.hash_len

    def test_from_bytes_too_short(self):
        """Test that from_bytes raises on short data."""
        with pytest.raises(ValueError, match="Data too short"):
            SecondLoaderHeader.from_bytes(bytes(100))

    def test_is_uboot(self):
        """Test is_uboot detection."""
        header = SecondLoaderHeader(magic=RK_UBOOT_MAGIC)
        assert header.is_uboot() is True
        assert header.is_trust() is False

    def test_is_trust(self):
        """Test is_trust detection."""
        header = SecondLoaderHeader(magic=RK_TRUST_MAGIC)
        assert header.is_trust() is True
        assert header.is_uboot() is False


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_align_size_already_aligned(self):
        """Test alignment when already aligned."""
        assert _align_size(1024, 4) == 1024
        assert _align_size(1024, 64) == 1024

    def test_align_size_needs_padding(self):
        """Test alignment when padding needed."""
        assert _align_size(1, 4) == 4
        assert _align_size(5, 4) == 8
        assert _align_size(63, 64) == 64
        assert _align_size(65, 64) == 128

    def test_calculate_sha256_deterministic(self):
        """Test SHA256 calculation is deterministic."""
        data = b"test data for hashing"
        hash1 = _calculate_sha256(data, 0, 0x200000, len(data), 32)
        hash2 = _calculate_sha256(data, 0, 0x200000, len(data), 32)
        assert hash1 == hash2
        assert len(hash1) == 32

    def test_calculate_sha256_different_inputs(self):
        """Test SHA256 produces different results for different inputs."""
        data = b"test data"
        hash1 = _calculate_sha256(data, 0, 0x200000, len(data), 32)
        hash2 = _calculate_sha256(data, 0, 0x300000, len(data), 32)  # Different addr
        hash3 = _calculate_sha256(data, 1, 0x200000, len(data), 32)  # Different version
        assert hash1 != hash2
        assert hash1 != hash3


class TestPackUnpack:
    """Tests for pack/unpack functionality."""

    def test_pack_uboot_basic(self, tmp_path):
        """Test basic U-Boot packing."""
        # Create test input file
        input_file = tmp_path / "u-boot.bin"
        test_data = b"\x00" * 1024 + b"U-BOOT TEST DATA" + b"\xFF" * 1024
        input_file.write_bytes(test_data)

        # Pack
        output_file = tmp_path / "uboot.img"
        result = pack_uboot(input_file, output_file, load_addr=0x200000)

        assert result == output_file
        assert output_file.exists()

        # Check output size (4 copies * 1MB)
        assert output_file.stat().st_size == 4 * 1024 * 1024

    def test_pack_uboot_custom_copies(self, tmp_path):
        """Test packing with custom copy count."""
        input_file = tmp_path / "u-boot.bin"
        input_file.write_bytes(b"\x00" * 1024)

        output_file = tmp_path / "uboot.img"
        pack_uboot(input_file, output_file, num_copies=2, max_size=512 * 1024)

        # 2 copies * 512KB
        assert output_file.stat().st_size == 2 * 512 * 1024

    def test_pack_trust_basic(self, tmp_path):
        """Test basic Trust packing."""
        input_file = tmp_path / "trust.bin"
        input_file.write_bytes(b"\x00" * 2048)

        output_file = tmp_path / "trust.img"
        result = pack_trust(input_file, output_file, load_addr=0x8400000)

        assert result == output_file
        assert output_file.exists()

        # Verify header magic
        header = SecondLoaderHeader.from_file(output_file)
        assert header.is_trust()
        assert header.loader_load_addr == 0x8400000

    def test_pack_too_large_file(self, tmp_path):
        """Test that packing fails for oversized input."""
        input_file = tmp_path / "large.bin"
        # Create file larger than max_size - header_size
        input_file.write_bytes(b"\x00" * (512 * 1024))

        output_file = tmp_path / "output.img"
        with pytest.raises(ValueError, match="too large"):
            pack_loader_image(
                input_file,
                output_file,
                load_addr=0x200000,
                max_size=512 * 1024,  # Only 512KB allowed
            )

    def test_unpack_roundtrip(self, tmp_path):
        """Test pack then unpack recovers original data."""
        # Create test data
        original_data = bytes(range(256)) * 100  # 25.6KB of test data
        input_file = tmp_path / "u-boot.bin"
        input_file.write_bytes(original_data)

        # Pack
        packed_file = tmp_path / "uboot.img"
        pack_uboot(input_file, packed_file)

        # Unpack
        unpacked_file = tmp_path / "u-boot-unpacked.bin"
        header, _ = unpack_loader_image(packed_file, unpacked_file)

        # Verify
        unpacked_data = unpacked_file.read_bytes()
        # Note: unpacked data may be 4-byte aligned
        assert unpacked_data[: len(original_data)] == original_data

    def test_get_loader_info(self, tmp_path):
        """Test getting loader info."""
        input_file = tmp_path / "u-boot.bin"
        input_file.write_bytes(b"\x00" * 1024)

        packed_file = tmp_path / "uboot.img"
        pack_uboot(input_file, packed_file, load_addr=0x200000, version=5)

        header = get_loader_info(packed_file)
        assert header.is_uboot()
        assert header.version == 5
        assert header.loader_load_addr == 0x200000

    def test_header_crc_matches(self, tmp_path):
        """Test that CRC in header matches calculated CRC."""
        from rkpyimg.core.checksum import crc32_rk

        # Create test data
        test_data = b"CRC TEST DATA" * 100
        input_file = tmp_path / "test.bin"
        input_file.write_bytes(test_data)

        # Pack
        packed_file = tmp_path / "test.img"
        pack_uboot(input_file, packed_file)

        # Read header and data
        with open(packed_file, "rb") as f:
            header_data = f.read(HEADER_SIZE)
            header = SecondLoaderHeader.from_bytes(header_data)
            payload = f.read(header.loader_load_size)

        # Verify CRC
        calculated_crc = crc32_rk(payload)
        assert header.crc32 == calculated_crc


class TestCLI:
    """Tests for CLI interface."""

    def test_cli_pack_uboot(self, tmp_path, monkeypatch):
        """Test CLI pack command."""
        import sys
        from rkpyimg.tools.loaderimage import main

        input_file = tmp_path / "u-boot.bin"
        input_file.write_bytes(b"\x00" * 1024)
        output_file = tmp_path / "uboot.img"

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "loaderimage",
                "--pack",
                "--uboot",
                str(input_file),
                str(output_file),
                "0x200000",
            ],
        )

        main()
        assert output_file.exists()

    def test_cli_info(self, tmp_path, monkeypatch, capsys):
        """Test CLI info command."""
        import sys
        from rkpyimg.tools.loaderimage import main

        # First create a packed file
        input_file = tmp_path / "u-boot.bin"
        input_file.write_bytes(b"\x00" * 1024)
        packed_file = tmp_path / "uboot.img"
        pack_uboot(input_file, packed_file, version=3)

        # Then get info
        monkeypatch.setattr(
            sys,
            "argv",
            ["loaderimage", "--info", str(packed_file)],
        )

        main()
        captured = capsys.readouterr()
        assert "Rollback index is 3" in captured.out
