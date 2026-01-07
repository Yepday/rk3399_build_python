"""
Tests for INI configuration parsing.
"""

import pytest
from pathlib import Path
import tempfile

from rkpyimg.core.ini_parser import RKBootConfig, RKTrustConfig


class TestRKBootConfig:
    """Tests for RKBootConfig class."""

    def test_parse_boot_ini(self, tmp_path):
        """Test parsing RKBOOT INI file."""
        ini_content = """
[CHIP_NAME]
NAME=RK330C

[VERSION]
MAJOR=2
MINOR=58

[CODE471_OPTION]
NUM=1
Path1=bin/rk33/rk3399_ddr_800MHz_v1.25.bin

[CODE472_OPTION]
NUM=1
Path1=bin/rk33/rk3399_miniloader_v1.26.bin

[OUTPUT]
PATH=rk3399_loader_v1.25.126.bin
"""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(ini_content)

        config = RKBootConfig.from_file(ini_file)

        assert config.chip_name == "RK330C"
        assert config.version == (2, 58)
        assert len(config.ddr_bins) == 1
        assert len(config.loader_bins) == 1
        assert config.output_path == Path("rk3399_loader_v1.25.126.bin")


class TestRKTrustConfig:
    """Tests for RKTrustConfig class."""

    def test_parse_trust_ini(self, tmp_path):
        """Test parsing RKTRUST INI file."""
        ini_content = """
[VERSION]
MAJOR=1
MINOR=0

[BL31_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl31_v1.35.elf
ADDR=0x10000

[BL32_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl32_v2.01.bin
ADDR=0x8400000

[OUTPUT]
PATH=trust.img
"""
        ini_file = tmp_path / "test.ini"
        ini_file.write_text(ini_content)

        config = RKTrustConfig.from_file(ini_file)

        assert config.version == (1, 0)
        assert config.bl31 is not None
        assert config.bl31.address == 0x10000
        assert config.bl32 is not None
        assert config.bl32.address == 0x8400000
        assert config.output_path == Path("trust.img")
