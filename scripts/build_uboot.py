#!/usr/bin/env python3
"""
U-Boot Build Script for RK3399

This script automates the process of:
1. Downloading U-Boot source code from OrangePi GitHub
2. Downloading the ARM toolchain if needed
3. Configuring and compiling U-Boot
4. Generating uboot.bin

Usage:
    python3 build_uboot.py                      # Download and build
    python3 build_uboot.py --skip-download      # Build only (assume source exists)
    python3 build_uboot.py --clean              # Clean build artifacts
    python3 build_uboot.py --config-only        # Only configure, don't compile
"""

import argparse
import sys
import shutil
import subprocess
import os
from pathlib import Path
from typing import Optional, Tuple
import time


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(message: str) -> None:
    """Print colored header message."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{message:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_step(step: int, message: str) -> None:
    """Print step message with number."""
    print(f"{Colors.BLUE}[{step}]{Colors.NC} {message}")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")


class UBootBuilder:
    """U-Boot builder for RK3399."""

    # GitHub repositories
    ORANGEPI_GITHUB = "https://github.com/orangepi-xunlong"
    UBOOT_REPO = f"{ORANGEPI_GITHUB}/OrangePiRK3399_uboot.git"
    UBOOT_BRANCH = "master"
    TOOLCHAIN_REPO = f"{ORANGEPI_GITHUB}/toolchain.git"
    TOOLCHAIN_BRANCH = "aarch64-linux-gnu-6.3"

    # Default paths (relative to project root)
    UBOOT_PATH = Path("components/uboot")
    TOOLCHAIN_PATH = Path("components/toolchain")
    BUILD_OUTPUT = Path("build/boot")

    # Toolchain configuration
    CROSS_COMPILE_ARM64 = "aarch64-linux-gnu-"

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize builder.

        Args:
            project_root: Project root directory. If None, auto-detect.
        """
        if project_root is None:
            # Auto-detect from script location
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

        self.project_root = project_root.resolve()
        self.uboot_dir = self.project_root / self.UBOOT_PATH
        self.toolchain_dir = self.project_root / self.TOOLCHAIN_PATH
        self.output_dir = self.project_root / self.BUILD_OUTPUT
        self.cores = os.cpu_count() or 4

    def log_step(self, step: int, message: str) -> None:
        """Log a build step."""
        print_step(step, message)

    def run_command(self, cmd: list, cwd: Optional[Path] = None,
                   check: bool = True, env: Optional[dict] = None) -> Tuple[int, str, str]:
        """Run a shell command.

        Args:
            cmd: Command as list of strings
            cwd: Working directory for command
            check: Raise exception on error
            env: Environment variables (None = inherit from parent)

        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=check,
                env=env
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            if check:
                raise
            return e.returncode, e.stdout, e.stderr

    def check_dependencies(self) -> bool:
        """Check if required tools are available.

        Returns:
            True if all dependencies are available
        """
        self.log_step(1, "Checking dependencies")

        # Only check essential build tools (not cross-compiler, as we'll download it)
        dependencies = [
            ("git", "git --version"),
            ("make", "make --version"),
            ("gcc", "gcc --version"),
        ]

        all_found = True
        for tool_name, check_cmd in dependencies:
            try:
                rc, _, _ = self.run_command(check_cmd.split(), check=False)
                if rc == 0:
                    print_success(f"{tool_name} found")
                else:
                    print_error(f"{tool_name} not found")
                    all_found = False
            except FileNotFoundError:
                print_error(f"{tool_name} not found")
                all_found = False

        # Check for cross-compiler separately (optional)
        try:
            rc, _, _ = self.run_command(
                ["aarch64-linux-gnu-gcc", "--version"],
                check=False
            )
            if rc == 0:
                print_success("aarch64-linux-gnu-gcc found in system")
            else:
                print_warning("aarch64-linux-gnu-gcc not in system (will download)")
        except FileNotFoundError:
            print_warning("aarch64-linux-gnu-gcc not in system (will download)")

        return all_found

    def download_uboot(self) -> bool:
        """Download U-Boot source code with retry mechanism.

        Returns:
            True if successful
        """
        self.log_step(2, f"Downloading U-Boot from {self.UBOOT_REPO}")

        if self.uboot_dir.exists():
            print_warning(f"U-Boot directory already exists: {self.uboot_dir}")
            print(f"  Skipping download. Use --clean to remove it first.")
            return True

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Repository: {self.UBOOT_REPO}")
        print(f"  Branch: {self.UBOOT_BRANCH}")
        print(f"  Destination: {self.uboot_dir}")
        print()

        # Try up to 3 times with retry
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n{Colors.YELLOW}Retry attempt {attempt}/{max_retries}...{Colors.NC}")
                # Clean up partial clone on retry
                if self.uboot_dir.exists():
                    import shutil
                    shutil.rmtree(self.uboot_dir)

            start_time = time.time()
            rc, stdout, stderr = self.run_command([
                "git", "clone",
                "--depth=1",
                "--branch", self.UBOOT_BRANCH,
                self.UBOOT_REPO,
                str(self.uboot_dir)
            ], check=False)

            elapsed = time.time() - start_time

            if rc == 0:
                print_success(f"U-Boot downloaded successfully ({elapsed:.1f}s)")
                return True
            else:
                if attempt < max_retries:
                    print_error(f"Download failed (attempt {attempt}/{max_retries})")
                    print(f"Error: {stderr}")
                else:
                    print_error(f"Failed to download U-Boot after {max_retries} attempts")
                    print(f"Error: {stderr}")
                    print()
                    print(f"{Colors.YELLOW}Troubleshooting:{Colors.NC}")
                    print(f"  1. Check network connection")
                    print(f"  2. Try manual clone:")
                    print(f"     git clone --depth=1 {self.UBOOT_REPO} components/uboot")
                    print(f"  3. Then run: python3 scripts/build_all.py --skip-download")

        return False

    def download_toolchain(self) -> bool:
        """Download ARM toolchain if needed.

        Returns:
            True if successful or already exists
        """
        self.log_step(3, "Checking toolchain")

        # Check if toolchain already in PATH
        try:
            rc, _, _ = self.run_command(
                ["aarch64-linux-gnu-gcc", "--version"],
                check=False
            )
            if rc == 0:
                print_success("Toolchain found in system PATH")
                return True
        except FileNotFoundError:
            pass  # Not in PATH, continue checking local

        # Check if local toolchain exists (Linaro GCC 6.3.1)
        linaro_gcc = self.toolchain_dir / "gcc-linaro-6.3.1-2017.05-x86_64_aarch64-linux-gnu"
        gcc_path = linaro_gcc / "bin" / "aarch64-linux-gnu-gcc"

        if gcc_path.exists():
            print_success(f"Local Linaro toolchain found at {linaro_gcc}")
            # Verify version
            try:
                rc, stdout, _ = self.run_command(
                    [str(gcc_path), "--version"],
                    check=False
                )
                if rc == 0 and "6.3.1" in stdout:
                    print_success("Linaro GCC 6.3.1 verified")
            except Exception:
                pass
            return True

        print_warning("Toolchain not found, downloading Linaro GCC 6.3.1...")
        print(f"  Repository: {self.TOOLCHAIN_REPO}")
        print(f"  Branch: {self.TOOLCHAIN_BRANCH}")
        print(f"  Destination: {self.toolchain_dir}")
        print()

        self.toolchain_dir.parent.mkdir(parents=True, exist_ok=True)

        # Try up to 3 times with retry
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n{Colors.YELLOW}Retry attempt {attempt}/{max_retries}...{Colors.NC}")
                # Clean up partial clone on retry
                if self.toolchain_dir.exists():
                    import shutil
                    shutil.rmtree(self.toolchain_dir)

            start_time = time.time()
            rc, stdout, stderr = self.run_command([
                "git", "clone",
                "--depth=1",
                "--branch", self.TOOLCHAIN_BRANCH,
                self.TOOLCHAIN_REPO,
                str(self.toolchain_dir)
            ], check=False)

            elapsed = time.time() - start_time

            if rc == 0:
                # Verify the download
                if gcc_path.exists():
                    print_success(f"Linaro GCC 6.3.1 downloaded successfully ({elapsed:.1f}s)")
                    # Make executables
                    import stat
                    for exe in (linaro_gcc / "bin").glob("*"):
                        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
                    return True
                else:
                    print_error("Download succeeded but toolchain structure unexpected")
                    return False
            else:
                if attempt < max_retries:
                    print_error(f"Download failed (attempt {attempt}/{max_retries})")
                    print(f"Error: {stderr}")
                else:
                    print_error(f"Failed to download toolchain after {max_retries} attempts")
                    print(f"Error: {stderr}")
                    print()
                    print(f"{Colors.YELLOW}Alternatives:{Colors.NC}")
                    print(f"  1. Install system toolchain: sudo apt-get install gcc-aarch64-linux-gnu")
                    print(f"  2. Manual download: git clone --depth=1 {self.TOOLCHAIN_REPO} components/toolchain")

        return False

    def get_toolchain_prefix(self) -> str:
        """Get the toolchain prefix for CROSS_COMPILE.

        Returns:
            Toolchain prefix string
        """
        # Check local toolchain first (Linaro GCC 6.3.1 structure)
        linaro_gcc = self.toolchain_dir / "gcc-linaro-6.3.1-2017.05-x86_64_aarch64-linux-gnu"
        gcc_path = linaro_gcc / "bin" / f"{self.CROSS_COMPILE_ARM64}gcc"

        if gcc_path.exists():
            toolchain_bin = linaro_gcc / "bin"
            return str(toolchain_bin / self.CROSS_COMPILE_ARM64)

        # Fall back to system toolchain
        return self.CROSS_COMPILE_ARM64

    def configure_uboot(self) -> bool:
        """Configure U-Boot for RK3399.

        Returns:
            True if successful
        """
        self.log_step(4, "Configuring U-Boot for RK3399")

        # Set toolchain
        cross_compile = self.get_toolchain_prefix()

        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = "arm64"

        print(f"  CROSS_COMPILE: {cross_compile}")
        print()

        # Run make defconfig
        rc, stdout, stderr = self.run_command(
            ["make", "evb-rk3399_defconfig"],
            cwd=self.uboot_dir,
            check=False,
            env=env
        )

        if rc == 0:
            print_success("U-Boot configured successfully")
            return True
        else:
            print_error("Failed to configure U-Boot")
            print(f"Error: {stderr}")
            return False

    def build_uboot(self) -> bool:
        """Build U-Boot.

        Returns:
            True if successful
        """
        self.log_step(5, f"Building U-Boot (using {self.cores} cores)")

        # Set toolchain
        cross_compile = self.get_toolchain_prefix()

        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = "arm64"

        print(f"  CROSS_COMPILE: {cross_compile}")
        print(f"  Build directory: {self.uboot_dir}")
        print()

        # Run make
        start_time = time.time()

        # We need to run this in a way that captures output
        try:
            result = subprocess.run(
                ["make", "-j", str(self.cores)],
                cwd=self.uboot_dir,
                env=env,
                capture_output=False,  # Show output directly
                text=True
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                print()
                print_success(f"U-Boot built successfully ({elapsed:.1f}s)")
                return True
            else:
                print()
                print_error("Build failed")
                return False
        except Exception as e:
            print_error(f"Build error: {e}")
            return False

    def extract_uboot_bin(self) -> bool:
        """Extract u-boot.bin from build output.

        Returns:
            True if successful
        """
        self.log_step(6, "Extracting u-boot.bin")

        # Find u-boot.bin in build directory
        uboot_bin_src = self.uboot_dir / "u-boot.bin"

        if not uboot_bin_src.exists():
            print_error(f"u-boot.bin not found at {uboot_bin_src}")
            return False

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy to output directory
        uboot_bin_dst = self.output_dir / "u-boot.bin"
        shutil.copy2(uboot_bin_src, uboot_bin_dst)

        size_kb = uboot_bin_dst.stat().st_size / 1024
        print_success(f"u-boot.bin copied to {uboot_bin_dst}")
        print(f"  Size: {size_kb:.1f} KB")

        return True

    def clean(self) -> None:
        """Clean build artifacts."""
        print_header("Cleaning")

        if self.uboot_dir.exists():
            print(f"Removing {self.uboot_dir}...")
            shutil.rmtree(self.uboot_dir)
            print_success("U-Boot source removed")

        if self.toolchain_dir.exists():
            print(f"Removing {self.toolchain_dir}...")
            shutil.rmtree(self.toolchain_dir)
            print_success("Toolchain removed")

        # Clean build artifacts but keep existing images
        if self.uboot_dir.exists():
            rc, _, _ = self.run_command(
                ["make", "distclean"],
                cwd=self.uboot_dir,
                check=False
            )
            if rc == 0:
                print_success("U-Boot build artifacts cleaned")

    def build(self, skip_download: bool = False, config_only: bool = False) -> bool:
        """Full build process.

        Args:
            skip_download: Skip downloading sources
            config_only: Only configure, don't build

        Returns:
            True if successful
        """
        print_header("Rockchip RK3399 U-Boot Builder")

        # Check dependencies
        if not self.check_dependencies():
            print_warning("Some dependencies not found. Build may fail.")
            print()

        # Download sources
        if not skip_download:
            if not self.download_uboot():
                return False
            if not self.download_toolchain():
                print_warning("Toolchain download failed, will try system toolchain")
        else:
            if not self.uboot_dir.exists():
                print_error(f"U-Boot source not found at {self.uboot_dir}")
                return False
            print_success("U-Boot source already exists, skipping download")

        print()

        # Configure
        if not self.configure_uboot():
            return False

        print()

        # Build (unless config_only)
        if not config_only:
            if not self.build_uboot():
                return False

            print()

            # Extract output
            if not self.extract_uboot_bin():
                return False

            print()
            print_header("Build Complete!")
            print(f"U-Boot binary: {self.output_dir}/u-boot.bin")
            print(f"Next steps:")
            print(f"  1. Run: python3 scripts/build_bootloader.py")
            print(f"  2. This will generate idbloader.img and uboot.img")
            print(f"  3. Flash to SD card using: sudo ./scripts/flash_bootloader.sh")
            print()
        else:
            print_header("Configuration Complete!")
            print(f"U-Boot configured. Ready to build.")
            print(f"Next steps:")
            print(f"  1. Run: make -j{self.cores} in {self.uboot_dir}")
            print(f"  2. Or use: python3 build_uboot.py --skip-download")
            print()

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build U-Boot for RK3399",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full build with download
  python3 build_uboot.py

  # Build without downloading (if sources already exist)
  python3 build_uboot.py --skip-download

  # Clean and rebuild
  python3 build_uboot.py --clean && python3 build_uboot.py

  # Configure only (prepare for manual build)
  python3 build_uboot.py --config-only
"""
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading sources (assume they exist)"
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only configure, don't compile"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts and exit"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not provided)"
    )

    args = parser.parse_args()

    # Create builder
    builder = UBootBuilder(args.project_root)

    # Handle clean
    if args.clean:
        builder.clean()
        return 0

    # Perform build
    success = builder.build(
        skip_download=args.skip_download,
        config_only=args.config_only
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
