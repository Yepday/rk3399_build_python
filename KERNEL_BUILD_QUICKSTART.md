# RK3399 Kernel Build Quick Start

> **新功能**: 完整的Linux kernel构建集成已实现！

## 快速开始（3步）

### 方式 1: 一键完整构建（推荐）

```bash
# 下载并编译U-Boot + Bootloader镜像 + Kernel
python3 scripts/build_all.py

# 耗时: 15-25分钟（取决于CPU）
# 输出:
#   build/boot/idbloader.img    (bootloader)
#   build/boot/uboot.img        (bootloader)
#   build/kernel/Image          (kernel)
#   build/kernel/dtbs/          (设备树)
```

### 方式 2: 仅构建Kernel

```bash
python3 scripts/build_kernel.py

# 输出相同，但不编译U-Boot和bootloader镜像
```

### 方式 3: 快速重建（已下载源码）

```bash
# 跳过所有下载和U-Boot编译
python3 scripts/build_all.py --skip-download --skip-uboot-build

# 仅编译新的bootloader镜像和kernel（2-3分钟）
```

## 常见命令

| 目标 | 命令 | 耗时 |
|------|------|------|
| 完整系统构建 | `python3 scripts/build_all.py` | 20-30m |
| 仅构建kernel | `python3 scripts/build_kernel.py` | 10-15m |
| 快速重新编译 | `python3 scripts/build_all.py --skip-download --skip-uboot-build --skip-kernel-build` | 2-3m |
| 跳过kernel编译 | `python3 scripts/build_all.py --skip-kernel-build` | 5-10m |
| 清理所有产物 | `python3 scripts/build_all.py --clean` | 1-2m |
| 仅配置kernel | `python3 scripts/build_kernel.py --config-only` | <1m |
| 跳过内核模块 | `python3 scripts/build_kernel.py --no-modules` | 5-10m |

## 输出文件说明

### Bootloader (build/boot/)
```
idbloader.img    ~150 KB    DDR初始化 + Miniloader
uboot.img        ~4 MB      U-Boot bootloader
u-boot.bin       ~800 KB    U-Boot 二进制（中间产物）
```

### Kernel (build/kernel/)
```
Image            ~20-30 MB  ARM64 kernel binary
System.map       ~2 MB      Kernel符号表
dtbs/
  ├── rk3399-evb.dtb
  ├── rk3399-orangepi.dtb
  └── ...                   设备树文件（支持多个板型）
```

## 故障排查

### 问题 1: "aarch64-linux-gnu-gcc not found"

**解决方案**：
```bash
# 先下载toolchain
python3 scripts/build_uboot.py
```

系统会自动下载Linaro GCC 6.3.1到`components/toolchain/`

### 问题 2: Kernel下载失败

**检查网络连接**：
```bash
git clone --depth=1 https://github.com/orangepi-xunlong/OrangePiRK3399_kernel.git
```

**清理并重试**：
```bash
python3 scripts/build_kernel.py --clean
python3 scripts/build_kernel.py
```

### 问题 3: 编译出错

**查看完整编译日志**：
```bash
cd components/kernel
make -j24 Image ARCH=arm64 \
  CROSS_COMPILE=components/toolchain/gcc-linaro-6.3.1-2017.05-x86_64_aarch64-linux-gnu/bin/aarch64-linux-gnu-
```

## 自定义kernel配置

```bash
# 交互式配置
cd components/kernel
make menuconfig ARCH=arm64

# 返回项目根目录并重新编译
cd ../..
python3 scripts/build_kernel.py --skip-download
```

## 硬件要求

| 项目 | 需求 |
|------|------|
| 磁盘空间 | ~2 GB (源码 + 编译产物) |
| 下载速度 | 500 KB/s (完成需10-20分钟) |
| CPU | 推荐4核以上 |

## 估计的编译时间

**多核系统（24核）**：
- Kernel源码下载: 30-60秒
- 配置: 10秒
- Kernel编译: 5-10分钟
- 模块编译: 3-5分钟
- **总计: 10-20分钟**

**单核系统**:
- 预期时间为多核的 10-20 倍

## 完整构建流程

```
Phase 1: Download & Compile U-Boot
  ├─ Download from GitHub
  ├─ Configure (evb-rk3399_defconfig)
  └─ Compile → u-boot.bin

Phase 2: Build Bootloader Images
  ├─ boot_merger: DDR init + miniloader → idbloader.img
  ├─ loaderimage: u-boot.bin → uboot.img
  └─ trust_merger: BL31/BL32 → trust.img (optional)

Phase 3: Download & Compile Kernel (NEW)
  ├─ Download from GitHub
  ├─ Configure (rk3399_linux_defconfig)
  ├─ Compile kernel Image
  ├─ Compile device tree blobs
  ├─ Compile kernel modules
  └─ Copy to build/kernel/

Phase 4: Flash to Device (optional)
  └─ DD to SD card or eMMC
```

## 下一步

构建完成后：

1. **测试bootloader启动**
   ```bash
   sudo ./scripts/flash_bootloader.sh /dev/sdb
   # 用串口调试线连接，观察启动日志
   ```

2. **集成rootfs**
   - 使用debootstrap创建root filesystem
   - 与kernel一起打包到SD卡

3. **完整系统镜像**
   - 创建GPT分区表
   - 组装bootloader + kernel + rootfs
   - 写入完整的可启动SD卡镜像

## 相关文档

- 详细指南: [docs/kernel_build_guide.md](../docs/kernel_build_guide.md)
- Bootloader指南: [docs/bootloader_build_guide.md](../docs/bootloader_build_guide.md)
- U-Boot指南: [docs/uboot_build_guide.md](../docs/uboot_build_guide.md)
- 项目说明: [README.md](../README.md)

## 技术参考

- Kernel源码: https://github.com/orangepi-xunlong/OrangePiRK3399_kernel
- Kernel版本: Linux 4.4.x (RK3399特定优化)
- Defconfig: `arch/arm64/configs/rk3399_linux_defconfig`
- Device Trees: `arch/arm64/boot/dts/rockchip/rk3399*.dtsi`
