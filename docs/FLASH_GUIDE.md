# RK3399 系统烧写指南

本指南说明如何将构建好的完整系统烧写到 SD 卡。

## 前提条件

确保已完成以下构建步骤：

```bash
# 1. 构建 bootloader
python3 scripts/build_all.py

# 2. 构建 kernel
python3 scripts/build_kernel.py

# 3. 构建 rootfs（需要 root 权限）
sudo python3 scripts/build_rootfs.py --distro focal --type desktop
```

## 一键烧写完整系统

### 方法 1: 自动检测设备（推荐）

```bash
sudo ./scripts/flash_bootloader.sh
```

脚本会：
1. 自动检测可移动存储设备（SD 卡/USB）
2. 显示设备列表供选择
3. 烧写所有组件（bootloader + kernel + rootfs）

### 方法 2: 手动指定设备

```bash
# 对于 SD 卡读卡器（USB）
sudo ./scripts/flash_bootloader.sh /dev/sdb

# 对于内置 SD 卡槽
sudo ./scripts/flash_bootloader.sh /dev/mmcblk0
```

## 烧写内容

脚本会自动烧写以下内容（如果存在）：

| 组件 | 源文件 | 目标位置 | 说明 |
|------|--------|----------|------|
| idbloader | `build/boot/idbloader.img` | 扇区 64 | DDR 初始化 + miniloader |
| U-Boot | `build/boot/uboot.img` | 扇区 24576 | U-Boot bootloader |
| Trust | `trust.img` | 扇区 32768 | ATF + OP-TEE（可选） |
| Kernel | `build/kernel/boot.img` | 扇区 49152 | Linux 内核 |
| Rootfs | `build/rootfs/` | 分区 4 | 根文件系统 |

## 分区布局

脚本会创建以下 GPT 分区表：

```
分区 1: uboot  (24576-32767)    - U-Boot 保留区
分区 2: trust  (32768-40959)    - Trust 保留区
分区 3: boot   (49152-114687)   - Kernel 分区
分区 4: rootfs (376832-末尾)    - 根文件系统分区
```

## Rootfs 处理

脚本会自动处理 rootfs：

1. **检测 rootfs**：
   - 优先使用 `build/rootfs.img`（已打包镜像）
   - 否则使用 `build/rootfs/`（目录）

2. **自动打包**（如果是目录）：
   - 计算目录大小
   - 创建 ext4 镜像文件
   - 复制所有文件（保留权限和链接）

3. **烧写到分区**：
   - 格式化 rootfs 分区为 ext4
   - 挂载并复制内容
   - 确保权限正确

## 烧写过程

```
[0/6] 创建 GPT 分区表
[1/6] 烧写 idbloader.img
[2/6] 烧写 uboot.img
[3/6] 烧写 trust.img (如果存在)
[4/6] 烧写 boot.img (如果存在)
[5/6] 准备并烧写 rootfs (如果存在)
[6/6] 同步数据到磁盘
```

## 注意事项

### ⚠️ 重要警告

- **数据将被完全清除**：烧写会重建分区表，SD 卡上的所有数据将丢失
- **确认设备路径**：确保选择正确的设备，避免误操作系统盘
- **使用 root 权限**：必须使用 `sudo` 运行脚本

### 设备识别

- **SD 卡读卡器（USB）**：通常是 `/dev/sdb`、`/dev/sdc` 等
- **内置 SD 卡槽**：通常是 `/dev/mmcblk0`
- **分区命名**：
  - USB: `/dev/sdb1`, `/dev/sdb2`, ...
  - MMC: `/dev/mmcblk0p1`, `/dev/mmcblk0p2`, ...

### 时间预估

- **仅 Bootloader**：约 10 秒
- **Bootloader + Kernel**：约 30 秒
- **完整系统（含 rootfs）**：约 5-10 分钟（取决于 rootfs 大小）

## 启动系统

烧写完成后：

1. **安全弹出 SD 卡**
   ```bash
   # 脚本已自动 sync，可以直接拔出
   ```

2. **插入 RK3399 开发板**
   - 将 SD 卡插入开发板的 SD 卡槽
   - 确保金属触点朝下

3. **连接串口**（可选）
   ```bash
   # 波特率 1500000
   sudo minicom -D /dev/ttyUSB0 -b 1500000
   ```

4. **上电启动**
   - 插入电源
   - 观察 LED 指示灯
   - 如果有显示器，应该能看到启动画面

## 默认用户信息

如果烧写了 rootfs，系统默认用户：

- **普通用户**：`orangepi` / `orangepi`
- **Root 用户**：`root` / `orangepi`
- **主机名**：`orangepi-rk3399`

## 故障排除

### 无法启动

1. **检查串口输出**：
   - 确认波特率为 1500000
   - 查看是否有 U-Boot 输出

2. **验证烧写**：
   ```bash
   # 重新运行烧写脚本
   sudo ./scripts/flash_bootloader.sh
   ```

3. **检查 SD 卡**：
   - 使用高质量 SD 卡（推荐 Class 10 或 UHS-I）
   - 尝试其他 SD 卡

### Rootfs 烧写失败

如果 rootfs 太大或烧写失败：

1. **清理 rootfs**：
   ```bash
   sudo python3 scripts/build_rootfs.py --clean
   ```

2. **重新构建**：
   ```bash
   sudo python3 scripts/build_rootfs.py --type server
   ```

3. **使用更大的 SD 卡**：
   - 推荐至少 8GB SD 卡
   - Desktop 版本推荐 16GB 以上

### 权限错误

确保使用 root 权限：

```bash
sudo ./scripts/flash_bootloader.sh
```

## 仅烧写 Bootloader

如果只想烧写 bootloader 和 kernel（不包括 rootfs）：

```bash
# 删除或重命名 rootfs 目录
sudo mv build/rootfs build/rootfs.backup

# 烧写
sudo ./scripts/flash_bootloader.sh
```

## 高级用法

### 仅更新 Rootfs

如果只需要更新 rootfs（保留 bootloader）：

```bash
# 1. 直接挂载 rootfs 分区
sudo mount /dev/sdb4 /mnt  # USB 设备
# 或
sudo mount /dev/mmcblk0p4 /mnt  # SD 卡

# 2. 同步 rootfs 内容
sudo rsync -aAX build/rootfs/ /mnt/

# 3. 卸载
sudo umount /mnt
```

### 自定义分区大小

编辑 `flash_bootloader.sh` 中的分区定义：

```bash
BOOT_END=114687        # boot 分区结束位置
# rootfs 自动使用剩余空间
```

## 参考资料

- [U-Boot 构建指南](README.md)
- [Kernel 构建指南](docs/kernel_build_guide.md)
- [Rootfs 构建指南](docs/rootfs_build_guide.md)
- [清理指南](docs/clean_guide.md)
