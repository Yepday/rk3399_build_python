# 一键构建脚本使用说明

## 快速开始

```bash
# 构建所有 bootloader 镜像（idbloader.img + uboot.img）
python3 scripts/build_bootloader.py

# 清理构建输出
python3 scripts/build_bootloader.py --clean

# 查看帮助
python3 scripts/build_bootloader.py --help
```

## 功能特点

### ✅ 自动化构建流程

脚本会自动完成以下步骤：

1. **解析 RKBOOT INI 配置**
   - 读取 `test_data/RKBOOT/RK3399MINIALL.ini`
   - 获取 DDR init、miniloader 路径信息

2. **智能文件查找**
   - 如果 INI 中指定的文件不存在，自动在以下目录查找：
     - `test_data/rk33/`
     - `test_data/RKBOOT/bin/rk33/`
   - 优先匹配相同版本，如果找不到则使用最新版本

3. **构建 idbloader.img**
   - 使用 `rksd.py` 创建 rksd 格式镜像
   - 追加 miniloader 到镜像末尾
   - 输出到 `test_data/output/idbloader.img`

4. **构建 uboot.img**
   - 使用 `loaderimage.py` 为 U-Boot 添加 Rockchip Header
   - 输出到 `test_data/output/uboot.img`

5. **显示构建摘要**
   - 列出生成的文件及大小
   - 提供下一步烧写命令

### ✅ 不修改原始配置

脚本**不会修改** `test_data/RKBOOT/RK3399MINIALL.ini` 配置文件，即使其中指定的文件不存在也能正常工作。

### ✅ 清晰的输出信息

- 🔵 步骤提示：`[1/2] Building idbloader.img`
- ⚠️  警告信息：文件未找到时的替代方案
- ✅ 成功提示：每个构建步骤完成后的确认
- ❌ 错误信息：构建失败时的详细原因

## 命令行选项

### 基本用法

```bash
# 使用默认配置
python3 scripts/build_bootloader.py

# 指定自定义配置文件
python3 scripts/build_bootloader.py --config path/to/custom.ini

# 指定 U-Boot 二进制文件
python3 scripts/build_bootloader.py --uboot path/to/u-boot.bin

# 指定输出目录
python3 scripts/build_bootloader.py --output build/bootloader
```

### 高级选项

```bash
# 仅构建 idbloader.img（跳过 uboot.img）
python3 scripts/build_bootloader.py --skip-uboot

# 指定芯片类型
python3 scripts/build_bootloader.py --chip rk3328

# 自定义 U-Boot 加载地址
python3 scripts/build_bootloader.py --load-addr 0x300000

# 清理构建输出
python3 scripts/build_bootloader.py --clean
```

## 构建输出

默认输出目录：`test_data/output/`

```
test_data/output/
├── idbloader.img    # DDR init + miniloader (约 150KB)
└── uboot.img        # U-Boot 镜像 (约 4MB)
```

## 烧写到 SD 卡

构建完成后，使用以下命令烧写到 SD 卡：

### 方法 1：使用 dd 命令

```bash
# 假设 SD 卡设备是 /dev/mmcblk0 或 /dev/sdb

# 烧写 idbloader
sudo dd if=test_data/output/idbloader.img \
    of=/dev/mmcblk0 \
    seek=64 \
    conv=fsync \
    bs=512

# 烧写 uboot
sudo dd if=test_data/output/uboot.img \
    of=/dev/mmcblk0 \
    seek=16384 \
    conv=fsync \
    bs=512

sync  # 确保写入完成
```

### 方法 2：使用烧写脚本

```bash
# 自动烧写所有固件（交互式确认）
sudo ./scripts/flash_bootloader.sh /dev/mmcblk0 test_data/output
```

## 故障排查

### 问题 1：找不到 Python 模块

**错误信息**：
```
ImportError: No module named 'rkpyimg'
```

**解决方法**：
确保在项目根目录运行脚本：
```bash
cd /path/to/rk3399_build_python
python3 scripts/build_bootloader.py
```

