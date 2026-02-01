# Rockchip RK3399 镜像 Boot 分区替换指南

本文档说明如何替换 RK3399 完整镜像中的 boot 分区（内核镜像）。

---

## 📋 镜像分区结构

根据分区表分析，OrangePi RK3399 镜像的分区布局如下：

```
┌─────────────────────────────────────────────────────────────┐
│  Sector 0-24575: 引导区域 (包含 idbloader.img)              │
├─────────────────────────────────────────────────────────────┤
│  Partition 1 (uboot): 扇区 24576-32767 (4MB)                │
│    └─ uboot.img                                              │
├─────────────────────────────────────────────────────────────┤
│  Partition 2 (trust): 扇区 32768-40959 (4MB)                │
│    └─ trust.img                                              │
├─────────────────────────────────────────────────────────────┤
│  Partition 3 (boot): 扇区 49152-114687 (32MB) ◄─── 目标分区  │
│    └─ boot.img (Android Boot Image 格式)                    │
├─────────────────────────────────────────────────────────────┤
│  Partition 4 (rootfs): 扇区 376832-6459358 (2.9GB)          │
│    └─ 根文件系统 (ext4)                                      │
└─────────────────────────────────────────────────────────────┘
```

**Boot 分区参数**:
- 起始扇区: 49152
- 扇区数量: 65536
- 大小: 32MB
- 格式: Android Boot Image (包含内核 + ramdisk)

---

## 🛠️ 替换方法

### 方法 1: 使用提供的脚本 (推荐)

#### 准备工作

1. 原始完整镜像文件
2. 新的 boot.img 文件（从内核构建输出）

#### 执行替换

```bash
cd /home/lyc/Desktop/rk3399_build_python

# 基本用法
./replace_boot.sh <原始镜像> <新boot.img> <输出镜像>

# 示例：替换 boot 分区
./replace_boot.sh \
  /home/lyc/Desktop/rk3399/origin/OrangePi_Build/OrangePiRK3399/output/images/OrangePi_4_ubuntu_bionic_desktop_linux4.4.179_v1.4.img \
  /home/lyc/Desktop/rk3399/origin/OrangePi_Build/OrangePiRK3399/output/kernel/boot.img \
  /tmp/new_system.img
```

#### 脚本功能

✅ 自动检查文件大小  
✅ 验证 boot.img 格式  
✅ 安全的分区替换  
✅ 替换后自动验证  
✅ 显示详细进度信息  

#### 替换方案选择

脚本提供两种方案：

**方案 1: 复制后替换 (推荐)**
- 复制原镜像到新文件
- 在新文件中替换 boot 分区
- 原镜像保持不变
- 适合: 正常使用

**方案 2: 原地替换 (危险)**
- 直接修改原镜像文件
- 不创建副本
- 节省磁盘空间
- 适合: 磁盘空间不足，且已备份原镜像

---

### 方法 2: 手动使用 dd 命令

如果你想手动操作，可以使用以下命令：

#### 步骤 1: 备份原镜像 (强烈推荐)

```bash
cp original.img backup.img
```

#### 步骤 2: 提取当前 boot 分区 (可选，用于对比)

```bash
dd if=original.img \
   of=boot_old.img \
   bs=512 \
   skip=49152 \
   count=65536
```

#### 步骤 3: 替换 boot 分区

```bash
# 先清零 boot 分区区域
dd if=/dev/zero \
   of=original.img \
   bs=512 \
   seek=49152 \
   count=65536 \
   conv=notrunc

# 写入新 boot.img
dd if=new_boot.img \
   of=original.img \
   bs=512 \
   seek=49152 \
   conv=notrunc
```

#### 步骤 4: 验证替换结果

```bash
# 检查 boot 分区的 magic (应该是 "ANDROID!")
dd if=original.img bs=512 skip=49152 count=1 2>/dev/null | hexdump -C | head -1
# 应该看到: 00000000  41 4e 44 52 4f 49 44 21  ...

# 查看分区表
parted original.img unit s print
```

---

### 方法 3: 挂载镜像后替换

适合需要同时修改多个分区的场景。

```bash
# 1. 设置 loop 设备
sudo losetup -P /dev/loop0 original.img

# 2. 查看分区
lsblk /dev/loop0

# 3. 直接写入 boot 分区
sudo dd if=new_boot.img of=/dev/loop0p3 bs=4M

# 4. 卸载
sudo losetup -d /dev/loop0
```

---

## ⚠️ 注意事项

### 1. Boot 镜像大小限制

boot.img 必须 ≤ 32MB (33554432 字节)，否则会覆盖后续分区导致数据损坏。

```bash
# 检查 boot.img 大小
ls -lh new_boot.img

# 如果超过 32MB，需要优化内核配置或压缩 ramdisk
```

