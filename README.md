# RK3399 完整构建系统

> 一键构建 Rockchip RK3399 完整固件（U-Boot + Kernel + Ubuntu Rootfs）

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

用 Python 实现的 RK3399 自动化构建系统，支持从源码到完整固件的一键构建。内置纯 Python 实现的 Rockchip 固件打包工具（`boot_merger`、`trust_merger`、`loaderimage`），无需官方 C 工具。

## 目标设备

- Orange Pi RK3399
- Orange Pi 4
- 其他 RK3399 开发板

## 核心功能

- ✅ **一键构建** - 全自动构建 U-Boot、Kernel、Rootfs
- ✅ **桌面环境** - 支持 XFCE 桌面或最小系统
- ✅ **Device Tree 自动修复** - 自动修复 OrangePi DTS 编译问题
- ✅ **智能清理** - 保留源码或完全重置
- ✅ **纯 Python 工具链** - 无需官方 C 编译工具

## 快速开始

### 一键构建全部组件

```bash
# 完整构建（U-Boot + Kernel + Rootfs with XFCE）
python3 scripts/build_all.py

# 跳过 rootfs 构建（仅 bootloader + kernel）
python3 scripts/build_all.py --skip-rootfs

# 构建最小系统（无桌面环境）
python3 scripts/build_all.py --minimal
```

构建完成后，`build/` 目录包含：
- `idbloader.img` - DDR 初始化 + Miniloader
- `uboot.img` - U-Boot bootloader
- `trust.img` - ARM Trusted Firmware
- `boot.img` - Kernel + Device Tree + Ramdisk
- `rootfs.img` - Ubuntu 根文件系统

### 烧录到设备

```bash
# 烧录 bootloader 到 eMMC/SD 卡
bash scripts/flash_bootloader.sh

# 或手动烧录
sudo dd if=build/idbloader.img of=/dev/sdX seek=64 conv=notrunc
sudo dd if=build/uboot.img of=/dev/sdX seek=16384 conv=notrunc
sudo dd if=build/trust.img of=/dev/sdX seek=24576 conv=notrunc
sudo dd if=build/boot.img of=/dev/sdX seek=32768 conv=notrunc
```

## 分步构建指南

### 1. 构建 U-Boot

```bash
python3 scripts/build_uboot.py
```

自动执行：
1. 下载 U-Boot 源码（如果不存在）
2. 下载 gcc-linaro 工具链
3. 编译 U-Boot（rk3399_defconfig）
4. 打包生成 `idbloader.img`、`uboot.img`、`trust.img`

生成文件位于 `build/` 目录。

### 2. 构建 Linux Kernel

```bash
python3 scripts/build_kernel.py
```

自动执行：
1. 下载 Linux 内核源码（如果不存在）
2. 下载 gcc-linaro 工具链
3. **自动修复 OrangePi Device Tree 编译问题**
4. 编译内核和设备树（rockchip_linux_defconfig）
5. 生成 `boot.img`（包含 kernel、dtb、ramdisk）

支持的设备树：
- `rk3399-orangepi.dtb`
- `rk3399-orangepi-4.dtb`
- `rk3399-orangepi-rk3399.dtb`

### 3. 构建 Ubuntu Rootfs

```bash
# XFCE 桌面环境（默认）
python3 scripts/build_rootfs.py

# 最小系统（无桌面）
python3 scripts/build_rootfs.py --minimal
```

XFCE 桌面版包含：
- Ubuntu 20.04 Base
- XFCE 桌面环境
- 中文字体和输入法（fcitx）
- 常用应用（Firefox、文件管理器等）
- 网络管理工具

最小系统版包含：
- Ubuntu 20.04 Base
- 基础命令行工具
- 网络工具

**注意**：需要 root 权限（使用 debootstrap 和 chroot）。

### 4. 生成 boot.img

```bash
# 使用默认设备树（rk3399-orangepi-4）
bash scripts/make_bootimg.sh

# 指定设备树
bash scripts/make_bootimg.sh rk3399-orangepi
bash scripts/make_bootimg.sh rk3399-orangepi-4
bash scripts/make_bootimg.sh rk3399-orangepi-rk3399
```

