# Rockchip RK3399 Bootloader 固件构建详解

## 目录
- [启动流程概述](#启动流程概述)
- [固件文件说明](#固件文件说明)
- [固件构建流程](#固件构建流程)
- [烧写到存储设备](#烧写到存储设备)

---

## 启动流程概述

RK3399 芯片从上电到启动 Linux 系统，需要经过多个阶段：

```
┌────────────────┐
│   上电复位      │
└───────┬────────┘
        ↓
┌────────────────┐
│   BootROM      │  ← 芯片内置，不可修改
│  (片内代码)     │     读取存储设备查找引导程序
└───────┬────────┘
        ↓
┌────────────────┐
│  idbloader.img │  ← 第一阶段引导 (本文重点)
│  ├─ DDR Init   │     初始化内存控制器
│  └─ Miniloader │     极简加载器
└───────┬────────┘
        ↓
┌────────────────┐
│   uboot.img    │  ← U-Boot 引导程序
│                │     提供启动菜单、加载内核
└───────┬────────┘
        ↓
┌────────────────┐
│   trust.img    │  ← ARM TrustZone 安全固件
│  ├─ BL31 (ATF) │     ARM Trusted Firmware
│  └─ BL32 (TEE) │     OP-TEE 可信执行环境
└───────┬────────┘
        ↓
┌────────────────┐
│  Linux Kernel  │
└────────────────┘
```

### 为什么需要这么多阶段？

1. **BootROM 限制**：芯片内置代码只有几十KB，只能做最基础的引导
2. **内存未初始化**：上电时 DDR 内存不可用，需要专门代码初始化
3. **安全启动**：TrustZone 需要在独立环境运行，提供安全服务
4. **功能分离**：每个阶段职责清晰，便于调试和更新

---

## 固件文件说明

### 1. idbloader.img - 第一阶段引导

**作用**：启动系统的第一步，初始化硬件和内存

**组成部分**：
```
idbloader.img (约 150KB)
├─ Header (2KB)           # 引导信息，告诉 BootROM 如何加载
├─ DDR Init (68KB)        # rk3399_ddr_800MHz_v1.15.bin
│  └─ 功能：配置 DDR4/LPDDR3/LPDDR4 内存时序参数
└─ Miniloader (75KB)      # rk3399_miniloader_v1.15.bin
   └─ 功能：从存储设备加载 U-Boot 到内存
```

**存储位置**：SD卡/eMMC 的扇区 64（偏移 32KB）

**关键特性**：
- 使用 **rksd 格式**（SD/eMMC 启动专用）
- Header 经过 RC4 加密（防止篡改）
- 包含 "RK33" 魔数标识芯片型号

---

### 2. uboot.img - U-Boot 引导程序

**作用**：提供启动选项、加载操作系统

**组成部分**：
```
uboot.img (约 700KB)
├─ Rockchip Header (2KB)  # "LOADER" 魔数
│  ├─ 加载地址：0x200000
│  ├─ CRC32 校验
│  └─ SHA256 哈希
└─ U-Boot Binary          # u-boot.bin（编译生成）
```

**存储位置**：扇区 16384（偏移 8MB）

**功能**：
- 显示启动菜单（选择内核版本）
- 从 SD/eMMC/USB 加载内核
- 设置内核启动参数
- 提供命令行（调试用）

---

### 3. trust.img - ARM 安全固件

**作用**：提供安全服务和电源管理

**组成部分**：
```
trust.img (约 300KB)
├─ Rockchip Header (2KB)  # "TOS" 魔数
├─ BL31 - ATF (130KB)     # ARM Trusted Firmware
│  └─ 功能：CPU 电源管理、PSCI 接口
└─ BL32 - OP-TEE (170KB)  # 可信执行环境
   └─ 功能：安全存储、DRM、密钥管理
```

**存储位置**：扇区 24576（偏移 12MB）

**关键作用**：
- CPU 核心的睡眠/唤醒控制
- 安全启动链验证
- DRM 视频解密（Netflix 等）

---

## 固件构建流程

### 流程图

```
原始二进制文件
    ↓
┌─────────────────────────────┐
│ 1. idbloader.img 构建       │
│                             │
│  DDR Init Binary            │
│       ↓                     │
│  [rksd 工具]                │
│   - 添加 rksd header        │
│   - RC4 加密头部            │
│   - 对齐到 2KB              │
│       ↓                     │
│  临时文件 (73KB)            │
│       ↓                     │
│  追加 Miniloader            │
│       ↓                     │
│  idbloader.img (150KB)      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 2. uboot.img 构建           │
│                             │
│  u-boot.bin (编译生成)      │
│       ↓                     │
│  [loaderimage 工具]         │
│   - 添加 Rockchip Header    │
│   - 计算 CRC32 和 SHA256    │
│   - 设置加载地址 0x200000   │
│       ↓                     │
│  uboot.img                  │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 3. trust.img 构建           │
│                             │
│  BL31 + BL32 Binary         │
│       ↓                     │
│  [trust_merger 工具]        │
│   - 读取 RKTRUST/*.ini      │
│   - 合并 BL31/BL32          │
│   - 添加 TOS Header         │
│       ↓                     │
│  trust.img                  │
└─────────────────────────────┘
```

---

### 详细步骤

#### Step 1: 构建 idbloader.img

**使用的工具**：`rksd.py`（Python 实现的 mkimage rksd 格式）

**输入文件**：
- `rk3399_ddr_800MHz_v1.15.bin` - DDR 初始化代码
- `rk3399_miniloader_v1.15.bin` - Miniloader

**执行命令**：
```bash
# 第 1 步：创建 rksd 格式基础镜像
python3 rksd.py --pack -n rk3399 \
    -d rk3399_ddr_800MHz_v1.15.bin \
    idbloader.img

# 输出：
# - 在偏移 0x000 写入 RC4 加密的 header0
# - 在偏移 0x800 写入 DDR init 代码（带 RK33 魔数）
# - 对齐到 140 blocks (71680 字节)

# 第 2 步：追加 miniloader
python3 rksd.py --append \
    idbloader.img \
    rk3399_miniloader_v1.15.bin

# 输出：
# - 在 DDR init 后面直接追加 miniloader
# - 最终文件大小：150300 字节
```

**生成的镜像结构**：
```
偏移量      大小     内容
0x00000     512B     Header0 (RC4 加密)
                     ├─ signature: 0x0FF0AA55
                     ├─ init_offset: 4 (从第 4 个扇区开始)
                     ├─ init_size: 140 blocks
                     └─ disable_rc4: 1

0x00200     1.5KB    填充 (对齐到 2KB)

0x00800     4B       SPL Header: "RK33"
0x00804     68KB     DDR Init 代码
                     └─ 配置内存控制器、训练时序

0x11800     75KB     Miniloader
                     └─ 从 SD/eMMC 加载 U-Boot
```

**为什么这样设计？**

1. **Header0 RC4 加密**：防止恶意修改引导参数
2. **2KB 对齐**：BootROM 要求 SPL 必须从 2KB 边界开始
3. **分两部分**：DDR init 运行在片内 SRAM，Miniloader 运行在已初始化的 DDR

---

#### Step 2: 构建 uboot.img

**使用的工具**：`loaderimage.py`

**输入文件**：
- `u-boot.bin` - U-Boot 编译输出

**执行命令**：
```bash
python3 loaderimage.py --pack \
    --type uboot \
    --addr 0x200000 \
    u-boot.bin uboot.img
```

**生成的镜像结构**：
```
偏移量      大小     内容
0x0000      8B       Magic: "LOADER  "
0x0008      4B       Version: 0
0x000C      4B       Reserved
0x0010      4B       Load Address: 0x00200000
0x0014      4B       Load Size: (实际大小)
0x0018      4B       CRC32: (校验和)
0x001C      4B       Hash Length: 32
0x0020      32B      SHA256 Hash
0x0040      960B     Reserved
0x0400      4B       Sign Tag: "SIGN"
0x0404      4B       Sign Length: 0
0x0408      256B     RSA Signature (空)
0x0508      760B     Reserved
0x0800      ...      U-Boot Binary Data
```

**关键参数说明**：

- **Load Address (0x200000)**：U-Boot 在内存中的运行地址
  - RK3399 内存布局：
    - 0x000000 - 0x100000: BootROM/SRAM
    - 0x200000 - 0xXXXXXX: U-Boot 运行区
    - 0x02000000+: Linux 内核加载区

- **CRC32 校验**：Miniloader 会验证，防止文件损坏
- **SHA256 哈希**：安全启动时验证签名

---

#### Step 3: 构建 trust.img

**使用的工具**：`trust_merger.py`

**输入文件**：
- `RKTRUST/RK3399TRUST.ini` - 配置文件
- `rk3399_bl31_v1.36.elf` - ARM Trusted Firmware
- `rk3399_bl32_v2.01.bin` - OP-TEE (可选)

**配置文件示例**：
```ini
[VERSION]
MAJOR=1
MINOR=0

[BL31_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl31_v1.36.elf
ADDR=0x00010000        # BL31 加载地址
OPTION=
ATFLOAD=0x00010000

[BL32_OPTION]
SEC=0                  # 0=不使用 OP-TEE
PATH=
ADDR=0x08400000

[OUTPUT]
PATH=trust.img
```

**执行命令**：
```bash
python3 trust_merger.py --pack \
    RKTRUST/RK3399TRUST.ini
```

**生成过程**：
1. 解析 INI 配置，读取 BL31 ELF 文件
2. 从 ELF 提取可执行段（.text、.data）
3. 添加 "TOS" 格式 Header
4. 计算 CRC32 和 SHA256
5. 输出 trust.img

**生成的镜像结构**：
```
偏移量      大小     内容
0x0000      8B       Magic: "TOS     "
0x0008      4B       Version: 0
0x0010      4B       Load Address: 0x00010000
0x0014      4B       Load Size
0x0018      4B       CRC32
0x001C      4B       Hash Length: 32
0x0020      32B      SHA256 Hash
...
0x0800      ...      BL31 Binary Data
0xXXXXX     ...      BL32 Binary Data (如果启用)
```

---

## 烧写到存储设备

### 存储布局

所有固件在 SD/eMMC 上的位置是固定的（由 Rockchip 规范定义）：

```
SD/eMMC 扇区布局 (每扇区 512 字节)

扇区 0-63         32KB      MBR / GPT 分区表
扇区 64           32KB ↓    idbloader.img 起始位置 ←【重要】
                  ...       (约 150KB / 294 扇区)
扇区 16384        8MB ↓     uboot.img 起始位置
                  ...       (约 1MB)
扇区 24576        12MB ↓    trust.img 起始位置
                  ...       (约 1MB)
扇区 32768        16MB ↓    保留区
扇区 65536        32MB ↓    第一个分区（通常是 /boot）
```

### 烧写命令

使用 `dd` 工具将固件写入指定扇区：

```bash
# 假设 SD 卡设备是 /dev/mmcblk0

# 1. 烧写 idbloader
sudo dd if=idbloader.img \
    of=/dev/mmcblk0 \
    seek=64 \
    conv=notrunc,fsync \
    bs=512

# 2. 烧写 uboot
sudo dd if=uboot.img \
    of=/dev/mmcblk0 \
    seek=16384 \
    conv=notrunc,fsync \
    bs=512

# 3. 烧写 trust
sudo dd if=trust.img \
    of=/dev/mmcblk0 \
    seek=24576 \
    conv=notrunc,fsync \
    bs=512

sync  # 确保写入完成
```

**参数说明**：
- `seek=N`：跳过 N 个扇区后开始写入
- `conv=notrunc`：不截断目标文件（保留分区数据）
- `conv=fsync`：强制同步到磁盘
- `bs=512`：每次读写 512 字节（1 扇区）

### 验证烧写结果

```bash
# 读取 idbloader 的前 512 字节（Header0）
sudo dd if=/dev/mmcblk0 \
    skip=64 \
    count=1 \
    bs=512 | hexdump -C

# 应该看到类似输出（RC4 加密的数据）：
# 00000000  3b 8c dc fc be 9f 9d 51  eb 30 34 ce 24 51 1f 98
# ...

# 读取扇区 68 (0x800 偏移) 应该看到 "RK33"
sudo dd if=/dev/mmcblk0 \
    skip=68 \
    count=1 \
    bs=512 | hexdump -C | head -1

# 应该看到：
# 00000000  52 4b 33 33 ...  |RK33...|
```

---

## 常见问题

### Q1: 为什么 idbloader.img 不是 boot_merger 生成的？

**A**: 有两种格式的 loader：

| 格式 | 工具 | 用途 | 文件名 |
|------|------|------|--------|
| **rksd** | mkimage/rksd.py | SD/eMMC 启动 | idbloader.img |
| **boot** | boot_merger | USB/Maskrom 烧录 | rk3399_loader_v1.xx.bin |

SD 卡启动必须用 rksd 格式，因为 BootROM 从存储设备读取时需要特定的头部结构。

---

### Q2: 为什么 Header0 要 RC4 加密？

**A**: BootROM 的安全机制：
1. 读取扇区 0（Header0）
2. 用固定密钥 RC4 解密
3. 验证 signature (0x0FF0AA55)
4. 读取 `init_offset` 和 `init_size` 参数
5. 加载 SPL 到 SRAM 执行

如果不加密，恶意程序可以修改参数，绕过安全检查。

---

### Q3: DDR Init 代码为什么这么重要？

**A**: 上电时 DDR 内存处于未初始化状态：
- 时钟未配置
- 阻抗未校准
- 读写时序未训练

DDR Init 代码会：
1. 配置 DDR PHY 时钟（800MHz、933MHz 等）
2. 运行 ZQ 阻抗校准
3. 执行读写时序训练（找到最佳采样点）
4. 测试内存完整性

没有它，系统无法使用 DDR，后续程序无法加载。

---

### Q4: 可以跳过 trust.img 吗？

**A**: 可以，但会失去部分功能：
- **必须**：CPU 电源管理（suspend/resume 不工作）
- **可选**：安全启动、DRM、OP-TEE

调试阶段可以不烧写 trust.img，但生产环境强烈建议使用。

---

## 总结

Rockchip 固件构建的核心流程：

```
原始二进制 → 添加专有 Header → 计算校验和 → 烧写到固定位置
```

**三个关键固件**：
1. **idbloader.img** (150KB) - 初始化硬件，加载 U-Boot
2. **uboot.img** (700KB) - 启动菜单，加载内核
3. **trust.img** (300KB) - 安全服务，电源管理

**Python 工具链优势**：
- ✅ 跨平台（Windows/Linux/macOS）
- ✅ 易于调试和修改
- ✅ 100% 兼容官方格式
- ✅ 适合教学和理解原理

本文档展示了如何用 Python 工具复现官方构建流程，验证结果显示生成的 idbloader.img 与官方工具完全一致（MD5 相同）。