### 2. 文件格式验证

boot.img 必须是 Android Boot Image 格式：

```bash
# 验证格式
file new_boot.img
# 输出应包含: "Android bootimg"

# 检查 magic
hexdump -C new_boot.img | head -1
# 应该看到: 41 4e 44 52 4f 49 44 21 (ANDROID!)
```

### 3. 备份重要性

❗ **强烈建议替换前备份原镜像**

```bash
# 完整备份
cp original.img backup_$(date +%Y%m%d_%H%M%S).img

# 或只备份 boot 分区
dd if=original.img of=boot_backup.img bs=512 skip=49152 count=65536
```

### 4. 版本兼容性

确保新 boot.img 与镜像中的 rootfs 兼容：
- 内核版本匹配
- 驱动模块兼容
- 设备树 (DTB) 正确

---

## 🔍 验证和调试

### 验证替换是否成功

```bash
# 1. 检查 magic
dd if=modified.img bs=512 skip=49152 count=1 2>/dev/null | \
   hexdump -C | head -1 | grep "ANDROID"

# 2. 提取并对比
dd if=modified.img of=/tmp/verify_boot.img bs=512 skip=49152 count=65536
sha256sum /tmp/verify_boot.img new_boot.img

# 3. 查看分区表
fdisk -l modified.img
parted modified.img unit s print
```

### 常见问题排查

**问题 1: 启动卡在 U-Boot**
- 原因: boot.img 损坏或格式错误
- 解决: 重新生成正确的 boot.img

**问题 2: 内核 panic**
- 原因: 内核与 rootfs 不匹配
- 解决: 使用兼容的内核版本

**问题 3: 找不到 rootfs**
- 原因: bootargs 参数错误
- 解决: 检查 U-Boot 环境变量中的 bootargs

---

## 📝 示例操作

### 完整示例：替换 boot 并测试

```bash
#!/bin/bash
set -e

# 参数
ORIGINAL="/path/to/original.img"
NEW_BOOT="/path/to/new_boot.img"
OUTPUT="/path/to/modified.img"

echo "1. 复制原镜像..."
cp "$ORIGINAL" "$OUTPUT"

echo "2. 验证 boot.img 格式..."
file "$NEW_BOOT" | grep -q "Android bootimg" || {
    echo "错误: boot.img 格式不正确"
    exit 1
}

echo "3. 检查大小..."
BOOT_SIZE=$(stat -c%s "$NEW_BOOT")
MAX_SIZE=$((65536 * 512))
if [ $BOOT_SIZE -gt $MAX_SIZE ]; then
    echo "错误: boot.img 过大 ($BOOT_SIZE > $MAX_SIZE)"
    exit 1
fi

echo "4. 替换 boot 分区..."
dd if=/dev/zero of="$OUTPUT" bs=512 seek=49152 count=65536 conv=notrunc
dd if="$NEW_BOOT" of="$OUTPUT" bs=512 seek=49152 conv=notrunc

echo "5. 验证..."
dd if="$OUTPUT" bs=512 skip=49152 count=1 2>/dev/null | \
   hexdump -C | head -1 | grep -q "ANDROID" && \
   echo "✅ 验证成功" || echo "❌ 验证失败"

echo "完成！输出镜像: $OUTPUT"
```

---

## 🚀 烧录到设备

替换完成后，可以将镜像烧录到 SD 卡或 eMMC：

### 烧录到 SD 卡 (Linux)

```bash
# 1. 确认 SD 卡设备 (假设是 /dev/sdX)
lsblk

# 2. 卸载所有分区
sudo umount /dev/sdX*

# 3. 烧录镜像
sudo dd if=modified.img of=/dev/sdX bs=4M status=progress conv=fsync

# 4. 同步缓存
sync
```

### 使用 Rockchip 工具烧录

```bash
# 使用 upgrade_tool (需要设备进入 maskrom/loader 模式)
sudo upgrade_tool uf modified.img
```

---

## 📚 相关参考

### Boot 镜像格式

Android Boot Image 格式包含：
- Header (2KB): 包含 magic, kernel/ramdisk 大小和加载地址
- Kernel: Linux 内核镜像
- Ramdisk: 初始化 RAM 磁盘 (initrd)
- Second stage (可选): 设备树或其他数据

### 分析 boot.img 工具

```bash
# 使用 abootimg 分析
abootimg -i boot.img

# 使用 binwalk 分析
binwalk boot.img

# 解包 boot.img
mkdir boot_unpacked
cd boot_unpacked
abootimg -x ../boot.img
```

---

**文档版本**: 1.0  
**更新日期**: 2026-01-18  
**适用芯片**: Rockchip RK3399  
**适用平台**: OrangePi 4, Firefly RK3399, 等