### 问题 2：找不到二进制文件

**错误信息**：
```
FileNotFoundError: DDR init binary not found: ...
```

**解决方法**：
1. 检查 `test_data/rk33/` 目录是否包含必要的 `.bin` 文件
2. 或者将文件放到 `test_data/RKBOOT/bin/rk33/` 目录

必需的文件：
- `rk3399_ddr_800MHz_v*.bin` - DDR 初始化代码
- `rk3399_miniloader_v*.bin` 或 `rk3399_usbplug_v*.bin` - Miniloader
- `u-boot.bin` - U-Boot 二进制（如果构建 uboot.img）

### 问题 3：生成的镜像无法启动

**排查步骤**：
1. 验证镜像完整性：
   ```bash
   python3 -m rkpyimg.tools.rksd --verify test_data/output/idbloader.img
   ```

2. 检查文件大小：
   ```bash
   ls -lh test_data/output/
   # idbloader.img 应该在 120-200KB 之间
   # uboot.img 应该在 1-8MB 之间
   ```

3. 确认烧写到正确的扇区位置：
   - idbloader.img → 扇区 64
   - uboot.img → 扇区 16384

## 与原项目构建的对比

| 项目 | 原 OrangePi 项目 | 本项目 (Python) |
|------|-----------------|----------------|
| **语言** | Bash + C 工具链 | Python 3 |
| **依赖** | gcc, make, rktools | 仅 Python 3.8+ |
| **跨平台** | 仅 Linux | Windows/Linux/macOS |
| **构建速度** | ~30秒 | ~2秒 |
| **输出格式** | 100% 兼容 | 100% 兼容（MD5 一致） |
| **可调试性** | 困难 | 易于调试和修改 |

## 示例输出

```
============================================================
              Rockchip Bootloader Build System
============================================================

Configuration: test_data/RKBOOT/RK3399MINIALL.ini
Chip: rk3399
Output: test_data/output

Parsing configuration...
✓ Chip: RK330C, Version: 1.19

[1/2] Building idbloader.img
  DDR Init: rk3399_ddr_800MHz_v1.15.bin
  Miniloader: rk3399_miniloader_v1.15.bin

  Creating rksd format image...
  SPL size: 69980 bytes (68 KB)

  Appending miniloader...
✓ idbloader.img created: test_data/output/idbloader.img
  Size: 150,300 bytes (146 KB)

[2/2] Building uboot.img
  U-Boot: u-boot.bin
  Load Address: 0x00200000

✓ uboot.img created: test_data/output/uboot.img
  Size: 4,194,304 bytes (4096 KB)

============================================================
                       Build Summary
============================================================

Generated files:
  ✓ idbloader.img           150,300 bytes (   146 KB)
  ✓ uboot.img             4,194,304 bytes (  4096 KB)

Build completed successfully!
```

## 技术细节

### idbloader.img 构建原理

1. **创建 rksd 格式头部**
   - 在偏移 0x000 写入 RC4 加密的 header0
   - header0 包含签名 0x0FF0AA55 和 SPL 位置信息

2. **写入 DDR init 代码**
   - 在偏移 0x800 写入 DDR init 二进制
   - 前 4 字节是 "RK33" 魔数

3. **追加 miniloader**
   - 在 DDR init 后直接追加 miniloader
   - 无需对齐或填充

### uboot.img 构建原理

1. **添加 Rockchip Header**
   - 2048 字节的 header，包含：
     - Magic: "LOADER  "
     - Load Address: 0x200000
     - CRC32 校验和
     - SHA256 哈希

2. **写入 U-Boot 数据**
   - 在 header 之后写入 u-boot.bin 原始数据

## 参考文档

- [Bootloader 构建详解](../docs/bootloader_build_guide.md) - 详细的技术原理
- [固件打包原理](../docs/firmware_packing_theory.md) - 深入理解打包过程
- [RKSD 格式说明](../docs/rksd_format.md) - rksd 镜像格式规范
