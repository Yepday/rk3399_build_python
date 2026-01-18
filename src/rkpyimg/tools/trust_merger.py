"""
trust_merger - Merge BL31 and BL32 into trust.img.

This module implements the functionality of Rockchip's trust_merger tool,
which combines ARM Trusted Firmware (BL31) and OP-TEE (BL32) into trust.img.

Original C implementation: trust_merger.c

Trust Image Structure:
    +-------------------+  0x0000
    | TRUST_HEADER      |  2048 bytes
    +-------------------+  0x0800
    | COMPONENT_DATA[0] |  48 bytes (load addr + SHA256 hash)
    | COMPONENT_DATA[1] |  48 bytes
    | ...               |
    +-------------------+  SignOffset
    | SIGNATURE         |  256 bytes (RSA signature, optional)
    +-------------------+  SignOffset + 256
    | TRUST_COMPONENT[0]|  16 bytes (storage info)
    | TRUST_COMPONENT[1]|  16 bytes
    | ...               |
    +-------------------+  2048
    | BL3x Component[0] |  Aligned to 2048 bytes
    | BL3x Component[1] |  Aligned to 2048 bytes
    | ...               |
    +-------------------+

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

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Literal

from rkpyimg.core.ini_parser import RKTrustConfig, BinaryEntry
from rkpyimg.core.checksum import crc32_rk, sha256_hash


class RSAMode(IntEnum):
    """RSA signing modes for trust image."""

    NONE = 0
    PKCS1_V15 = 1
    PKCS1_V15_RSA2048 = 2  # Default for RK3399 and most chips
    PKCS1_V21 = 3  # Used by RK3308/PX30
    PKCS1_V21_NEW = 4  # Alternative mode


class SHAMode(IntEnum):
    """SHA hash modes for trust image."""

    NONE = 0
    SHA1 = 1
    SHA256_RK = 2  # RK3368 only (big-endian)
    SHA256 = 3  # Little-endian (default)


# Constants from trust_merger.h
TRUST_HEADER_SIZE = 2048  # Padded size for alignment
TRUST_HEADER_STRUCT_SIZE = 800  # Actual struct size (tag+version+flags+size+reserved+RSA arrays)
SIGNATURE_SIZE = 256
ENTRY_ALIGN = 2048
ELF_MAGIC = 0x464C457F  # b'\x7fELF'
PT_LOAD = 1  # Loadable segment type


def align_size(size: int, alignment: int = ENTRY_ALIGN) -> int:
    """Align size to specified alignment."""
    if size > 0:
        return ((size - 1) // alignment + 1) * alignment
    return size


def get_bcd(value: int) -> int:
    """
    Convert decimal value to BCD (Binary-Coded Decimal) format.

    Args:
        value: Decimal value (0-99)

    Returns:
        BCD encoded value

    Example:
        >>> get_bcd(58)
        88  # 0x58
    """
    if value > 99:
        value = value % 100
    return ((value // 10) << 4) | (value % 10)


@dataclass
class ELFSegment:
    """ELF PT_LOAD segment information."""

    offset: int  # File offset
    vaddr: int  # Virtual address
    filesz: int  # Size in file
    memsz: int  # Size in memory


@dataclass
class BLComponent:
    """
    BL3x component information.

    Represents a single BL30/BL31/BL32/BL33 component that will be
    included in the trust image.
    """

    component_id: bytes  # 4-byte ID: b'BL30', b'BL31', b'BL32', b'BL33'
    path: Path
    load_addr: int
    offset: int = 0  # Offset within file (for ELF segments)
    size: int = 0  # Actual data size
    align_size: int = 0  # Aligned size

    @classmethod
    def from_binary_entry(
        cls,
        entry: BinaryEntry,
        component_id: bytes,
    ) -> BLComponent:
        """Create BLComponent from BinaryEntry."""
        size = entry.path.stat().st_size if entry.path.exists() else 0
        return cls(
            component_id=component_id,
            path=entry.path,
            load_addr=entry.address,
            offset=0,
            size=size,
            align_size=align_size(size),
        )

    @classmethod
    def from_elf(
        cls,
        entry: BinaryEntry,
        component_id: bytes,
        segment: ELFSegment,
    ) -> BLComponent:
        """Create BLComponent from ELF segment."""
        return cls(
            component_id=component_id,
            path=entry.path,
            load_addr=segment.vaddr,
            offset=segment.offset,
            size=segment.filesz,
            align_size=align_size(segment.filesz),
        )


def parse_elf_segments(file_path: Path) -> list[ELFSegment]:
    """
    Parse ELF file and extract PT_LOAD segments.

    Args:
        file_path: Path to ELF file

    Returns:
        List of PT_LOAD segments

    Raises:
        ValueError: If file is not a valid ELF file
    """
    segments: list[ELFSegment] = []

    with open(file_path, "rb") as f:
        # Read ELF header
        magic = struct.unpack("<I", f.read(4))[0]
        if magic != ELF_MAGIC:
            raise ValueError(f"Not an ELF file: {file_path}")

        # Read ELF class (32/64-bit)
        elf_class = struct.unpack("B", f.read(1))[0]
        f.seek(5)
        endian = struct.unpack("B", f.read(1))[0]

        if endian != 1:  # Only support little-endian
            raise ValueError("Only little-endian ELF files are supported")

        # Seek to e_type
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
        if e_type != 2:  # Only support executable
            raise ValueError("Only executable ELF files are supported")

        if elf_class == 2:  # 64-bit ELF
            # Seek to program header offset
            f.seek(32)
            e_phoff = struct.unpack("<Q", f.read(8))[0]
            f.seek(54)
            e_phentsize = struct.unpack("<H", f.read(2))[0]
            e_phnum = struct.unpack("<H", f.read(2))[0]

            # Read program headers
            for i in range(e_phnum):
                f.seek(e_phoff + i * e_phentsize)
                p_type = struct.unpack("<I", f.read(4))[0]
                p_flags = struct.unpack("<I", f.read(4))[0]
                p_offset = struct.unpack("<Q", f.read(8))[0]
                p_vaddr = struct.unpack("<Q", f.read(8))[0]
                p_paddr = struct.unpack("<Q", f.read(8))[0]
                p_filesz = struct.unpack("<Q", f.read(8))[0]
                p_memsz = struct.unpack("<Q", f.read(8))[0]

                if p_type == PT_LOAD:
                    segments.append(ELFSegment(
                        offset=p_offset,
                        vaddr=p_vaddr,
                        filesz=p_filesz,
                        memsz=p_memsz,
                    ))
        else:  # 32-bit ELF
            # Seek to program header offset
            f.seek(28)
            e_phoff = struct.unpack("<I", f.read(4))[0]
            f.seek(42)
            e_phentsize = struct.unpack("<H", f.read(2))[0]
            e_phnum = struct.unpack("<H", f.read(2))[0]

            # Read program headers
            for i in range(e_phnum):
                f.seek(e_phoff + i * e_phentsize)
                p_type = struct.unpack("<I", f.read(4))[0]
                p_offset = struct.unpack("<I", f.read(4))[0]
                p_vaddr = struct.unpack("<I", f.read(4))[0]
                p_paddr = struct.unpack("<I", f.read(4))[0]
                p_filesz = struct.unpack("<I", f.read(4))[0]
                p_memsz = struct.unpack("<I", f.read(4))[0]

                if p_type == PT_LOAD:
                    segments.append(ELFSegment(
                        offset=p_offset,
                        vaddr=p_vaddr,
                        filesz=p_filesz,
                        memsz=p_memsz,
                    ))

    return segments


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
    rsa_mode: RSAMode = RSAMode.PKCS1_V15_RSA2048  # Default: RSA-2048 (mode=2)
    sha_mode: SHAMode = SHAMode.SHA256  # Default: SHA256 little-endian (mode=3)
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

    def _prepare_components(self) -> list[BLComponent]:
        """
        Prepare all BL components from config.

        Handles ELF files by extracting PT_LOAD segments.

        Returns:
            List of BLComponent instances
        """
        components: list[BLComponent] = []

        # Process BL31 (required)
        if self.config.bl31 and self.config.bl31.path.exists():
            try:
                # Try to parse as ELF
                segments = parse_elf_segments(self.config.bl31.path)
                # Add all PT_LOAD segments as separate BL31 components
                # This matches the original C implementation behavior
                if segments:
                    for segment in segments:
                        comp = BLComponent.from_elf(
                            self.config.bl31,
                            b'BL31',
                            segment,
                        )
                        components.append(comp)
            except ValueError:
                # Not an ELF file, treat as binary
                comp = BLComponent.from_binary_entry(
                    self.config.bl31,
                    b'BL31',
                )
                components.append(comp)

        # Process BL32 (optional)
        if self.config.bl32 and self.config.bl32.path.exists():
            try:
                segments = parse_elf_segments(self.config.bl32.path)
                # Add all PT_LOAD segments as separate BL32 components
                if segments:
                    for segment in segments:
                        comp = BLComponent.from_elf(
                            self.config.bl32,
                            b'BL32',
                            segment,
                        )
                        components.append(comp)
            except ValueError:
                comp = BLComponent.from_binary_entry(
                    self.config.bl32,
                    b'BL32',
                )
                components.append(comp)

        return components

    def pack(self, output: str | Path) -> Path:
        """
        Pack the trust image.

        Creates trust.img containing:
        1. Trust header with version and security settings
        2. Component data (load addresses and SHA256 hashes)
        3. Trust components (storage metadata)
        4. Binary data for all components

        Args:
            output: Output file path

        Returns:
            Path to created file

        Raises:
            FileNotFoundError: If required binary files don't exist
            ValueError: If configuration is invalid
        """
        output_path = Path(output)

        # Validate binaries exist
        if not self.validate_binaries():
            raise FileNotFoundError("Required binaries not found")

        # Prepare components
        components = self._prepare_components()
        if not components:
            raise ValueError("No components to pack")

        num_components = len(components)

        # Calculate offsets
        # TRUST_HEADER struct: 800 bytes (but padded to 2048 for binary data)
        # Component data: 48 bytes per component (after header struct at offset 800)
        # Signature: 256 bytes (after component data)
        # Trust components: 16 bytes per component (after signature)
        # Binary data: starts at 2048 (TRUST_HEADER_SIZE)
        sign_offset = TRUST_HEADER_STRUCT_SIZE + num_components * 48
        component_info_offset = sign_offset + SIGNATURE_SIZE

        # Build header (2048 bytes)
        header_buf = bytearray(TRUST_HEADER_SIZE)

        # Trust header structure
        # tag: 4B, version: 4B, flags: 4B, size: 4B, reserved: 16B
        # RSA_N: 256B, RSA_E: 256B, RSA_C: 256B
        struct.pack_into("<4s", header_buf, 0, b'BL3X')  # Tag

        # Version in BCD format
        major_bcd = get_bcd(self.config.version[0])
        minor_bcd = get_bcd(self.config.version[1])
        version_val = (major_bcd << 8) | minor_bcd
        struct.pack_into("<I", header_buf, 4, version_val)

        # Flags: SHA mode (bits 0-3), RSA mode (bits 4-7)
        flags = (self.sha_mode & 0xF) | ((self.rsa_mode & 0xF) << 4)
        struct.pack_into("<I", header_buf, 8, flags)

        # Size: high 16 bits = num_components, low 16 bits = sign_offset >> 2
        size_val = (num_components << 16) | (sign_offset >> 2)
        struct.pack_into("<I", header_buf, 12, size_val)

        # Reserved: 16 bytes (already zero)
        # RSA_N, RSA_E, RSA_C: 768 bytes total (not implemented, leave as zero)

        # Allocate output buffer
        # Calculate total size
        # Header + ComponentData + Signature + TrustComponent + Binary data
        out_file_size = component_info_offset + num_components * 16
        for comp in components:
            out_file_size += comp.align_size

        out_buf = bytearray(out_file_size)

        # Copy header
        out_buf[0:TRUST_HEADER_SIZE] = header_buf

        # Write component data and binary data
        # Binary data starts at TRUST_HEADER_SIZE (2048), matching C implementation
        data_offset = TRUST_HEADER_SIZE
        comp_data_offset = TRUST_HEADER_STRUCT_SIZE  # COMPONENT_DATA starts at offset 800

        for idx, comp in enumerate(components):
            # Read component binary data
            with open(comp.path, "rb") as f:
                f.seek(comp.offset)
                comp_data = f.read(comp.size)

            # Pad to aligned size
            if len(comp_data) < comp.align_size:
                comp_data += b'\x00' * (comp.align_size - len(comp_data))

            # Calculate SHA256 hash
            hash_data = sha256_hash(comp_data)

            # Write component data (48 bytes)
            # HashData[8]: 32 bytes, LoadAddr: 4 bytes, reserved[3]: 12 bytes
            struct.pack_into("<32s", out_buf, comp_data_offset, hash_data)
            struct.pack_into("<I", out_buf, comp_data_offset + 32, comp.load_addr)
            # Reserved 12 bytes (already zero)
            comp_data_offset += 48

            # Write trust component info (16 bytes) at component_info_offset
            # ComponentID: 4B, StorageAddr: 4B, ImageSize: 4B, reserved: 4B
            comp_info_pos = component_info_offset + idx * 16
            struct.pack_into("<4s", out_buf, comp_info_pos, comp.component_id)
            struct.pack_into("<I", out_buf, comp_info_pos + 4, data_offset >> 9)  # In 512-byte units
            struct.pack_into("<I", out_buf, comp_info_pos + 8, comp.align_size >> 9)  # In 512-byte units
            # Reserved 4 bytes (already zero)

            # Write component binary data
            out_buf[data_offset:data_offset + len(comp_data)] = comp_data
            data_offset += comp.align_size

        # Write to file with backup copies
        # Original C code: g_trust_max_num = 2, g_trust_max_size = 2MB
        # Creates 4MB file with 2 copies of the trust image
        TRUST_MAX_SIZE = 2 * 1024 * 1024  # 2MB per copy
        TRUST_MAX_NUM = 2  # Number of copies

        # Check if image fits in max size
        if len(out_buf) > TRUST_MAX_SIZE:
            raise ValueError(f"Trust image size ({len(out_buf)}) exceeds max size ({TRUST_MAX_SIZE})")

        # Create buffer for all copies
        total_buf = bytearray(TRUST_MAX_SIZE * TRUST_MAX_NUM)

        # Copy trust image to each backup location
        for i in range(TRUST_MAX_NUM):
            offset = i * TRUST_MAX_SIZE
            total_buf[offset:offset + len(out_buf)] = out_buf

        # Write to file
        with open(output_path, "wb") as f:
            f.write(total_buf)

        return output_path

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

    @staticmethod
    def unpack(trust_img: str | Path, output_dir: str | Path | None = None) -> dict[str, Path]:
        """
        Unpack trust.img and extract components.

        Args:
            trust_img: Path to trust.img file
            output_dir: Output directory (defaults to current directory)

        Returns:
            Dictionary mapping component IDs to extracted file paths

        Example:
            >>> files = TrustMerger.unpack("trust.img", "output")
            >>> print(files)
            {'BL31': Path('output/BL31'), 'BL32': Path('output/BL32')}
        """
        trust_path = Path(trust_img)
        out_dir = Path(output_dir) if output_dir else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)

        extracted: dict[str, Path] = {}

        with open(trust_path, "rb") as f:
            # Read header
            header_data = f.read(TRUST_HEADER_SIZE)

            # Parse header
            tag = struct.unpack_from("<4s", header_data, 0)[0]
            if tag != b'BL3X':
                raise ValueError(f"Invalid trust image magic: {tag}")

            version = struct.unpack_from("<I", header_data, 4)[0]
            flags = struct.unpack_from("<I", header_data, 8)[0]
            size_field = struct.unpack_from("<I", header_data, 12)[0]

            # Extract fields
            num_components = (size_field >> 16) & 0xFFFF
            sign_offset = (size_field & 0xFFFF) << 2

            print(f"Trust Image Header:")
            print(f"  Tag: {tag.decode('ascii')}")
            print(f"  Version: {version:04X}")
            print(f"  Flags: SHA={flags & 0xF}, RSA={(flags >> 4) & 0xF}")
            print(f"  Components: {num_components}")
            print(f"  Sign Offset: {sign_offset}")

            # Component info is at sign_offset + SIGNATURE_SIZE
            component_info_offset = sign_offset + SIGNATURE_SIZE

            # Parse components
            for i in range(num_components):
                # Read component data (load address and hash)
                comp_data_offset = TRUST_HEADER_STRUCT_SIZE + i * 48  # After header struct at 800
                load_addr = struct.unpack_from("<I", header_data, comp_data_offset + 32)[0]

                # Read component info
                comp_info_offset = component_info_offset + i * 16
                f.seek(comp_info_offset)
                comp_info = f.read(16)

                component_id = struct.unpack_from("<4s", comp_info, 0)[0]
                storage_addr = struct.unpack_from("<I", comp_info, 4)[0]
                image_size = struct.unpack_from("<I", comp_info, 8)[0]

                # Convert to bytes
                storage_offset = storage_addr << 9
                size_bytes = image_size << 9

                print(f"\nComponent {i}: {component_id.decode('ascii')}")
                print(f"  Load Address: 0x{load_addr:08X}")
                print(f"  Storage Offset: 0x{storage_offset:X}")
                print(f"  Size: {size_bytes} bytes")

                # Extract component data
                f.seek(storage_offset)
                comp_data = f.read(size_bytes)

                # Save to file
                comp_name = component_id.decode('ascii').strip()
                out_file = out_dir / comp_name
                with open(out_file, "wb") as out_f:
                    out_f.write(comp_data)

                extracted[comp_name] = out_file
                print(f"  Extracted to: {out_file}")

        return extracted


# Command-line interface
def main() -> None:
    """Command-line interface for trust_merger."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Merge BL31/BL32 into trust.img (Rockchip trust_merger Python implementation)"
    )
    parser.add_argument(
        "config",
        nargs="?",
        help="RKTRUST INI configuration file (for pack mode)",
    )
    parser.add_argument(
        "--pack",
        action="store_true",
        help="Pack trust image (default)",
    )
    parser.add_argument(
        "--unpack",
        metavar="TRUST_IMG",
        help="Unpack trust image",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="PATH",
        help="Output file path (pack) or directory (unpack)",
    )
    parser.add_argument(
        "--rsa",
        type=int,
        default=2,
        choices=[0, 1, 2, 3, 4],
        help="RSA mode: 0=none, 1=1024, 2=2048 (default), 3=2048 PSS, 4=2048 new",
    )
    parser.add_argument(
        "--sha",
        type=int,
        default=3,
        choices=[0, 1, 2, 3],
        help="SHA mode: 0=none, 1=SHA1, 2=SHA256 RK, 3=SHA256 (default)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=1024,
        help="Trust image size in KB (default: 1024)",
    )

    args = parser.parse_args()

    if args.unpack:
        # Unpack mode
        output_dir = args.output or "."
        files = TrustMerger.unpack(args.unpack, output_dir)
        print(f"\nSuccessfully unpacked {len(files)} components")
    else:
        # Pack mode
        if not args.config:
            parser.error("config file required for pack mode")

        merger = TrustMerger.from_ini(args.config)
        merger.set_rsa_mode(args.rsa)
        merger.set_sha_mode(args.sha)
        merger.size = args.size

        output = args.output or merger.config.output_path
        result = merger.pack(output)
        print(f"Successfully created trust image: {result}")


if __name__ == "__main__":
    main()
