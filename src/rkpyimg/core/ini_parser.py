"""
INI configuration file parser for Rockchip firmware.

This module parses RKBOOT/*.ini and RKTRUST/*.ini configuration files
used by boot_merger and trust_merger tools.

RKBOOT INI Format Example (RK3399MINIALL.ini):
    [CHIP_NAME]
    NAME=RK330C

    [VERSION]
    MAJOR=2
    MINOR=58

    [CODE471_OPTION]
    NUM=1
    Path1=bin/rk33/rk3399_ddr_800MHz_v1.25.bin

    [CODE472_OPTION]
    NUM=1
    Path1=bin/rk33/rk3399_miniloader_v1.26.bin

    [OUTPUT]
    PATH=rk3399_loader_v1.25.126.bin

RKTRUST INI Format Example (RK3399TRUST.ini):
    [VERSION]
    MAJOR=1
    MINOR=0

    [BL31_OPTION]
    SEC=1
    PATH=bin/rk33/rk3399_bl31_v1.35.elf
    ADDR=0x10000

    [BL32_OPTION]
    SEC=1
    PATH=bin/rk33/rk3399_bl32_v2.01.bin
    ADDR=0x8400000

    [OUTPUT]
    PATH=trust.img
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BinaryEntry:
    """Represents a binary file entry in the INI configuration."""

    path: Path
    address: int = 0
    size: int = 0

    @classmethod
    def from_section(
        cls,
        config: configparser.ConfigParser,
        section: str,
        base_path: Path | None = None
    ) -> BinaryEntry | None:
        """
        Parse a binary entry from a config section.

        Args:
            config: ConfigParser instance
            section: Section name to parse
            base_path: Base path for resolving relative paths

        Returns:
            BinaryEntry or None if section doesn't exist
        """
        if section not in config:
            return None

        sec = config[section]

        # Check if section is enabled (SEC=1)
        sec_enabled = sec.get("SEC", "0")
        if sec_enabled == "0":
            return None

        path_str = sec.get("PATH", sec.get("Path1", ""))
        if not path_str:
            return None

        path = Path(path_str)
        if base_path and not path.is_absolute():
            path = base_path / path

        addr_str = sec.get("ADDR", "0")
        addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)

        return cls(path=path, address=addr)


@dataclass
class RKBootConfig:
    """
    Configuration for boot_merger (RKBOOT/*.ini).

    This represents the configuration used to merge DDR initialization
    code and miniloader into idbloader.img/loader.bin.

    Attributes:
        chip_name: Chip identifier (e.g., "RK330C")
        version: Tuple of (major, minor) version
        ddr_bins: List of DDR initialization binaries (CODE471)
        loader_bins: List of miniloader binaries (CODE472)
        output_path: Output file path

    Example:
        >>> config = RKBootConfig.from_file("RKBOOT/RK3399MINIALL.ini")
        >>> print(config.chip_name)
        RK330C
        >>> for ddr in config.ddr_bins:
        ...     print(ddr.path)
    """

    chip_name: str = ""
    version: tuple[int, int] = (0, 0)
    ddr_bins: list[BinaryEntry] = field(default_factory=list)
    loader_bins: list[BinaryEntry] = field(default_factory=list)
    output_path: Path = Path("loader.bin")

    @classmethod
    def from_file(cls, path: str | Path) -> RKBootConfig:
        """
        Parse RKBOOT INI configuration file.

        Args:
            path: Path to the INI file

        Returns:
            Parsed RKBootConfig instance
        """
        path = Path(path)
        config = configparser.ConfigParser()
        config.read(path, encoding="utf-8")

        base_path = path.parent

        # Parse chip name
        chip_name = ""
        if "CHIP_NAME" in config:
            chip_name = config["CHIP_NAME"].get("NAME", "")

        # Parse version
        version = (0, 0)
        if "VERSION" in config:
            major = int(config["VERSION"].get("MAJOR", "0"))
            minor = int(config["VERSION"].get("MINOR", "0"))
            version = (major, minor)

        # Parse DDR binaries (CODE471_OPTION)
        ddr_bins: list[BinaryEntry] = []
        if "CODE471_OPTION" in config:
            num = int(config["CODE471_OPTION"].get("NUM", "0"))
            for i in range(1, num + 1):
                path_key = f"Path{i}"
                if path_key in config["CODE471_OPTION"]:
                    bin_path = Path(config["CODE471_OPTION"][path_key])
                    if not bin_path.is_absolute():
                        bin_path = base_path / bin_path
                    ddr_bins.append(BinaryEntry(path=bin_path))

        # Parse loader binaries (CODE472_OPTION)
        loader_bins: list[BinaryEntry] = []
        if "CODE472_OPTION" in config:
            num = int(config["CODE472_OPTION"].get("NUM", "0"))
            for i in range(1, num + 1):
                path_key = f"Path{i}"
                if path_key in config["CODE472_OPTION"]:
                    bin_path = Path(config["CODE472_OPTION"][path_key])
                    if not bin_path.is_absolute():
                        bin_path = base_path / bin_path
                    loader_bins.append(BinaryEntry(path=bin_path))

        # Parse output path
        output_path = Path("loader.bin")
        if "OUTPUT" in config:
            output_path = Path(config["OUTPUT"].get("PATH", "loader.bin"))

        return cls(
            chip_name=chip_name,
            version=version,
            ddr_bins=ddr_bins,
            loader_bins=loader_bins,
            output_path=output_path,
        )


@dataclass
class RKTrustConfig:
    """
    Configuration for trust_merger (RKTRUST/*.ini).

    This represents the configuration used to merge BL31 (ATF) and
    BL32 (OP-TEE) into trust.img.

    Attributes:
        version: Tuple of (major, minor) version
        bl31: BL31 (ARM Trusted Firmware) binary entry
        bl32: BL32 (OP-TEE) binary entry (optional)
        output_path: Output file path

    Example:
        >>> config = RKTrustConfig.from_file("RKTRUST/RK3399TRUST.ini")
        >>> if config.bl31:
        ...     print(f"BL31: {config.bl31.path} @ 0x{config.bl31.address:X}")
    """

    version: tuple[int, int] = (0, 0)
    bl31: BinaryEntry | None = None
    bl32: BinaryEntry | None = None
    output_path: Path = Path("trust.img")

    @classmethod
    def from_file(cls, path: str | Path) -> RKTrustConfig:
        """
        Parse RKTRUST INI configuration file.

        Args:
            path: Path to the INI file

        Returns:
            Parsed RKTrustConfig instance
        """
        path = Path(path)
        config = configparser.ConfigParser()
        config.read(path, encoding="utf-8")

        base_path = path.parent

        # Parse version
        version = (0, 0)
        if "VERSION" in config:
            major = int(config["VERSION"].get("MAJOR", "0"))
            minor = int(config["VERSION"].get("MINOR", "0"))
            version = (major, minor)

        # Parse BL31
        bl31 = BinaryEntry.from_section(config, "BL31_OPTION", base_path)

        # Parse BL32
        bl32 = BinaryEntry.from_section(config, "BL32_OPTION", base_path)

        # Parse output path
        output_path = Path("trust.img")
        if "OUTPUT" in config:
            output_path = Path(config["OUTPUT"].get("PATH", "trust.img"))

        return cls(
            version=version,
            bl31=bl31,
            bl32=bl32,
            output_path=output_path,
        )
