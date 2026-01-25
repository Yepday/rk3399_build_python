"""
boot_merger - Merge DDR init and miniloader binaries.

This module implements the functionality of Rockchip's boot_merger tool,
which combines DDR initialization code and miniloader into idbloader.img
or loader.bin.

Original C implementation: boot_merger.c

Rockchip Boot Image Layout:
    ┌──────────────────────────────┐
    │ rk_boot_header (102 bytes)   │  Header with magic, version, chip type
    ├──────────────────────────────┤
    │ CODE471 Entry array          │  DDR init code metadata
    ├──────────────────────────────┤
    │ CODE472 Entry array          │  USB plug code metadata (optional)
    ├──────────────────────────────┤
    │ Loader Entry array           │  FlashData/FlashBoot metadata
    ├──────────────────────────────┤
    │ CODE471 Data (aligned)       │  DDR init code (RC4 encrypted if enabled)
    ├──────────────────────────────┤
    │ CODE472 Data (aligned)       │  USB plug code (RC4 encrypted if enabled)
    ├──────────────────────────────┤
    │ Loader Data (aligned)        │  FlashData/FlashBoot (block RC4 encrypted)
    ├──────────────────────────────┤
    │ CRC32 (4 bytes)              │  Checksum of entire image
    └──────────────────────────────┘

Usage:
    # From INI file
    merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
    merger.pack("idbloader.img")

    # Unpack existing image
    merger.unpack("idbloader.img", "output_dir/")
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from rkpyimg.core.checksum import crc32_rk
from rkpyimg.core.ini_parser import BinaryEntry, RKBootConfig
from rkpyimg.core.rc4 import rc4_decrypt, rc4_decrypt_blocks, rc4_encrypt, rc4_encrypt_blocks


# Constants
TAG_BOOT = 0x544F4F42  # "BOOT" magic number
MERGER_VERSION = 0x01030000
SMALL_PACKET = 512  # 512-byte blocks for RC4 encryption
ENTRY_ALIGN = 2048  # Data alignment (2KB)
MAX_NAME_LEN = 20
BOOT_RESERVED_SIZE = 57


class RKChipType(IntEnum):
    """Rockchip chip type enumeration."""
    RKNONE = 0
    RK27 = 0x10
    RKCAYMAN = 0x11
    RK28 = 0x20
    RK281X = 0x21
    RKPANDA = 0x22
    RKNANO = 0x30
    RKSMART = 0x31
    RKCROWN = 0x40
    RK29 = 0x50
    RK292X = 0x51
    RK30 = 0x60
    RK30B = 0x61
    RK31 = 0x70
    RK32 = 0x80


class RKEntryType(IntEnum):
    """Entry type enumeration."""
    ENTRY_471 = 1  # DDR init code
    ENTRY_472 = 2  # USB plug code
    ENTRY_LOADER = 4  # FlashData/FlashBoot


# Chip name mapping (for older chips)
CHIP_NAME_MAP = {
    "RK28": RKChipType.RK28,
    "RK281X": RKChipType.RK281X,
    "RKPANDA": RKChipType.RKPANDA,
    "RK27": RKChipType.RK27,
    "RKNANO": RKChipType.RKNANO,
    "RKSMART": RKChipType.RKSMART,
    "RKCROWN": RKChipType.RKCROWN,
    "RKCAYMAN": RKChipType.RKCAYMAN,
    "RK29": RKChipType.RK29,
    "RK292X": RKChipType.RK292X,
    "RK30": RKChipType.RK30,
    "RK30B": RKChipType.RK30B,
    "RK31": RKChipType.RK31,
    "RK32": RKChipType.RK32,
}


@dataclass
class RKTime:
    """
    Rockchip timestamp structure.

    Attributes:
        year: Year (e.g., 2025)
        month: Month (1-12)
        day: Day (1-31)
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
    """
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int

    def to_bytes(self) -> bytes:
        """Serialize to binary format (7 bytes)."""
        return struct.pack("<HBBBBB",
                           self.year, self.month, self.day,
                           self.hour, self.minute, self.second)

    @classmethod
    def from_bytes(cls, data: bytes) -> RKTime:
        """Parse from binary data."""
        year, month, day, hour, minute, second = struct.unpack("<HBBBBB", data[:7])
        return cls(year, month, day, hour, minute, second)

    @classmethod
    def now(cls) -> RKTime:
        """Create timestamp for current time."""
        t = time.localtime()
        return cls(
            year=t.tm_year,
            month=t.tm_mon,
            day=t.tm_mday,
            hour=t.tm_hour,
            minute=t.tm_min,
            second=t.tm_sec,
        )


@dataclass
class RKBootHeader:
    """
    Rockchip Boot Image header structure (102 bytes).

    Fields layout matches the C struct rk_boot_header in boot_merger.h.
    Uses #pragma pack(1) for exact binary layout.
    """
    tag: int = TAG_BOOT
    size: int = 0  # Size of this header structure
    version: int = 0  # BCD encoded version (major << 8 | minor)
    merger_version: int = MERGER_VERSION
    release_time: RKTime = field(default_factory=RKTime.now)
    chip_type: int = 0
    code471_num: int = 0
    code471_offset: int = 0
    code471_size: int = 0
    code472_num: int = 0
    code472_offset: int = 0
    code472_size: int = 0
    loader_num: int = 0
    loader_offset: int = 0
    loader_size: int = 0
    sign_flag: int = 0
    rc4_flag: int = 1  # 1=disabled, 0=enabled (default disabled)
    reserved: bytes = field(default_factory=lambda: bytes(BOOT_RESERVED_SIZE))

    # Struct format string (total: 102 bytes)
    # tag(4) + size(2) + version(4) + mergerVersion(4) + releaseTime(7) +
    # chipType(4) + code471Num(1) + code471Offset(4) + code471Size(1) +
    # code472Num(1) + code472Offset(4) + code472Size(1) +
    # loaderNum(1) + loaderOffset(4) + loaderSize(1) +
    # signFlag(1) + rc4Flag(1) + reserved(57)
    HEADER_FORMAT = "<IHIIHBBBBBIBBIBBIBBBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    HEADER_SIZE = 102

    def to_bytes(self) -> bytes:
        """Serialize header to binary format."""
        time_bytes = self.release_time.to_bytes()

        # Pack header fields (without reserved)
        header = struct.pack(
            "<IHIIHBBBBBIBIBBIBBIBBB",
            self.tag,
            self.HEADER_SIZE,
            self.version,
            self.merger_version,
            self.release_time.year,
            self.release_time.month,
            self.release_time.day,
            self.release_time.hour,
            self.release_time.minute,
            self.release_time.second,
            self.chip_type,
            self.code471_num,
            self.code471_offset,
            self.code471_size,
            self.code472_num,
            self.code472_offset,
            self.code472_size,
            self.loader_num,
            self.loader_offset,
            self.loader_size,
            self.sign_flag,
            self.rc4_flag,
        )

        # Append reserved bytes
        result = header + bytes(BOOT_RESERVED_SIZE)
        assert len(result) == self.HEADER_SIZE, f"Header size mismatch: {len(result)} != {self.HEADER_SIZE}"
        return result

    @classmethod
    def from_bytes(cls, data: bytes) -> RKBootHeader:
        """Parse header from binary data."""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError(f"Data too short: {len(data)} < {cls.HEADER_SIZE}")

        # Unpack header fields
        fields = struct.unpack("<IHIIHBBBBBIBIBBIBBIBBB", data[:45])

        return cls(
            tag=fields[0],
            size=fields[1],
            version=fields[2],
            merger_version=fields[3],
            release_time=RKTime(fields[4], fields[5], fields[6], fields[7], fields[8], fields[9]),
            chip_type=fields[10],
            code471_num=fields[11],
            code471_offset=fields[12],
            code471_size=fields[13],
            code472_num=fields[14],
            code472_offset=fields[15],
            code472_size=fields[16],
            loader_num=fields[17],
            loader_offset=fields[18],
            loader_size=fields[19],
            sign_flag=fields[20],
            rc4_flag=fields[21],
            reserved=data[45:cls.HEADER_SIZE],
        )


@dataclass
class RKBootEntry:
    """
    Boot entry metadata (54 bytes).

    Describes one binary component (DDR init, USB plug, or loader).
    """
    size: int = 0  # Size of this entry structure
    entry_type: RKEntryType = RKEntryType.ENTRY_LOADER
    name: list[int] = field(default_factory=lambda: [0] * MAX_NAME_LEN)  # Wide char (uint16) array
    data_offset: int = 0  # Offset in image where data starts
    data_size: int = 0  # Size of data (aligned)
    data_delay: int = 0  # Delay in ms

    ENTRY_SIZE = 54

    def to_bytes(self) -> bytes:
        """Serialize entry to binary format."""
        # Pack name as uint16 array (20 * 2 = 40 bytes)
        name_bytes = struct.pack(f"<{MAX_NAME_LEN}H", *self.name[:MAX_NAME_LEN])

        # Pack entry fields
        entry = struct.pack(
            "<BB",
            self.ENTRY_SIZE,
            self.entry_type,
        )

        entry += name_bytes
        entry += struct.pack("<III", self.data_offset, self.data_size, self.data_delay)

        assert len(entry) == self.ENTRY_SIZE, f"Entry size mismatch: {len(entry)} != {self.ENTRY_SIZE}"
        return entry

    @classmethod
    def from_bytes(cls, data: bytes) -> RKBootEntry:
        """Parse entry from binary data."""
        if len(data) < cls.ENTRY_SIZE:
            raise ValueError(f"Data too short: {len(data)} < {cls.ENTRY_SIZE}")

        size, entry_type = struct.unpack("<BB", data[:2])
        name = list(struct.unpack(f"<{MAX_NAME_LEN}H", data[2:42]))
        data_offset, data_size, data_delay = struct.unpack("<III", data[42:54])

        return cls(
            size=size,
            entry_type=RKEntryType(entry_type),
            name=name,
            data_offset=data_offset,
            data_size=data_size,
            data_delay=data_delay,
        )


# Utility functions

def get_bcd(value: int) -> int:
    """
    Convert decimal to BCD (Binary-Coded Decimal).

    Args:
        value: Decimal value (0-99)

    Returns:
        BCD encoded value (lower 8 bits)

    Example:
        >>> get_bcd(25)  # 25 -> 0x25
        37
        >>> get_bcd(50)  # 50 -> 0x50
        80
    """
    if value > 99:
        value = value % 100

    tens = (value // 10) % 10
    ones = value % 10
    bcd = (tens << 4) | ones
    return bcd & 0xFF


def get_chip_type(chip_name: str) -> int:
    """
    Convert chip name to chip type ID.

    Args:
        chip_name: Chip name (e.g., "RK3399", "RK330C")

    Returns:
        Chip type ID (32-bit integer)

    Example:
        >>> hex(get_chip_type("RK3399"))
        '0x33333939'
        >>> hex(get_chip_type("RK330C"))
        '0x33333043'
    """
    # Try predefined chip names first
    if chip_name in CHIP_NAME_MAP:
        return CHIP_NAME_MAP[chip_name]

    # For newer chips, convert chip ID to 32-bit integer
    # Skip "RK" prefix, take next 4 characters
    # Example: "RK3399" -> "3399" -> 0x33333939
    chip_id = chip_name[2:6] if chip_name.startswith("RK") else chip_name[:4]
    chip_id = chip_id.ljust(4, '\x00')  # Pad to 4 chars

    # Convert to big-endian 32-bit integer
    chip_type = struct.unpack(">I", chip_id.encode('ascii'))[0]
    return chip_type


def align_size(size: int, alignment: int = ENTRY_ALIGN) -> int:
    """
    Align size to specified boundary.

    Args:
        size: Original size
        alignment: Alignment boundary (default: 2048)

    Returns:
        Aligned size (rounded up)
    """
    return ((size + alignment - 1) // alignment) * alignment


def str_to_wide(s: str, max_len: int = MAX_NAME_LEN) -> list[int]:
    """
    Convert ASCII string to wide character array (uint16).

    Args:
        s: Input ASCII string
        max_len: Maximum length

    Returns:
        List of uint16 values (Unicode code points)
    """
    wide = [ord(c) for c in s[:max_len]]
    # Pad with zeros
    wide.extend([0] * (max_len - len(wide)))
    return wide[:max_len]


def get_file_name(path: Path) -> str:
    """
    Extract filename without extension from path.

    Args:
        path: File path

    Returns:
        Filename without extension

    Example:
        >>> get_file_name(Path("bin/rk33/rk3399_ddr_800MHz_v1.25.bin"))
        'rk3399_ddr_800MHz_v1'
    """
    return path.stem


@dataclass
class BootMerger:
    """
    Merge DDR init and miniloader into bootable image.

    This class implements the boot_merger functionality which creates
    idbloader.img (for SD card boot) or loader.bin.

    Attributes:
        config: Parsed RKBOOT INI configuration
        enable_rc4: Enable RC4 encryption (default: False)

    Example:
        >>> merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
        >>> merger.pack("idbloader.img")
    """

    config: RKBootConfig
    enable_rc4: bool = False

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

        This creates a Rockchip boot loader image containing:
        - Boot header with metadata
        - Entry descriptors for all components
        - Binary data for DDR init, USB plug, and loaders

        Args:
            output: Output file path

        Returns:
            Path to created file

        Raises:
            FileNotFoundError: If input binaries don't exist
            ValueError: If configuration is invalid
        """
        output_path = Path(output)
        print(f"Packing boot loader image: {output_path}")

        # Validate binaries exist
        for entry in self.config.ddr_bins:
            if not entry.path.exists():
                raise FileNotFoundError(f"DDR binary not found: {entry.path}")
        for entry in self.config.loader_bins:
            if not entry.path.exists():
                raise FileNotFoundError(f"Loader binary not found: {entry.path}")

        # Build header
        header = self._build_header()

        # Build entries
        entries_471 = []
        entries_472 = []
        entries_loader = []
        data_offset = self._calculate_data_offset(header)

        # Create entry descriptors
        for bin_entry in self.config.ddr_bins:
            entry = self._create_entry(bin_entry, RKEntryType.ENTRY_471, data_offset, delay=0, fix=False)
            entries_471.append(entry)
            data_offset = entry.data_offset + entry.data_size

        # CODE472 is usually empty in modern configs
        # for bin_entry in self.config.code472_bins:  # Not in RKBootConfig currently
        #     entry = self._create_entry(bin_entry, RKEntryType.ENTRY_472, data_offset, delay=0, fix=False)
        #     entries_472.append(entry)
        #     data_offset = entry.data_offset + entry.data_size

        for bin_entry in self.config.loader_bins:
            entry = self._create_entry(bin_entry, RKEntryType.ENTRY_LOADER, data_offset, delay=0, fix=True)
            entries_loader.append(entry)
            data_offset = entry.data_offset + entry.data_size

        # Write image
        with open(output_path, "wb") as f:
            # Write header
            f.write(header.to_bytes())

            # Write entries
            for entry in entries_471:
                f.write(entry.to_bytes())
            for entry in entries_472:
                f.write(entry.to_bytes())
            for entry in entries_loader:
                f.write(entry.to_bytes())

            # Write data
            for i, entry in enumerate(entries_471):
                bin_entry = self.config.ddr_bins[i]
                self._write_entry_data(f, bin_entry.path, entry, fix=False)

            for i, entry in enumerate(entries_loader):
                bin_entry = self.config.loader_bins[i]
                self._write_entry_data(f, bin_entry.path, entry, fix=True)

            # Calculate and write CRC32
            f.flush()

        # Calculate CRC of entire image
        with open(output_path, "rb") as f:
            image_data = f.read()
        crc = crc32_rk(image_data)

        # Append CRC
        with open(output_path, "ab") as f:
            f.write(struct.pack("<I", crc))

        # RC4 encrypt entire image if enabled (full image encryption like rksd format)
        if self.enable_rc4:
            with open(output_path, "rb") as f:
                full_image = f.read()
            encrypted_image = rc4_encrypt(full_image)
            with open(output_path, "wb") as f:
                f.write(encrypted_image)
            print(f"Applied RC4 encryption to entire image")

        print(f"Pack success: {output_path}")
        print(f"Image size: {output_path.stat().st_size} bytes")
        print(f"CRC32: 0x{crc:08X}")

        return output_path

    def _build_header(self) -> RKBootHeader:
        """Build boot header from configuration."""
        major, minor = self.config.version
        version_bcd = (get_bcd(major) << 8) | get_bcd(minor)

        # Count entries
        code471_num = len(self.config.ddr_bins)
        code472_num = 0  # Usually empty
        loader_num = len(self.config.loader_bins)

        # Calculate entry offsets
        code471_offset = RKBootHeader.HEADER_SIZE
        code471_size = RKBootEntry.ENTRY_SIZE

        code472_offset = code471_offset + code471_num * code471_size
        code472_size = RKBootEntry.ENTRY_SIZE

        loader_offset = code472_offset + code472_num * code472_size
        loader_size = RKBootEntry.ENTRY_SIZE

        header = RKBootHeader(
            tag=TAG_BOOT,
            size=RKBootHeader.HEADER_SIZE,
            version=version_bcd,
            merger_version=MERGER_VERSION,
            release_time=RKTime.now(),
            chip_type=get_chip_type(self.config.chip_name),
            code471_num=code471_num,
            code471_offset=code471_offset,
            code471_size=code471_size,
            code472_num=code472_num,
            code472_offset=code472_offset,
            code472_size=code472_size,
            loader_num=loader_num,
            loader_offset=loader_offset,
            loader_size=loader_size,
            rc4_flag=0 if self.enable_rc4 else 1,
        )

        return header

    def _calculate_data_offset(self, header: RKBootHeader) -> int:
        """Calculate offset where data section starts."""
        total_entries = header.code471_num + header.code472_num + header.loader_num
        return RKBootHeader.HEADER_SIZE + total_entries * RKBootEntry.ENTRY_SIZE

    def _create_entry(
        self,
        bin_entry: BinaryEntry,
        entry_type: RKEntryType,
        data_offset: int,
        delay: int = 0,
        fix: bool = False,
    ) -> RKBootEntry:
        """
        Create entry descriptor for a binary file.

        Args:
            bin_entry: Binary file entry
            entry_type: Type of entry
            data_offset: Offset where data will be written
            delay: Delay in ms
            fix: Use fixed block size for alignment

        Returns:
            RKBootEntry instance
        """
        # Get file size
        file_size = bin_entry.path.stat().st_size

        # Calculate aligned size
        if fix:
            # Fixed mode: align to 512 bytes, then to 2048 bytes
            aligned_size = ((file_size - 1) // SMALL_PACKET + 1) * SMALL_PACKET
            aligned_size = align_size(aligned_size, ENTRY_ALIGN)
        else:
            # Normal mode: align directly to 2048 bytes
            aligned_size = align_size(file_size, ENTRY_ALIGN)

        # Extract filename (without extension)
        file_name = get_file_name(bin_entry.path)
        name_wide = str_to_wide(file_name, MAX_NAME_LEN)

        entry = RKBootEntry(
            size=RKBootEntry.ENTRY_SIZE,
            entry_type=entry_type,
            name=name_wide,
            data_offset=data_offset,
            data_size=aligned_size,
            data_delay=delay,
        )

        return entry

    def _write_entry_data(
        self,
        f: Path,
        bin_path: Path,
        entry: RKBootEntry,
        fix: bool = False,
    ) -> None:
        """
        Write binary data for an entry.

        Args:
            f: Output file handle
            bin_path: Path to binary file
            entry: Entry descriptor
            fix: Use fixed block size for alignment
        """
        # Read binary data
        with open(bin_path, "rb") as bin_file:
            data = bin_file.read()

        # Align and pad data
        if fix:
            # Fixed mode: pad to 512-byte blocks
            aligned_size = ((len(data) - 1) // SMALL_PACKET + 1) * SMALL_PACKET
            aligned_size = align_size(aligned_size, ENTRY_ALIGN)
        else:
            # Normal mode: pad to 2048-byte boundary
            aligned_size = align_size(len(data), ENTRY_ALIGN)

        padded_data = data.ljust(aligned_size, b'\x00')

        # Note: RC4 encryption is now applied to the entire image at the end
        # (in pack() method) rather than per-entry, to match rksd format
        f.write(padded_data)

    def unpack(self, input_path: str | Path, output_dir: str | Path) -> None:
        """
        Unpack boot loader image to individual binaries.

        Args:
            input_path: Path to packed image
            output_dir: Directory to extract binaries to
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Unpacking: {input_path}")

        with open(input_path, "rb") as f:
            # Read header
            header_data = f.read(RKBootHeader.HEADER_SIZE)
            header = RKBootHeader.from_bytes(header_data)

            print(f"Header: chip_type=0x{header.chip_type:08X}, version=0x{header.version:04X}")

            # Read all entries
            entry_count = header.code471_num + header.code472_num + header.loader_num
            entries = []
            for _ in range(entry_count):
                entry_data = f.read(RKBootEntry.ENTRY_SIZE)
                entry = RKBootEntry.from_bytes(entry_data)
                entries.append(entry)

            # Extract each entry
            for entry in entries:
                # Convert wide char name to string
                name = ''.join(chr(c) for c in entry.name if c != 0)
                output_file = output_dir / f"{name}.bin"

                print(f"Extracting: {name} (offset=0x{entry.data_offset:X}, size={entry.data_size})")

                # Seek to data offset
                f.seek(entry.data_offset)
                data = f.read(entry.data_size)

                # RC4 decryption if needed
                if header.rc4_flag == 0:  # RC4 enabled (0=enabled, 1=disabled)
                    if entry.entry_type == RKEntryType.ENTRY_LOADER:
                        # Block decryption for loader data
                        data = rc4_decrypt_blocks(data, SMALL_PACKET)
                    else:
                        # Whole decryption for CODE471/CODE472 data
                        data = rc4_decrypt(data)

                # Write extracted data
                with open(output_file, "wb") as out_f:
                    out_f.write(data)

        print(f"Unpack complete: {output_dir}")

    def validate_binaries(self) -> bool:
        """
        Check if all required binaries exist.

        Returns:
            True if all binaries are accessible
        """
        for entry in self.config.ddr_bins:
            if not entry.path.exists():
                print(f"Missing DDR binary: {entry.path}")
                return False
        for entry in self.config.loader_bins:
            if not entry.path.exists():
                print(f"Missing loader binary: {entry.path}")
                return False
        return True


# CLI interface
def main() -> None:
    """Command line interface for boot_merger."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Rockchip boot_merger - Merge DDR init and miniloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pack from INI file
  %(prog)s --pack RKBOOT/RK3399MINIALL.ini

  # Unpack existing image
  %(prog)s --unpack idbloader.img -o output_dir/

  # Enable RC4 encryption
  %(prog)s --pack --rc4 RKBOOT/RK3399MINIALL.ini
        """,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--pack", metavar="INI", help="Pack from INI file")
    mode_group.add_argument("--unpack", metavar="IMAGE", help="Unpack image")

    parser.add_argument("-o", "--output", help="Output file/directory")
    parser.add_argument("--rc4", action="store_true", help="Enable RC4 encryption")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.pack:
        merger = BootMerger.from_ini(args.pack)
        merger.enable_rc4 = args.rc4

        if not merger.validate_binaries():
            print("Error: Some binaries are missing!")
            return

        output = args.output or merger.config.output_path
        merger.pack(output)

    elif args.unpack:
        output_dir = args.output or "unpacked"
        merger = BootMerger(config=RKBootConfig())  # Dummy config for unpack
        merger.unpack(args.unpack, output_dir)


if __name__ == "__main__":
    main()
