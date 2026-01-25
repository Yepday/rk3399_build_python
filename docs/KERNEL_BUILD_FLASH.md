# RK3399 Kernel 编译与烧写快速指南

本文档说明如何编译 Linux Kernel 并将其烧写到 SD 卡。

## 完整流程

### 1. 编译 Kernel

项目已内置 kernel 编译功能：

```bash
# 一键编译（包括 bootloader + kernel）
python3 scripts/build_all.py

# 或仅编译 kernel
python3 scripts/build_kernel.py
```

编译输出：
- `build/kernel/Image` - ARM64 kernel 镜像
- `build/kernel/dtbs/` - 设备树文件（DTB）
- `build/kernel/System.map` - 符号表

### 2. 生成 boot.img

编译完成后，需要将 `Image` 打包成 RK3399 bootloader 可识别的 `boot.img` 格式：

```bash
# 使用默认 DTB (rk3399-firefly-linux)
./scripts/make_bootimg.sh

# 或指定特定 DTB
./scripts/make_bootimg.sh rk3399-sapphire-excavator-linux
```

**注意**：OrangePi RK3399 的专用 DTB (`rk3399-orangepi-4.dtb`) 需要单独编译，默认使用 Firefly 通用 DTB 进行测试。

生成输出：
- `build/kernel/resource.img` - 设备树资源包
- `build/kernel/boot.img` - 最终的 kernel 启动镜像（~18MB）

### 3. 烧写到 SD 卡

生成 `boot.img` 后，使用烧写脚本将完整的启动组件写入 SD 卡：

```bash
# 自动检测 SD 卡设备
sudo ./scripts/flash_bootloader.sh

# 或指定设备
sudo ./scripts/flash_bootloader.sh /dev/sdb
```

脚本会自动检测并烧写：
1. **idbloader.img** → 扇区 64 (32KB)
2. **uboot.img** → 扇区 24576 (12MB)
3. **trust.img** → 扇区 32768 (16MB)
4. **boot.img** → 扇区 49152 (24MB) ✨

## 扇区布局

| 组件 | 扇区起始 | 偏移量 | 大小 | 说明 |
|------|----------|--------|------|------|
| Reserved | 0 | 0 | 32KB | 保留区域 |
| idbloader.img | 64 | 32KB | ~146KB | DDR + miniloader |
| uboot.img | 24576 | 12MB | 4MB | U-Boot |
| trust.img | 32768 | 16MB | 4MB | ARM Trusted Firmware |
| **boot.img** | 49152 | 24MB | ~18MB | **Linux Kernel** |
| boot partition | 49152 | 24MB | 32MB | FAT32 启动分区 |
| rootfs partition | 376832 | 184MB | ... | EXT4 根文件系统 |

## 工具说明

### make_bootimg.sh

从已编译的 `Image` 生成 `boot.img`。

**功能**：
1. 使用 `resource_tool` 将 DTB 打包成 `resource.img`
2. 使用 `mkbootimg` 将 `Image` + `resource.img` 合并成 `boot.img`

**依赖工具**（已内置于 kernel 源码）：
- `components/kernel/scripts/resource_tool` - Rockchip 资源打包工具
- `components/kernel/scripts/mkbootimg` - Android boot image 打包工具

### flash_bootloader.sh

智能烧写脚本，支持：
- ✓ 自动检测可移动存储设备
- ✓ 交互式设备选择
- ✓ 自动卸载已挂载分区
- ✓ 检测并烧写所有启动组件（包括 kernel）
- ✓ 数据同步确保完整写入

## 快速开始（完整流程）

```bash
# 1. 编译 bootloader + kernel
python3 scripts/build_all.py

# 2. 生成 boot.img
./scripts/make_bootimg.sh

# 3. 烧写到 SD 卡
sudo ./scripts/flash_bootloader.sh

# 4. 弹出 SD 卡，插入 RK3399 开发板启动
```

## 常见问题

### Q1: 找不到 boot.img？
**A**: 需要先运行 `./scripts/make_bootimg.sh` 生成 boot.img。`build_kernel.py` 只生成 `Image`，不会自动打包成 `boot.img`。

### Q2: 如何使用 OrangePi 专用 DTB？
**A**: OrangePi DTB (`rk3399-orangepi-4.dts`) 存在于源码中，但未包含在默认编译列表。可以手动编译：

```bash
cd components/kernel
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  rockchip/rk3399-orangepi-4.dtb
```

然后使用：
```bash
./scripts/make_bootimg.sh rk3399-orangepi-4
```

### Q3: boot.img 可以单独烧写吗？
**A**: 可以。如果 bootloader 已烧写，只想更新 kernel：

```bash
sudo dd if=build/kernel/boot.img \
  of=/dev/sdX seek=49152 bs=512 conv=notrunc,fsync
```

### Q4: 为什么使用 Firefly DTB？
**A**: Firefly RK3399 是通用参考板，DTB 兼容性较好。对于初次测试和验证启动流程足够。实际部署时建议使用对应硬件的专用 DTB。

## 参考

- 扇区布局来源：`OrangePiRK3399_Merged/scripts/lib/build_image.sh`
- mkbootimg 工具：Android AOSP 项目
- resource_tool：Rockchip 官方工具

## 相关文档

- [Bootloader 构建指南](../README.md#bootloader-构建流程)
- [完整镜像构建](BUILD_FULL_IMAGE.md)（规划中）
