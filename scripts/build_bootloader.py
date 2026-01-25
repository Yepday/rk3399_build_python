#!/usr/bin/env python3
"""
Rockchip Bootloader Build Script

This script automates the building of bootloader images:
- idbloader.img (DDR init + miniloader)
- uboot.img (U-Boot)
- trust.img (ATF + OP-TEE)

Usage:
    python3 build_bootloader.py
    python3 build_bootloader.py --config test_data/RKBOOT/RK3399MINIALL.ini
    python3 build_bootloader.py --clean
"""

import argparse
import sys
import shutil
from pathlib import Path
from typing import Optional

# Add src to Python path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from rkpyimg.tools.rksd import create_rksd_image, append_to_rksd
from rkpyimg.tools.loaderimage import pack_uboot
from rkpyimg.core.ini_parser import RKBootConfig


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(message: str) -> None:
    """Print colored header message."""
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
    print(f"{Colors.CYAN}{message:^60}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")


def print_step(step: int, total: int, message: str) -> None:
    """Print build step."""
    print(f"{Colors.BLUE}[{step}/{total}]{Colors.NC} {message}")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.NC} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")


def clean_build(output_dir: Path) -> None:
    """Clean build output directory."""
    print_header("Cleaning Build Output")

    if output_dir.exists():
        print(f"Removing {output_dir}")
        shutil.rmtree(output_dir)
        print_success("Build directory cleaned")
    else:
        print("Build directory doesn't exist, nothing to clean")


