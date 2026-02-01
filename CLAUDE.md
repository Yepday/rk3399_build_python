# CLAUDE.md

本文件为 Claude Code 提供项目维护指导。

## 项目概述

RK3399 构建系统 - 用 Python 实现的 Rockchip RK3399 完整构建流程，支持 U-Boot、Kernel、Rootfs 的自动化构建和打包。

### 核心功能
- **自动化构建**：一键构建 U-Boot、Linux Kernel、Rootfs
- **桌面环境支持**：集成 XFCE 桌面环境的 Ubuntu rootfs
- **完整工具链**：包含 bootloader、kernel、rootfs 打包工具
- **设备树修复**：自动修复 OrangePi 设备树编译问题

### 目标设备
- Orange Pi RK3399
- Orange Pi 4
- 其他 RK3399 开发板

## 项目结构

```
rk3399_build_python/
├── scripts/               # 构建脚本
│   ├── build_all.py       # 全自动构建脚本
│   ├── build_kernel.py    # 内核构建
│   ├── build_uboot.py     # U-Boot 构建
│   ├── build_rootfs.py    # Rootfs 构建
│   ├── clean.py           # 清理脚本
│   ├── make_bootimg.sh    # boot.img 生成
│   └── flash_bootloader.sh # Bootloader 烧录
├── RKBOOT/                # U-Boot 配置文件
├── RKTRUST/               # Trust 镜像配置
├── bin/rk33/              # Rockchip 二进制固件
├── build/                 # 构建输出目录
└── docs/                  # 文档
```

## 常用命令

```bash
# 完整构建流程
python3 scripts/build_all.py

# 分步构建
python3 scripts/build_uboot.py              # 编译 U-Boot
python3 scripts/build_kernel.py             # 编译内核和设备树
python3 scripts/build_rootfs.py             # 构建 Ubuntu rootfs
bash scripts/make_bootimg.sh rk3399-orangepi-4  # 生成 boot.img

# 烧录
bash scripts/flash_bootloader.sh            # 烧录 bootloader 到 eMMC

# 清理命令
python3 scripts/clean.py --clean            # 清理编译产物，保留源码
python3 scripts/clean.py --distclean        # 深度清理，删除所有源码和工具链
python3 scripts/clean.py --dry-run          # 预览删除内容
```

## 清理功能

- `--clean`：删除 build/ 目录（约 54MB），保留源码
- `--distclean`：删除所有源码和工具链（约 6.2GB），重置项目
- `--dry-run`：预览删除内容，不实际删除

## 技术说明

### Device Tree 自动修复

OrangePi 的 DTS 源文件存在但 Makefile 中缺少编译规则时，`build_kernel.py` 会自动修复：
- 检测并添加缺失的 Orange Pi 编译规则
- 在编译 DTB 之前自动执行
- 具有幂等性，多次运行安全

### Rootfs 构建

支持两种桌面环境构建：

1. **XFCE 桌面**（默认）
   - 完整的 Ubuntu base + XFCE 桌面环境
   - 包含中文字体、输入法、常用应用
   - 适合日常使用

2. **最小系统**
   - 仅包含 Ubuntu base 系统
   - 无桌面环境
   - 适合服务器或嵌入式应用

构建命令：
```bash
# XFCE 桌面版
python3 scripts/build_rootfs.py

# 最小系统
python3 scripts/build_rootfs.py --minimal
```

### Boot.img 生成

支持多个 OrangePi RK3399 设备树：
- `rk3399-orangepi.dtb`
- `rk3399-orangepi-4.dtb`
- `rk3399-orangepi-rk3399.dtb`

## 构建产物

成功构建后，`build/` 目录包含：
- `idbloader.img` - DDR 初始化 + Miniloader
- `uboot.img` - U-Boot bootloader
- `trust.img` - ARM Trusted Firmware
- `boot.img` - Kernel + Device Tree + Ramdisk
- `rootfs.img` - 根文件系统镜像

## 文档

详细文档位于 `docs/` 目录：
- 快速入门指南
- 分步构建教程
- 烧录指南
- 故障排查
