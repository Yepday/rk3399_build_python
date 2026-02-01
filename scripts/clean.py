#!/usr/bin/env python3
"""
Clean and distclean functionality for the RK3399 build system.

Provides two cleaning modes:
- clean: Remove build artifacts (build/ directory) but keep sources
- distclean: Remove all generated files and sources, keeping only the pristine project

Usage:
    python3 clean.py                    # Interactive mode (ask what to do)
    python3 clean.py --clean            # Clean build artifacts only
    python3 clean.py --distclean        # Clean everything including sources
    python3 clean.py --dry-run          # Show what would be deleted (no actual deletion)
    python3 clean.py --help             # Show this help message
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple


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
    """Print colored header."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{message:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC} {message}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.BLUE}ℹ{Colors.NC} {message}")


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_directory_size(path: Path) -> int:
    """Calculate total size of directory."""
    total = 0
    if path.exists():
        for item in path.rglob('*'):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, PermissionError):
                    pass
    return total


def list_items_to_delete(items: List[Tuple[Path, str]]) -> Tuple[int, str]:
    """List items that will be deleted and calculate total size.

    Args:
        items: List of (path, description) tuples

    Returns:
        Tuple of (total_size, formatted_message)
    """
    total_size = 0
    message_lines = []

    for path, description in items:
        if path.exists():
            size = get_directory_size(path) if path.is_dir() else path.stat().st_size
            total_size += size
            size_str = format_size(size)
            message_lines.append(f"  • {description:40s} ({size_str})")

    if not message_lines:
        return 0, "No items found to delete"

    message = "\n".join(message_lines)
    return total_size, message


