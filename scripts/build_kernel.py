#!/usr/bin/env python3
"""
Linux Kernel Build Script for RK3399

This script automates the process of:
1. Downloading Linux kernel source code from OrangePi GitHub
2. Using the ARM toolchain (downloaded by build_uboot.py)
3. Configuring and compiling the kernel
4. Generating kernel image (Image format for arm64)
5. Compiling device tree blobs (dtb)
6. Optionally compiling kernel modules

Usage:
    python3 build_kernel.py                      # Download and build
    python3 build_kernel.py --skip-download      # Build only (assume source exists)
    python3 build_kernel.py --clean              # Clean build artifacts
    python3 build_kernel.py --config-only        # Only configure, don't compile
    python3 build_kernel.py --no-modules         # Skip kernel modules compilation
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


class KernelBuilder:
    """Linux kernel builder for RK3399."""

    # GitHub repositories
    ORANGEPI_GITHUB = "https://github.com/orangepi-xunlong"
    KERNEL_REPO = f"{ORANGEPI_GITHUB}/OrangePiRK3399_kernel.git"
    KERNEL_BRANCH = "master"

    # Default paths (relative to project root)
    KERNEL_PATH = Path("components/kernel")
    TOOLCHAIN_PATH = Path("components/toolchain")
    BUILD_OUTPUT = Path("build/kernel")

    # Kernel configuration
    ARCH = "arm64"
    CROSS_COMPILE_ARM64 = "aarch64-linux-gnu-"
    KERNEL_DEFCONFIG = "rk3399_linux_defconfig"

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
        self.kernel_dir = self.project_root / self.KERNEL_PATH
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
                print_warning("aarch64-linux-gnu-gcc not in system (will use downloaded)")
        except FileNotFoundError:
            print_warning("aarch64-linux-gnu-gcc not in system (will use downloaded)")

        return all_found

    def download_kernel(self) -> bool:
        """Download kernel source code with retry mechanism.

        Returns:
            True if successful
        """
        self.log_step(2, "Downloading Linux kernel")

        if self.kernel_dir.exists():
            print_warning(f"Kernel directory already exists: {self.kernel_dir}")
            print(f"  Skipping download. Use --clean to remove it first.")
            return True

        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Repository: {self.KERNEL_REPO}")
        print(f"  Branch: {self.KERNEL_BRANCH}")
        print(f"  Destination: {self.kernel_dir}")
        print()

        # Try up to 3 times with retry
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"\n{Colors.YELLOW}Retry attempt {attempt}/{max_retries}...{Colors.NC}")
                # Clean up partial clone on retry
                if self.kernel_dir.exists():
                    import shutil
                    shutil.rmtree(self.kernel_dir)

            start_time = time.time()
            rc, stdout, stderr = self.run_command([
                "git", "clone",
                "--depth=1",
                "--branch", self.KERNEL_BRANCH,
                self.KERNEL_REPO,
                str(self.kernel_dir)
            ], check=False)

            elapsed = time.time() - start_time

            if rc == 0:
                print_success(f"Kernel downloaded successfully ({elapsed:.1f}s)")
                return True
            else:
                if attempt < max_retries:
                    print_error(f"Download failed (attempt {attempt}/{max_retries})")
                    print(f"Error: {stderr}")
                else:
                    print_error(f"Failed to download kernel after {max_retries} attempts")
                    print(f"Error: {stderr}")
                    print()
                    print(f"{Colors.YELLOW}Troubleshooting:{Colors.NC}")
                    print(f"  1. Check network connection")
                    print(f"  2. Try manual clone:")
                    print(f"     git clone --depth=1 {self.KERNEL_REPO} components/kernel")
                    print(f"  3. Then run: python3 scripts/build_all.py --skip-download")

        return False

    def get_toolchain_prefix(self) -> str:
        """Get the cross-compiler prefix path.

        Returns:
            Full path to cross-compiler prefix
        """
        # Check if toolchain in PATH
        try:
            rc, _, _ = self.run_command(
                ["aarch64-linux-gnu-gcc", "--version"],
                check=False
            )
            if rc == 0:
                return self.CROSS_COMPILE_ARM64
        except FileNotFoundError:
            pass

        # Check local Linaro toolchain
        linaro_gcc = self.toolchain_dir / "gcc-linaro-6.3.1-2017.05-x86_64_aarch64-linux-gnu"
        gcc_path = linaro_gcc / "bin" / "aarch64-linux-gnu-gcc"

        if gcc_path.exists():
            return str(linaro_gcc / "bin" / self.CROSS_COMPILE_ARM64)

        # Fallback to system PATH
        return self.CROSS_COMPILE_ARM64

    def configure_kernel(self) -> bool:
        """Configure kernel using defconfig.

        Returns:
            True if successful
        """
        self.log_step(3, "Configuring kernel")

        cross_compile = self.get_toolchain_prefix()

        print(f"  Architecture: {self.ARCH}")
        print(f"  Configuration: {self.KERNEL_DEFCONFIG}")
        print(f"  Cross-compiler: {cross_compile}")
        print()

        # Prepare environment
        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = self.ARCH

        # Run defconfig
        try:
            rc, stdout, stderr = self.run_command(
                ["make", f"{self.KERNEL_DEFCONFIG}"],
                cwd=self.kernel_dir,
                check=False,
                env=env
            )

            if rc == 0:
                print_success("Kernel configured")
                return True
            else:
                print_error(f"Failed to configure kernel")
                print(f"Error: {stderr}")
                return False
        except Exception as e:
            print_error(f"Configuration error: {e}")
            return False

    def compile_kernel(self) -> bool:
        """Compile kernel image.

        Returns:
            True if successful
        """
        self.log_step(4, "Compiling kernel (using {0} cores)".format(self.cores))

        cross_compile = self.get_toolchain_prefix()
        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = self.ARCH

        print(f"  Using {self.cores} cores for parallel build")
        print()

        start_time = time.time()

        try:
            # Compile kernel Image
            rc, stdout, stderr = self.run_command(
                ["make", f"-j{self.cores}", "Image"],
                cwd=self.kernel_dir,
                check=False,
                env=env
            )

            elapsed = time.time() - start_time

            if rc == 0:
                print_success(f"Kernel compiled successfully ({elapsed:.1f}s)")
                return True
            else:
                print_error(f"Failed to compile kernel")
                print(f"Error: {stderr[-500:]}")  # Last 500 chars
                return False
        except Exception as e:
            print_error(f"Compilation error: {e}")
            return False

    def fix_orangepi_makefile(self) -> bool:
        """Fix Makefile to include Orange Pi device tree builds.

        The OrangePi DTB sources are present but the Makefile was not updated
        to compile them. This function adds the necessary rules.

        Returns:
            True if successful or already fixed
        """
        makefile_path = self.kernel_dir / "arch/arm64/boot/dts/rockchip/Makefile"

        if not makefile_path.exists():
            print_error(f"Makefile not found: {makefile_path}")
            return False

        # Read the Makefile
        with open(makefile_path, 'r') as f:
            content = f.read()

        # Check if Orange Pi DTB rules already exist
        if "rk3399-orangepi-4.dtb" in content:
            print_success("Orange Pi DTB rules already in Makefile")
            return True

        # Add Orange Pi DTB rules before rk3399-rock960
        # Find the insertion point
        insertion_marker = "dtb-$(CONFIG_ARCH_ROCKCHIP) += rk3399-rock960-ab.dtb"

        if insertion_marker not in content:
            print_warning("Could not find insertion point in Makefile (DTB compilation may still work)")
            return True

        orangepi_rules = """dtb-$(CONFIG_ARCH_ROCKCHIP) += rk3399-orangepi.dtb
