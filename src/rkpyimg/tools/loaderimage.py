"""
loaderimage - Pack/Unpack U-Boot and Trust binaries into Rockchip format.

This module implements the functionality of Rockchip's loaderimage tool,
which wraps u-boot.bin/trust.bin with Rockchip headers to create uboot.img/trust.img.

Original C implementation: loaderimage.c

Header Structure (second_loader_hdr, 2048 bytes total):
    Offset  Size   Field              Description
    0x000   8B     magic              "LOADER  " or "TOS     "
    0x008   4B     version            Rollback protection version
    0x00C   4B     reserved0          Reserved
    0x010   4B     loader_load_addr   Load address in DRAM
    0x014   4B     loader_load_size   Data size (4-byte aligned)
    0x018   4B     crc32              CRC32 checksum
    0x01C   4B     hash_len           Hash length (32 for SHA256)
    0x020   32B    hash               SHA256 hash
    0x040   960B   reserved           Padding to 1024 bytes
    0x400   4B     sign_tag           "SIGN" (0x4E474953)
    0x404   4B     sign_len           RSA signature length
    0x408   256B   rsa_hash           RSA signature
    0x508   760B   reserved2          Padding to 2048 bytes

Usage:
    # Pack U-Boot
    pack_uboot("u-boot.bin", "uboot.img", load_addr=0x200000)

    # Pack Trust
    pack_trust("trust.bin", "trust.img", load_addr=0x8400000)

    # Unpack
    unpack_loader_image("uboot.img", "u-boot.bin")

    # Get info
    info = get_loader_info("uboot.img")
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from rkpyimg.core.checksum import crc32_rk


# Constants
HEADER_SIZE = 2048  # Total header size in bytes
LOADER_MAGIC_SIZE = 8
LOADER_HASH_SIZE = 32

# Magic strings (8 bytes, padded with spaces)
RK_UBOOT_MAGIC = b"LOADER  "
RK_TRUST_MAGIC = b"TOS     "

# Default configurations
UBOOT_NUM = 4  # Number of backup copies
UBOOT_MAX_SIZE = 1024 * 1024  # 1MB per copy

TRUST_NUM = 4
TRUST_MAX_SIZE = 1024 * 1024


class ImageType(Enum):
    """Image type enumeration."""
    UBOOT = "uboot"
    TRUST = "trust"


@dataclass
class SecondLoaderHeader:
    """
    Rockchip Second Stage Loader header structure.

    This header is prepended to u-boot.bin or trust.bin to create
    images that the Rockchip BootROM can load and verify.

    Attributes:
        magic: Image type identifier ("LOADER  " or "TOS     ")
        version: Rollback protection version number
        loader_load_addr: Physical address where BootROM loads the image
        loader_load_size: Size of the payload data (4-byte aligned)
        crc32: CRC32 checksum of the payload
        hash_len: Length of SHA hash (32 for SHA256)
        hash: SHA256 hash for secure boot verification
        sign_tag: Signature marker (0x4E474953 = "SIGN")
        sign_len: RSA signature length
        rsa_hash: RSA signature data
    """
    magic: bytes = RK_UBOOT_MAGIC
    version: int = 0
    reserved0: int = 0
    loader_load_addr: int = 0x200000
    loader_load_size: int = 0
    crc32: int = 0
    hash_len: int = 32  # SHA256
    hash: bytes = field(default_factory=lambda: bytes(LOADER_HASH_SIZE))
    reserved1: bytes = field(default_factory=lambda: bytes(1024 - 32 - 32))
    sign_tag: int = 0
    sign_len: int = 0
    rsa_hash: bytes = field(default_factory=lambda: bytes(256))
    reserved2: bytes = field(default_factory=lambda: bytes(2048 - 1024 - 256 - 8))

    # Struct format for packing/unpacking
    # Base info (32 bytes): magic(8) + version(4) + reserved(4) + addr(4) + size(4) + crc(4) + hash_len(4)
    _BASE_FORMAT = "<8sIIIIII"
    _BASE_SIZE = 32

    def to_bytes(self) -> bytes:
        """
        Serialize header to binary format (2048 bytes).

        Returns:
            Binary representation of the header
        """
        # Pack base fields
        base = struct.pack(
            self._BASE_FORMAT,
            self.magic,
            self.version,
            self.reserved0,
            self.loader_load_addr,
            self.loader_load_size,
            self.crc32,
            self.hash_len,
        )

        # Hash (32 bytes)
        hash_data = self.hash[:LOADER_HASH_SIZE].ljust(LOADER_HASH_SIZE, b'\x00')

        # Reserved1 (960 bytes to reach 1024)
        reserved1 = bytes(1024 - 32 - 32)

        # Sign section (264 bytes)
        sign_section = struct.pack("<II", self.sign_tag, self.sign_len)
        rsa_data = self.rsa_hash[:256].ljust(256, b'\x00')

        # Reserved2 (760 bytes to reach 2048)
        reserved2 = bytes(2048 - 1024 - 256 - 8)

        result = base + hash_data + reserved1 + sign_section + rsa_data + reserved2
        assert len(result) == HEADER_SIZE, f"Header size mismatch: {len(result)} != {HEADER_SIZE}"
        return result

    @classmethod
    def from_bytes(cls, data: bytes) -> SecondLoaderHeader:
        """
        Parse header from binary data.

        Args:
            data: Binary data (at least 2048 bytes)

        Returns:
            Parsed SecondLoaderHeader instance

        Raises:
            ValueError: If data is too short or magic is invalid
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Data too short: {len(data)} < {HEADER_SIZE}")

        # Unpack base fields
        magic, version, reserved0, load_addr, load_size, crc32, hash_len = struct.unpack(
            cls._BASE_FORMAT, data[:cls._BASE_SIZE]
        )

        # Extract hash
        hash_data = data[32:64]

        # Extract sign section
        sign_tag, sign_len = struct.unpack("<II", data[1024:1032])
        rsa_hash = data[1032:1288]

        return cls(
            magic=magic,
            version=version,
            reserved0=reserved0,
            loader_load_addr=load_addr,
            loader_load_size=load_size,
            crc32=crc32,
            hash_len=hash_len,
            hash=hash_data,
            sign_tag=sign_tag,
            sign_len=sign_len,
            rsa_hash=rsa_hash,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> SecondLoaderHeader:
        """
        Parse header from a file.

        Args:
            path: Path to the image file

        Returns:
            Parsed SecondLoaderHeader instance
        """
        with open(path, "rb") as f:
            data = f.read(HEADER_SIZE)
        return cls.from_bytes(data)

    def is_uboot(self) -> bool:
        """Check if this is a U-Boot image."""
        return self.magic.startswith(b"LOADER")

    def is_trust(self) -> bool:
        """Check if this is a Trust image."""
        return self.magic.startswith(b"TOS")

    def __str__(self) -> str:
        """Human-readable representation."""
        img_type = "UBOOT" if self.is_uboot() else "TRUST" if self.is_trust() else "UNKNOWN"
        return (
            f"SecondLoaderHeader(\n"
            f"  type={img_type},\n"
            f"  version={self.version},\n"
            f"  load_addr=0x{self.loader_load_addr:08X},\n"
            f"  load_size={self.loader_load_size} ({self.loader_load_size // 1024} KB),\n"
            f"  crc32=0x{self.crc32:08X},\n"
            f"  hash_len={self.hash_len}\n"
            f")"
        )


def _calculate_sha256(
    data: bytes,
    version: int,
    load_addr: int,
    load_size: int,
    hash_len: int,
) -> bytes:
    """
    Calculate SHA256 hash for secure boot verification.

    The hash is calculated over:
    1. Image data
    2. Version number (8 bytes, if version > 0)
    3. Load address (4 bytes)
    4. Load size (4 bytes)
    5. Hash length (4 bytes)

    Args:
        data: Image binary data
        version: Version number
        load_addr: Load address
        load_size: Data size
        hash_len: Hash length

    Returns:
        32-byte SHA256 hash
    """
    ctx = hashlib.sha256()

    # 1. Image data
    ctx.update(data)

    # 2. Version (8 bytes, only if > 0)
    if version > 0:
        ctx.update(struct.pack("<Q", version))

    # 3. Load address (4 bytes)
    ctx.update(struct.pack("<I", load_addr))

    # 4. Load size (4 bytes)
    ctx.update(struct.pack("<I", load_size))

    # 5. Hash length (4 bytes)
    ctx.update(struct.pack("<I", hash_len))

    return ctx.digest()


def _align_size(size: int, alignment: int = 4) -> int:
    """Align size to specified boundary."""
    return (size + alignment - 1) & ~(alignment - 1)


def pack_loader_image(
    input_file: str | Path,
    output_file: str | Path,
    load_addr: int,
    image_type: Literal["uboot", "trust"] = "uboot",
    version: int = 0,
    max_size: int | None = None,
    num_copies: int | None = None,
) -> Path:
    """
    Pack a binary file with Rockchip header.

    This function wraps a raw binary (like u-boot.bin) with the
    Rockchip header format required by the BootROM.

    Args:
        input_file: Path to input binary file
        output_file: Path to output image file
        load_addr: Load address for the binary
        image_type: Type of image ("uboot" or "trust")
        version: Rollback protection version (default: 0)
        max_size: Maximum size per copy in bytes (default: 1MB)
        num_copies: Number of backup copies (default: 4)

    Returns:
        Path to the created output file

    Raises:
        ValueError: If input file is too large
        FileNotFoundError: If input file doesn't exist

    Example:
        >>> pack_loader_image("u-boot.bin", "uboot.img", 0x200000)
        PosixPath('uboot.img')
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    # Configure based on image type
    if image_type == "uboot":
        magic = RK_UBOOT_MAGIC
        default_max_size = UBOOT_MAX_SIZE
        default_num = UBOOT_NUM
    else:  # trust
        magic = RK_TRUST_MAGIC
        default_max_size = TRUST_MAX_SIZE
        default_num = TRUST_NUM

    max_size = max_size or default_max_size
    num_copies = num_copies or default_num

    # Read input binary
    with open(input_path, "rb") as f:
        data = f.read()

    # Check size limit (must leave room for header)
    if len(data) > max_size - HEADER_SIZE:
        raise ValueError(
            f"Input file too large: {len(data)} bytes > {max_size - HEADER_SIZE} bytes limit"
        )

    print(f"pack input {input_path}")
    print(f"pack file size: {len(data)} ({len(data) // 1024} KB)")
    print(f"load addr is 0x{load_addr:x}!")

    # Align size to 4 bytes
    aligned_size = _align_size(len(data), 4)

    # Pad data to aligned size
    padded_data = data.ljust(aligned_size, b'\x00')

    # Calculate CRC32
    crc = crc32_rk(padded_data)
    print(f"crc = 0x{crc:08x}")

    # Calculate SHA256
    hash_len = 32
    sha_hash = _calculate_sha256(padded_data, version, load_addr, aligned_size, hash_len)

    # Build header
    header = SecondLoaderHeader(
        magic=magic,
        version=version,
        loader_load_addr=load_addr,
        loader_load_size=aligned_size,
        crc32=crc,
        hash_len=hash_len,
        hash=sha_hash,
    )

    # Build complete image block (header + data, padded to max_size)
    header_bytes = header.to_bytes()
    image_block = header_bytes + padded_data
    image_block = image_block.ljust(max_size, b'\x00')

    # Write multiple copies
    with open(output_path, "wb") as f:
        for _ in range(num_copies):
            f.write(image_block)

    print(f"pack {output_path} success!")
    return output_path


def pack_uboot(
    input_file: str | Path,
    output_file: str | Path,
    load_addr: int = 0x200000,
    version: int = 0,
    max_size: int | None = None,
    num_copies: int | None = None,
) -> Path:
    """
    Pack U-Boot binary into Rockchip format.

    Convenience wrapper for pack_loader_image with uboot defaults.

    Args:
        input_file: Path to u-boot.bin
        output_file: Path to output uboot.img
        load_addr: Load address (default: 0x200000)
        version: Rollback protection version
        max_size: Maximum size per copy
        num_copies: Number of backup copies

    Returns:
        Path to created uboot.img
    """
    return pack_loader_image(
        input_file,
        output_file,
        load_addr,
        image_type="uboot",
        version=version,
        max_size=max_size,
        num_copies=num_copies,
    )


def pack_trust(
    input_file: str | Path,
    output_file: str | Path,
    load_addr: int = 0x8400000,
    version: int = 0,
    max_size: int | None = None,
    num_copies: int | None = None,
) -> Path:
    """
    Pack Trust binary into Rockchip format.

    Convenience wrapper for pack_loader_image with trust defaults.

    Args:
        input_file: Path to trust.bin
        output_file: Path to output trust.img
        load_addr: Load address (default: 0x8400000)
        version: Rollback protection version
        max_size: Maximum size per copy
        num_copies: Number of backup copies

    Returns:
        Path to created trust.img
    """
    return pack_loader_image(
        input_file,
        output_file,
        load_addr,
        image_type="trust",
        version=version,
        max_size=max_size,
        num_copies=num_copies,
    )


def unpack_loader_image(
    input_file: str | Path,
    output_file: str | Path,
) -> tuple[SecondLoaderHeader, Path]:
    """
    Extract binary from a Rockchip loader image.

    Args:
        input_file: Path to Rockchip image file (uboot.img or trust.img)
        output_file: Path to output raw binary

    Returns:
        Tuple of (header, output_path)

    Raises:
        ValueError: If input file has invalid header
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    print(f"unpack input {input_path}")

    # Read and parse header
    with open(input_path, "rb") as f:
        header_data = f.read(HEADER_SIZE)
        header = SecondLoaderHeader.from_bytes(header_data)

        # Read payload data
        payload = f.read(header.loader_load_size)

    # Verify CRC
    calculated_crc = crc32_rk(payload)
    if calculated_crc != header.crc32:
        print(f"Warning: CRC mismatch! Expected 0x{header.crc32:08x}, got 0x{calculated_crc:08x}")

    # Write extracted data
    with open(output_path, "wb") as f:
        f.write(payload)

    print(f"unpack {output_path} success!")
    return header, output_path


def get_loader_info(input_file: str | Path) -> SecondLoaderHeader:
    """
    Get information from a Rockchip loader image.

    Args:
        input_file: Path to image file

    Returns:
        Parsed header with image information

    Raises:
        ValueError: If file has invalid header
    """
    header = SecondLoaderHeader.from_file(input_file)

    # Validate magic
    if not (header.is_uboot() or header.is_trust()):
        raise ValueError(f"Invalid magic: {header.magic!r}")

    print("The image info:")
    print(f"Rollback index is {header.version}")
    print(f"Load Addr is 0x{header.loader_load_addr:x}")

    return header


# CLI interface
def main() -> None:
    """Command line interface for loaderimage."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Rockchip loader image pack/unpack tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pack U-Boot
  %(prog)s --pack --uboot u-boot.bin uboot.img 0x200000

  # Pack U-Boot with custom size (KB) and copies
  %(prog)s --pack --uboot u-boot.bin uboot.img 0x200000 --size 1024 1

  # Pack Trust
  %(prog)s --pack --trustos trust.bin trust.img

  # Unpack
  %(prog)s --unpack --uboot uboot.img u-boot.bin

  # Show info
  %(prog)s --info uboot.img
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--pack", action="store_true", help="Pack mode")
    mode_group.add_argument("--unpack", action="store_true", help="Unpack mode")
    mode_group.add_argument("--info", action="store_true", help="Info mode")

    # Image type
    type_group = parser.add_mutually_exclusive_group()
    type_group.add_argument("--uboot", action="store_true", help="U-Boot image")
    type_group.add_argument("--trustos", action="store_true", help="Trust OS image")

    # Files and options
    parser.add_argument("input", nargs="?", help="Input file")
    parser.add_argument("output", nargs="?", help="Output file")
    parser.add_argument("load_addr", nargs="?", help="Load address (hex)")
    parser.add_argument("--size", nargs=2, type=int, metavar=("KB", "NUM"),
                        help="Size in KB and number of copies")
    parser.add_argument("--version", type=int, default=0,
                        help="Version number for rollback protection")

    args = parser.parse_args()

    if args.info:
        if not args.input:
            parser.error("--info requires input file")
        get_loader_info(args.input)

    elif args.pack:
        if not args.input or not args.output:
            parser.error("--pack requires input and output files")

        image_type = "trust" if args.trustos else "uboot"

        # Parse load address
        if args.load_addr:
            load_addr = int(args.load_addr, 16) if args.load_addr.startswith("0x") else int(args.load_addr)
        else:
            load_addr = 0x8400000 if args.trustos else 0x200000

        # Parse size options
        max_size = args.size[0] * 1024 if args.size else None
        num_copies = args.size[1] if args.size else None

        pack_loader_image(
            args.input,
            args.output,
            load_addr,
            image_type=image_type,
            version=args.version,
            max_size=max_size,
            num_copies=num_copies,
        )

    elif args.unpack:
        if not args.input or not args.output:
            parser.error("--unpack requires input and output files")
        unpack_loader_image(args.input, args.output)


if __name__ == "__main__":
    main()
