"""
boot_merger - Merge DDR init and miniloader binaries.

This module implements the functionality of Rockchip's boot_merger tool,
which combines DDR initialization code and miniloader into idbloader.img
or loader.bin.

Original C implementation: boot_merger.c

Usage:
    # Command line equivalent:
    # boot_merger RKBOOT/RK3399MINIALL.ini

    from rkpyimg.tools import BootMerger

    merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
    merger.pack("idbloader.img")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from rkpyimg.core.ini_parser import RKBootConfig, BinaryEntry
from rkpyimg.core.checksum import crc32_rk


@dataclass
class BootMerger:
    """
    Merge DDR init and miniloader into bootable image.

    This class implements the boot_merger functionality which creates
    idbloader.img (for SD card boot) or loader.bin.

    The idbloader contains:
    1. ID Block header (for BootROM)
    2. DDR initialization code (trains memory)
    3. Miniloader (loads U-Boot)

    Attributes:
        config: Parsed RKBOOT INI configuration

    Example:
        >>> merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
        >>> merger.pack("idbloader.img")

        >>> # Or with custom binaries
        >>> merger = BootMerger(config)
        >>> merger.add_ddr_binary("ddr.bin")
        >>> merger.add_loader_binary("miniloader.bin")
        >>> merger.pack("idbloader.img")
    """

    config: RKBootConfig

    @classmethod
    def from_ini(cls, ini_path: str | Path) -> BootMerger:
        """
        Create BootMerger from INI configuration file.

        Args:
            ini_path: Path to RKBOOT/*.ini file

        Returns:
            Configured BootMerger instance
        """
        config = RKBootConfig.from_file(ini_path)
        return cls(config=config)

    def pack(self, output: str | Path) -> Path:
        """
        Pack the idbloader/loader image.

        Args:
            output: Output file path

        Returns:
            Path to created file
        """
        output_path = Path(output)

        # TODO: Implement based on boot_merger.c
        # Key steps:
        # 1. Create ID Block header
        # 2. Append DDR init code at correct offset
        # 3. Append miniloader at correct offset
        # 4. Calculate and add checksums

        raise NotImplementedError(
            "boot_merger packing not yet implemented. "
            "See boot_merger.c for reference implementation."
        )

    def pack_spl(self, output: str | Path) -> Path:
        """
        Pack as idbloader.img for SD card boot.

        This creates the format expected when booting from SD card,
        which has a slightly different layout than loader.bin.

        Args:
            output: Output file path

        Returns:
            Path to created file
        """
        # idbloader = ID Block + SPL
        raise NotImplementedError(
            "SPL packing not yet implemented."
        )

    def validate_binaries(self) -> bool:
        """
        Check if all required binaries exist.

        Returns:
            True if all binaries are accessible
        """
        for entry in self.config.ddr_bins:
            if not entry.path.exists():
                return False
        for entry in self.config.loader_bins:
            if not entry.path.exists():
                return False
        return True