dtb-$(CONFIG_ARCH_ROCKCHIP) += rk3399-orangepi-4.dtb
dtb-$(CONFIG_ARCH_ROCKCHIP) += rk3399-orangepi-rk3399.dtb
"""

        new_content = content.replace(insertion_marker, orangepi_rules + insertion_marker)

        # Write the modified Makefile
        with open(makefile_path, 'w') as f:
            f.write(new_content)

        print_success("Orange Pi DTB rules added to Makefile")
        return True

    def compile_dtbs(self) -> bool:
        """Compile device tree blobs.

        Returns:
            True if successful
        """
        self.log_step(5, "Compiling device tree blobs")

        # Fix Makefile to include Orange Pi DTBs before compiling
        if not self.fix_orangepi_makefile():
            print_warning("Failed to fix Makefile, continuing anyway...")

        cross_compile = self.get_toolchain_prefix()
        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = self.ARCH

        try:
            rc, stdout, stderr = self.run_command(
                ["make", f"-j{self.cores}", "dtbs"],
                cwd=self.kernel_dir,
                check=False,
                env=env
            )

            if rc == 0:
                print_success("Device tree blobs compiled")
                return True
            else:
                print_warning("Device tree compilation had warnings (continuing...)")
                # DTB compilation warnings are usually non-fatal
                return True
        except Exception as e:
            print_warning(f"DTB compilation warning (continuing): {e}")
            return True

    def compile_modules(self) -> bool:
        """Compile kernel modules.

        Returns:
            True if successful
        """
        self.log_step(6, "Compiling kernel modules")

        cross_compile = self.get_toolchain_prefix()
        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = self.ARCH

        try:
            rc, stdout, stderr = self.run_command(
                ["make", f"-j{self.cores}", "modules"],
                cwd=self.kernel_dir,
                check=False,
                env=env
            )

            if rc == 0:
                print_success("Kernel modules compiled")
                return True
            else:
                print_warning("Module compilation had issues (continuing...)")
                return True
        except Exception as e:
            print_warning(f"Module compilation warning (continuing): {e}")
            return True

    def install_modules(self) -> bool:
        """Install kernel modules to components/kernel/modules.

        Returns:
            True if successful
        """
        self.log_step(7, "Installing kernel modules")

        # Module installation path
        modules_install_path = self.project_root / "components" / "kernel" / "modules"

        # Clean old modules if they exist
        if modules_install_path.exists():
            print(f"  Cleaning old modules at {modules_install_path}")
            shutil.rmtree(modules_install_path)

        modules_install_path.mkdir(parents=True, exist_ok=True)

        cross_compile = self.get_toolchain_prefix()
        env = os.environ.copy()
        env["CROSS_COMPILE"] = cross_compile
        env["ARCH"] = self.ARCH

        try:
            rc, stdout, stderr = self.run_command(
                [
                    "make",
                    "modules_install",
                    f"INSTALL_MOD_PATH={modules_install_path}"
                ],
                cwd=self.kernel_dir,
                check=False,
                env=env
            )

            if rc == 0:
                # Check if modules were installed
                modules_dir = modules_install_path / "lib" / "modules"
                if modules_dir.exists():
                    # Count installed modules
                    module_count = sum(1 for _ in modules_dir.rglob("*.ko"))
                    print_success(f"Kernel modules installed ({module_count} modules)")
                    print(f"  Installation path: {modules_install_path}")
                    return True
                else:
                    print_warning("Modules directory not found after installation")
                    return True
            else:
                print_warning("Module installation had issues (continuing...)")
                return True
        except Exception as e:
            print_warning(f"Module installation warning (continuing): {e}")
            return True

    def copy_kernel_image(self) -> bool:
        """Copy compiled kernel image to output directory.

        Returns:
            True if successful
        """
        self.log_step(8, "Copying kernel image to output")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        kernel_image = self.kernel_dir / "arch" / self.ARCH / "boot" / "Image"

        if not kernel_image.exists():
            print_error(f"Kernel image not found at {kernel_image}")
            return False

        output_image = self.output_dir / "Image"

        try:
            shutil.copy2(kernel_image, output_image)
            size_mb = output_image.stat().st_size / (1024 * 1024)
            print_success(f"Kernel image copied ({size_mb:.1f} MB)")
            return True
        except Exception as e:
            print_error(f"Failed to copy kernel image: {e}")
            return False

    def copy_dtbs(self) -> bool:
        """Copy device tree blobs to output directory.

        Returns:
            True if successful
        """
        self.log_step(9, "Copying device tree blobs to output")

        dts_dir = self.kernel_dir / "arch" / self.ARCH / "boot" / "dts"

        if not dts_dir.exists():
            print_warning(f"Device tree directory not found: {dts_dir}")
            return True

        # Create dtb directory
        dtb_output = self.output_dir / "dtbs"
        dtb_output.mkdir(parents=True, exist_ok=True)

        # Copy all .dtb files
        dtb_files = list(dts_dir.glob("**/*.dtb"))

        if not dtb_files:
            print_warning("No device tree blobs found")
            return True

        copied_count = 0
        for dtb_file in dtb_files:
            try:
                dest = dtb_output / dtb_file.name
                shutil.copy2(dtb_file, dest)
                copied_count += 1
            except Exception as e:
                print_warning(f"Failed to copy {dtb_file.name}: {e}")

        print_success(f"Copied {copied_count} device tree blobs")
        return True

    def copy_system_map(self) -> bool:
        """Copy System.map to output directory.

        Returns:
            True if successful
        """
        system_map = self.kernel_dir / "System.map"

        if not system_map.exists():
            print_warning("System.map not found")
            return True

        output_map = self.output_dir / "System.map"

        try:
            shutil.copy2(system_map, output_map)
            size_kb = output_map.stat().st_size / 1024
            print_success(f"System.map copied ({size_kb:.1f} KB)")
            return True
        except Exception as e:
            print_warning(f"Failed to copy System.map: {e}")
            return True

    def clean_build(self) -> bool:
        """Clean build artifacts and downloaded sources.

        Returns:
            True if successful
        """
        self.log_step(0, "Cleaning kernel build artifacts")

        # Remove kernel source directory
        if self.kernel_dir.exists():
            print(f"  Removing {self.kernel_dir}")
            try:
                shutil.rmtree(self.kernel_dir)
                print_success("Kernel source removed")
            except Exception as e:
                print_error(f"Failed to remove kernel source: {e}")
                return False

        # Clean build output
        if self.output_dir.exists():
            print(f"  Cleaning {self.output_dir}")
            try:
                # Keep the directory, but remove contents
                for item in self.output_dir.glob("*"):
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                print_success("Build output cleaned")
            except Exception as e:
                print_warning(f"Partial cleanup: {e}")

        return True

    def build(self, skip_download: bool = False, config_only: bool = False,
              skip_modules: bool = False) -> bool:
        """Execute full build pipeline.

        Args:
            skip_download: Skip downloading kernel source
            config_only: Only configure, don't compile
            skip_modules: Skip kernel modules compilation

        Returns:
            True if successful
        """
        print_header("RK3399 Linux Kernel Build Pipeline")

        if not self.check_dependencies():
            print_error("Missing required dependencies")
            return False

        if not skip_download:
            if not self.download_kernel():
                return False

        if not self.configure_kernel():
            return False

        if config_only:
            print_success("Configuration complete (build skipped)")
            return True

        if not self.compile_kernel():
            return False

        if not self.compile_dtbs():
            return False

        if not skip_modules:
            if not self.compile_modules():
                return False
            if not self.install_modules():
                return False

        if not self.copy_kernel_image():
            return False

        if not self.copy_dtbs():
            return False

        if not self.copy_system_map():
            return False

        print_header("Kernel Build Complete!")
        print(f"Output directory: {self.output_dir}")
        print(f"  ✓ Image")
        print(f"  ✓ dtbs/")
        print(f"  ✓ System.map")
        if not skip_modules:
            modules_path = self.project_root / "components" / "kernel" / "modules"
            if modules_path.exists():
                print(f"  ✓ modules/ (installed to components/kernel/modules)")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build Linux kernel for RK3399",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 build_kernel.py                    # Download and build
  python3 build_kernel.py --skip-download    # Build only
  python3 build_kernel.py --clean            # Clean all
  python3 build_kernel.py --config-only      # Configure only
  python3 build_kernel.py --no-modules       # Skip modules
        """
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading kernel source (assume exists)"
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only configure, don't compile"
    )
    parser.add_argument(
        "--no-modules",
        action="store_true",
        help="Skip kernel modules compilation"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts and sources"
    )

    args = parser.parse_args()

    # Initialize builder
    builder = KernelBuilder()

    # Handle clean operation
    if args.clean:
        if builder.clean_build():
            print_success("Clean operation complete")
            return 0
        else:
            print_error("Clean operation failed")
            return 1

    # Execute build
    if builder.build(
        skip_download=args.skip_download,
        config_only=args.config_only,
        skip_modules=args.no_modules
    ):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
