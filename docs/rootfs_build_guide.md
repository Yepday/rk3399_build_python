# RK3399 Root Filesystem Build Guide

本文档说明如何为 RK3399 构建 Ubuntu-based 根文件系统。

## 概述

`build_rootfs.py` 脚本基于参考项目的 shell 脚本重写为 Python，提供了从 Ubuntu Base 构建根文件系统的完整流程。

## 功能特性

- **下载 Ubuntu Base tarball**: 自动从官方源下载指定版本的 Ubuntu Base
- **解压和配置**: 自动解压并配置基础系统
- **QEMU 支持**: 使用 QEMU 在 x86_64 主机上 chroot ARM64 环境
- **软件包安装**: 自动安装必要的系统软件包
- **内核模块集成**: 自动安装编译好的内核模块
- **固件集成**: 集成必要的硬件固件
- **用户配置**: 创建默认用户（orangepi/orangepi）

## 系统要求

### 必需软件包

```bash
sudo apt-get install -y \
    qemu-user-static \
    debootstrap \
    binfmt-support
```

### 运行权限

脚本必须以 root 权限运行（因为需要 chroot 和 mount 操作）：

```bash
sudo python3 scripts/build_rootfs.py [options]
```

## 支持的发行版

| 发行版 | 代号 | 版本 | 推荐 |
|--------|------|------|------|
| Ubuntu 18.04 | bionic | 18.04.5 | |
| Ubuntu 20.04 | focal | 20.04.5 | ✓ (默认) |
| Ubuntu 22.04 | jammy | 22.04.3 | |

## 使用方法

### 基础用法

```bash
# 构建默认配置（Ubuntu 20.04 Server, 中国镜像）
sudo python3 scripts/build_rootfs.py

# 指定发行版
sudo python3 scripts/build_rootfs.py --distro focal

# 选择镜像源
sudo python3 scripts/build_rootfs.py --mirror cn       # 中国镜像（默认）
sudo python3 scripts/build_rootfs.py --mirror official # 官方镜像

# 桌面版（暂未实现）
sudo python3 scripts/build_rootfs.py --type desktop
```

### 完整构建示例

```bash
# Ubuntu 20.04 Server + 中国镜像（推荐）
sudo python3 scripts/build_rootfs.py --distro focal --type server --mirror cn

# Ubuntu 18.04 Server + 官方镜像
sudo python3 scripts/build_rootfs.py --distro bionic --type server --mirror official

# Ubuntu 22.04 Server + 默认镜像
sudo python3 scripts/build_rootfs.py --distro jammy --type server --mirror default
```

### 集成到完整构建流程

```bash
# 使用 build_all.py 构建完整系统（包含 rootfs）
python3 scripts/build_all.py

# 跳过 rootfs 构建
python3 scripts/build_all.py --skip-rootfs

# 指定 rootfs 配置
python3 scripts/build_all.py \
    --rootfs-distro focal \
    --rootfs-type server \
    --rootfs-mirror cn
```

## 构建流程详解

### 1. 下载阶段

脚本会从以下位置下载 Ubuntu Base tarball：

```
http://cdimage.ubuntu.com/ubuntu-base/releases/{version}/release/ubuntu-base-{version}-base-arm64.tar.gz
```

下载的文件保存在 `build/` 目录，下次构建时会复用。

**大小参考**：
- Ubuntu 18.04 Base: ~50 MB
- Ubuntu 20.04 Base: ~45 MB
- Ubuntu 22.04 Base: ~48 MB

### 2. 解压阶段

将 tarball 解压到 `build/rootfs/` 目录：

```bash
build/
└── rootfs/              # 根文件系统目录
    ├── bin/
    ├── boot/
    ├── dev/
    ├── etc/
    ├── home/
    ├── lib/
    ├── usr/
    └── var/
```

### 3. QEMU 设置

复制 QEMU 静态二进制到 rootfs：

```bash
cp /usr/bin/qemu-aarch64-static build/rootfs/usr/bin/
```

这允许在 x86_64 主机上运行 ARM64 程序。

### 4. 系统配置

在 chroot 环境中执行以下操作：

#### 安装基础软件包
```bash
apt-get install -y \
    dosfstools curl xz-utils iw rfkill \
    wpasupplicant openssh-server alsa-utils \
    rsync u-boot-tools vim parted \
    network-manager net-tools sudo systemd
```

#### 创建用户
- **用户名**: `orangepi`
- **密码**: `orangepi`
- **权限**: sudo, adm, video, plugdev

- **root 密码**: `orangepi`

#### 配置网络
- 主机名: `orangepi-rk3399`
- 启用 NetworkManager 和 SSH

### 5. 内核模块安装

从 `components/kernel/modules/` 复制内核模块：

```bash
cp -r components/kernel/modules/lib/modules/* build/rootfs/lib/modules/
```

### 6. 固件安装

从 `external/firmware/` 复制硬件固件：

```bash
cp -r external/firmware/* build/rootfs/lib/firmware/
```

### 7. 系统配置文件

#### /etc/fstab
```
/dev/root  /  ext4  defaults,noatime  0  1
```

#### /etc/securetty
添加 RK3399 串口控制台：
```
ttyFIQ0
```

## 输出文件

构建完成后，根文件系统位于：

```
build/rootfs/
```

**大小估计**：
- Server 最小安装: ~400-600 MB
- Server 完整安装: ~800-1200 MB
- Desktop 安装: ~2-3 GB（暂未实现）

## 构建时间

| 配置 | 下载时间 | 构建时间 | 总时间 |
|------|----------|----------|--------|
| Server (中国镜像) | 1-3 分钟 | 5-10 分钟 | 6-13 分钟 |
| Server (官方镜像) | 3-10 分钟 | 5-10 分钟 | 8-20 分钟 |

