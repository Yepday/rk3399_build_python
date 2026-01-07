"""
loaderimage - Pack U-Boot binary into Rockchip format.

This module implements the functionality of Rockchip's loaderimage tool,
which wraps u-boot.bin with Rockchip headers to create uboot.img.

Original C implementation: loaderimage.c

Usage:
    # Command line equivalent:
    # loaderimage --pack --uboot u-boot.bin uboot.img 0x200000 --size 1024 1

    from rkpyimg.tools import pack_loader_image
    pack_loader_image(
        input_file="u-boot.bin",
        output_file="uboot.img",
        load_addr=0x200000,
        chip="RK3399"
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from rkpyimg.core.header import RKHeader, RKChip
from rkpyimg.core.checksum import crc32_rk


def pack_loader_image(
    input_file: str | Path,
    output_file: str | Path,
    load_addr: int = 0x200000,
    chip: str = "RK3399",
    image_type: Literal["uboot", "trust"] = "uboot",
) -> Path:
    """
    Pack a binary file with Rockchip header.

    This function wraps a raw binary (like u-boot.bin) with the
    Rockchip header format required by the BootROM.

    Args:
        input_file: Path to input binary file
        output_file: Path to output image file
        load_addr: Load address for the binary (default: 0x200000)
        chip: Chip type (e.g., "RK3399", "RK3588")
        image_type: Type of image ("uboot" or "trust")

    Returns:
        Path to the created output file

    Example:
        >>> pack_loader_image("u-boot.bin", "uboot.img")
        PosixPath('uboot.img')

        >>> pack_loader_image(
        ...     "u-boot.bin",
        ...     "uboot.img",
        ...     load_addr=0x200000,
        ...     chip="RK3588"
        ... )
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    # Read input binary
    with open(input_path, "rb") as f:
        data = f.read()

    # Create header
    # TODO: Map chip string to RKChip enum
    # TODO: Implement actual header creation based on C source

    raise NotImplementedError(
        "loaderimage packing not yet implemented. "
        "See loaderimage.c for reference implementation."
    )


def unpack_loader_image(
    input_file: str | Path,
    output_file: str | Path,
) -> tuple[RKHeader, Path]:
    """
    Extract binary from a Rockchip loader image.

    Args:
        input_file: Path to Rockchip image file
        output_file: Path to output raw binary

    Returns:
        Tuple of (header, output_path)
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    # Read and parse header
    header = RKHeader.from_file(input_path)

    # TODO: Extract data after header

    raise NotImplementedError(
        "loaderimage unpacking not yet implemented."
    )
