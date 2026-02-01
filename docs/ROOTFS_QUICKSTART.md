# RK3399 快速开始 - 根文件系统构建

本文档提供从零开始构建 RK3399 Ubuntu 根文件系统的快速指南。

## 前置要求

### 系统要求
- Ubuntu 18.04+ 或 Debian 10+ （主机系统）
- sudo 权限
- 至少 15GB 磁盘空间（Desktop 版本需要更多空间）

### 安装依赖
```bash
sudo apt-get update
sudo apt-get install -y \
    qemu-user-static \
    debootstrap \
    binfmt-support \
    python3 python3-pip
```

## 快速构建

### 方式一：完整构建（推荐）

构建完整系统（U-Boot + 内核 + 根文件系统）：

```bash
# 进入项目目录
cd rk3399_build_python

# 一键完整构建（默认 Desktop 版本）
python3 scripts/build_all.py
```

构建完成后，你将得到：
- `build/boot/idbloader.img` - Bootloader
- `build/boot/uboot.img` - U-Boot
- `build/boot/trust.img` - ATF + OP-TEE
- `build/kernel/Image` - 内核镜像
- `build/kernel/dtbs/` - 设备树文件
- `build/rootfs/` - 根文件系统目录（Desktop 版本）

### 方式二：仅构建根文件系统

如果你已经有了 bootloader 和内核，只需要构建根文件系统：

```bash
# 需要 root 权限（默认构建 Desktop 版本）
sudo python3 scripts/build_rootfs.py
```

默认配置：
- 发行版：Ubuntu 20.04 (Focal)
- 类型：**Desktop (LXDE)** ✨
- 镜像源：中国镜像

### 方式三：自定义配置

```bash
# Ubuntu 20.04 Desktop + 中国镜像（默认）
sudo python3 scripts/build_rootfs.py \
    --distro focal \
    --type desktop \
    --mirror cn

# Ubuntu 18.04 Server + 官方镜像
sudo python3 scripts/build_rootfs.py \
    --distro bionic \
    --type server \
    --mirror official

# Ubuntu 22.04 Desktop + 官方镜像
sudo python3 scripts/build_rootfs.py \
    --distro jammy \
    --type desktop \
    --mirror official
```

## 构建时间参考

| 组件 | Server | Desktop |
|------|--------|---------|
| 下载 Ubuntu Base | 1-5 分钟 | 1-5 分钟 |
| 配置系统 | 5-10 分钟 | 5-10 分钟 |
| 安装桌面环境 | - | **10-20 分钟** |
| 安装内核模块 | 1-2 分钟 | 1-2 分钟 |
| **总计** | **7-17 分钟** | **17-37 分钟** |

*时间取决于网络速度和主机性能*

## 验证构建结果

### 检查输出目录

```bash
# 查看 rootfs 目录结构
ls -lh build/rootfs/

# 应该看到标准的 Linux 目录结构
# bin/ boot/ dev/ etc/ home/ lib/ root/ usr/ var/ ...
```

### 检查文件大小

```bash
# 统计 rootfs 大小
du -sh build/rootfs/

# 典型大小:
# - Ubuntu 20.04 Server: 600-800 MB
# - Ubuntu 20.04 Desktop: 2-3 GB  ✨
```

### 检查已安装软件包

```bash
# 进入 chroot 环境检查
sudo chroot build/rootfs /bin/bash

# 查看已安装软件包
dpkg -l | grep openssh-server

# Desktop 版本额外检查
dpkg -l | grep lxde               # LXDE 桌面环境
dpkg -l | grep lightdm            # 显示管理器
dpkg -l | grep chromium           # 浏览器

# 退出 chroot
exit
```

### Desktop 版本特定检查

```bash
# 检查桌面环境配置
ls -lh build/rootfs/etc/xdg/lxsession/LXDE/

# 检查 LightDM 配置
cat build/rootfs/etc/lightdm/lightdm.conf

# 检查安装的图形应用
ls build/rootfs/usr/share/applications/
```

## 使用构建的根文件系统

### 制作 SD 卡镜像