def find_alternative_binary(original_path: Path, project_root: Path) -> Optional[Path]:
    """
    Try to find an alternative binary if the original doesn't exist.

    Search order:
    1. components/firmware/rk33/ directory (standard location)
    2. configs/RKBOOT/bin/rk33/ directory (INI-relative)
    3. test_data/rk33/ directory (legacy, backward compatibility)
    4. test_data/RKBOOT/bin/rk33/ directory (legacy)

    Args:
        original_path: Original path from INI config
        project_root: Project root directory

    Returns:
        Alternative path if found, None otherwise
    """
    filename = original_path.name
    base_name = filename.rsplit('_v', 1)[0] if '_v' in filename else filename.stem

    # Search locations (new structure first, then fallback to legacy)
    search_dirs = [
        project_root / "components" / "firmware" / "rk33",  # Standard location
        project_root / "configs" / "RKBOOT" / "bin" / "rk33",
        project_root / "test_data" / "rk33",  # Legacy fallback
        project_root / "test_data" / "RKBOOT" / "bin" / "rk33",  # Legacy fallback
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        # Try exact match first
        exact_match = search_dir / filename
        if exact_match.exists():
            return exact_match

        # Try to find any version of the same file
        pattern = f"{base_name}_v*.bin"
        matches = list(search_dir.glob(pattern))
        if matches:
            # Return the newest version (sort by name, higher version numbers come later)
            matches.sort()
            return matches[-1]

    return None


def find_uboot_binary(specified_path: Optional[Path], project_root: Path) -> Optional[Path]:
    """
    Find u-boot.bin with intelligent search.

    Search order:
    1. Specified path (if provided)
    2. build/boot/u-boot.bin (compiled output, standard location)
    3. components/uboot/u-boot.bin (in-tree build)
    4. test_data/u-boot.bin (legacy reference binary)

    Args:
        specified_path: User-specified path to u-boot.bin
        project_root: Project root directory

    Returns:
        Path to u-boot.bin if found, None otherwise
    """
    # Priority 1: User-specified path
    if specified_path and specified_path.exists():
        return specified_path

    # Priority 2: Compiled output (standard location)
    compiled_uboot = project_root / "build" / "boot" / "u-boot.bin"
    if compiled_uboot.exists():
        return compiled_uboot

    # Priority 3: In-tree build
    intree_uboot = project_root / "components" / "uboot" / "u-boot.bin"
    if intree_uboot.exists():
        return intree_uboot

    # Priority 4: Legacy reference binary (backward compatibility)
    reference_uboot = project_root / "test_data" / "u-boot.bin"
    if reference_uboot.exists():
        return reference_uboot

    return None


def build_idbloader(config: RKBootConfig, output_dir: Path, chip: str = "rk3399") -> Path:
    """
    Build idbloader.img from DDR init and miniloader.

    Args:
        config: Parsed RKBOOT configuration
        output_dir: Output directory
        chip: Chip name (default: rk3399)

    Returns:
        Path to created idbloader.img
    """
    print_step(1, 2, "Building idbloader.img")

    # Get DDR init binary (FlashData)
    if not config.ddr_bins:
        raise ValueError("No DDR init binary found in config")

    ddr_bin = config.ddr_bins[0].path
    if not ddr_bin.exists():
        print_warning(f"DDR init binary not found: {ddr_bin}")
        # Try to find alternative
        alt_ddr = find_alternative_binary(ddr_bin, PROJECT_ROOT)
        if alt_ddr:
            print(f"  Found alternative: {alt_ddr}")
            ddr_bin = alt_ddr
        else:
            raise FileNotFoundError(f"DDR init binary not found: {ddr_bin}")

    print(f"  DDR Init: {ddr_bin.name}")

    # Get miniloader binary (FlashBoot)
    if not config.loader_bins:
        raise ValueError("No miniloader binary found in config")

    miniloader_bin = config.loader_bins[0].path
    if not miniloader_bin.exists():
        print_warning(f"Miniloader binary not found: {miniloader_bin}")
        # Try to find alternative
        alt_miniloader = find_alternative_binary(miniloader_bin, PROJECT_ROOT)
        if alt_miniloader:
            print(f"  Found alternative: {alt_miniloader}")
            miniloader_bin = alt_miniloader
        else:
            raise FileNotFoundError(f"Miniloader binary not found: {miniloader_bin}")

    print(f"  Miniloader: {miniloader_bin.name}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    idbloader_path = output_dir / "idbloader.img"

    # Step 1: Create rksd image from DDR init
    print(f"\n  Creating rksd format image...")
    create_rksd_image(ddr_bin, idbloader_path, chip=chip)

    # Step 2: Append miniloader
    print(f"\n  Appending miniloader...")
    append_to_rksd(idbloader_path, miniloader_bin)

    print_success(f"idbloader.img created: {idbloader_path}")
    print(f"  Size: {idbloader_path.stat().st_size:,} bytes ({idbloader_path.stat().st_size // 1024} KB)")

    return idbloader_path


def build_uboot(uboot_bin: Path, output_dir: Path, load_addr: int = 0x200000) -> Path:
    """
    Build uboot.img from u-boot.bin.

    Args:
        uboot_bin: Path to u-boot.bin
        output_dir: Output directory
        load_addr: Load address (default: 0x200000)

    Returns:
        Path to created uboot.img
    """
    print_step(2, 2, "Building uboot.img")

    if not uboot_bin.exists():
        raise FileNotFoundError(f"U-Boot binary not found: {uboot_bin}")

    print(f"  U-Boot: {uboot_bin.name}")
    print(f"  Load Address: 0x{load_addr:08X}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    uboot_img_path = output_dir / "uboot.img"

    # Pack U-Boot
    print(f"\n  Packing U-Boot with Rockchip header...")
    pack_uboot(uboot_bin, uboot_img_path, load_addr=load_addr)

    print_success(f"uboot.img created: {uboot_img_path}")
    print(f"  Size: {uboot_img_path.stat().st_size:,} bytes ({uboot_img_path.stat().st_size // 1024} KB)")

    return uboot_img_path


def main():
    parser = argparse.ArgumentParser(
        description="Build Rockchip bootloader images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build all bootloader images
  %(prog)s

  # Use custom configuration
  %(prog)s --config test_data/RKBOOT/RK3399MINIALL.ini

  # Specify U-Boot binary
  %(prog)s --uboot test_data/u-boot.bin

  # Clean build output
  %(prog)s --clean

  # Build with custom output directory
  %(prog)s --output build/bootloader
        """
    )

    parser.add_argument(
        "-c", "--config",
        default="configs/RKBOOT/RK3399MINIALL.ini",
        help="Path to RKBOOT INI config (default: configs/RKBOOT/RK3399MINIALL.ini, fallback: test_data/RKBOOT/RK3399MINIALL.ini)"
    )

    parser.add_argument(
        "-u", "--uboot",
        default=None,
        help="Path to u-boot.bin (default: auto-detect from build/boot/, test_data/, or components/uboot/)"
    )

    parser.add_argument(
        "-o", "--output",
        default="build/boot",
        help="Output directory (default: build/boot, fallback: test_data/output)"
    )

    parser.add_argument(
        "--chip",
        default="rk3399",
        choices=["rk3036", "rk3066", "rk3128", "rk3188", "rk322x", "rk3288",
                 "rk3308", "rk3328", "rk3368", "rk3399", "px30", "rv1108"],
        help="Chip name (default: rk3399)"
    )

    parser.add_argument(
        "--load-addr",
        default="0x200000",
        help="U-Boot load address (default: 0x200000)"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build output and exit"
    )

    parser.add_argument(
        "--skip-uboot",
        action="store_true",
        help="Skip building uboot.img (only build idbloader.img)"
    )

    args = parser.parse_args()

    # Convert paths with fallback logic
    config_path = Path(args.config)
    if not config_path.exists():
        # Fallback to old location
        fallback_config = Path("test_data/RKBOOT/RK3399MINIALL.ini")
        if fallback_config.exists():
            print_warning(f"Config not found at {config_path}, using {fallback_config}")
            config_path = fallback_config

    # Handle u-boot.bin path with intelligent search
    if args.uboot:
        uboot_bin_path = Path(args.uboot)
    else:
        uboot_bin_path = find_uboot_binary(None, PROJECT_ROOT)

    output_dir = Path(args.output)
    if not output_dir.exists() and output_dir == Path("build/boot"):
        # If new structure doesn't exist yet, fallback to old
        fallback_output = Path("test_data/output")
        if fallback_output.exists():
            print_warning(f"Output dir doesn't exist: {output_dir}, using {fallback_output}")
            output_dir = fallback_output

    load_addr = int(args.load_addr, 0)  # Support 0x prefix

    # Handle clean
    if args.clean:
        clean_build(output_dir)
        return 0

    # Print header
    print_header("Rockchip Bootloader Build System")
    print(f"Configuration: {config_path}")
    print(f"Chip: {args.chip}")
    print(f"Output: {output_dir}")
    if uboot_bin_path:
        print(f"U-Boot binary: {uboot_bin_path}")

    try:
        # Parse configuration
        print(f"\nParsing configuration...")
        config = RKBootConfig.from_file(config_path)
        print_success(f"Chip: {config.chip_name}, Version: {config.version[0]}.{config.version[1]}")

        # Build idbloader.img
        idbloader_path = build_idbloader(config, output_dir, chip=args.chip)

        # Build uboot.img
        if not args.skip_uboot:
            if not uboot_bin_path or not uboot_bin_path.exists():
                print_warning(f"U-Boot binary not found")
                print_warning("To build U-Boot, run: python3 scripts/build_uboot.py")
                print_warning("Skipping uboot.img build")
            else:
                uboot_path = build_uboot(uboot_bin_path, output_dir, load_addr=load_addr)
        else:
            print_step(2, 2, "Skipping uboot.img (--skip-uboot specified)")

        # Summary
        print_header("Build Summary")
        print(f"Output directory: {output_dir}")
        print("\nGenerated files:")
        for img in output_dir.glob("*.img"):
            size = img.stat().st_size
            print(f"  {Colors.GREEN}✓{Colors.NC} {img.name:20s} {size:>10,} bytes ({size // 1024:>6} KB)")

        print(f"\n{Colors.GREEN}Build completed successfully!{Colors.NC}\n")

        # Next steps
        print("Next steps:")
        print(f"  1. Flash to SD card:")
        print(f"     sudo dd if={output_dir}/idbloader.img of=/dev/sdX seek=64 conv=fsync")
        if not args.skip_uboot:
            print(f"     sudo dd if={output_dir}/uboot.img of=/dev/sdX seek=16384 conv=fsync")
        print(f"\n  2. Or use the flash script:")
        print(f"     sudo ./scripts/flash_bootloader.sh /dev/sdX {output_dir}")
        print()

        return 0

    except Exception as e:
        print_error(f"Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
