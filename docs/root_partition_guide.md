# Root 分区标识方法指南

## 概述

在嵌入式 Linux 系统中，正确指定根分区至关重要。本文档介绍三种主要方法及其应用场景。

## 为什么需要唯一标识

### 问题场景

当系统中存在多个存储设备时，设备节点可能动态变化：

```bash
# 仅 SD 卡
/dev/mmcblk0     ← SD 卡
/dev/mmcblk0p4   ← rootfs 分区

# SD 卡 + eMMC
/dev/mmcblk0     ← eMMC（先检测到）
/dev/mmcblk0p4   ← eMMC 的分区
/dev/mmcblk1     ← SD 卡（后检测到）
/dev/mmcblk1p4   ← SD 卡的 rootfs ❌ 启动失败
```

使用 `root=/dev/mmcblk0p4` 会导致不稳定！

## 三种方法对比

| 方法 | 内核参数 | 稳定性 | 可读性 | 适用场景 |
|------|----------|--------|--------|----------|
| 设备节点 | `root=/dev/mmcblk0p4` | ⚠️ 低 | ✓ 好 | 单一固定设备 |
| 分区标签 | `root=LABEL=rootfs` | ✓ 高 | ✓✓ 很好 | 多系统、开发测试 |
| 分区UUID | `root=PARTUUID=xxx` | ✓✓ 最高 | ⚠️ 差 | 生产环境、官方镜像 |
| 文件系统UUID | `root=UUID=xxx` | ✓ 高 | ⚠️ 差 | 通用 Linux 系统 |

## 方法详解

### 1. 分区标签 (LABEL) - **本项目采用**

#### 优点
- **语义化命名**：可以用有意义的名字区分分区
- **多系统共存**：不同标签互不干扰
- **易于调试**：一眼就知道挂载的是哪个分区

#### 设置方法

创建分区时设置标签：
```bash
sudo mkfs.ext4 -L "orangepi-focal" /dev/mmcblk0p4
sudo mkfs.ext4 -L "orangepi-jammy" /dev/sda1
```

修改现有分区标签：
```bash
sudo e2label /dev/mmcblk0p4 "my-rootfs"
```

查看标签：
```bash
sudo blkid | grep LABEL
# 输出：/dev/mmcblk0p4: LABEL="orangepi-focal" ...
```

#### 内核命令行
```bash
root=LABEL=orangepi-focal rootwait rootfstype=ext4
```

#### 实际应用场景

**场景 1：开发测试多个系统版本**
```bash
# SD 卡 1：Ubuntu 20.04
mkfs.ext4 -L "opi-focal" /dev/mmcblk0p4
boot.img cmdline: root=LABEL=opi-focal

# SD 卡 2：Ubuntu 22.04
mkfs.ext4 -L "opi-jammy" /dev/sda1
boot.img cmdline: root=LABEL=opi-jammy
```

**场景 2：主系统 + 备份系统**
```bash
# 主分区
mkfs.ext4 -L "rootfs-main" /dev/mmcblk0p4

# 备份分区
mkfs.ext4 -L "rootfs-backup" /dev/mmcblk0p5

# U-Boot 菜单选择
setenv bootargs_main "root=LABEL=rootfs-main"
setenv bootargs_backup "root=LABEL=rootfs-backup"
```

#### 注意事项
- **避免重复标签**：同一标签只能用于一个分区
- **标签限制**：ext4 标签最长 16 字符
- **格式化重置**：重新格式化会丢失标签

### 2. 分区 UUID (PARTUUID) - **Rockchip 官方方案**

#### 优点
- **真正唯一**：GPT 标准定义的 128-bit UUID
- **官方兼容**：与 Rockchip 官方工具链一致
- **系统无关**：不依赖文件系统类型

#### Rockchip 标准 UUID

Rockchip 官方固件使用固定 PARTUUID：
```
PARTUUID=614e0000-0000  ← rootfs 分区的标准 UUID
```

这个 UUID 在所有 Rockchip 官方镜像中都一致。

#### 设置方法