```bash
# 创建镜像文件（2GB）
dd if=/dev/zero of=sdcard.img bs=1M count=2048

# 创建分区表
sudo parted sdcard.img mklabel gpt

# 创建 rootfs 分区（从 48MB 开始）
sudo parted sdcard.img mkpart primary ext4 48M 100%

# 设置 loop 设备
sudo losetup -fP sdcard.img
LOOP_DEV=$(losetup -j sdcard.img | cut -d: -f1)

# 格式化分区
sudo mkfs.ext4 ${LOOP_DEV}p1

# 挂载并复制 rootfs
sudo mkdir -p /mnt/rootfs
sudo mount ${LOOP_DEV}p1 /mnt/rootfs
sudo cp -a build/rootfs/* /mnt/rootfs/
sudo umount /mnt/rootfs

# 写入 bootloader
sudo dd if=build/boot/idbloader.img of=$LOOP_DEV seek=64 conv=notrunc
sudo dd if=build/boot/uboot.img of=$LOOP_DEV seek=16384 conv=notrunc
sudo dd if=build/boot/trust.img of=$LOOP_DEV seek=24576 conv=notrunc

# 卸载 loop 设备
sudo losetup -d $LOOP_DEV

echo "SD 卡镜像已创建: sdcard.img"
```

### 直接写入 SD 卡

```bash
# 查看 SD 卡设备名
lsblk

# 假设 SD 卡是 /dev/sdb
DEVICE=/dev/sdb

# 写入 bootloader
sudo dd if=build/boot/idbloader.img of=$DEVICE seek=64 conv=fsync
sudo dd if=build/boot/uboot.img of=$DEVICE seek=16384 conv=fsync
sudo dd if=build/boot/trust.img of=$DEVICE seek=24576 conv=fsync

# 创建分区
sudo parted $DEVICE mklabel gpt
sudo parted $DEVICE mkpart primary ext4 48M 100%

# 格式化 rootfs 分区
sudo mkfs.ext4 ${DEVICE}1

# 挂载并复制 rootfs
sudo mkdir -p /mnt/rootfs
sudo mount ${DEVICE}1 /mnt/rootfs
sudo cp -a build/rootfs/* /mnt/rootfs/
sudo umount /mnt/rootfs

echo "SD 卡已准备完成"
```

## 默认登录信息

构建的系统包含以下默认账户：

| 用户名 | 密码 | 权限 |
|--------|------|------|
| root | orangepi | 超级用户 |
| orangepi | orangepi | sudo 权限 |

**安全提示**：首次启动后请立即修改密码！

```bash
# 修改密码（系统启动后）
passwd           # 修改当前用户密码
sudo passwd      # 修改 root 密码
```

## 常见问题

### Q1: 构建失败：qemu-aarch64-static not found

```bash
# 安装 QEMU
sudo apt-get install qemu-user-static
```

### Q2: 下载 Ubuntu Base 很慢

```bash
# 使用中国镜像（默认）
sudo python3 scripts/build_rootfs.py --mirror cn

# 或手动下载后放到 build/ 目录
wget http://cdimage.ubuntu.com/ubuntu-base/releases/20.04.5/release/ubuntu-base-20.04.5-base-arm64.tar.gz
mv ubuntu-base-*.tar.gz build/
```

### Q3: chroot 时提示 format error

这通常是因为没有安装 qemu-user-static 或 binfmt-support：

```bash
sudo apt-get install -y qemu-user-static binfmt-support
sudo systemctl restart systemd-binfmt
```

### Q4: 清理构建产物

```bash
# 仅清理 rootfs
sudo rm -rf build/rootfs/

# 清理所有构建产物
python3 scripts/clean.py --clean

# 深度清理（包括源码）
python3 scripts/clean.py --distclean
```

## 下一步

- [完整构建文档](docs/rootfs_build_guide.md) - 详细的构建流程说明
- [内核构建指南](KERNEL_BUILD_GUIDE.md) - 如何编译 Linux 内核
- [U-Boot 构建指南](docs/uboot_build_guide.md) - 如何编译 U-Boot
- [镜像烧录指南](docs/flash_guide.md) - 如何将镜像烧录到设备

## 获取帮助

遇到问题？

1. 查看 [常见问题](docs/rootfs_build_guide.md#故障排除)
2. 提交 [Issue](https://github.com/yourusername/rk3399_build_python/issues)
3. 查看构建日志获取详细错误信息

## 贡献

欢迎贡献代码和文档！特别是：

- 添加桌面环境支持 (LXDE/XFCE)
- 支持更多 Ubuntu 版本
- 添加 Debian 支持
- 改进错误处理和日志输出

详见 [CONTRIBUTING.md](CONTRIBUTING.md)
