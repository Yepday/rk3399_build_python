"""
Core functionality for Rockchip image processing.

This module contains:
- header: RK Header parsing and generation
- ini_parser: INI configuration file parsing
- checksum: CRC and checksum calculations
"""

from rkpyimg.core.header import RKHeader
from rkpyimg.core.ini_parser import RKBootConfig, RKTrustConfig
from rkpyimg.core.checksum import crc32_rk

__all__ = [
    "RKHeader",
    "RKBootConfig",
    "RKTrustConfig",
    "crc32_rk",
]
