"""
Complete image builder for Rockchip devices.

This module provides a high-level API for building complete
bootable images for Rockchip devices like OrangePi RK3399.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rkpyimg.image.partition import (
    GPTPartition,
    create_partition_table,
    RK_IDBLOADER_OFFSET,
    RK_UBOOT_OFFSET,
    RK_TRUST_OFFSET,
    RK_BOOT_OFFSET,
    RK_ROOTFS_OFFSET,
    SECTOR_SIZE,
)


@dataclass
class ImageBuilder:
    """
    High-level image builder for Rockchip devices.

    This class provides a convenient API for building complete
    bootable images with all required components.

    Attributes:
        board: Board name (e.g., "orangepi-rk3399")
        chip: Chip type (e.g., "RK3399")
        output_dir: Directory for output files

    Example:
        >>> builder = ImageBuilder(board="orangepi-rk3399")
        >>> builder.set_idbloader("idbloader.img")
        >>> builder.set_uboot("uboot.img")
        >>> builder.set_trust("trust.img")
        >>> builder.set_boot("boot.img")
        >>> builder.set_rootfs("rootfs.ext4")
        >>> builder.build("output.img")
    """

    board: str = "orangepi-rk3399"
    chip: str = "RK3399"
    output_dir: Path = field(default_factory=lambda: Path("."))

    # Component paths
    _idbloader: Path | None = None
    _uboot: Path | None = None
    _trust: Path | None = None
    _boot: Path | None = None
    _rootfs: Path | None = None

    def set_idbloader(self, path: str | Path) -> ImageBuilder:
        """Set idbloader.img path."""
        self._idbloader = Path(path)
        return self

    def set_uboot(self, path: str | Path) -> ImageBuilder:
        """Set uboot.img path."""
        self._uboot = Path(path)
        return self

    def set_trust(self, path: str | Path) -> ImageBuilder:
        """Set trust.img path."""
        self._trust = Path(path)
        return self

    def set_boot(self, path: str | Path) -> ImageBuilder:
        """Set boot.img (kernel) path."""
        self._boot = Path(path)
        return self

    def set_rootfs(self, path: str | Path) -> ImageBuilder:
        """Set rootfs path (ext4 image or directory)."""
        self._rootfs = Path(path)
        return self

    def validate(self) -> list[str]:
        """
        Validate all components are set and exist.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if self._idbloader and not self._idbloader.exists():
            errors.append(f"idbloader not found: {self._idbloader}")
        if self._uboot and not self._uboot.exists():
            errors.append(f"uboot not found: {self._uboot}")
        if self._trust and not self._trust.exists():
            errors.append(f"trust not found: {self._trust}")
        if self._boot and not self._boot.exists():
            errors.append(f"boot not found: {self._boot}")
        if self._rootfs and not self._rootfs.exists():
            errors.append(f"rootfs not found: {self._rootfs}")

        return errors

    def build(
        self,
        output: str | Path,
        image_size_mb: int = 2048,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> Path:
        """
        Build the complete image.

        Args:
            output: Output image path
            image_size_mb: Total image size in MB
            progress_callback: Optional callback for progress updates

        Returns:
            Path to created image

        Raises:
            ValueError: If validation fails
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation failed: {errors}")

        output_path = Path(output)

        # TODO: Implement image building
        # Steps:
        # 1. Create empty image file of specified size
        # 2. Write GPT partition table
        # 3. Write idbloader at sector 64
        # 4. Write uboot at uboot partition
        # 5. Write trust at trust partition
        # 6. Write boot at boot partition
        # 7. Write rootfs at rootfs partition

        raise NotImplementedError(
            "Image building not yet implemented."
        )

    def info(self) -> str:
        """Get summary of configured components."""
        lines = [
            f"Board: {self.board}",
            f"Chip: {self.chip}",
            f"idbloader: {self._idbloader or '(not set)'}",
            f"uboot: {self._uboot or '(not set)'}",
            f"trust: {self._trust or '(not set)'}",
            f"boot: {self._boot or '(not set)'}",
            f"rootfs: {self._rootfs or '(not set)'}",
        ]
        return "\n".join(lines)
