# rkpyimg

> 纯 Python 实现的 Rockchip 固件打包工具

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**首个 Python 实现**的 Rockchip 官方固件打包工具（`boot_merger`、`trust_merger`、`loaderimage`）。

## 为什么做这个项目？

Rockchip 官方工具的问题：
- C 语言二进制文件，缺乏文档
- 难以集成到现代 CI/CD 流程
- 跨平台支持差
- 难以理解和修改

**rkpyimg** 提供：
- ✅ 纯 Python 3.10+ 实现
- ✅ 完整类型注解和现代 API
- ✅ 跨平台支持（Windows/Linux/macOS）
- ✅ 详细的二进制格式文档
- ✅ 易于集成到构建系统

## 支持的工具

| 工具 | 状态 | 说明 |
|------|------|------|
| `loaderimage` | ✅ 完成 | 打包/解包 U-Boot 和 Trust 二进制 |
| `boot_merger` | ✅ 完成 | 合并 DDR 初始化代码和 miniloader |
| `trust_merger` | ✅ 完成 | 合并 BL31 (ATF) 和 BL32 (OP-TEE) |

## 支持的芯片

| 芯片 | 状态 | 适用设备 |
|------|------|----------|
| RK3399 | ✅ 支持 | Orange Pi RK3399, Firefly, NanoPC-T4 |
| RK3588/RK3588S | 🔜 计划中 | Orange Pi 5, Rock 5B |
| RK3568/RK3566 | 🔜 计划中 | Quartz64, ROC-RK3568-PC |
| RK3328 | 🔜 计划中 | Rock64, Renegade |

## 安装

### 从源码安装（推荐）

```bash
# 克隆仓库
git clone https://github.com/yourusername/rkpyimg.git
cd rkpyimg

# 安装（开发模式）
pip install -e .

# 验证安装
rkpyimg --version
```

### 从 PyPI 安装（即将上线）

```bash
pip install rkpyimg
```

## 快速开始

rkpyimg 提供三个子命令，对应 Rockchip 的三个官方工具：

```bash
rkpyimg loaderimage --help    # U-Boot/Trust 打包工具
rkpyimg boot-merger --help    # Boot loader 合并工具
rkpyimg trust-merger --help   # Trust 镜像合并工具
```

## 使用指南

### 1. loaderimage - 打包 U-Boot 镜像

**功能**：将 u-boot.bin 打包为带 Rockchip 头部的 uboot.img

```bash
# 打包 U-Boot（默认加载地址 0x200000）
rkpyimg loaderimage pack u-boot.bin uboot.img 0x200000

# 打包 Trust OS（加载地址 0x8400000）
rkpyimg loaderimage pack trust.bin trust.img --type trust

# 解包镜像
rkpyimg loaderimage unpack uboot.img u-boot.bin

# 查看镜像信息
rkpyimg loaderimage info uboot.img
```

**输出示例**：
```
Packing loader image (type=uboot, addr=0x200000):
  Input:  u-boot.bin (520192 bytes)
  Output: uboot.img
  Header: 2048 bytes
  Data:   520192 bytes
  Total:  522240 bytes
The image info:
Rollback index is 0
Load Addr is 0x200000
✓ Packed: uboot.img
```

---

### 2. boot-merger - 合并 DDR 和 Miniloader

**功能**：根据 INI 配置文件，合并 DDR 初始化代码和 miniloader 为 idbloader.img

#### 2.1 准备 INI 配置文件

示例：`RKBOOT/RK3399MINIALL.ini`

```ini
[CHIP_NAME]
NAME=RK330C

[VERSION]
MAJOR=2
MINOR=58

[CODE471_OPTION]
NUM=1
Path1=bin/rk33/rk3399_ddr_800MHz_v1.25.bin

[CODE472_OPTION]
NUM=1
Path1=bin/rk33/rk3399_miniloader_v1.26.bin

[OUTPUT]
PATH=rk3399_loader_v1.25.126.bin
```

#### 2.2 打包镜像

```bash
# 从 INI 文件打包
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini

# 指定输出路径
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini -o idbloader.img

# 启用 RC4 加密（可选）
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini --rc4

# 详细输出
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini --verbose
```

#### 2.3 解包镜像

```bash
# 解包到默认目录 (unpacked/)
rkpyimg boot-merger unpack idbloader.img

# 解包到指定目录
rkpyimg boot-merger unpack idbloader.img -o output_dir
```

**输出示例**：
```
Boot Merger - Pack from INI
  Chip: RK330C (0x33304343)
  Version: 2.58 (BCD)
  Output: idbloader.img
  RC4 Encryption: Disabled

Loading CODE471 entries (DDR init):
  [0] rk3399_ddr_800MHz_v1.25.bin (143360 bytes)

Loading CODE472 entries (Miniloader):
  [0] rk3399_miniloader_v1.26.bin (65536 bytes)

Writing boot header (102 bytes)
Writing entries (108 bytes total, 2 entries)
Writing CODE471 data (143360 bytes, aligned to 145408)
Writing CODE472 data (65536 bytes, aligned to 67584)
Writing CRC32 checksum: 0xABCD1234

✓ Packed: idbloader.img (213302 bytes)
```

