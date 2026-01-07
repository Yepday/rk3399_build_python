# rkpyimg

> 纯 Python 实现的 Rockchip 固件打包工具

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**首个 Python 实现**的 Rockchip 官方固件打包工具（`boot_merger`、`trust_merger`、`loaderimage`）。

## 为什么做这个项目？

Rockchip 官方工具的问题：
- C 语言二进制文件，缺乏文档
- 难以集成到现代 CI/CD 流程
- 跨平台支持差
- 难以理解和修改

**rkpyimg** 提供：
- 纯 Python 3.10+ 实现
- 完整类型注解和现代 API
- 跨平台支持（Windows/Linux/macOS）
- 详细的二进制格式文档
- 易于集成到构建系统

## 支持的芯片

| 芯片 | 状态 | 适用设备 |
|------|------|----------|
| RK3399 | 开发中 | Orange Pi RK3399, Firefly, NanoPC-T4 |
| RK3588/RK3588S | 计划中 | Orange Pi 5, Rock 5B |
| RK3568/RK3566 | 计划中 | Quartz64, ROC-RK3568-PC |
| RK3328 | 计划中 | Rock64, Renegade |
| RK3308 | 计划中 | Rock Pi S |

## 安装

```bash
# 从 PyPI 安装（即将上线）
pip install rkpyimg

# 从源码安装
git clone https://github.com/yourusername/rkpyimg.git
cd rkpyimg
pip install -e ".[dev]"
```

## 快速开始

### 命令行

```bash
# 查看固件镜像信息
rkpyimg inspect uboot.img

# 将 u-boot.bin 打包为 uboot.img
rkpyimg pack -i u-boot.bin -o uboot.img -t uboot -c RK3399

# 使用 INI 配置合并二进制文件
rkpyimg merge -i RKBOOT/RK3399MINIALL.ini -t boot -o idbloader.img

# 构建完整镜像
rkpyimg build --board orangepi-rk3399 \
    --idbloader idbloader.img \
    --uboot uboot.img \
    --trust trust.img \
    --boot boot.img \
    --rootfs rootfs.ext4 \
    -o output.img
```

### Python API

```python
from rkpyimg import RKHeader
from rkpyimg.tools import BootMerger, TrustMerger, pack_loader_image
from rkpyimg.image import ImageBuilder

# 解析 RK 头部
header = RKHeader.from_file("uboot.img")
print(f"芯片: {header.chip}, 加载地址: 0x{header.load_addr:08X}")

# 打包 u-boot.bin
pack_loader_image("u-boot.bin", "uboot.img", chip="RK3399")

# 合并 boot loader
merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
merger.pack("idbloader.img")

# 合并 trust 镜像
trust = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")
trust.pack("trust.img")

# 构建完整镜像
builder = ImageBuilder(board="orangepi-rk3399")
builder.set_idbloader("idbloader.img")
builder.set_uboot("uboot.img")
builder.set_trust("trust.img")
builder.set_boot("boot.img")
builder.set_rootfs("rootfs.ext4")
builder.build("output.img", image_size_mb=2048)
```

## 文档

- [RK Header 格式](docs/rk_header_format.md) - 二进制头部结构
- [INI 文件格式](docs/ini_file_format.md) - RKBOOT/RKTRUST 配置说明
- [打包原理](docs/packing_theory.md) - 固件打包工作原理
- [API 参考](docs/api.md) - Python API 文档

## 镜像布局

Rockchip RK3399 标准分区布局：

```
扇区       大小     分区           内容
------     ----     ---------      -------
64         32KB     [idbloader]    DDR 初始化 + Miniloader
24576      4MB      uboot          U-Boot 引导程序
32768      4MB      trust          ARM Trusted Firmware + OP-TEE
49152      32MB     boot           内核 + 设备树 + Initramfs
376832     ~GB      rootfs         根文件系统 (ext4)
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 类型检查
mypy src/

# 代码检查和格式化
ruff check src/ tests/
ruff format src/ tests/
```

## 参与贡献

欢迎贡献代码！

### 需要帮助的方向：
- [ ] 完善 C 源码分析的 header 解析
- [ ] 实现 boot_merger 打包逻辑
- [ ] 实现 trust_merger 打包逻辑
- [ ] 添加更多 Rockchip 芯片支持
- [ ] 编写完整测试
- [ ] 完善文档

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

## 致谢

- [Rockchip](https://www.rock-chips.com/) - 原始 C 工具
- [OrangePi](http://www.orangepi.org/) - RK3399 参考实现
- [Armbian](https://www.armbian.com/) 社区 - 文档贡献

## 相关项目

- [LinuxBootImageFileGenerator](https://github.com/robseb/LinuxBootImageFileGenerator) - 通用嵌入式 Linux 镜像构建器
- [pyUBoot](https://github.com/molejar/pyUBoot) - U-Boot 镜像操作工具
- [diskimage-builder](https://github.com/openstack/diskimage-builder) - OpenStack 镜像构建工具
