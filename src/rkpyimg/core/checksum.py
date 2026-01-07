"""
Checksum and CRC calculations for Rockchip firmware.

Rockchip uses CRC32 for verifying firmware integrity.
The specific CRC32 variant and polynomial needs to be verified
from the C source code.
"""

from __future__ import annotations

import binascii


def crc32_rk(data: bytes) -> int:
    """
    Calculate CRC32 checksum for Rockchip firmware.

    Args:
        data: Binary data to calculate checksum for

    Returns:
        CRC32 checksum value

    Note:
        The exact CRC32 variant (polynomial, initial value, etc.)
        needs to be verified from the C source code.

    TODO: Verify CRC32 parameters from loaderimage.c
    """
    # Standard CRC32 as placeholder
    # May need adjustment based on Rockchip's specific implementation
    return binascii.crc32(data) & 0xFFFFFFFF


def calculate_checksum(data: bytes) -> int:
    """
    Calculate simple additive checksum.

    Some Rockchip headers use simple additive checksums
    instead of CRC32.

    Args:
        data: Binary data

    Returns:
        Checksum value (sum of all bytes)
    """
    return sum(data) & 0xFFFFFFFF


def verify_crc(data: bytes, expected_crc: int) -> bool:
    """
    Verify CRC32 checksum.

    Args:
        data: Binary data to verify
        expected_crc: Expected CRC32 value

    Returns:
        True if CRC matches
    """
    return crc32_rk(data) == expected_crc
