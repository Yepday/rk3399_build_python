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
    python3 build_all.py --clean                  # Clean build artifacts (keep sources)
    python3 build_all.py --distclean              # Deep clean (remove sources too)
"""

import argparse
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple


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


def run_shell_script(script_path: Path, args: list = None, check: bool = True, use_sudo: bool = True) -> int:
    """Run a shell script with arguments.

    Args:
        script_path: Path to the script
        args: Additional arguments
        check: Raise exception on error
        use_sudo: Whether to run with sudo (default: True)

    Returns:
        Return code
    """
    if use_sudo:
        cmd = ["sudo", "bash", str(script_path)]
    else:
        cmd = ["bash", str(script_path)]

    if args:
        cmd.extend(args)

    print(f"{Colors.BLUE}Running:{Colors.NC} {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, check=False)

    if result.returncode != 0 and check:
        raise subprocess.CalledProcessError(result.returncode, cmd)

    return result.returncode


def run_script_with_sudo(script_path: Path, args: list = None, check: bool = True) -> int:
    """Run a Python script with sudo for root privileges.

    Args:
        script_path: Path to the script
        args: Additional arguments
        check: Raise exception on error

    Returns:
        Return code
    """
    cmd = ["sudo", sys.executable, str(script_path)]
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
        self.build_rootfs_script = self.scripts_dir / "build_rootfs.py"
        self.make_bootimg_script = self.scripts_dir / "make_bootimg.sh"
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
            ("build_rootfs.py", self.build_rootfs_script),
            ("make_bootimg.sh", self.make_bootimg_script),
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

    def is_uboot_compiled(self) -> bool:
        """Check if U-Boot is already compiled.

        Returns:
            True if u-boot.bin exists and bootloader images exist
        """
        uboot_bin = self.project_root / "components" / "uboot" / "u-boot.bin"
        uboot_img = self.build_boot_dir / "uboot.img"
        idbloader_img = self.build_boot_dir / "idbloader.img"

        # Check if u-boot.bin exists OR if bootloader images exist
        return (uboot_bin.exists() or (uboot_img.exists() and idbloader_img.exists()))

    def is_kernel_compiled(self) -> bool:
        """Check if kernel is already compiled.

        Returns:
            True if kernel Image and DTBs exist
        """
        kernel_image = self.build_kernel_dir / "Image"
        dtbs_dir = self.build_kernel_dir / "dtbs"

        # Check if kernel Image exists and DTBs directory has .dtb files
        if not kernel_image.exists():
            return False

        if not dtbs_dir.exists():
            return False

        # Check if there are any .dtb files
        dtb_files = list(dtbs_dir.glob("*.dtb"))
        return len(dtb_files) > 0

    def is_rootfs_built(self) -> bool:
        """Check if rootfs is already built.

        Returns:
            True if rootfs directory exists with content
        """
        rootfs_dir = self.project_root / "build" / "rootfs"

        if not rootfs_dir.exists():
            return False

        # Check if rootfs has any content (img files or extracted directories)
        has_content = (
            len(list(rootfs_dir.glob("*.img"))) > 0 or
            len(list(rootfs_dir.glob("*/"))) > 0
        )

        return has_content

    def detect_build_status(self) -> Tuple[bool, bool, bool]:
        """Detect what has already been built.

        Returns:
            Tuple of (uboot_compiled, kernel_compiled, rootfs_built)
        """
        uboot_status = self.is_uboot_compiled()
        kernel_status = self.is_kernel_compiled()
        rootfs_status = self.is_rootfs_built()

        return (uboot_status, kernel_status, rootfs_status)

    def clean_all(self) -> int:
        """Clean build artifacts (keep sources).

        Removes: build/ directory (idbloader.img, uboot.img, kernel Image, etc.)
        Keeps: components/uboot/, components/kernel/, components/toolchain/

        Returns:
            Return code
        """
        print_header("RK3399 Build Cleanup (Keep Sources)")

        # First, show dry-run preview
        print(f"{Colors.YELLOW}Previewing what will be deleted:{Colors.NC}\n")
        clean_script = self.scripts_dir / "clean.py"
        rc = run_script(clean_script, ["--clean", "--dry-run"], check=False)

        if rc != 0:
            print_error("Failed to preview cleanup")
            return rc

        # Ask for confirmation
        print()
        response = input(f"{Colors.YELLOW}Continue with cleanup? (yes/no): {Colors.NC}").strip().lower()
        if response != "yes":
            print_warning("Cleanup cancelled")
            return 1

        print()

        # Execute actual cleanup (with --force to skip re-confirmation)
        return run_script(clean_script, ["--clean", "--force"], check=False)

    def distclean_all(self) -> int:
        """Deep clean - remove all sources and build artifacts.

        Removes:
        - build/ (all artifacts)
        - components/uboot/ (U-Boot source)
        - components/kernel/ (kernel source)
        - components/toolchain/ (toolchain)

        Keeps:
        - components/firmware/ (required for rebuilding)
        - configs/ (required for rebuilding)
        - All project files

        Returns:
            Return code
        """
        print_header("RK3399 Deep Cleanup (Remove All Sources)")

        # First, show dry-run preview
        print(f"{Colors.YELLOW}Previewing what will be deleted:{Colors.NC}\n")
        clean_script = self.scripts_dir / "clean.py"
        rc = run_script(clean_script, ["--distclean", "--dry-run"], check=False)

        if rc != 0:
            print_error("Failed to preview cleanup")
            return rc

        # Ask for confirmation
        print()
        response = input(f"{Colors.YELLOW}Continue with cleanup? (yes/no): {Colors.NC}").strip().lower()
        if response != "yes":
            print_warning("Cleanup cancelled")
            return 1

        print()

        # Execute actual cleanup (with --force to skip re-confirmation)
        return run_script(clean_script, ["--distclean", "--force"], check=False)


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
        print_phase(3, 5, "Building Linux Kernel")

        args = []
        if skip_download:
            args.append("--skip-download")

        return run_script(self.build_kernel_script, args)

    def build_bootimg(self, dtb_name: str = "rk3399-orangepi-4") -> int:
        """Build boot.img from kernel Image and DTB.

        Args:
            dtb_name: Device tree blob name (without .dtb extension)

        Returns:
            Return code
        """
        print_phase(4, 6, "Generating boot.img")

        # Check if make_bootimg.sh exists
        if not self.make_bootimg_script.exists():
            print_error(f"Script not found: {self.make_bootimg_script}")
            return 1

        return run_shell_script(self.make_bootimg_script, [dtb_name], check=True, use_sudo=False)

    def build_rootfs(self, distro: str = "focal", image_type: str = "server",
                      mirror: str = "cn") -> int:
        """Build root filesystem.

        Args:
            distro: Ubuntu distribution (bionic, focal, jammy)
            image_type: Image type (server, desktop)
            mirror: Ubuntu mirror (cn, official, default)

        Returns:
            Return code
        """
        print_phase(5, 6, "Building Root Filesystem")

        args = [
            "--distro", distro,
            "--type", image_type,
            "--mirror", mirror
        ]

        # Use sudo to run rootfs build (requires root privileges)
        return run_script_with_sudo(self.build_rootfs_script, args)

    def flash_to_device(self, device: str) -> int:
        """Flash bootloader to device.

        Args:
            device: Device path (e.g., /dev/sdb)

        Returns:
            Return code
        """
        print_phase(6, 6, f"Flashing to {device}")

        return run_shell_script(self.flash_script, [device])

    def build_all(self, skip_uboot_build: bool = False, skip_kernel_build: bool = False,
                  skip_rootfs: bool = False, skip_download: bool = False,
                  auto_detect: bool = True,
                  dtb_name: str = "rk3399-orangepi-4",
                  flash_device: Optional[str] = None,
                  rootfs_distro: str = "focal", rootfs_type: str = "server",
                  rootfs_mirror: str = "cn") -> int:
        """Execute complete build pipeline.

        Args:
            skip_uboot_build: Skip U-Boot compilation (use existing)
            skip_kernel_build: Skip kernel compilation (use existing)
            skip_rootfs: Skip rootfs build
            skip_download: Skip downloading sources
            auto_detect: Auto-detect already built components (default: True)
            dtb_name: Device tree blob name for boot.img
            flash_device: Device to flash to (None = don't flash)
            rootfs_distro: Ubuntu distribution for rootfs
            rootfs_type: Rootfs type (server or desktop)
            rootfs_mirror: Ubuntu mirror

        Returns:
            Return code
        """
        print_header("RK3399 Complete System Build Pipeline")

        # Validate sudo access early if needed (for rootfs build or flashing)
        if not skip_rootfs or flash_device:
            print(f"{Colors.YELLOW}This build requires root privileges (for rootfs build or flashing).{Colors.NC}")
            print(f"{Colors.YELLOW}Please enter your password to continue:{Colors.NC}\n")

            # Validate and cache sudo credentials
            result = subprocess.run(["sudo", "-v"], check=False)
            if result.returncode != 0:
                print_error("Failed to obtain sudo privileges")
                return 1
            print()

        # Check scripts
        print("Checking build scripts...")
        if not self.check_scripts_exist():
            print_error("Required scripts missing")
            return 1

        print()

        # Auto-detect already built components
        if auto_detect:
            print(f"{Colors.CYAN}Detecting build status...{Colors.NC}")
            uboot_compiled, kernel_compiled, rootfs_built = self.detect_build_status()

            # Display detection results
            if uboot_compiled:
                print_success("U-Boot already compiled")
                skip_uboot_build = True
            else:
                print_warning("U-Boot not found, will compile")

            if kernel_compiled:
                print_success("Kernel already compiled")
                skip_kernel_build = True
            else:
                print_warning("Kernel not found, will compile")

            if rootfs_built:
                print_success("Rootfs already built")
                skip_rootfs = True
            else:
                print_warning("Rootfs not found, will build")

            print()

        try:
            # Phase 1: Build U-Boot (optional)
            if not skip_uboot_build:
                rc = self.build_uboot(skip_download=skip_download)
                if rc != 0:
                    print_error("U-Boot build failed")
                    return rc
            else:
                print_phase(1, 5, "Skipping U-Boot Build")
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
                print_phase(3, 6, "Skipping Kernel Build")
                print("Using existing kernel image")

            # Phase 4: Generate boot.img
            rc = self.build_bootimg(dtb_name=dtb_name)
            if rc != 0:
                print_error("boot.img generation failed")
                return rc

            # Phase 5: Build rootfs (optional)
            if not skip_rootfs:
                rc = self.build_rootfs(
                    distro=rootfs_distro,
                    image_type=rootfs_type,
                    mirror=rootfs_mirror
                )
                if rc != 0:
                    print_error("Root filesystem build failed")
                    return rc
            else:
                print_phase(5, 6, "Skipping Root Filesystem Build")
                print("Using existing rootfs")

            # Phase 6: Flash (optional)
            if flash_device:
                rc = self.flash_to_device(flash_device)
                if rc != 0:
                    print_error("Flash failed")
                    return rc
            else:
                print_phase(6, 6, "Skipping Flash")
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

                # boot.img
                boot_img = self.build_kernel_dir / "boot.img"
                if boot_img.exists():
                    size = boot_img.stat().st_size
                    print(f"    {Colors.GREEN}✓{Colors.NC} {'boot.img':25s} {size:>10,} bytes ({size // (1024*1024):>6} MB)")

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
  # Full build with auto-detection (default)
  # Will automatically skip already compiled components
  python3 build_all.py

  # Force rebuild everything (disable auto-detection)
  python3 build_all.py --no-auto-detect

  # Build without downloading sources (if already downloaded)
  python3 build_all.py --skip-download

  # Manually skip U-Boot compilation
  python3 build_all.py --skip-uboot-build

  # Manually skip kernel compilation
  python3 build_all.py --skip-kernel-build

  # Build and flash to SD card
  python3 build_all.py --flash /dev/sdb

  # Clean build artifacts (keep sources for quick rebuild)
  python3 build_all.py --clean

  # Deep clean: remove all sources (reset to pristine project)
  python3 build_all.py --distclean

Auto-detection behavior:
  By default, the script will detect which components are already built:
  - U-Boot: checks for u-boot.bin or bootloader images
  - Kernel: checks for Image and DTB files
  - Rootfs: checks for rootfs directory with content

  Use --no-auto-detect to force rebuilding all components.
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
        "--skip-rootfs",
        action="store_true",
        help="Skip root filesystem build"
    )
    parser.add_argument(
        "--rootfs-distro",
        choices=["bionic", "focal", "jammy"],
        default="focal",
        help="Ubuntu distribution for rootfs (default: focal)"
    )
    parser.add_argument(
        "--rootfs-type",
        choices=["server", "desktop"],
        default="desktop",
        help="Rootfs type (default: desktop)"
    )
    parser.add_argument(
        "--rootfs-mirror",
        choices=["cn", "official", "default"],
        default="cn",
        help="Ubuntu mirror for rootfs (default: cn)"
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
        help="Clean build artifacts (keep sources)"
    )
    parser.add_argument(
        "--distclean",
        action="store_true",
        help="Deep clean: remove all sources and artifacts (pristine project)"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not provided)"
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Disable auto-detection of already built components (force rebuild)"
    )
    parser.add_argument(
        "--dtb",
        default="rk3399-orangepi-4",
        help="Device tree blob name for boot.img (default: rk3399-orangepi-4)"
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = BuildPipeline(args.project_root)

    # Handle clean/distclean
    if args.clean and args.distclean:
        print_error("Cannot specify both --clean and --distclean")
        return 1
    elif args.clean:
        return pipeline.clean_all()
    elif args.distclean:
        return pipeline.distclean_all()

    # Execute build pipeline
    return pipeline.build_all(
        skip_uboot_build=args.skip_uboot_build,
        skip_kernel_build=args.skip_kernel_build,
        skip_rootfs=args.skip_rootfs,
        skip_download=args.skip_download,
        auto_detect=not args.no_auto_detect,  # Default is True, --no-auto-detect makes it False
        dtb_name=args.dtb,
        flash_device=args.flash,
        rootfs_distro=args.rootfs_distro,
        rootfs_type=args.rootfs_type,
        rootfs_mirror=args.rootfs_mirror
    )


if __name__ == "__main__":
    sys.exit(main())
