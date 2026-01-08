# Loaderimage 工具完全教程

## 目录

1. [工具概述](#工具概述)
2. [快速开始](#快速开始)
3. [命令行使用](#命令行使用)
4. [Python API 使用](#python-api-使用)
5. [原理深度解析](#原理深度解析)
6. [实战案例](#实战案例)
7. [常见问题](#常见问题)

---

## 工具概述

### 什么是 loaderimage？

`loaderimage` 是 Rockchip 固件工具链中的关键工具，用于将原始二进制文件（如 `u-boot.bin`、`trust.bin`）封装成 Rockchip BootROM 可识别的镜像格式（`uboot.img`、`trust.img`）。

**rkpyimg 版本** 是用纯 Python 实现的替代方案，相比官方 C 语言工具具有以下优势：

- **跨平台**：Windows/Linux/macOS 无缝运行
- **易于集成**：可作为 Python 库直接导入项目
- **可读性强**：代码结构清晰，便于学习和二次开发
- **现代化**：类型注解、数据类、异常处理

### 核心功能

```
┌─────────────┐                      ┌──────────────┐
│ u-boot.bin  │  --[loaderimage]-->  │  uboot.img   │
│  (原始)     │                      │ (带 Header)  │
└─────────────┘                      └──────────────┘
     500KB                                4MB (4 copies)

每个 copy 包含：
[RK Header 2048B] + [u-boot.bin] + [Padding]
```

**三大功能**：
1. **Pack（打包）**：原始 bin → Rockchip 镜像
2. **Unpack（解包）**：Rockchip 镜像 → 原始 bin
3. **Info（查看信息）**：显示镜像头部信息

---

## 快速开始

### 安装

```bash
# 从源码安装（开发模式）
git clone https://github.com/your-repo/rkpyimg.git
cd rkpyimg
pip install -e .

# 或直接安装（发布后）
pip install rkpyimg
```

### 5 分钟快速体验

#### 1. 打包 U-Boot

```bash
# 最简单用法（使用默认配置）
python -m rkpyimg.tools.loaderimage --pack --uboot u-boot.bin uboot.img 0x200000

# 输出：
# pack input u-boot.bin
# pack file size: 524288 (512 KB)
# load addr is 0x200000!
# crc = 0x12345678
# pack uboot.img success!
```

#### 2. 查看镜像信息

```bash
python -m rkpyimg.tools.loaderimage --info uboot.img

# 输出：
# The image info:
# Rollback index is 0
# Load Addr is 0x200000
```

#### 3. 解包镜像

```bash
python -m rkpyimg.tools.loaderimage --unpack --uboot uboot.img extracted.bin

# 输出：
# unpack input uboot.img
# unpack extracted.bin success!
```

---

## 命令行使用

### 基本语法

```bash
python -m rkpyimg.tools.loaderimage [模式] [选项] <参数>
```

### 模式 1：Pack（打包）

#### U-Boot 打包

```bash
# 基本用法
loaderimage --pack --uboot <input.bin> <output.img> <load_addr>

# 示例：RK3399 U-Boot
loaderimage --pack --uboot u-boot.bin uboot.img 0x200000

# 自定义配置
loaderimage --pack --uboot u-boot.bin uboot.img 0x200000 \
    --size 1024 1      # 每个 copy 1024KB，只生成 1 个副本
    --version 5        # 设置 rollback 版本号为 5
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `input.bin` | 文件路径 | ✓ | 原始二进制文件 | - |
| `output.img` | 文件路径 | ✓ | 输出镜像文件 | - |
| `load_addr` | 十六进制 | ✓ | 加载地址 | - |
| `--size KB NUM` | 整数 | ✗ | 每个副本大小(KB) 和副本数 | 1024KB, 4 副本 |
| `--version` | 整数 | ✗ | Rollback 保护版本号 | 0 |

#### Trust 打包

```bash
# Trust 镜像（ATF + OP-TEE）
loaderimage --pack --trustos trust.bin trust.img 0x8400000

# 或者省略地址（自动使用 Trust 默认地址）
loaderimage --pack --trustos trust.bin trust.img
```

**U-Boot vs Trust 默认配置对比**：

| 配置项 | U-Boot | Trust |
|--------|--------|-------|
| Magic | `LOADER  ` | `TOS     ` |
| 默认加载地址 | `0x200000` | `0x8400000` |
| 默认最大尺寸 | 1MB | 1MB |
| 默认副本数 | 4 | 4 |

### 模式 2：Unpack（解包）

```bash
# 解包 U-Boot
loaderimage --unpack --uboot uboot.img u-boot-extracted.bin

# 解包 Trust
loaderimage --unpack --trustos trust.img trust-extracted.bin
```

**输出示例**：
```
unpack input uboot.img
Warning: CRC mismatch! Expected 0x12345678, got 0x87654321  # 如果校验失败
unpack u-boot-extracted.bin success!
```

### 模式 3：Info（查看信息）

```bash
loaderimage --info uboot.img
```

**输出示例**：
```
The image info:
Rollback index is 0
Load Addr is 0x200000
```

---

## Python API 使用

### 导入模块

```python
from rkpyimg.tools.loaderimage import (
    pack_uboot,
    pack_trust,
    unpack_loader_image,
    get_loader_info,
    SecondLoaderHeader,
)
```

### API 1：打包 U-Boot

```python
from pathlib import Path
from rkpyimg.tools.loaderimage import pack_uboot

# 基本用法
output_path = pack_uboot(
    input_file="u-boot.bin",
    output_file="uboot.img",
    load_addr=0x200000,
)
print(f"Created: {output_path}")

# 高级用法：自定义配置
output_path = pack_uboot(
    input_file="u-boot.bin",
    output_file="uboot.img",
    load_addr=0x200000,
    version=5,              # Rollback 保护版本
    max_size=2048 * 1024,   # 每个副本 2MB
    num_copies=2,           # 只生成 2 个副本
)
```

**函数签名**：
```python
def pack_uboot(
    input_file: str | Path,
    output_file: str | Path,
    load_addr: int = 0x200000,
    version: int = 0,
    max_size: int | None = None,
    num_copies: int | None = None,
) -> Path
```

### API 2：打包 Trust

```python
from rkpyimg.tools.loaderimage import pack_trust

output_path = pack_trust(
    input_file="trust.bin",
    output_file="trust.img",
    load_addr=0x8400000,  # Trust 默认地址
)
```

### API 3：解包镜像

```python
from rkpyimg.tools.loaderimage import unpack_loader_image

# 解包并获取 Header 信息
header, output_path = unpack_loader_image(
    input_file="uboot.img",
    output_file="u-boot-extracted.bin",
)

# 查看 Header 信息
print(header)
# 输出：
# SecondLoaderHeader(
#   type=UBOOT,
#   version=0,
#   load_addr=0x00200000,
#   load_size=524288 (512 KB),
#   crc32=0x12345678,
#   hash_len=32
# )

# 检查镜像类型
if header.is_uboot():
    print("This is a U-Boot image")
elif header.is_trust():
    print("This is a Trust image")
```

### API 4：查看镜像信息

```python
from rkpyimg.tools.loaderimage import get_loader_info

header = get_loader_info("uboot.img")
print(f"Load Address: 0x{header.loader_load_addr:08X}")
print(f"Size: {header.loader_load_size} bytes")
print(f"CRC32: 0x{header.crc32:08X}")
```

### API 5：直接操作 Header

```python
from rkpyimg.tools.loaderimage import SecondLoaderHeader

# 从文件解析 Header
header = SecondLoaderHeader.from_file("uboot.img")

# 手动创建 Header
header = SecondLoaderHeader(
    magic=b"LOADER  ",
    version=0,
    loader_load_addr=0x200000,
    loader_load_size=524288,
    crc32=0x12345678,
)

# 序列化为二进制
header_bytes = header.to_bytes()  # 返回 2048 字节

# 写入文件
with open("header.bin", "wb") as f:
    f.write(header_bytes)
```

---

## 原理深度解析

### RK Header 格式详解

Rockchip Second Loader Header 是 2048 字节的固定结构，包含以下关键信息：

```
┌─────────────────────────────────────────────────────────┐
│                    2048 Bytes Total                      │
├───────────┬───────────────────────────────────────────────┤
│ Offset    │ Field                                         │
├───────────┼───────────────────────────────────────────────┤
│ 0x000     │ Magic (8B): "LOADER  " or "TOS     "         │
│ 0x008     │ Version (4B): Rollback protection version    │
│ 0x00C     │ Reserved0 (4B)                               │
│ 0x010     │ Load Address (4B): DRAM 加载地址             │
│ 0x014     │ Load Size (4B): 数据大小（4 字节对齐）       │
│ 0x018     │ CRC32 (4B): 数据校验和                       │
│ 0x01C     │ Hash Length (4B): SHA256 长度 (32)           │
│ 0x020     │ SHA256 Hash (32B): 安全启动哈希               │
│ 0x040     │ Reserved1 (960B): 填充到 1024 字节           │
├───────────┼───────────────────────────────────────────────┤
│ 0x400     │ Sign Tag (4B): "SIGN" (0x4E474953)           │
│ 0x404     │ Sign Length (4B): RSA 签名长度               │
│ 0x408     │ RSA Signature (256B): RSA-2048 签名          │
│ 0x508     │ Reserved2 (760B): 填充到 2048 字节           │
└───────────┴───────────────────────────────────────────────┘
```

### 关键字段解析

#### 1. Magic（魔数）

```python
RK_UBOOT_MAGIC = b"LOADER  "  # 8 字节，用空格填充
RK_TRUST_MAGIC = b"TOS     "
```

- **作用**：BootROM 通过 Magic 识别镜像类型
- **注意**：必须严格 8 字节，不足部分用空格填充

#### 2. Load Address（加载地址）

```python
# 常见地址分配
RK3399:
  DDR:      0x00000000 - 0xFFFFFFFF
  U-Boot:   0x00200000  (2MB offset)
  ATF:      0x00010000  (64KB offset)
  OP-TEE:   0x08400000  (132MB offset)
```

- **作用**：BootROM 将镜像加载到此 DRAM 地址
- **来源**：通常由 SoC 厂商规定

#### 3. CRC32 校验

```python
# Rockchip 使用特定的 CRC32 多项式
def crc32_rk(data: bytes) -> int:
    """
    CRC32 校验（Rockchip 版本）
    多项式：0xEDB88320
    """
    # 见 rkpyimg/core/checksum.py
```

#### 4. SHA256 哈希

```python
# 计算顺序（必须严格遵守）
hash = SHA256(
    data +                      # 原始数据
    version (8 bytes) +         # 版本号（如果 > 0）
    load_addr (4 bytes) +       # 加载地址
    load_size (4 bytes) +       # 数据大小
    hash_len (4 bytes)          # 哈希长度
)
```

**注意事项**：
- 版本号为 0 时不参与哈希计算
- 所有整数使用小端序

### 打包流程详解

```python
def pack_loader_image(input_file, output_file, load_addr, ...):
    """完整打包流程"""

    # Step 1: 读取原始数据
    data = read_file(input_file)  # 如 u-boot.bin

    # Step 2: 4 字节对齐
    aligned_size = (len(data) + 3) & ~3
    padded_data = data.ljust(aligned_size, b'\x00')

    # Step 3: 计算 CRC32
    crc = crc32_rk(padded_data)

    # Step 4: 计算 SHA256
    sha_hash = calculate_sha256(
        padded_data, version, load_addr, aligned_size, hash_len=32
    )

    # Step 5: 构建 Header
    header = SecondLoaderHeader(
        magic=b"LOADER  ",
        version=0,
        loader_load_addr=load_addr,
        loader_load_size=aligned_size,
        crc32=crc,
        hash_len=32,
        hash=sha_hash,
    )

    # Step 6: 组装镜像块
    image_block = header.to_bytes() + padded_data
    image_block = image_block.ljust(max_size, b'\x00')  # 填充到 1MB

    # Step 7: 写入多个副本（默认 4 个）
    with open(output_file, 'wb') as f:
        for _ in range(num_copies):
            f.write(image_block)
```

### 为什么需要多个副本？

```
┌─────────┬─────────┬─────────┬─────────┐
│ Copy 0  │ Copy 1  │ Copy 2  │ Copy 3  │ = 4MB total
└─────────┴─────────┴─────────┴─────────┘
  1MB        1MB        1MB        1MB

目的：
1. 冗余备份：防止 Flash 单点损坏
2. BootROM 容错：按顺序尝试读取，任一成功即可
3. 升级安全：升级时保留旧版本
```

### 二进制序列化技术

#### struct 模块应用

```python
import struct

# 定义格式字符串
FORMAT = "<8sIIIIII"
#         │││││││└── 7 个无符号整数 (4 bytes each)
#         │└─────── 小端序
#         └──────── 8 字节字符串

# 打包（Python → Binary）
binary = struct.pack(
    FORMAT,
    b"LOADER  ",  # 8s
    0,            # I (version)
    0,            # I (reserved)
    0x200000,     # I (load_addr)
    524288,       # I (load_size)
    0x12345678,   # I (crc32)
    32,           # I (hash_len)
)

# 解包（Binary → Python）
magic, version, reserved, addr, size, crc, hash_len = struct.unpack(
    FORMAT, binary[:32]
)
```

#### 格式字符串速查表

| 字符 | C 类型 | Python 类型 | 字节数 |
|------|--------|-------------|--------|
| `<` | - | 小端序 | - |
| `s` | char[] | bytes | 可变 |
| `I` | unsigned int | int | 4 |
| `H` | unsigned short | int | 2 |
| `Q` | unsigned long long | int | 8 |

---

## 实战案例

### 案例 1：OrangePi RK3399 固件打包

**场景**：为 OrangePi RK3399 开发板打包自编译的 U-Boot

```bash
# 1. 编译 U-Boot
cd u-boot
make orangepi-rk3399_defconfig
make -j8
# 生成 u-boot.bin

# 2. 打包为 Rockchip 格式
python -m rkpyimg.tools.loaderimage \
    --pack \
    --uboot u-boot.bin uboot.img 0x200000 \
    --version 1

# 3. 验证镜像
python -m rkpyimg.tools.loaderimage --info uboot.img

# 4. 烧录到 eMMC/SD 卡（使用 rkdeveloptool 或 dd）
sudo rkdeveloptool wl 0x4000 uboot.img
```

### 案例 2：自动化构建脚本

**场景**：在 CI/CD 流程中自动打包固件

```python
#!/usr/bin/env python3
"""
自动化固件打包脚本
"""

from pathlib import Path
from rkpyimg.tools.loaderimage import pack_uboot, pack_trust, get_loader_info

def build_firmware(build_dir: Path, output_dir: Path):
    """构建完整固件"""

    # 1. 打包 U-Boot
    print("=== Packing U-Boot ===")
    uboot_img = pack_uboot(
        input_file=build_dir / "u-boot.bin",
        output_file=output_dir / "uboot.img",
        load_addr=0x200000,
        version=1,
    )

    # 2. 打包 Trust
    print("\n=== Packing Trust ===")
    trust_img = pack_trust(
        input_file=build_dir / "trust.bin",
        output_file=output_dir / "trust.img",
        load_addr=0x8400000,
    )

    # 3. 验证镜像
    print("\n=== Verification ===")
    for img in [uboot_img, trust_img]:
        header = get_loader_info(img)
        print(f"{img.name}: OK")
        print(f"  Load Addr: 0x{header.loader_load_addr:08X}")
        print(f"  Size: {header.loader_load_size} bytes")

    print("\n✓ Firmware build complete!")

if __name__ == "__main__":
    build_firmware(
        build_dir=Path("./build"),
        output_dir=Path("./output"),
    )
```

### 案例 3：镜像完整性检查

**场景**：下载固件后验证是否损坏

```python
from rkpyimg.tools.loaderimage import unpack_loader_image
from rkpyimg.core.checksum import crc32_rk

def verify_image(image_file: str) -> bool:
    """验证镜像完整性"""
    try:
        # 解包镜像
        header, temp_file = unpack_loader_image(image_file, "temp.bin")

        # 读取解包的数据
        with open(temp_file, "rb") as f:
            data = f.read()

        # 重新计算 CRC32
        calculated_crc = crc32_rk(data)

        # 对比校验和
        if calculated_crc == header.crc32:
            print(f"✓ CRC32 matched: 0x{calculated_crc:08X}")
            return True
        else:
            print(f"✗ CRC32 mismatch!")
            print(f"  Expected: 0x{header.crc32:08X}")
            print(f"  Got:      0x{calculated_crc:08X}")
            return False

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

# 使用
verify_image("uboot.img")
```

### 案例 4：批量处理多个镜像

```python
from pathlib import Path
from rkpyimg.tools.loaderimage import pack_uboot

# 为不同芯片打包
CHIP_CONFIGS = {
    "rk3399": {"load_addr": 0x200000},
    "rk3588": {"load_addr": 0x200000},
    "rk3568": {"load_addr": 0x200000},
}

for chip, config in CHIP_CONFIGS.items():
    input_file = f"build/{chip}/u-boot.bin"
    output_file = f"output/{chip}_uboot.img"

    if Path(input_file).exists():
        pack_uboot(
            input_file=input_file,
            output_file=output_file,
            **config,
        )
        print(f"✓ Packed {chip}")
```

---

## 常见问题

### Q1: 打包时报错 "Input file too large"

**原因**：输入文件超过单个副本的最大尺寸（默认 1MB - 2048 字节）

**解决方案**：
```bash
# 方法 1：增加单个副本大小
loaderimage --pack --uboot u-boot.bin uboot.img 0x200000 --size 2048 4

# 方法 2：使用 Python API
pack_uboot(
    "u-boot.bin",
    "uboot.img",
    load_addr=0x200000,
    max_size=2048 * 1024,  # 2MB
)
```

### Q2: CRC32 校验失败怎么办？

**可能原因**：
1. 传输过程中文件损坏
2. Flash 读取错误
3. 使用了错误的 CRC32 算法

**诊断步骤**：
```python
from rkpyimg.tools.loaderimage import unpack_loader_image

# 解包会自动显示 CRC 警告
header, output = unpack_loader_image("uboot.img", "out.bin")

# 手动验证
from rkpyimg.core.checksum import crc32_rk
with open("out.bin", "rb") as f:
    data = f.read()
print(f"Calculated CRC: 0x{crc32_rk(data):08X}")
print(f"Header CRC:     0x{header.crc32:08X}")
```

### Q3: 如何支持新的芯片型号？

**答**：loaderimage 是芯片无关的，只需调整加载地址：

```python
# RK3588 示例
pack_uboot(
    "u-boot.bin",
    "uboot.img",
    load_addr=0x200000,  # 查阅芯片手册获取正确地址
)
```

### Q4: 生成的镜像比原文件大很多？

**原因**：默认生成 4 个 1MB 副本 = 4MB 总大小

**优化方案**：
```bash
# 只生成 1 个副本，且减小单副本大小
loaderimage --pack --uboot u-boot.bin uboot.img 0x200000 --size 512 1
```

### Q5: 如何在 Python 脚本中捕获异常？

```python
from pathlib import Path
from rkpyimg.tools.loaderimage import pack_uboot

try:
    pack_uboot("u-boot.bin", "uboot.img", 0x200000)
except FileNotFoundError:
    print("Error: Input file not found!")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Q6: Rollback 版本号的作用？

**答**：用于防止降级攻击（安全启动功能）

```python
# 版本号单调递增
pack_uboot("u-boot.bin", "uboot_v1.img", 0x200000, version=1)
pack_uboot("u-boot.bin", "uboot_v2.img", 0x200000, version=2)

# BootROM 会拒绝加载版本号 < 当前版本的镜像
```

### Q7: 为什么有些字段是 Reserved？

**答**：Rockchip 为未来功能预留，目前填充 0 即可

```python
# 当前未使用的字段
header.reserved0 = 0      # 4 bytes
header.reserved1 = b'\x00' * 960
header.reserved2 = b'\x00' * 760
```

---

## 附录

### 参考资料

1. **官方 C 源码**：`D:\docs\proxy\build_rk3399\uboot\tools\rockchip\loaderimage.c`
2. **Rockchip BootROM 文档**：查阅芯片技术参考手册（TRM）
3. **相关工具**：
   - `boot_merger`: 合并 DDR init + miniloader
   - `trust_merger`: 合并 ATF + OP-TEE

### 术语表

| 术语 | 说明 |
|------|------|
| BootROM | 芯片内置的第一阶段启动代码 |
| Second Loader | 第二阶段加载器（U-Boot/ATF） |
| ATF | ARM Trusted Firmware（EL3 固件） |
| OP-TEE | 开源可信执行环境（TrustZone） |
| Rollback | 回滚保护，防止加载旧版本固件 |

### 开发者资源

- **GitHub 仓库**：https://github.com/your-repo/rkpyimg
- **问题反馈**：提交 Issue 到 GitHub
- **贡献代码**：欢迎提交 Pull Request

---

## 总结

本教程涵盖了 loaderimage 工具的：

1. **基础使用** - 命令行和 Python API
2. **原理解析** - Header 格式、打包流程、二进制序列化
3. **实战案例** - 固件打包、自动化构建、完整性检查
4. **问题解答** - 常见错误和解决方案

**下一步学习**：
- 学习 `boot_merger` 工具：合并 DDR init 和 miniloader
- 学习 `trust_merger` 工具：合并 ATF 和 OP-TEE
- 完整固件构建流程：从源码到可刷写镜像

**实践建议**：
1. 先在虚拟环境中测试打包流程
2. 使用真实固件前务必验证 CRC32
3. 保留原始固件备份
4. 阅读芯片手册确认加载地址

祝开发顺利！