使用 `sgdisk` 设置分区 UUID：
```bash
# 查看当前 UUID
sudo sgdisk -i 4 /dev/mmcblk0

# 设置为 Rockchip 标准 UUID
sudo sgdisk --partition-guid=4:614e0000-0000-4a53-8000-1d28000054a9 /dev/mmcblk0

# 或使用 gdisk 交互式修改
sudo gdisk /dev/mmcblk0
```

#### 内核命令行
```bash
root=PARTUUID=614e0000-0000 rootwait rootfstype=ext4
```

#### 应用场景

**官方镜像兼容**：
- 使用 Rockchip 官方烧写工具时自动设置
- 与官方 Android 固件共存
- 出厂镜像默认配置

**设备树硬编码**：
```dts
chosen {
    bootargs = "root=PARTUUID=614e0000-0000 rootwait";
};
```

### 3. 文件系统 UUID - **通用 Linux 方案**

#### 优点
- **自动生成**：格式化时自动创建
- **广泛支持**：所有主流 Linux 发行版

#### 查看和使用
```bash
# 查看 UUID
sudo blkid /dev/mmcblk0p4
# PARTUUID="614e0000-..." UUID="a1b2c3d4-..."

# 内核命令行
root=UUID=a1b2c3d4-5678-90ab-cdef-1234567890ab rootwait
```

#### 缺点
- UUID 太长，不便于手动输入
- 重新格式化会改变

## 本项目的选择

### 当前实现：LABEL 方式

```bash
# make_bootimg.sh 中的配置
CMDLINE="earlycon=uart8250,mmio32,0xff1a0000 swiotlb=1 \
         console=ttyFIQ0 root=LABEL=rootfs rootwait \
         rootfstype=ext4 rw"
```

```bash
# flash_bootloader.sh 中格式化时设置标签
mkfs.ext4 -F -L "rootfs" "$ROOTFS_PARTITION"
```

### 选择理由

1. **灵活性**：开发测试时可以轻松切换不同系统
2. **可读性**：日志和调试时容易识别
3. **简单性**：不需要特殊工具设置 UUID
4. **兼容性**：与我们自建的分区方案配合良好

### 如果需要切换到 PARTUUID

修改 `make_bootimg.sh`：
```bash
CMDLINE="... root=PARTUUID=614e0000-0000 ..."
```

修改 `flash_bootloader.sh` 在创建分区后设置 UUID：
```bash
# 创建分区后
sudo sgdisk --partition-guid=4:614e0000-0000-4a53-8000-1d28000054a9 $DEVICE
```

## 最佳实践建议

### 开发环境
- ✅ 使用 **LABEL**
- 好处：方便多系统切换、易于识别

### 生产环境
- ✅ 使用 **PARTUUID**
- 好处：真正唯一、符合官方标准

### 个人用户
- ✅ 使用 **LABEL** 或 **PARTUUID**
- 避免使用设备节点（`/dev/mmcblkXpY`）

## 故障排查

### 问题：启动卡在 "Waiting for root device"

**可能原因**：
1. 分区标签/UUID 不匹配
2. 文件系统类型错误
3. 分区不存在

**解决步骤**：

1. 检查分区信息
```bash
sudo blkid /dev/mmcblk0p4
```

2. 检查内核命令行
```bash
# 解包 boot.img 查看
strings boot.img | grep "root="
```

3. 修正不匹配
```bash
# 方法 1：修改分区标签匹配 boot.img
sudo e2label /dev/mmcblk0p4 "rootfs"

# 方法 2：重新生成 boot.img 匹配分区
# 修改 make_bootimg.sh 中的 CMDLINE
bash scripts/make_bootimg.sh
```

## 总结

- **LABEL** = 人类可读，适合开发
- **PARTUUID** = 系统级唯一，适合生产
- **避免设备节点** = 不稳定，仅适合单设备测试
- **本项目使用 LABEL** = 平衡了灵活性和稳定性

## 参考资料

- [Linux Documentation: Root Device Names](https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html)
- [Rockchip Wiki: Parameter File](http://opensource.rock-chips.com/wiki_Parameter_file)
- [GPT Partition UUID Standard](https://en.wikipedia.org/wiki/GUID_Partition_Table)