打包内容：
- Linux 内核镜像
- 指定的设备树（.dtb）
- Initramfs（如果存在）

## 清理功能

```bash
# 清理编译产物，保留源码（约 54MB）
python3 scripts/clean.py --clean

# 深度清理，删除所有源码和工具链（约 6.2GB）
python3 scripts/clean.py --distclean

# 预览删除内容，不实际删除
python3 scripts/clean.py --dry-run
```

清理级别：
- `--clean`: 删除 `build/` 目录
- `--distclean`: 删除源码（u-boot/、linux/、toolchain/、rootfs/）

## 项目结构

```
rk3399_build_python/
├── scripts/                    # 构建脚本
│   ├── build_all.py            # 一键构建脚本
│   ├── build_uboot.py          # U-Boot 构建
│   ├── build_kernel.py         # 内核构建（含 DTS 修复）
│   ├── build_rootfs.py         # Rootfs 构建
│   ├── clean.py                # 清理脚本
│   ├── make_bootimg.sh         # boot.img 生成
│   └── flash_bootloader.sh     # Bootloader 烧录
├── src/rkpyimg/                # Python 固件打包工具
│   ├── tools/
│   │   ├── boot_merger.py      # DDR + Miniloader 合并
│   │   ├── trust_merger.py     # BL31 + BL32 合并
│   │   └── loaderimage.py      # U-Boot 镜像打包
│   └── core/                   # 核心库（INI 解析、ELF 处理等）
├── RKBOOT/                     # U-Boot 配置文件
│   └── RK3399MINIALL.ini
├── RKTRUST/                    # Trust 镜像配置
│   └── RK3399TRUST.ini
├── bin/rk33/                   # Rockchip 固件
│   ├── rk3399_ddr_800MHz_v1.25.bin
│   ├── rk3399_miniloader_v1.26.bin
│   ├── rk3399_bl31_v1.35.elf
│   └── rk3399_bl32_v2.01.bin
├── build/                      # 构建输出目录（自动生成）
└── docs/                       # 文档
```

## 技术亮点

### Device Tree 自动修复

OrangePi 的设备树源文件（.dts）存在但 Makefile 中缺少编译规则，`build_kernel.py` 会自动检测并修复：

```bash
# 自动检测 arch/arm64/boot/dts/rockchip/*.dts
# 自动添加缺失的编译规则到 Makefile
# 幂等性设计，多次运行安全
```

### 纯 Python 打包工具

本项目实现了 Rockchip 官方 C 工具的完整功能：

| 功能 | 官方工具 | rkpyimg | 兼容性 |
|------|----------|---------|--------|
| DDR + Miniloader 合并 | boot_merger (C) | boot_merger.py | ✅ 字节级一致 |
| BL31 + BL32 合并 | trust_merger (C) | trust_merger.py | ✅ 字节级一致 |
| U-Boot 镜像打包 | loaderimage (C) | loaderimage.py | ✅ 字节级一致 |

优势：
- 跨平台支持（Windows/Linux/macOS）
- 完整类型注解和现代 API
- 易于集成到 CI/CD 流程
- 详细的二进制格式文档

## 镜像布局

Rockchip RK3399 标准分区布局：

```
扇区        偏移量      大小      分区           内容
------      -------     -----     ---------      -------
64          32KB        4MB       idbloader      DDR 初始化 + Miniloader
16384       8MB         4MB       uboot          U-Boot 引导程序
24576       12MB        4MB       trust          ARM Trusted Firmware + OP-TEE
32768       16MB        32MB      boot           内核 + 设备树 + Initramfs
98304       48MB        ...       rootfs         根文件系统 (ext4)
```

## 高级用法

### rkpyimg 命令行工具

除了集成在构建脚本中，rkpyimg 也可以独立使用：

