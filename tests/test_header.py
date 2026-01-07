"""
Tests for RK Header parsing and generation.
"""

import pytest
from rkpyimg.core.header import RKHeader, RK_HEADER_MAGIC, validate_header


class TestRKHeader:
    """Tests for RKHeader class."""

    def test_default_values(self):
        """Test default header values."""
        header = RKHeader()
        assert header.magic == RK_HEADER_MAGIC
        assert header.load_addr == 0x200000

    def test_validate_header_valid(self):
        """Test header validation with valid magic."""
        # Little-endian 0x0FF0AA55
        data = bytes([0x55, 0xAA, 0xF0, 0x0F])
        assert validate_header(data) is True

    def test_validate_header_invalid(self):
        """Test header validation with invalid magic."""
        data = bytes([0x00, 0x00, 0x00, 0x00])
        assert validate_header(data) is False

    def test_validate_header_short(self):
        """Test header validation with short data."""
        data = bytes([0x55, 0xAA])
        assert validate_header(data) is False

    @pytest.mark.skip(reason="Not yet implemented")
    def test_from_bytes(self):
        """Test parsing header from bytes."""
        # TODO: Implement when from_bytes is complete
        pass

    @pytest.mark.skip(reason="Not yet implemented")
    def test_to_bytes(self):
        """Test serializing header to bytes."""
        # TODO: Implement when to_bytes is complete
        pass
