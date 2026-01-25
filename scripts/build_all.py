#!/usr/bin/env python3
"""
Complete RK3399 System Build Pipeline

This script coordinates the complete build pipeline:
1. Download and compile U-Boot (if needed)
2. Build idbloader.img and uboot.img
3. Download and compile Linux kernel (if needed)
4. Optionally flash to SD card

Usage:
    python3 build_all.py                          # Full build
    python3 build_all.py --skip-uboot-build       # Skip U-Boot compilation
    python3 build_all.py --skip-kernel-build      # Skip kernel compilation
    python3 build_all.py --flash /dev/sdX         # Build and flash
    python3 build_all.py --clean                  # Clean everything
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import Optional


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


def print_header(message: str) -> None:
    """Print colored header message."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{message:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_phase(phase: int, total: int, message: str) -> None:
    """Print build phase."""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}[Phase {phase}/{total}]{Colors.NC} {message}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")


def run_script(script_path: Path, args: list = None, check: bool = True) -> int:
    """Run a Python script with arguments.

    Args:
        script_path: Path to the script
        args: Additional arguments
        check: Raise exception on error

    Returns:
        Return code
    """
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"{Colors.BLUE}Running:{Colors.NC} {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0 and check:
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return result.returncode


def run_shell_script(script_path: Path, args: list = None, check: bool = True) -> int:
    """Run a shell script with arguments.

    Args:
        script_path: Path to the script
        args: Additional arguments
        check: Raise exception on error

    Returns:
        Return code
    """
    cmd = ["sudo", "bash", str(script_path)]
    if args:
        cmd.extend(args)

    print(f"{Colors.BLUE}Running:{Colors.NC} {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0 and check:
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return result.returncode


class BuildPipeline:
    """Complete build pipeline coordinator."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize pipeline.

        Args:
            project_root: Project root directory. If None, auto-detect.
        """
        if project_root is None:
            # Auto-detect from script location
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

        self.project_root = project_root.resolve()
        self.scripts_dir = self.project_root / "scripts"
        self.build_boot_dir = self.project_root / "build" / "boot"
        self.build_kernel_dir = self.project_root / "build" / "kernel"

        # Script paths
        self.build_uboot_script = self.scripts_dir / "build_uboot.py"
        self.build_bootloader_script = self.scripts_dir / "build_bootloader.py"
        self.build_kernel_script = self.scripts_dir / "build_kernel.py"
        self.flash_script = self.scripts_dir / "flash_bootloader.sh"

    def check_scripts_exist(self) -> bool:
        """Check if all required scripts exist.

        Returns:
            True if all scripts exist
        """
        scripts = [
            ("build_uboot.py", self.build_uboot_script),
            ("build_bootloader.py", self.build_bootloader_script),
            ("build_kernel.py", self.build_kernel_script),
            ("flash_bootloader.sh", self.flash_script),
        ]

        all_exist = True
        for name, path in scripts:
            if not path.exists():
                print_error(f"Script not found: {name} at {path}")
                all_exist = False
            else:
                print_success(f"Found {name}")

        return all_exist

    def clean_all(self) -> int:
        """Clean all build artifacts.

        Returns:
            Return code
        """
        print_header("Cleaning All Build Artifacts")

        # Clean U-Boot
        print("\n1. Cleaning U-Boot...")
        rc1 = run_script(self.build_uboot_script, ["--clean"], check=False)

        # Clean bootloader images
        print("\n2. Cleaning bootloader images...")
        rc2 = run_script(self.build_bootloader_script, ["--clean"], check=False)

        # Clean kernel
        print("\n3. Cleaning kernel...")
        rc3 = run_script(self.build_kernel_script, ["--clean"], check=False)

        if rc1 == 0 and rc2 == 0 and rc3 == 0:
            print_success("All clean completed")
            return 0
        else:
            print_warning("Clean completed with warnings")
            return 1

    def build_uboot(self, skip_download: bool = False) -> int:
        """Build U-Boot from source.

        Args:
            skip_download: Skip downloading sources

        Returns:
            Return code
        """
        print_phase(1, 4, "Building U-Boot from Source")

        args = []
        if skip_download:
            args.append("--skip-download")

        return run_script(self.build_uboot_script, args)

    def build_bootloader_images(self) -> int:
        """Build bootloader images (idbloader.img, uboot.img).

        Returns:
            Return code
        """
        print_phase(2, 4, "Building Bootloader Images")

        return run_script(self.build_bootloader_script)

    def build_kernel(self, skip_download: bool = False) -> int:
        """Build Linux kernel from source.

        Args:
            skip_download: Skip downloading sources

        Returns:
            Return code
        """
        print_phase(3, 4, "Building Linux Kernel")

        args = []
        if skip_download:
            args.append("--skip-download")

        return run_script(self.build_kernel_script, args)

    def flash_to_device(self, device: str) -> int:
        """Flash bootloader to device.

        Args:
            device: Device path (e.g., /dev/sdb)

        Returns:
            Return code
        """
        print_phase(4, 4, f"Flashing to {device}")

        return run_shell_script(self.flash_script, [device])

    def build_all(self, skip_uboot_build: bool = False, skip_kernel_build: bool = False,
                  skip_download: bool = False, flash_device: Optional[str] = None) -> int:
        """Execute complete build pipeline.

        Args:
            skip_uboot_build: Skip U-Boot compilation (use existing)
            skip_kernel_build: Skip kernel compilation (use existing)
            skip_download: Skip downloading sources
            flash_device: Device to flash to (None = don't flash)

        Returns:
            Return code
        """
        print_header("RK3399 Complete System Build Pipeline")

        # Check scripts
        print("Checking build scripts...")
        if not self.check_scripts_exist():
            print_error("Required scripts missing")
            return 1

        print()

        try:
            # Phase 1: Build U-Boot (optional)
            if not skip_uboot_build:
                rc = self.build_uboot(skip_download=skip_download)
                if rc != 0:
                    print_error("U-Boot build failed")
                    return rc
            else:
                print_phase(1, 4, "Skipping U-Boot Build")
                print("Using existing u-boot.bin")

            # Phase 2: Build bootloader images
            rc = self.build_bootloader_images()
            if rc != 0:
                print_error("Bootloader image build failed")
                return rc

            # Phase 3: Build kernel (optional)
            if not skip_kernel_build:
                rc = self.build_kernel(skip_download=skip_download)
                if rc != 0:
                    print_error("Kernel build failed")
                    return rc
            else:
                print_phase(3, 4, "Skipping Kernel Build")
                print("Using existing kernel image")

            # Phase 4: Flash (optional)
            if flash_device:
                rc = self.flash_to_device(flash_device)
                if rc != 0:
                    print_error("Flash failed")
                    return rc
            else:
                print_phase(4, 4, "Skipping Flash")
                print("Images are ready. To flash to SD card, run:")
                print(f"  {Colors.YELLOW}sudo ./scripts/flash_bootloader.sh{Colors.NC}")
                print()
                print("The script will auto-detect the build directory and guide you to select the target device.")

            # Success!
            print_header("Build Pipeline Complete!")
            print()
            print(f"{Colors.GREEN}All images built successfully!{Colors.NC}")
            print()

            # List generated files
            print("Generated files:")
            print()
            print(f"  {Colors.BLUE}Bootloader (build/boot/){Colors.NC}:")
            if self.build_boot_dir.exists():
                for img in sorted(self.build_boot_dir.glob("*.img")) + sorted(self.build_boot_dir.glob("*.bin")):
                    size = img.stat().st_size
                    print(f"    {Colors.GREEN}✓{Colors.NC} {img.name:25s} {size:>10,} bytes ({size // 1024:>6} KB)")

            print()
            print(f"  {Colors.BLUE}Kernel (build/kernel/){Colors.NC}:")
            if self.build_kernel_dir.exists():
                # Kernel image
                kernel_image = self.build_kernel_dir / "Image"
                if kernel_image.exists():
                    size = kernel_image.stat().st_size
                    print(f"    {Colors.GREEN}✓{Colors.NC} {'Image':25s} {size:>10,} bytes ({size // (1024*1024):>6} MB)")

                # DTBs
                dtb_dir = self.build_kernel_dir / "dtbs"
                if dtb_dir.exists():
                    dtb_count = len(list(dtb_dir.glob("*.dtb")))
                    if dtb_count > 0:
                        print(f"    {Colors.GREEN}✓{Colors.NC} {'dtbs/ ({} files)'.format(dtb_count):25s}")

                # System.map
                system_map = self.build_kernel_dir / "System.map"
                if system_map.exists():
                    size = system_map.stat().st_size
                    print(f"    {Colors.GREEN}✓{Colors.NC} {'System.map':25s} {size:>10,} bytes ({size // 1024:>6} KB)")

            print()

            return 0

        except subprocess.CalledProcessError as e:
            print_error(f"Build pipeline failed at command: {' '.join(e.cmd)}")
            return e.returncode
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Complete RK3399 system build pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full build (download + compile + pack)
  python3 build_all.py

  # Build without downloading sources (if already downloaded)
  python3 build_all.py --skip-download

  # Skip U-Boot compilation (use existing u-boot.bin)
  python3 build_all.py --skip-uboot-build

  # Skip kernel compilation (use existing kernel)
  python3 build_all.py --skip-kernel-build

  # Build and flash to SD card
  python3 build_all.py --flash /dev/sdb

  # Clean all build artifacts
  python3 build_all.py --clean

  # Quick rebuild (skip downloads and recompilation)
  python3 build_all.py --skip-download --skip-uboot-build --skip-kernel-build
"""
    )

    parser.add_argument(
        "--skip-uboot-build",
        action="store_true",
        help="Skip U-Boot compilation (use existing u-boot.bin)"
    )
    parser.add_argument(
        "--skip-kernel-build",
        action="store_true",
        help="Skip kernel compilation (use existing kernel)"
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading sources (assume they exist)"
    )
    parser.add_argument(
        "--flash",
        metavar="DEVICE",
        help="Flash to device after build (e.g., /dev/sdb)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean all build artifacts and exit"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not provided)"
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = BuildPipeline(args.project_root)

    # Handle clean
    if args.clean:
        return pipeline.clean_all()

    # Execute build pipeline
    return pipeline.build_all(
        skip_uboot_build=args.skip_uboot_build,
        skip_kernel_build=args.skip_kernel_build,
        skip_download=args.skip_download,
        flash_device=args.flash
    )


if __name__ == "__main__":
    sys.exit(main())
