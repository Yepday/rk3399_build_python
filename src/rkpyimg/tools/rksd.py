"""
rksd - Rockchip SD/MMC boot image format tool.

This module implements U-Boot mkimage's rksd format for creating SD/MMC
boot images for Rockchip SoCs.

Original C implementation: tools/rksd.c, tools/rkcommon.c (U-Boot)

Image Structure:
    Offset  Size   Description
    0x000   512B   header0 (RC4 encrypted)
    0x200   1.5KB  Reserved (padding)
    0x800   4B     header1 (SPL magic: "RK33" for RK3399)
    0x804   ...    SPL binary data (DDR init, miniloader)

header0 format (512 bytes, RC4 encrypted):
    Offset  Size   Field
    0x000   4B     signature (0x0ff0aa55)
    0x004   4B     reserved
    0x008   4B     disable_rc4 (0=enabled, 1=disabled)
    0x00C   2B     init_offset (4 = 2KB offset for SPL)
    0x00E   492B   reserved1
    0x1F8   2B     init_size (SPL size in 512-byte blocks)
    0x1FA   2B     init_boot_size (total boot size in blocks)
    0x1FC   2B     reserved2

Usage:
    # Create idbloader.img from DDR init binary
    create_rksd_image("ddr.bin", "idbloader.img", chip="rk3399")

    # Append miniloader to existing image
    append_to_rksd("idbloader.img", "miniloader.bin")

Command line:
    # Pack DDR init
    python -m rkpyimg.tools.rksd --pack -n rk3399 -d ddr.bin idbloader.img

    # Append miniloader
    python -m rkpyimg.tools.rksd --append idbloader.img miniloader.bin
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rkpyimg.core.rc4 import rc4_crypt, ROCKCHIP_RC4_KEY


# Constants
RK_SIGNATURE = 0x0FF0AA55
RK_BLK_SIZE = 512
RK_INIT_OFFSET = 4  # SPL starts at block 4 (2KB)
RK_SPL_HDR_START = RK_INIT_OFFSET * RK_BLK_SIZE  # 2048 bytes
RK_INIT_SIZE_ALIGN = 4  # Init size must be multiple of 4 blocks (2KB)

# Chip configurations
CHIP_CONFIGS = {
    "rk3036": {"spl_hdr": b"RK30", "spl_size": 0x1000, "spl_rc4": False},
    "rk3066": {"spl_hdr": b"RK30", "spl_size": 0x8000, "spl_rc4": True},
    "rk3128": {"spl_hdr": b"RK31", "spl_size": 0x1800, "spl_rc4": False},
    "rk3188": {"spl_hdr": b"RK31", "spl_size": 0x8000 - 0x800, "spl_rc4": True},
    "rk322x": {"spl_hdr": b"RK32", "spl_size": 0x8000 - 0x1000, "spl_rc4": False},
    "rk3288": {"spl_hdr": b"RK32", "spl_size": 0x8000, "spl_rc4": False},
    "rk3308": {"spl_hdr": b"RK33", "spl_size": 0x40000 - 0x1000, "spl_rc4": False},
    "rk3328": {"spl_hdr": b"RK32", "spl_size": 0x8000 - 0x1000, "spl_rc4": False},
    "rk3368": {"spl_hdr": b"RK33", "spl_size": 0x8000 - 0x1000, "spl_rc4": False},
    "rk3399": {"spl_hdr": b"RK33", "spl_size": 0x30000 - 0x2000, "spl_rc4": False},
    "px30": {"spl_hdr": b"RK33", "spl_size": 0x2800, "spl_rc4": False},
    "rv1108": {"spl_hdr": b"RK11", "spl_size": 0x1800, "spl_rc4": False},
}


@dataclass
class Header0:
    """
    Rockchip SD/MMC boot header (512 bytes, RC4 encrypted).

    This header is stored at the beginning of the SD/MMC image and
    tells the BootROM where to find the SPL code.

    Attributes:
        signature: Must be 0x0FF0AA55
        disable_rc4: 0=SPL is RC4 encrypted, 1=plain binary
        init_offset: SPL offset in blocks (typically 4 = 2KB)
        init_size: SPL size in 512-byte blocks (aligned to 4 blocks)
        init_boot_size: Total boot size including next stage
    """
    signature: int = RK_SIGNATURE
    reserved: bytes = bytes(4)
    disable_rc4: int = 1  # 1=disabled by default
    init_offset: int = RK_INIT_OFFSET
    reserved1: bytes = bytes(490)
    reserved2: bytes = bytes(2)
    init_size: int = 0  # In blocks
    init_boot_size: int = 0  # In blocks

    def to_bytes(self) -> bytes:
        """Serialize to 512 bytes (before RC4 encryption)."""
        data = bytearray(512)

        # Pack fields
        struct.pack_into("<I", data, 0x000, self.signature)
        data[0x004:0x008] = self.reserved
        struct.pack_into("<I", data, 0x008, self.disable_rc4)
        struct.pack_into("<H", data, 0x00C, self.init_offset)
        data[0x00E:0x1F8] = self.reserved1
        data[0x1F8:0x1FA] = self.reserved2
        struct.pack_into("<H", data, 0x1FA, self.init_size)
        struct.pack_into("<H", data, 0x1FC, self.init_boot_size)

        return bytes(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> Header0:
        """Parse from 512 bytes (after RC4 decryption)."""
        if len(data) < 512:
            raise ValueError(f"Data too short: {len(data)} < 512")

        signature = struct.unpack_from("<I", data, 0x000)[0]
        reserved = data[0x004:0x008]
        disable_rc4 = struct.unpack_from("<I", data, 0x008)[0]
        init_offset = struct.unpack_from("<H", data, 0x00C)[0]
        reserved1 = data[0x00E:0x1F8]
        reserved2 = data[0x1F8:0x1FA]
        init_size = struct.unpack_from("<H", data, 0x1FA)[0]
        init_boot_size = struct.unpack_from("<H", data, 0x1FC)[0]

        return cls(
            signature=signature,
            reserved=reserved,
            disable_rc4=disable_rc4,
            init_offset=init_offset,
            reserved1=reserved1,
            reserved2=reserved2,
            init_size=init_size,
            init_boot_size=init_boot_size,
        )


def _round_up(n: int, align: int) -> int:
    """Round up to alignment."""
    return (n + align - 1) // align * align


def _div_round_up(n: int, d: int) -> int:
    """Divide and round up."""
    return (n + d - 1) // d


def create_rksd_image(
    spl_file: str | Path,
    output_file: str | Path,
    chip: str = "rk3399",
    max_boot_size: int = 512 * 1024,
) -> Path:
    """
    Create a Rockchip SD/MMC boot image.

    This function creates an image compatible with U-Boot mkimage rksd format.
    The image structure:
      - 0x000: header0 (512B, RC4 encrypted)
      - 0x200: padding (1.5KB)
      - 0x800: header1 (SPL magic, 4B) + SPL data

    Args:
        spl_file: Path to SPL binary (DDR init code)
        output_file: Path to output image
        chip: Chip name (e.g., "rk3399")
        max_boot_size: Maximum size for next-stage bootloader

    Returns:
        Path to created image

    Raises:
        ValueError: If chip is not supported or SPL is too large

    Example:
        >>> create_rksd_image("ddr.bin", "idbloader.img", "rk3399")
        PosixPath('idbloader.img')
    """
    spl_path = Path(spl_file)
    output_path = Path(output_file)

    # Get chip configuration
    if chip not in CHIP_CONFIGS:
        raise ValueError(
            f"Unsupported chip: {chip}. "
            f"Supported: {', '.join(CHIP_CONFIGS.keys())}"
        )

    config = CHIP_CONFIGS[chip]
    spl_hdr = config["spl_hdr"]
    spl_size_limit = config["spl_size"]
    need_rc4 = config["spl_rc4"]

    # Read SPL binary
    with open(spl_path, "rb") as f:
        spl_data = f.read()

    file_size = len(spl_data)

    # Check size limit
    if file_size > spl_size_limit:
        raise ValueError(
            f"SPL too large: {file_size} bytes > {spl_size_limit} bytes limit"
        )

    print(f"Creating rksd image for {chip}")
    print(f"SPL file: {spl_path}")
    print(f"SPL size: {file_size} bytes ({file_size // 1024} KB)")
    print(f"SPL magic: {spl_hdr.decode('ascii')}")

    # Calculate sizes in blocks
    init_size = _div_round_up(file_size, RK_BLK_SIZE)
    # Round to multiple of 4 blocks (required by BootROM)
    init_size = _round_up(init_size, RK_INIT_SIZE_ALIGN)

    init_boot_size = init_size + _div_round_up(max_boot_size, RK_BLK_SIZE)
    init_boot_size = _round_up(init_boot_size, RK_INIT_SIZE_ALIGN)

    # Create header0
    header0 = Header0(
        signature=RK_SIGNATURE,
        disable_rc4=1 if not need_rc4 else 0,
        init_offset=RK_INIT_OFFSET,
        init_size=init_size,
        init_boot_size=init_boot_size,
    )

    # Serialize and encrypt header0
    header0_bytes = header0.to_bytes()
    header0_encrypted = rc4_crypt(header0_bytes, ROCKCHIP_RC4_KEY)

    # Build image
    with open(output_path, "wb") as f:
        # Write encrypted header0 (512 bytes)
        f.write(header0_encrypted)

        # Write padding to reach 0x800 (2048 bytes)
        padding_size = RK_SPL_HDR_START - RK_BLK_SIZE
        f.write(bytes(padding_size))

        # Pad SPL data to init_size blocks
        padded_size = init_size * RK_BLK_SIZE
        spl_data_padded = spl_data.ljust(padded_size, b'\x00')

        # Write SPL data (DDR bin already has "RK33" magic at start)
        if need_rc4:
            # Encrypt SPL in 512-byte blocks
            encrypted_spl = bytearray()
            offset = 0
            while offset < len(spl_data_padded):
                block = spl_data_padded[offset:offset + RK_BLK_SIZE]
                encrypted_block = rc4_crypt(block, ROCKCHIP_RC4_KEY)
                encrypted_spl.extend(encrypted_block)
                offset += RK_BLK_SIZE
            f.write(encrypted_spl)
        else:
            # Write padded SPL without encryption
            f.write(spl_data_padded)

    print(f"Created: {output_path}")
    print(f"Image size: {output_path.stat().st_size} bytes")
    print(f"init_size: {init_size} blocks ({init_size * RK_BLK_SIZE} bytes)")
    print(f"init_boot_size: {init_boot_size} blocks")

    return output_path


def append_to_rksd(image_file: str | Path, append_file: str | Path) -> Path:
    """
    Append data to an existing rksd image.

    This is used to append miniloader to the idbloader.img after
    DDR init code.

    Args:
        image_file: Existing rksd image
        append_file: File to append

    Returns:
        Path to modified image

    Example:
        >>> append_to_rksd("idbloader.img", "miniloader.bin")
        PosixPath('idbloader.img')
    """
    image_path = Path(image_file)
    append_path = Path(append_file)

    # Read append data
    with open(append_path, "rb") as f:
        append_data = f.read()

    # Append to image
    with open(image_path, "ab") as f:
        f.write(append_data)

    print(f"Appended {len(append_data)} bytes from {append_path}")
    print(f"New image size: {image_path.stat().st_size} bytes")

    return image_path


def verify_rksd_image(image_file: str | Path) -> dict:
    """
    Verify and extract info from rksd image.

    Args:
        image_file: Path to rksd image

    Returns:
        Dictionary with image info

    Raises:
        ValueError: If image is invalid
    """
    image_path = Path(image_file)

    with open(image_path, "rb") as f:
        # Read and decrypt header0
        header0_encrypted = f.read(RK_BLK_SIZE)
        header0_bytes = rc4_crypt(header0_encrypted, ROCKCHIP_RC4_KEY)
        header0 = Header0.from_bytes(header0_bytes)

        # Verify signature
        if header0.signature != RK_SIGNATURE:
            raise ValueError(
                f"Invalid signature: 0x{header0.signature:08X} != 0x{RK_SIGNATURE:08X}"
            )

        # Read header1 (SPL magic)
        f.seek(RK_SPL_HDR_START)
        header1 = f.read(4)

        # Find matching chip
        chip_name = "unknown"
        for name, config in CHIP_CONFIGS.items():
            if config["spl_hdr"] == header1:
                chip_name = name
                break

        info = {
            "signature": f"0x{header0.signature:08X}",
            "chip": chip_name,
            "spl_magic": header1.decode("ascii", errors="replace"),
            "init_offset": header0.init_offset,
            "init_size_blocks": header0.init_size,
            "init_size_bytes": header0.init_size * RK_BLK_SIZE,
            "init_boot_size_blocks": header0.init_boot_size,
            "disable_rc4": header0.disable_rc4,
            "file_size": image_path.stat().st_size,
        }

        return info


# CLI
def main():
    """Command line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Rockchip SD/MMC boot image tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create idbloader.img from DDR init
  %(prog)s --pack -n rk3399 -d ddr.bin idbloader.img

  # Append miniloader
  %(prog)s --append idbloader.img miniloader.bin

  # Verify image
  %(prog)s --verify idbloader.img
        """,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pack", action="store_true", help="Create rksd image")
    mode.add_argument("--append", action="store_true", help="Append to existing image")
    mode.add_argument("--verify", action="store_true", help="Verify and show image info")

    parser.add_argument("-n", "--chip", default="rk3399", help="Chip name (default: rk3399)")
    parser.add_argument("-d", "--data", help="Input SPL file (for --pack)")
    parser.add_argument("image", help="Output/input image file")
    parser.add_argument("append_file", nargs="?", help="File to append (for --append)")

    args = parser.parse_args()

    if args.pack:
        if not args.data:
            parser.error("--pack requires -d/--data")
        create_rksd_image(args.data, args.image, args.chip)

    elif args.append:
        if not args.append_file:
            parser.error("--append requires append_file argument")
        append_to_rksd(args.image, args.append_file)

    elif args.verify:
        info = verify_rksd_image(args.image)
        print("Image info:")
        for key, value in info.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