class CleanupManager:
    """Manages cleanup operations."""

    def __init__(self, project_root: Path = None):
        """Initialize cleanup manager.

        Args:
            project_root: Project root directory. If None, auto-detect.
        """
        if project_root is None:
            script_dir = Path(__file__).parent
            project_root = script_dir.parent

        self.project_root = project_root.resolve()
        self.dry_run = False
        self.force = False  # Skip confirmation prompts

    def delete_recursive(self, path: Path, label: str = None) -> bool:
        """Delete a directory recursively.

        Args:
            path: Path to delete
            label: Description label

        Returns:
            True if successful, False otherwise
        """
        if not path.exists():
            return True

        try:
            if path.is_dir():
                if self.dry_run:
                    size = get_directory_size(path)
                    print_info(f"[DRY RUN] Would remove directory: {path} ({format_size(size)})")
                else:
                    size = get_directory_size(path)
                    shutil.rmtree(path)
                    print_success(f"Removed {label or path.name} ({format_size(size)})")
            else:
                if self.dry_run:
                    size = path.stat().st_size
                    print_info(f"[DRY RUN] Would remove file: {path} ({format_size(size)})")
                else:
                    size = path.stat().st_size
                    path.unlink()
                    print_success(f"Removed {label or path.name} ({format_size(size)})")
            return True
        except Exception as e:
            print_error(f"Failed to remove {label or path}: {e}")
            return False

    def clean(self) -> int:
        """Remove build artifacts only (keep sources).

        Clean removes:
        - build/ directory (idbloader.img, uboot.img, kernel Image, rootfs, etc.)
        - components/kernel/modules/ (installed kernel modules)
        - Python cache files (__pycache__/, *.pyc)

        Keep:
        - components/uboot/ (U-Boot source)
        - components/kernel/ (kernel source, excluding modules/)
        - components/toolchain/ (toolchain)
        - components/firmware/ (Rockchip firmware files)
        - configs/ (INI configuration files)

        Returns:
            0 on success, 1 on failure
        """
        print_header("RK3399 Build Cleanup (Keep Sources)")

        # Items to delete for 'clean'
        items_to_delete = [
            (self.project_root / "build" / "boot", "Bootloader artifacts (idbloader.img, uboot.img)"),
            (self.project_root / "build" / "kernel", "Kernel artifacts (Image, dtbs, System.map)"),
            (self.project_root / "build" / "image", "Disk image artifacts"),
            (self.project_root / "build" / "rootfs", "Root filesystem directory"),
            (self.project_root / "build" / "rootfs.img", "Root filesystem image"),
            (self.project_root / "components" / "kernel" / "modules", "Installed kernel modules"),
        ]

        # Add Python cache directories
        for pycache_dir in self.project_root.rglob("__pycache__"):
            items_to_delete.append((pycache_dir, f"Python cache ({pycache_dir.relative_to(self.project_root)})"))

        # Add .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            items_to_delete.append((pyc_file, f"Python bytecode ({pyc_file.relative_to(self.project_root)})"))

        total_size, message = list_items_to_delete(items_to_delete)

        if total_size == 0:
            print_warning("No build artifacts found to clean")
            return 0

        print(f"{Colors.YELLOW}Items to be removed:{Colors.NC}")
        print(message)
        print()
        print_info(f"Total space to be freed: {format_size(total_size)}")
        print()

        if self.dry_run:
            print_info("[DRY RUN MODE] No actual deletion performed")
            return 0

        # Ask for confirmation (unless --force is set)
        if not self.force:
            response = input(f"{Colors.YELLOW}Continue? (yes/no): {Colors.NC}").strip().lower()
            if response != "yes":
                print_warning("Cleanup cancelled")
                return 1

        print()

        # Perform cleanup
        all_success = True
        for path, description in items_to_delete:
            if path.exists():
                if not self.delete_recursive(path, description):
                    all_success = False

        print()
        if all_success:
            print_success("Cleanup completed successfully")
            print_info("Sources are preserved in:")
            print(f"  • components/uboot/")
            print(f"  • components/kernel/")
            print(f"  • components/toolchain/")
            print()
            print_info("To rebuild, run:")
            print(f"  {Colors.BOLD}python3 scripts/build_all.py{Colors.NC}")
            return 0
        else:
            print_warning("Cleanup completed with errors")
            return 1

    def distclean(self) -> int:
        """Remove all build and source files (pristine project).

        Distclean removes:
        - build/ (all build artifacts)
        - components/uboot/ (U-Boot source)
        - components/kernel/ (Linux kernel source)
        - components/toolchain/ (cross-compiler toolchain)
        - Python cache files (__pycache__/, *.pyc)

        Keep:
        - components/firmware/ (Rockchip firmware blobs - required for building)
        - configs/ (INI configuration files - required for building)
        - scripts/ (build scripts)
        - docs/ (documentation)
        - All project metadata files (CLAUDE.md, PROGRESS.md, README.md, etc.)

        Returns:
            0 on success, 1 on failure
        """
        print_header("RK3399 Deep Cleanup (Remove All Sources)")

        print(f"{Colors.YELLOW}This will remove:{Colors.NC}")
        print("  1. All build artifacts (build/)")
        print("  2. Downloaded U-Boot source (components/uboot/)")
        print("  3. Downloaded Linux kernel source (components/kernel/)")
        print("  4. Cross-compiler toolchain (components/toolchain/)")
        print("  5. Python cache files (__pycache__/, *.pyc)")
        print()

        print(f"{Colors.YELLOW}This will KEEP:{Colors.NC}")
        print("  • Rockchip firmware files (components/firmware/)")
        print("  • Build configuration (configs/)")
        print("  • Build scripts (scripts/)")
        print("  • Documentation (docs/)")
        print("  • Project metadata files")
        print()

        # Items to delete for 'distclean'
        items_to_delete = [
            (self.project_root / "build", "All build artifacts"),
            (self.project_root / "components" / "uboot", "U-Boot source code"),
            (self.project_root / "components" / "kernel", "Linux kernel source code"),
            (self.project_root / "components" / "toolchain", "Cross-compiler toolchain"),
        ]

        # Add Python cache directories
        for pycache_dir in self.project_root.rglob("__pycache__"):
            items_to_delete.append((pycache_dir, f"Python cache ({pycache_dir.relative_to(self.project_root)})"))

        # Add .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            items_to_delete.append((pyc_file, f"Python bytecode ({pyc_file.relative_to(self.project_root)})"))

        total_size, message = list_items_to_delete(items_to_delete)

        if total_size == 0:
            print_warning("No files found to delete")
            return 0

        print(f"{Colors.YELLOW}Items to be removed:{Colors.NC}")
        print(message)
        print()
        print_info(f"Total space to be freed: {format_size(total_size)}")
        print()

        if self.dry_run:
            print_info("[DRY RUN MODE] No actual deletion performed")
            return 0

        # Double confirmation for distclean (unless --force is set)
        if not self.force:
            print(f"{Colors.RED}{Colors.BOLD}⚠ This is a deep cleanup operation!{Colors.NC}")
            response1 = input(f"{Colors.YELLOW}Are you sure? Type 'distclean' to continue: {Colors.NC}").strip()
            if response1 != "distclean":
                print_warning("Distclean cancelled")
                return 1

        print()

        # Perform cleanup
        all_success = True
        for path, description in items_to_delete:
            if path.exists():
                if not self.delete_recursive(path, description):
                    all_success = False

        print()
        if all_success:
            print_success("Distclean completed successfully")
            print_info("Project reset to pristine state")
            print()
            print_info("To rebuild from scratch, run:")
            print(f"  {Colors.BOLD}python3 scripts/build_all.py{Colors.NC}")
            return 0
        else:
            print_warning("Distclean completed with errors")
            return 1

    def interactive_menu(self) -> int:
        """Interactive menu for choosing cleanup mode.

        Returns:
            0 on success, 1 on failure
        """
        print_header("RK3399 Project Cleanup")

        print("Choose cleanup mode:")
        print()
        print(f"  {Colors.YELLOW}[1]{Colors.NC} clean      - Remove build artifacts, keep sources")
        print(f"  {Colors.YELLOW}[2]{Colors.NC} distclean  - Remove everything, keep only pristine project")
        print(f"  {Colors.YELLOW}[q]{Colors.NC} quit       - Cancel cleanup")
        print()

        choice = input(f"{Colors.YELLOW}Select option (1/2/q): {Colors.NC}").strip().lower()

        if choice == "1":
            return self.clean()
        elif choice == "2":
            return self.distclean()
        elif choice == "q" or choice == "":
            print_warning("Cleanup cancelled")
            return 1
        else:
            print_error("Invalid choice")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean build artifacts and sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (choose what to clean)
  python3 clean.py

  # Clean build artifacts only (keep sources)
  python3 clean.py --clean

  # Deep clean (remove sources, keep pristine project)
  python3 clean.py --distclean

  # Dry run (show what would be deleted)
  python3 clean.py --clean --dry-run
  python3 clean.py --distclean --dry-run
"""
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build artifacts only (keep sources)"
    )
    parser.add_argument(
        "--distclean",
        action="store_true",
        help="Remove all sources and build artifacts (pristine project)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actual deletion"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation (used internally by build_all.py)"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (auto-detected if not provided)"
    )

    args = parser.parse_args()

    # Create cleanup manager
    manager = CleanupManager(args.project_root)
    manager.dry_run = args.dry_run
    manager.force = args.force

    # Determine action
    if args.clean and args.distclean:
        print_error("Cannot specify both --clean and --distclean")
        return 1
    elif args.clean:
        return manager.clean()
    elif args.distclean:
        return manager.distclean()
    else:
        return manager.interactive_menu()


if __name__ == "__main__":
    sys.exit(main())
