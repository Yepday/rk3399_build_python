"""
GPT partition handling for Rockchip images.

This module provides functionality to create and manipulate GPT
partition tables for Rockchip firmware images.

Rockchip RK3399 Standard Partition Layout:
    Sector     Size     Partition      Content
    ------     ----     ---------      -------
    64         32KB     [idbloader]    DDR init + Miniloader (no partition entry)
    24576      4MB      uboot          U-Boot bootloader
    32768      4MB      trust          ARM Trusted Firmware + OP-TEE
    49152      32MB     boot           Kernel + Device Tree + Initramfs
    376832     ~GB      rootfs         Root filesystem (ext4)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


# Sector size (standard)
SECTOR_SIZE = 512

# Rockchip specific offsets (in sectors)
RK_IDBLOADER_OFFSET = 64
RK_UBOOT_OFFSET = 24576
RK_TRUST_OFFSET = 32768
RK_BOOT_OFFSET = 49152
RK_ROOTFS_OFFSET = 376832


@dataclass
class GPTPartition:
    """
    Represents a GPT partition.

    Attributes:
        name: Partition name (max 36 UTF-16 chars)
        start_sector: Starting sector (LBA)
        end_sector: Ending sector (LBA)
        type_guid: Partition type GUID
        partition_guid: Unique partition GUID
        attributes: Partition attributes
    """

    name: str
    start_sector: int
    end_sector: int
    type_guid: UUID | None = None
    partition_guid: UUID | None = None
    attributes: int = 0

    @property
    def size_bytes(self) -> int:
        """Size in bytes."""
        return (self.end_sector - self.start_sector + 1) * SECTOR_SIZE

    @property
    def size_mb(self) -> float:
        """Size in megabytes."""
        return self.size_bytes / (1024 * 1024)


def create_partition_table(
    image_size_mb: int = 2048,
    boot_size_mb: int = 32,
    include_rootfs: bool = True,
) -> list[GPTPartition]:
    """
    Create standard Rockchip partition table.

    Args:
        image_size_mb: Total image size in MB
        boot_size_mb: Boot partition size in MB
        include_rootfs: Whether to include rootfs partition

    Returns:
        List of GPTPartition objects
    """
    partitions = [
        GPTPartition(
            name="uboot",
            start_sector=RK_UBOOT_OFFSET,
            end_sector=RK_TRUST_OFFSET - 1,
        ),
        GPTPartition(
            name="trust",
            start_sector=RK_TRUST_OFFSET,
            end_sector=RK_BOOT_OFFSET - 1,
        ),
        GPTPartition(
            name="boot",
            start_sector=RK_BOOT_OFFSET,
            end_sector=RK_ROOTFS_OFFSET - 1,
        ),
    ]

    if include_rootfs:
        total_sectors = (image_size_mb * 1024 * 1024) // SECTOR_SIZE
        partitions.append(GPTPartition(
            name="rootfs",
            start_sector=RK_ROOTFS_OFFSET,
            end_sector=total_sectors - 34,  # Leave space for backup GPT
        ))

    return partitions


def write_gpt_header(f: BinaryIO, partitions: list[GPTPartition]) -> None:
    """
    Write GPT header and partition entries.

    Args:
        f: File object opened in binary write mode
        partitions: List of partitions to write
    """
    # TODO: Implement GPT header writing
    raise NotImplementedError(
        "GPT header writing not yet implemented."
    )
