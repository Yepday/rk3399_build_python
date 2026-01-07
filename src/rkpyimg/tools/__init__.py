"""
Python implementations of Rockchip firmware packing tools.

This module contains:
- loaderimage: Pack u-boot.bin into uboot.img
- boot_merger: Merge DDR init + miniloader into idbloader.img
- trust_merger: Merge BL31 + BL32 into trust.img
"""

from rkpyimg.tools.loaderimage import pack_loader_image
from rkpyimg.tools.boot_merger import BootMerger
from rkpyimg.tools.trust_merger import TrustMerger

__all__ = [
    "pack_loader_image",
    "BootMerger",
    "TrustMerger",
]