---

### 3. trust-merger - 合并 BL31 和 BL32

**功能**：根据 INI 配置文件，合并 ARM Trusted Firmware (BL31) 和 OP-TEE (BL32) 为 trust.img

#### 3.1 准备 INI 配置文件

示例：`RKTRUST/RK3399TRUST.ini`

```ini
[VERSION]
MAJOR=1
MINOR=0

[BL31_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl31_v1.35.elf
ADDR=0x10000

[BL32_OPTION]
SEC=1
PATH=bin/rk33/rk3399_bl32_v2.01.bin
ADDR=0x8400000

[OUTPUT]
PATH=trust.img
```

#### 3.2 打包镜像

```bash
# 从 INI 文件打包（使用默认 RSA/SHA 模式）
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini

# 指定输出路径
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini -o trust.img

# 指定 RSA 和 SHA 模式
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini --rsa 4 --sha 2

# 指定镜像大小（KB）
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini --size 1024

# 详细输出
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini --verbose
```

**RSA/SHA 模式说明**：
- RSA: `0`=none, `1`=1024, `2`=2048, `3`=2048 PSS, `4`=2048 new (默认)
- SHA: `0`=none, `1`=SHA1, `2`=SHA256 (默认), `3`=SHA512

#### 3.3 解包镜像

```bash
# 解包到当前目录
rkpyimg trust-merger unpack trust.img

# 解包到指定目录
rkpyimg trust-merger unpack trust.img -o output_dir
```

**输出示例**：
```
Trust Merger - Pack from INI
  Version: 1.0 (BCD)
  Output: trust.img
  RSA Mode: 4 (RSA 2048 new)
  SHA Mode: 2 (SHA256)
  Size: 1024 KB

Loading components:
  [BL31] bin/rk33/rk3399_bl31_v1.35.elf
    -> Extracted PT_LOAD segment: 65536 bytes @ 0x10000
  [BL32] bin/rk33/rk3399_bl32_v2.01.bin
    -> Loaded binary: 143360 bytes @ 0x8400000

Writing trust header (2048 bytes)
Writing component data (96 bytes, 2 components)
Writing trust components (32 bytes)
Writing BL31 component (65536 bytes, aligned to 67584)
Writing BL32 component (143360 bytes, aligned to 145408)

✓ Packed: trust.img (215168 bytes)
```

---

## 完整固件构建流程

以 RK3399 为例，构建完整的固件需要以下步骤：

### 步骤 1: 准备二进制文件

确保你有以下文件：
```
project/
├── bin/rk33/
│   ├── rk3399_ddr_800MHz_v1.25.bin      # DDR 初始化
│   ├── rk3399_miniloader_v1.26.bin      # Miniloader
│   ├── rk3399_bl31_v1.35.elf            # ARM Trusted Firmware
│   └── rk3399_bl32_v2.01.bin            # OP-TEE
├── u-boot.bin                           # U-Boot 二进制
├── RKBOOT/RK3399MINIALL.ini             # Boot 配置
└── RKTRUST/RK3399TRUST.ini              # Trust 配置
```

### 步骤 2: 打包各个镜像

```bash
# 1. 打包 idbloader.img (DDR + Miniloader)
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini -o idbloader.img

# 2. 打包 uboot.img
rkpyimg loaderimage pack u-boot.bin uboot.img 0x200000

# 3. 打包 trust.img (BL31 + BL32)
rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini -o trust.img
```

### 步骤 3: 烧录到设备

使用 `dd` 命令将镜像写入 SD 卡或 eMMC：

```bash
# 烧录 idbloader.img 到扇区 64 (32KB 偏移)
sudo dd if=idbloader.img of=/dev/sdX seek=64 conv=notrunc

# 烧录 uboot.img 到扇区 16384 (8MB 偏移)
sudo dd if=uboot.img of=/dev/sdX seek=16384 conv=notrunc

# 烧录 trust.img 到扇区 24576 (12MB 偏移)
sudo dd if=trust.img of=/dev/sdX seek=24576 conv=notrunc
```

**注意**：`/dev/sdX` 替换为实际设备名（如 `/dev/sdb`）

---

## 验证构建结果

### 1. 验证镜像信息

```bash
# 查看 uboot.img 信息
rkpyimg loaderimage info uboot.img

# 解包验证
rkpyimg loaderimage unpack uboot.img u-boot-extracted.bin
diff u-boot.bin u-boot-extracted.bin  # 应该一致
```

### 2. 验证 boot-merger 输出

```bash
# 解包并检查
rkpyimg boot-merger unpack idbloader.img -o verify_boot

# 检查解包的文件
ls -lh verify_boot/
# 应该看到 CODE471.bin, CODE472.bin 等文件

# 验证文件大小和内容
md5sum bin/rk33/rk3399_ddr_800MHz_v1.25.bin verify_boot/CODE471.bin
```

