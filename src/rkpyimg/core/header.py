"""
Rockchip Header handling.

This module implements parsing and generation of Rockchip firmware headers.
The header format is required by Rockchip's BootROM to correctly load firmware.

Header Format (from loaderimage.c):
    Offset  Size  Field
    0x000   4B    Magic (0x0FF0AA55, little-endian)
    0x004   4B    Reserved
    0x008   4B    Chip Signature (e.g., "RK33" for RK3399)
    0x00C   4B    Check Size (size of data for CRC)
    0x010   4B    Load Address
    ...

TODO: Complete implementation based on C source analysis
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO


class RKChip(IntEnum):
    """Rockchip chip identifiers."""

    RK3399 = 0x33333339  # "RK33" + 0x39
    RK3588 = 0x33353838  # Placeholder, needs verification
    RK3568 = 0x33353638  # Placeholder, needs verification
    # TODO: Add more chip types


# Magic number for RK header
RK_HEADER_MAGIC = 0x0FF0AA55


@dataclass
class RKHeader:
    """
    Rockchip firmware header.

    This class represents the header structure used in Rockchip firmware images
    such as uboot.img, trust.img, and loader images.

    Attributes:
        magic: Header magic number (should be 0x0FF0AA55)
        chip: Chip identifier
        load_addr: Address where firmware should be loaded
        data_size: Size of the firmware data

    Example:
        >>> header = RKHeader.from_file("uboot.img")
        >>> print(f"Chip: {header.chip}, Load addr: 0x{header.load_addr:08X}")

        >>> header = RKHeader(chip=RKChip.RK3399, load_addr=0x200000, data_size=1024)
        >>> header.to_bytes()
    """

    magic: int = RK_HEADER_MAGIC
    chip: int = RKChip.RK3399
    load_addr: int = 0x200000
    data_size: int = 0

    # Header size in bytes
    HEADER_SIZE: int = 512  # TODO: Verify from C source

    @classmethod
    def from_bytes(cls, data: bytes) -> RKHeader:
        """
        Parse header from binary data.

        Args:
            data: Binary data containing the header

        Returns:
            Parsed RKHeader instance

        Raises:
            ValueError: If magic number doesn't match
        """
        # TODO: Implement based on C source analysis
        raise NotImplementedError("Header parsing not yet implemented")

    @classmethod
    def from_file(cls, path: str | Path) -> RKHeader:
        """
        Parse header from a file.

        Args:
            path: Path to the firmware image file

        Returns:
            Parsed RKHeader instance
        """
        with open(path, "rb") as f:
            data = f.read(cls.HEADER_SIZE)
        return cls.from_bytes(data)

    def to_bytes(self) -> bytes:
        """
        Serialize header to binary format.

        Returns:
            Binary representation of the header
        """
        # TODO: Implement based on C source analysis
        raise NotImplementedError("Header serialization not yet implemented")

    def write_to(self, f: BinaryIO) -> int:
        """
        Write header to a file object.

        Args:
            f: File object opened in binary write mode

        Returns:
            Number of bytes written
        """
        data = self.to_bytes()
        return f.write(data)


def validate_header(data: bytes) -> bool:
    """
    Check if data starts with a valid RK header.

    Args:
        data: Binary data to check

    Returns:
        True if valid RK header is present
    """
    if len(data) < 4:
        return False
    magic = struct.unpack("<I", data[:4])[0]
    return magic == RK_HEADER_MAGIC
