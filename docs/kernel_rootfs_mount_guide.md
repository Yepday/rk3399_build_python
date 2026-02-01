# Linux 根文件系统挂载详解

本文档详细讲解 Linux 内核启动时如何找到并挂载根文件系统（rootfs），以及块设备的命名规则。

---

## 目录

1. [Linux 启动流程概览](#linux-启动流程概览)
2. [根文件系统挂载机制](#根文件系统挂载机制)
3. [root 参数的各种格式](#root-参数的各种格式)
4. [块设备命名规则](#块设备命名规则)
5. [RK3399 特定情况](#rk3399-特定情况)
6. [常见问题与调试](#常见问题与调试)

---

## Linux 启动流程概览

完整的 Linux 系统启动流程：

```
┌─────────────┐
│  BootROM    │  硬件固化的启动代码，加载 SPL
└──────┬──────┘
       │
┌──────▼──────┐
│  SPL/TPL    │  次级程序加载器（Secondary Program Loader）
│ (idbloader)  │  初始化 DDR，加载 U-Boot
└──────┬──────┘
       │
┌──────▼──────┐
│   U-Boot    │  通用引导加载器
│             │  - 初始化硬件
│             │  - 加载内核 + DTB + initramfs（可选）
│             │  - 设置内核命令行参数
│             │  - 跳转到内核入口
└──────┬──────┘
       │
┌──────▼──────┐
│   Kernel    │  Linux 内核
│             │  1. 解压缩自身
│             │  2. 初始化子系统（内存、调度、驱动等）
│             │  3. **挂载根文件系统** ← 本文重点
│             │  4. 启动 init 进程（PID 1）
└──────┬──────┘
       │
┌──────▼──────┐
│    Init     │  用户空间初始化（systemd/sysvinit）
│  (PID 1)    │  - 挂载其他文件系统（/proc, /sys, /dev）
│             │  - 启动系统服务
└─────────────┘
```

---

## 根文件系统挂载机制

### 内核如何找到 rootfs

内核通过**启动参数 `root=`** 来确定根文件系统的位置。这个参数由 U-Boot 通过以下方式传递：

#### 方式 1：U-Boot 环境变量（传统方式）
```bash
# U-Boot 命令行
setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p4 rootwait"
saveenv
boot
```

#### 方式 2：boot.img 内嵌（RK3399 使用）
```bash
# 使用 mkbootimg 打包时指定
mkbootimg \
    --kernel Image \
    --second resource.img \
    --cmdline "console=ttyFIQ0 root=/dev/mmcblk0p4 rootwait rootfstype=ext4 rw" \
    -o boot.img
```

U-Boot 从 boot.img 提取 cmdline 并传递给内核。

### 挂载过程详解

```c
// 简化的内核挂载流程（kernel/init/do_mounts.c）

1. 解析 root= 参数
   ┌─────────────────────────────────────────┐
   │ root=/dev/mmcblk0p4                      │
   │   ↓                                      │
   │ 解析为设备号: MAJOR=179, MINOR=4         │
   └─────────────────────────────────────────┘

2. 等待设备准备（如果指定 rootwait）
   ┌─────────────────────────────────────────┐
   │ while (\!device_exists("/dev/mmcblk0p4")){ │
   │     msleep(100);  // 每100ms检查一次      │
   │     // 等待块设备驱动注册设备            │
   │ }                                         │
   └─────────────────────────────────────────┘

3. 探测文件系统类型（如果未指定 rootfstype）
   ┌─────────────────────────────────────────┐
   │ 尝试各种文件系统驱动:                    │
   │ - ext4_fs_type->mount()                  │
   │ - ext3_fs_type->mount()                  │
   │ - squashfs_fs_type->mount()              │
   │ - 直到成功或全部失败                     │
   └─────────────────────────────────────────┘

4. 挂载根文件系统
   ┌─────────────────────────────────────────┐
   │ do_mount("/dev/mmcblk0p4", "/", "ext4",  │
   │          MS_RDONLY | MS_SILENT, NULL)    │
   │   ↓                                      │
   │ VFS: Mounted root (ext4 filesystem)      │
   └─────────────────────────────────────────┘

5. 切换根目录
   ┌─────────────────────────────────────────┐
   │ sys_chdir("/");                          │
   │ sys_chroot(".");                         │
   └─────────────────────────────────────────┘

6. 启动 init 进程
   ┌─────────────────────────────────────────┐
   │ 按顺序尝试执行:                          │
   │ 1. /sbin/init                            │
   │ 2. /etc/init                             │
   │ 3. /bin/init                             │
   │ 4. /bin/sh (最后的备用方案)              │
   └─────────────────────────────────────────┘
```

### 关键内核参数

| 参数 | 作用 | 示例 |
|------|------|------|
| `root=` | 指定根设备 | `root=/dev/mmcblk0p4` |
| `rootwait` | 无限等待根设备出现 | 推荐用于 SD/eMMC |
| `rootdelay=N` | 等待 N 秒后再挂载 | `rootdelay=5` |
| `rootfstype=` | 指定文件系统类型 | `rootfstype=ext4` |
| `ro` / `rw` | 只读/读写挂载 | `rw` 用于可写 rootfs |
| `init=` | 指定 init 程序路径 | `init=/bin/bash` (调试) |

---

## root 参数的各种格式

内核支持多种方式指定根设备：

### 1. 设备节点路径（最直接，最可靠）

```bash
root=/dev/mmcblk0p4
```

**优点：**
- 最直接，无需额外解析
- 兼容性好，所有内核版本都支持

**缺点：**
- 硬编码设备名，设备顺序变化时会失败
- 例如：添加 USB 设备可能改变 `sdb` → `sdc`

### 2. LABEL（文件系统标签）

```bash
root=LABEL=rootfs
```

**工作原理：**
```c
// 内核会扫描所有块设备分区，查找匹配的标签
for_each_block_device(dev) {
    if (get_fs_label(dev) == "rootfs") {
        root_device = dev;
        break;
    }
}
```

**设置标签：**
```bash
# ext4 文件系统
sudo e2label /dev/mmcblk0p4 rootfs

# 查看标签
sudo blkid /dev/mmcblk0p4
# 输出: LABEL="rootfs" UUID="..." TYPE="ext4"
```

**限制：**
- 需要内核支持（CONFIG_BLOCK + 文件系统支持）
- 旧内核（< 2.6.30）可能不支持所有 fs
- **无 initramfs 时，部分内核可能解析失败**（我们遇到的问题）

### 3. UUID（通用唯一标识符）

```bash
root=UUID=dfd60810-81ce-49dc-81a8-c00fe822ff8b
```

**优点：**
- 每个分区 UUID 唯一，永不冲突
- 适合多磁盘系统

**查看 UUID：**
```bash
sudo blkid /dev/mmcblk0p4
# 输出: UUID="dfd60810-81ce-49dc-81a8-c00fe822ff8b"
```

### 4. PARTUUID（分区表 UUID）

```bash
root=PARTUUID=614e0000-0000
```

**特点：**
- 基于 GPT/MBR 分区表的 UUID，而非文件系统的 UUID
- 即使格式化分区也不变（只要不重建分区表）

### 5. 主设备号:次设备号

```bash
root=/dev/block/179:4
```

**格式：**
```
MAJOR:MINOR
  ↓     ↓
 179  : 4
  │     └─ 次设备号（分区号）
  └────── 主设备号（MMC 设备类型）
```

**查看设备号：**
```bash
ls -l /dev/mmcblk0p4
# 输出: brw-rw---- 1 root disk 179, 4 ...
#                            ^^^  ^
#                            主   次
```

---

## 块设备命名规则

### Linux 块设备命名约定

Linux 中块设备（block device）的命名遵循严格的规则：

```
/dev/前缀 + 设备类型 + 设备编号 + 分区号
    ↓         ↓          ↓         ↓
  /dev/    mmcblk      0         p4
```

### 常见设备类型

| 设备类型 | 命名格式 | 说明 | 示例 |
|---------|---------|------|------|
| **SD/eMMC/MMC** | `/dev/mmcblkN` | N = 控制器编号（0, 1, 2...） | `mmcblk0`, `mmcblk1` |
| **SCSI/SATA/USB 磁盘** | `/dev/sdX` | X = a, b, c... (按检测顺序) | `sda`, `sdb` |
| **NVMe SSD** | `/dev/nvmeNn1` | N = 控制器编号 | `nvme0n1` |
| **IDE 硬盘** | `/dev/hdX` | X = a, b, c... (旧式) | `hda` |
| **虚拟块设备** | `/dev/vdX` | 虚拟机磁盘 (virtio) | `vda` |
| **Loop 设备** | `/dev/loopN` | 挂载镜像文件 | `loop0` |

### 分区命名规则

#### 1. MMC/SD/eMMC 设备（使用 `p` 分隔符）

```
/dev/mmcblk0     ← 整个设备（磁盘）
/dev/mmcblk0p1   ← 分区 1
/dev/mmcblk0p2   ← 分区 2
/dev/mmcblk0p3   ← 分区 3
/dev/mmcblk0p4   ← 分区 4
     │       │ └─ 分区号（1-based）
     │       └─── 'p' 分隔符（partition）
     └─────────── 设备编号
```

**为什么要用 `p`？**
因为设备名本身包含数字 `mmcblk0`，直接加数字会混淆：
- `mmcblk01` ← 无法区分是 `mmcblk0` 的分区 1 还是 `mmcblk` 设备 01
- `mmcblk0p1` ← 清晰：`mmcblk0` 的分区 `p1`

#### 2. SCSI/SATA/USB 磁盘（直接加数字）

```
/dev/sda      ← 整个磁盘
/dev/sda1     ← 分区 1
/dev/sda2     ← 分区 2
  │    └─ 分区号
  └────── 磁盘编号（字母）
```

**为什么不用 `p`？**
设备名 `sda` 不包含数字，直接加数字不会混淆。

#### 3. NVMe 设备（双重编号）

```
/dev/nvme0n1      ← 命名空间 1
/dev/nvme0n1p1    ← 命名空间 1，分区 1
     │   │  └─ 分区号
     │   └──── 命名空间号（Namespace）
     └──────── 控制器编号
```

### 设备号分配

Linux 使用**主设备号（MAJOR）**和**次设备号（MINOR）**来标识设备：

```bash
$ ls -l /dev/mmcblk0*
brw-rw---- 1 root disk 179, 0  ← mmcblk0（整个设备）
brw-rw---- 1 root disk 179, 1  ← mmcblk0p1
brw-rw---- 1 root disk 179, 2  ← mmcblk0p2
brw-rw---- 1 root disk 179, 3  ← mmcblk0p3
brw-rw---- 1 root disk 179, 4  ← mmcblk0p4
                    ^^^  ^
                    主   次
```

**主设备号：** 标识设备驱动类型
- `179` = MMC 块设备
- `8` = SCSI 磁盘（包括 SATA, USB）
- `259` = NVMe

**次设备号：** 标识具体设备实例
- 计算公式：`MINOR = (设备号 << 4) | 分区号`
- 例如：`mmcblk0p4` = `(0 << 4) | 4` = `4`

---

## RK3399 特定情况

### RK3399 存储控制器映射

RK3399 SoC 有多个 MMC 控制器：

```
硬件控制器地址            设备树节点        Linux设备      用途
─────────────────────────────────────────────────────────────
0xfe320000 (SDMMC)    →   sdmmc    →   mmc0/mmcblk0   SD卡槽
0xfe330000 (SDHCI)    →   sdhci    →   mmc1/mmcblk1   eMMC
0xfe310000 (SDIO0)    →   sdio0    →   mmc2           WiFi/BT
```

### 启动日志中的映射关系

从实际启动日志中可以看到：

```
[1.762] dwmmc_rockchip fe320000.dwmmc: ...  ← SD卡控制器初始化
[1.955] mmc_host mmc0: Bus speed ...       ← 注册为 mmc0
[1.957] mmc0: new high speed SDHC card     ← 检测到 SD 卡
[1.960] mmcblk0: mmc0:aaaa SS08G 7.40 GiB  ← 创建块设备 mmcblk0
[1.991]  mmcblk0: p1 p2 p3 p4              ← 解析出 4 个分区

[1.799] sdhci-arasan fe330000.sdhci: ...   ← eMMC 控制器初始化
[1.826] mmc1: SDHCI controller ...         ← 注册为 mmc1
[1.907] mmc1: new HS400 Enhanced strobe    ← 检测到 eMMC
[1.909] mmcblk1: mmc1:0001 AJTD4R 14.6 GiB ← 创建块设备 mmcblk1

[2.294] dwmmc_rockchip fe310000.dwmmc: ... ← SDIO 控制器（WiFi）
[2.304] mmc_host mmc2: Bus speed ...       ← 注册为 mmc2
[3.077] mmc2: new ultra high speed SDR104  ← WiFi 模块（无块设备）
```

**关键结论：**
- **SD 卡 = mmc0 = mmcblk0**
- **eMMC = mmc1 = mmcblk1**
- **WiFi = mmc2（SDIO，无块设备）**

### OrangePi RK3399 分区布局

SD 卡分区表（GPT 格式）：

```
设备            起始扇区   结束扇区   大小    类型        用途
───────────────────────────────────────────────────────────
/dev/mmcblk0p1     24576     32767     4MB   loader1     U-Boot SPL (未使用)
/dev/mmcblk0p2     32768     40959     4MB   loader2     未使用
/dev/mmcblk0p3     49152    114687    32MB   kernel      boot.img (内核+DTB)
/dev/mmcblk0p4    376832  15523806   7.2GB   rootfs      根文件系统
```

**注意：** Bootloader 实际是直接烧写到固定扇区位置，不使用 p1/p2 分区：

```
镜像           起始扇区   大小    说明
─────────────────────────────────────────
idbloader.img     64       4MB   DDR init + miniloader
uboot.img       24576      4MB   U-Boot 主程序
trust.img       32768      4MB   ARM Trusted Firmware
boot.img        49152     32MB   Linux 内核 + 设备树
```

### 为什么我们的启动失败？

**原始配置（失败）：**
```bash
root=LABEL=rootfs
```
- SD 卡分区确实有 `LABEL="rootfs"` ✓
- 但内核 4.4.179 的 LABEL 扫描机制在无 initramfs 时不完整 ✗
- 内核一直等待，永不超时

**错误修复尝试（仍然失败）：**
```bash
root=/dev/mmcblk1p4
```
- `mmcblk1` 是 **eMMC**，而我们的 rootfs 在 **SD 卡** ✗
- SD 卡启动却指向 eMMC，当然找不到

**正确配置（成功）：**
```bash
root=/dev/mmcblk0p4
```
- `mmcblk0` = SD 卡（从启动日志确认）✓
- `p4` = 第 4 分区（rootfs 所在）✓

---

## 常见问题与调试

### 问题 1：内核启动卡住，显示 "Waiting for root device"

**症状：**
```
[2.782] Waiting for root device LABEL=rootfs...
[永远等待]
```

**可能原因：**
1. **设备路径错误**
   - 检查 `root=` 参数是否指向正确设备
   - 确认设备编号：查看启动日志中的 `mmcblk0` / `mmcblk1` 映射

2. **LABEL/UUID 解析失败**
   - 旧内核可能不支持 LABEL/UUID（特别是无 initramfs 时）
   - 解决：使用固定设备路径 `root=/dev/mmcblkXpY`

3. **缺少 rootwait 参数**
   - SD 卡初始化较慢，可能内核还未检测到设备就尝试挂载
   - 解决：添加 `rootwait` 或 `rootdelay=5`

4. **块设备驱动未编译进内核**
   - 检查内核配置：
     ```bash
     CONFIG_MMC=y                  # MMC 核心支持
     CONFIG_MMC_DW_ROCKCHIP=y      # Rockchip DW MMC 驱动
     CONFIG_MMC_BLOCK=y            # MMC 块设备支持
     ```

5. **设备树未启用存储控制器**
   - 检查 DTB 中 `&sdmmc` 节点是否 `status = "okay"`

**调试方法：**
```bash
# 1. 查看启动日志中的设备检测信息
grep -E "mmc|mmcblk" boot.log

# 2. 内核启动参数中加入详细日志
console=ttyFIQ0 loglevel=7 debug

# 3. 临时使用 init=/bin/sh 进入 shell 手动调试
root=/dev/mmcblk0p4 init=/bin/sh
```

### 问题 2：root= 参数不生效

**检查方法：**
```bash
# 在 U-Boot 中查看传递给内核的参数
printenv bootargs

# 或者查看内核启动日志第一行
[0.000000] Kernel command line: ...
```

**修复：**
```bash
# U-Boot 中设置
setenv bootargs "console=ttyFIQ0 root=/dev/mmcblk0p4 rootwait"
saveenv

# 或重新生成 boot.img 时指定正确的 cmdline
```

### 问题 3：设备编号混乱

**症状：**
每次启动 SD 卡可能是 `mmcblk0` 或 `mmcblk1`

**原因：**
- 内核按控制器**初始化顺序**分配编号，可能受驱动加载顺序影响
- 如果有多个存储设备，顺序可能不固定

**解决方案：**
1. **使用 PARTUUID（推荐）**
   ```bash
   root=PARTUUID=5848fa72-2bf5-463a-be34-4fad04fd178e
   ```
   - 基于分区表的 UUID，永不变化
   - 兼容性好，大部分内核都支持

2. **固定设备树别名**
   ```dts
   aliases {
       mmc0 = &sdmmc;    // 强制 SD 卡为 mmc0
       mmc1 = &sdhci;    // 强制 eMMC 为 mmc1
   };
   ```

3. **使用 initramfs + udev**
   - initramfs 中的 udev 可以创建稳定的符号链接
   - 例如 `/dev/disk/by-label/rootfs` → `/dev/mmcblk0p4`

### 问题 4：如何查看当前挂载的根设备

**方法 1：查看 `/proc/cmdline`**
```bash
cat /proc/cmdline
# 显示内核启动时的完整参数
```

**方法 2：查看挂载信息**
```bash
mount | grep "on / "
# 输出示例：
# /dev/mmcblk0p4 on / type ext4 (rw,relatime)

df -h /
# 输出示例：
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/mmcblk0p4  7.0G  1.2G  5.5G  18% /
```

**方法 3：查看 sysfs**
```bash
readlink -f /sys/dev/block/$(mountpoint -d /)
# 输出：/sys/devices/.../mmcblk0/mmcblk0p4
```

### 问题 5：修改 cmdline 后如何验证

**在烧写前验证：**
```bash
# 查看 boot.img 中的 cmdline
strings build/kernel/boot.img | grep "root="

# 应输出：
# ... root=/dev/mmcblk0p4 rootwait rootfstype=ext4 rw
```

**在板子上验证：**
```bash
# 通过串口在 U-Boot 阶段查看
printenv bootargs

# 或在 Linux 启动后查看
cat /proc/cmdline
```

---

## 最佳实践建议

### 1. 选择合适的 root= 格式

| 场景 | 推荐格式 | 理由 |
|------|---------|------|
| **嵌入式固定硬件** | `root=/dev/mmcblk0p4` | 简单直接，无依赖 |
| **多磁盘系统** | `root=PARTUUID=...` | 不受设备顺序影响 |
| **通用 Linux 发行版** | `root=UUID=...` | 兼容性好，支持动态检测 |
| **容器/虚拟机** | `root=/dev/vda1` | 虚拟设备编号固定 |

### 2. 必备内核参数

```bash
# 最小配置（推荐）
root=/dev/mmcblk0p4 rootwait rootfstype=ext4 rw

# 详细说明：
# - root=/dev/mmcblk0p4   : 根设备路径
# - rootwait              : 等待设备准备（SD卡必须）
# - rootfstype=ext4       : 指定文件系统类型（加快挂载）
# - rw                    : 读写模式（允许写入）

# 可选调试参数
console=ttyFIQ0,1500000 loglevel=7 debug init=/bin/bash
```

### 3. 文件系统标签命名规范

```bash
# 创建分区时设置有意义的标签
sudo e2label /dev/mmcblk0p3 boot
sudo e2label /dev/mmcblk0p4 rootfs

# 查看所有分区标签
lsblk -o NAME,LABEL,SIZE,TYPE,MOUNTPOINT
```

### 4. 调试技巧

**启用内核详细日志：**
```bash
# 临时调试启动问题
root=/dev/mmcblk0p4 rootwait loglevel=8 debug initcall_debug
```

**紧急 Shell 模式：**
```bash
# 如果 rootfs 损坏，启动到 shell 手动修复
root=/dev/mmcblk0p4 init=/bin/sh
# 或
init=/bin/bash
```

**检查设备准备情况：**
```bash
# 在 initramfs 或早期 shell 中
cat /proc/partitions    # 查看内核识别的所有分区
ls -l /dev/mmcblk*      # 查看设备节点
blkid                   # 查看所有分区的 UUID 和 LABEL
```

---

## 参考资源

### 内核文档
- [Documentation/admin-guide/kernel-parameters.txt](https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html)
- [Documentation/filesystems/ramfs-rootfs-initramfs.rst](https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html)

### 相关内核源码
```
init/do_mounts.c           - 根文件系统挂载主逻辑
init/do_mounts_rd.c        - RAM disk 支持
init/do_mounts_initrd.c    - initrd 支持
drivers/mmc/core/block.c   - MMC 块设备驱动
```

### 常用工具
```bash
# 查看块设备信息
lsblk              # 树形显示所有块设备
blkid              # 显示分区 UUID/LABEL/TYPE
fdisk -l           # 显示分区表
parted -l          # 显示详细分区信息

# 查看设备号
ls -l /dev/mmcblk* # 显示 MAJOR:MINOR
cat /proc/devices  # 显示已注册的设备类型

# 查看挂载信息
mount              # 显示所有挂载点
findmnt            # 树形显示挂载关系
cat /proc/mounts   # 内核视角的挂载信息
```

---

## 总结

**核心要点：**

1. **内核通过 `root=` 参数找到 rootfs**
   - 格式：`root=/dev/mmcblk0p4` 或 `root=LABEL=rootfs` 等
   - 由 U-Boot 通过 cmdline 传递给内核

2. **MMC 设备命名规则：`/dev/mmcblkNpM`**
   - `N` = 控制器编号（mmc0, mmc1, mmc2...）
   - `M` = 分区号（p1, p2, p3...）
   - `p` 是必需的分隔符

3. **RK3399 设备映射：**
   - SD 卡 = mmc0 = mmcblk0
   - eMMC = mmc1 = mmcblk1
   - WiFi = mmc2（无块设备）

4. **优先使用固定设备路径**
   - 嵌入式系统硬件固定，`/dev/mmcblk0p4` 最可靠
   - LABEL/UUID 在某些旧内核可能不支持

5. **必须添加 `rootwait` 参数**
   - SD 卡初始化需要时间
   - 否则内核可能在设备准备前就放弃

---

**文档版本：** v1.0  
**最后更新：** 2026-02-01  
**作者：** Claude (Anthropic)  
**适用平台：** RK3399 / Linux Kernel 4.4.x
