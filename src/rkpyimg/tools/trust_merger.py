"""
trust_merger - Merge BL31 and BL32 into trust.img.

This module implements the functionality of Rockchip's trust_merger tool,
which combines ARM Trusted Firmware (BL31) and OP-TEE (BL32) into trust.img.

Original C implementation: trust_merger.c

Usage:
    # Command line equivalent:
    # trust_merger --rsa 4 --sha 2 --size 1024 RKTRUST/RK3399TRUST.ini

    from rkpyimg.tools import TrustMerger

    merger = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")
    merger.set_rsa_mode(4)  # RSA PKCS1 V2.1
    merger.set_sha_mode(2)  # SHA256
    merger.pack("trust.img")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Literal

from rkpyimg.core.ini_parser import RKTrustConfig
from rkpyimg.core.checksum import crc32_rk


class RSAMode(IntEnum):
    """RSA signing modes for trust image."""

    NONE = 0
    PKCS1_V15 = 1
    PKCS1_V21 = 3  # Used by RK3308/PX30
    PKCS1_V21_NEW = 4  # Default for most chips


class SHAMode(IntEnum):
    """SHA hash modes for trust image."""

    SHA1 = 1
    SHA256 = 2
    SHA512 = 3


@dataclass
class TrustMerger:
    """
    Merge BL31 and BL32 into trust image.

    This class implements the trust_merger functionality which creates
    trust.img containing ARM Trusted Firmware and optionally OP-TEE.

    The trust.img contains:
    1. Trust header
    2. BL31 - ARM Trusted Firmware (ATF)
    3. BL32 - OP-TEE (optional)

    Attributes:
        config: Parsed RKTRUST INI configuration
        rsa_mode: RSA signing mode
        sha_mode: SHA hash mode
        size: Image size parameter

    Example:
        >>> merger = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")
        >>> merger.pack("trust.img")

        >>> # With specific security settings
        >>> merger = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")
        >>> merger.rsa_mode = RSAMode.PKCS1_V21_NEW
        >>> merger.sha_mode = SHAMode.SHA256
        >>> merger.pack("trust.img")
    """

    config: RKTrustConfig
    rsa_mode: RSAMode = RSAMode.PKCS1_V21_NEW
    sha_mode: SHAMode = SHAMode.SHA256
    size: int = 1024  # KB

    @classmethod
    def from_ini(cls, ini_path: str | Path) -> TrustMerger:
        """
        Create TrustMerger from INI configuration file.

        Args:
            ini_path: Path to RKTRUST/*.ini file

        Returns:
            Configured TrustMerger instance
        """
        config = RKTrustConfig.from_file(ini_path)
        return cls(config=config)

    def set_rsa_mode(self, mode: int | RSAMode) -> None:
        """Set RSA signing mode."""
        self.rsa_mode = RSAMode(mode)

    def set_sha_mode(self, mode: int | SHAMode) -> None:
        """Set SHA hash mode."""
        self.sha_mode = SHAMode(mode)

    def pack(self, output: str | Path) -> Path:
        """
        Pack the trust image.

        Args:
            output: Output file path

        Returns:
            Path to created file
        """
        output_path = Path(output)

        # TODO: Implement based on trust_merger.c
        # Key steps:
        # 1. Create trust header
        # 2. Load and append BL31 at specified address
        # 3. Load and append BL32 at specified address (if present)
        # 4. Apply RSA/SHA according to mode
        # 5. Calculate and add checksums

        raise NotImplementedError(
            "trust_merger packing not yet implemented. "
            "See trust_merger.c for reference implementation."
        )

    def validate_binaries(self) -> bool:
        """
        Check if all required binaries exist.

        Returns:
            True if all binaries are accessible
        """
        if self.config.bl31 and not self.config.bl31.path.exists():
            return False
        if self.config.bl32 and not self.config.bl32.path.exists():
            return False
        return True

    @property
    def has_optee(self) -> bool:
        """Check if OP-TEE (BL32) is configured."""
        return self.config.bl32 is not None