### 3. 验证 trust-merger 输出

```bash
# 解包并检查
rkpyimg trust-merger unpack trust.img -o verify_trust

# 检查解包的组件
ls -lh verify_trust/
# 应该看到 BL31, BL32 等文件
```

### 4. 二进制对比验证

如果你有官方工具生成的镜像，可以对比：

```bash
# 使用官方 C 工具生成
./boot_merger RKBOOT/RK3399MINIALL.ini
mv idbloader.img idbloader_official.img

# 使用 rkpyimg 生成
rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini -o idbloader_python.img

# 对比两个文件
xxd idbloader_official.img > official.hex
xxd idbloader_python.img > python.hex
diff official.hex python.hex
```

---

## Python API 使用

除了命令行工具，rkpyimg 也提供 Python API：

### loaderimage API

```python
from rkpyimg.tools.loaderimage import pack_loader_image, unpack_loader_image, get_loader_info

# 打包
pack_loader_image(
    "u-boot.bin",
    "uboot.img",
    load_addr=0x200000,
    image_type="uboot",
    version=0
)

# 解包
unpack_loader_image("uboot.img", "u-boot-extracted.bin")

# 获取信息
header = get_loader_info("uboot.img")
print(f"Load address: 0x{header.loader_load_addr:08X}")
```

### boot_merger API

```python
from rkpyimg.tools.boot_merger import BootMerger

# 从 INI 文件加载
merger = BootMerger.from_ini("RKBOOT/RK3399MINIALL.ini")

# 启用 RC4 加密（可选）
merger.enable_rc4 = True

# 打包
merger.pack("idbloader.img")

# 解包
merger.unpack("idbloader.img", "output_dir")
```

### trust_merger API

```python
from rkpyimg.tools.trust_merger import TrustMerger

# 从 INI 文件加载
merger = TrustMerger.from_ini("RKTRUST/RK3399TRUST.ini")

# 配置 RSA/SHA 模式
merger.set_rsa_mode(4)  # RSA 2048 new
merger.set_sha_mode(2)  # SHA256
merger.size = 1024      # 1024 KB

# 打包
merger.pack("trust.img")

# 解包
files = TrustMerger.unpack("trust.img", "output_dir")
for name, path in files.items():
    print(f"{name}: {path}")
```

---

## 开发和测试

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_boot_merger.py -v

# 生成覆盖率报告
pytest --cov=rkpyimg --cov-report=html
```

### 代码质量检查

```bash
# 类型检查
mypy src/

# 代码检查
ruff check src/ tests/

# 代码格式化
ruff format src/ tests/
```

---

## 常见问题

### Q: 生成的镜像和官方工具不一致？

A: 检查以下几点：
1. INI 配置文件路径是否正确
2. 二进制文件版本是否一致
3. 是否启用了 RC4 加密（官方工具默认禁用）
4. 使用 `--verbose` 查看详细输出

### Q: 支持哪些 Python 版本？

A: Python 3.10+ （使用了类型注解的新语法）

### Q: 如何获取 DDR/miniloader/BL31/BL32 二进制文件？

A: 可以从以下来源获取：
- Rockchip 官方 SDK
- U-Boot 仓库（rkbin 分支）
- Armbian 构建脚本
- 设备厂商（OrangePi、Firefly 等）

### Q: 是否支持签名（RSA）？

A: 目前支持 RSA 模式配置，但不实现实际签名功能。镜像会预留 RSA 签名区域。

---

## 镜像布局参考

Rockchip RK3399 标准分区布局：

```
扇区        偏移量      大小      分区           内容
------      -------     -----     ---------      -------
64          32KB        4MB       idbloader      DDR 初始化 + Miniloader
16384       8MB         4MB       uboot          U-Boot 引导程序
24576       12MB        4MB       trust          ARM Trusted Firmware + OP-TEE
32768       16MB        32MB      boot           内核 + 设备树 + Initramfs
98304       48MB        ...       rootfs         根文件系统 (ext4)
```

---

## 参与贡献

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

### 需要帮助的方向

- [ ] 添加更多芯片支持（RK3588, RK3568 等）
- [ ] 实现 GPT 分区和完整镜像构建
- [ ] 添加更多测试用例
- [ ] 完善文档和教程
- [ ] 性能优化

---

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)

---

## 致谢

- [Rockchip](https://www.rock-chips.com/) - 原始 C 工具
- [OrangePi](http://www.orangepi.org/) - RK3399 参考实现
- [Armbian](https://www.armbian.com/) 社区 - 文档贡献
- [U-Boot](https://github.com/u-boot/u-boot) - rkbin 二进制文件

---

## 相关项目

- [rkbin](https://github.com/rockchip-linux/rkbin) - Rockchip 官方二进制文件
- [rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) - Rockchip USB 烧录工具
- [pyUBoot](https://github.com/molejar/pyUBoot) - U-Boot 镜像操作工具