```bash
# 安装 rkpyimg
pip install -e .

# 打包 idbloader.img
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini -o idbloader.img

# 打包 trust.img
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini -o trust.img

# 打包 uboot.img
rkpyimg loaderimage pack u-boot.bin uboot.img 0x200000

# 查看镜像信息
rkpyimg loaderimage info uboot.img

# 解包镜像
rkpyimg boot-merger unpack idbloader.img -o output_dir
rkpyimg trust-merger unpack trust.img -o output_dir
```

### Python API

```python
from rkpyimg.tools.boot_merger import BootMerger
from rkpyimg.tools.trust_merger import TrustMerger
from rkpyimg.tools.loaderimage import pack_loader_image

# 打包 idbloader
merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")
merger.pack("idbloader.img")

# 打包 trust
trust = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")
trust.pack("trust.img")

# 打包 uboot
pack_loader_image("u-boot.bin", "uboot.img", load_addr=0x200000)
```

详细 API 文档请参考 `docs/` 目录。

### 自定义配置

修改 INI 配置文件以使用不同的固件版本：

```ini
# RKBOOT/RK3399MINIALL.ini
[CODE471_OPTION]
NUM=1
Path1=bin/rk33/rk3399_ddr_800MHz_v1.25.bin  # DDR 固件

[CODE472_OPTION]
NUM=1
Path1=bin/rk33/rk3399_miniloader_v1.26.bin  # Miniloader 固件
```

```ini
# RKTRUST/RK3399TRUST.ini
[BL31_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl31_v1.35.elf         # ARM Trusted Firmware
ADDR=0x10000

[BL32_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl32_v2.01.bin         # OP-TEE Secure OS
ADDR=0x8400000
```

## 常见问题

### Q: 如何获取 Rockchip 固件文件？

A: 固件文件已包含在 `bin/rk33/` 目录中。如需更新，可从以下来源获取：
- [rkbin](https://github.com/rockchip-linux/rkbin) - Rockchip 官方仓库
- [Armbian 构建脚本](https://github.com/armbian/build)
- OrangePi 官方 SDK

### Q: 为什么需要 root 权限构建 rootfs？

A: Ubuntu rootfs 构建使用 `debootstrap` 和 `chroot`，需要 root 权限创建系统镜像。可以使用 `--skip-rootfs` 跳过此步骤。

### Q: Device Tree 自动修复是如何工作的？

A: `build_kernel.py` 会检查 `arch/arm64/boot/dts/rockchip/` 中的 `.dts` 文件，如果发现 OrangePi 相关文件但 Makefile 中缺少编译规则，会自动添加。此修复具有幂等性，多次运行安全。

### Q: 生成的镜像可以在哪些设备上使用？

A: 本项目针对 RK3399 芯片，已在 Orange Pi RK3399 和 Orange Pi 4 上测试通过。其他 RK3399 开发板理论上也可使用，但可能需要调整设备树。

### Q: 如何验证生成的镜像？

A: 可以使用以下命令验证：

```bash
# 查看镜像信息
rkpyimg loaderimage info build/uboot.img

# 解包并对比
rkpyimg boot-merger unpack build/idbloader.img -o verify/
ls -lh verify/

# 对比 SHA256
sha256sum build/*.img
```

### Q: 支持哪些 Python 版本？

A: Python 3.10+ （使用了现代类型注解语法）

## 开发和测试

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_boot_merger.py -v

# 生成覆盖率报告
pytest --cov=rkpyimg --cov-report=html
```

### 代码质量检查

```bash
# 类型检查
mypy src/

# 代码检查
ruff check src/ tests/

# 代码格式化
ruff format src/ tests/
```

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

## 致谢

- [Rockchip](https://www.rock-chips.com/) - 原始 C 工具和固件
- [OrangePi](http://www.orangepi.org/) - RK3399 参考实现
- [Armbian](https://www.armbian.com/) 社区 - 文档和构建经验
- [U-Boot](https://github.com/u-boot/u-boot) - Bootloader 源码

## 相关项目

- [rkbin](https://github.com/rockchip-linux/rkbin) - Rockchip 官方二进制文件
- [rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) - Rockchip USB 烧录工具
- [Armbian](https://github.com/armbian/build) - ARM 设备构建框架
