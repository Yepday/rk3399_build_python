"""
rkpyimg - Rockchip firmware packing tools in pure Python

This package provides Python implementations of Rockchip's proprietary
firmware packing tools (boot_merger, trust_merger, loaderimage).
"""

__version__ = "0.1.0"

from rkpyimg.core.header import RKHeader
from rkpyimg.core.ini_parser import RKBootConfig, RKTrustConfig

__all__ = [
    "__version__",
    "RKHeader",
    "RKBootConfig",
    "RKTrustConfig",
]