*时间取决于网络速度和主机性能*

## 故障排除

### 1. qemu-aarch64-static 未找到

**错误**:
```
qemu-aarch64-static not found
```

**解决**:
```bash
sudo apt-get install qemu-user-static
```

### 2. 权限错误

**错误**:
```
[ERROR] This script must be run as root
```

**解决**:
使用 sudo 运行：
```bash
sudo python3 scripts/build_rootfs.py
```

### 3. 下载失败

**错误**:
```
Failed to download Ubuntu base
```

**解决**:
1. 检查网络连接
2. 使用中国镜像: `--mirror cn`
3. 手动下载 tarball 并放到 `build/` 目录

### 4. mount 失败

**错误**:
```
Failed to mount /dev
```

**解决**:
手动清理挂载点：
```bash
sudo umount build/rootfs/sys
sudo umount build/rootfs/proc
sudo umount build/rootfs/dev/pts
sudo umount build/rootfs/dev
```

然后重新运行脚本。

### 5. APT 更新失败

**错误**:
```
apt-get update failed
```

**解决**:
1. 检查 `/etc/resolv.conf` 是否有效
2. 尝试不同的镜像源
3. 检查防火墙设置

## 清理

### 清理 rootfs

```bash
sudo rm -rf build/rootfs/
```

### 清理下载的 tarball

```bash
rm -f build/ubuntu-base-*.tar.gz
```

### 使用 clean.py 清理

```bash
# 清理所有构建产物（包含 rootfs）
python3 scripts/clean.py --clean

# 深度清理
python3 scripts/clean.py --distclean
```

## 自定义

### 添加额外软件包

编辑 `build_rootfs.py` 中的 `configure_base_system()` 函数：

```python
script_content = """#!/bin/bash
# ... existing packages ...
apt-get install -y your-package-here
"""
```

### 修改默认用户

编辑 `configure_base_system()` 中的用户创建部分：

```python
script_content = """
useradd -m -s /bin/bash -G sudo myuser
echo "myuser:mypassword" | chpasswd
"""
```

### 添加自定义配置文件

在 `configure_base_system()` 之后添加文件复制：

```python
# Copy custom files
custom_files = Path("configs/rootfs_overlay/")
if custom_files.exists():
    shutil.copytree(custom_files, ROOTFS_DIR, dirs_exist_ok=True)
```

## 与参考项目的差异

本实现与 OrangePi 参考项目的 `distributions.sh` 相比：

### 相同点
- 使用 Ubuntu Base tarball 作为基础
- 支持多个 Ubuntu 版本
- 使用 QEMU chroot 配置系统
- 安装相同的基础软件包

### 差异点

| 特性 | 参考项目 | 本项目 |
|------|----------|--------|
| 语言 | Bash | Python 3 |
| 交互性 | whiptail 菜单 | 命令行参数 |
| 桌面支持 | LXDE | 暂未实现 |
| 配置管理 | 多个 shell 文件 | 单个 Python 文件 |
| 错误处理 | 基础 | 详细的异常处理 |
| 日志输出 | 彩色 echo | 结构化日志 |

### 待实现功能

- [ ] LXDE 桌面环境安装
- [ ] GPU 库安装（Mali）
- [ ] GStreamer 硬件加速
- [ ] OrangePi GPIO 库
- [ ] 蓝牙配置
- [ ] Resize helper 服务
- [ ] 更多发行版支持 (Debian)

## 相关脚本

- `scripts/build_rootfs.py` - 根文件系统构建（本文档）
- `scripts/build_kernel.py` - 内核编译
- `scripts/build_all.py` - 完整构建流程
- `scripts/clean.py` - 清理脚本

## 参考资料

- [Ubuntu Base 下载](http://cdimage.ubuntu.com/ubuntu-base/releases/)
- [QEMU User Emulation](https://www.qemu.org/docs/master/user/main.html)
- [Debootstrap Guide](https://wiki.debian.org/Debootstrap)
- OrangePi RK3399 Build System (参考项目)

## 常见问题

### Q: 为什么必须使用 root 权限？

A: 因为脚本需要执行以下特权操作：
- `mount`/`umount` 伪文件系统
- `chroot` 到 ARM64 环境
- 创建设备节点
- 设置文件权限和所有者

### Q: 可以在 ARM64 主机上构建吗？

A: 可以，但不需要 QEMU。脚本会自动检测架构。

### Q: 构建的 rootfs 包含内核吗？

A: 不包含。内核 Image 和 DTB 文件独立存放在 `build/kernel/`。
   Rootfs 只包含内核模块（`.ko` 文件）。

### Q: 如何打包成镜像？

A: 使用 `build_image.py`（待实现）或手动创建 ext4 镜像：

```bash
# 创建镜像文件
dd if=/dev/zero of=rootfs.img bs=1M count=2048
mkfs.ext4 rootfs.img

# 挂载并复制
sudo mount rootfs.img /mnt
sudo cp -a build/rootfs/* /mnt/
sudo umount /mnt
```

### Q: 默认语言是什么？

A: 英语（en_US.UTF-8）。要添加中文支持：

1. 编辑 `configure_base_system()` 添加：
```python
locale-gen zh_CN.UTF-8
```

2. 或在系统启动后执行：
```bash
sudo locale-gen zh_CN.UTF-8
sudo update-locale LANG=zh_CN.UTF-8
```

## 贡献

欢迎贡献代码和建议！特别是：

- [ ] 桌面环境支持
- [ ] Debian 支持
- [ ] 更好的错误恢复
- [ ] 单元测试
- [ ] CI/CD 集成
