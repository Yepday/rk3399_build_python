# RK3399 Bootloader 完整构建流程

本文档说明如何从零开始构建 RK3399 bootloader，包括下载 U-Boot 源码、编译和打包。

## 📁 新的目录结构

```
rk3399_build_python/
├── build/                      # 构建产物（新）
│   ├── boot/                   # Boot 阶段输出
│   │   ├── idbloader.img      # DDR init + miniloader
│   │   ├── uboot.img          # U-Boot bootloader
│   │   ├── trust.img          # ATF + OP-TEE（可选）
│   │   └── u-boot.bin         # U-Boot 编译产物
│   ├── kernel/                 # 内核输出（未来）
│   └── image/                  # 完整镜像（未来）
│
├── components/                 # 源码组件（新）
│   ├── uboot/                  # U-Boot 源码
│   │   └── ... (git clone)
│   ├── toolchain/              # 交叉编译工具链
│   │   └── bin/aarch64-linux-gnu-*
│   └── firmware/               # 二进制固件（DDR init、miniloader 等）
│
├── configs/                    # 配置文件（新）
│   ├── RKBOOT/                 # Boot 配置
│   │   └── RK3399MINIALL.ini
│   └── RKTRUST/                # Trust 配置
│       └── RK3399TRUST.ini
│
├── scripts/                    # 构建脚本
│   ├── build_all.py           # 一键构建脚本（新）
│   ├── build_uboot.py         # U-Boot 编译脚本（新）
│   ├── build_bootloader.py    # 镜像打包脚本（更新）
│   └── flash_bootloader.sh    # 烧写脚本（更新）
│
└── test_data/                  # 测试数据（兼容旧版）
    ├── rk33/                   # 二进制文件
    ├── RKBOOT/                 # 配置（兼容）
    └── output/                 # 旧的输出位置（兼容）
```

## 🚀 快速开始

### 方案 1: 一键构建（推荐）

```bash
# 完整构建：下载 + 编译 + 打包
python3 scripts/build_all.py

# 构建并烧写到 SD 卡
python3 scripts/build_all.py --flash /dev/sdX

# 跳过下载（如果源码已存在）
python3 scripts/build_all.py --skip-download

# 跳过 U-Boot 编译（使用现有 u-boot.bin）
python3 scripts/build_all.py --skip-uboot-build
```

### 方案 2: 分步构建

#### 步骤 1: 编译 U-Boot

```bash
# 下载并编译 U-Boot
python3 scripts/build_uboot.py

# 输出：build/boot/u-boot.bin
```

**详细选项：**
```bash
# 跳过下载（如果源码已存在）
python3 scripts/build_uboot.py --skip-download

# 仅配置，不编译
python3 scripts/build_uboot.py --config-only

# 清理源码和编译产物
python3 scripts/build_uboot.py --clean
```

#### 步骤 2: 打包 Bootloader 镜像

```bash
# 自动查找 u-boot.bin 并打包
python3 scripts/build_bootloader.py

# 输出：
#   build/boot/idbloader.img
#   build/boot/uboot.img
```

**详细选项：**
```bash
# 指定 U-Boot 二进制
python3 scripts/build_bootloader.py --uboot build/boot/u-boot.bin

# 指定配置文件
python3 scripts/build_bootloader.py --config configs/RKBOOT/RK3399MINIALL.ini

# 指定输出目录
python3 scripts/build_bootloader.py --output build/boot

# 仅构建 idbloader.img（跳过 uboot.img）
python3 scripts/build_bootloader.py --skip-uboot

# 清理构建输出
python3 scripts/build_bootloader.py --clean
```

#### 步骤 3: 烧写到 SD 卡

```bash
# 自动检测 SD 卡设备（推荐）
sudo ./scripts/flash_bootloader.sh

# 手动指定设备
sudo ./scripts/flash_bootloader.sh /dev/sdX

# 指定构建目录
sudo ./scripts/flash_bootloader.sh /dev/sdX build/boot
```

## 📝 U-Boot 源码配置

### 源码来源

**U-Boot 仓库：**
- URL: https://github.com/orangepi-xunlong/OrangePiRK3399_uboot.git
- 分支: master
- 版本: v2017.09-rk3399

**工具链：**
- URL: https://github.com/orangepi-xunlong/toolchain.git
- 分支: aarch64-linux-gnu-6.3
- 编译器: gcc-linaro-6.3.1 (aarch64)

### 编译环境要求

**系统依赖：**
```bash
# Ubuntu/Debian
sudo apt-get install git make gcc bsdtar

# 交叉编译工具链（自动下载 or 系统安装）
sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
```

### 构建流程

`build_uboot.py` 执行以下步骤：

1. **检查依赖** - 验证 git, make, gcc 等工具
2. **下载源码** - 从 GitHub clone U-Boot 仓库到 `components/uboot/`
3. **下载工具链** - Clone 工具链仓库到 `components/toolchain/`（如果系统无工具链）
4. **配置 U-Boot** - 运行 `make evb-rk3399_defconfig`
5. **编译** - 运行 `make -j$(nproc)`
6. **提取产物** - 复制 `u-boot.bin` 到 `build/boot/`

### 缓存策略

- **增量编译**：源码已存在时，使用 `--skip-download` 跳过下载
- **清理编译**：使用 `--clean` 删除所有源码和编译产物
- **手动编译**：可以直接进入 `components/uboot/` 手动运行 `make`

## 🔧 常见问题

### Q1: U-Boot 编译失败

**问题**：编译过程中报错

**解决方案：**
```bash
# 检查依赖
python3 scripts/build_uboot.py

# 如果工具链缺失
sudo apt-get install gcc-aarch64-linux-gnu

# 清理并重新编译
python3 scripts/build_uboot.py --clean
python3 scripts/build_uboot.py
```

### Q2: 找不到 u-boot.bin

**问题**：`build_bootloader.py` 找不到 U-Boot 二进制

**解决方案：**
```bash
# 首先编译 U-Boot
python3 scripts/build_uboot.py

# 或者手动指定路径
python3 scripts/build_bootloader.py --uboot path/to/u-boot.bin

# 或者使用参考项目的 u-boot.bin
python3 scripts/build_bootloader.py --uboot test_data/u-boot.bin
```

### Q3: 目录结构混乱

**问题**：同时存在 `build/boot/` 和 `test_data/output/`

**解决方案：**
```bash
# 新的标准位置是 build/boot/
# 脚本会自动优先使用新位置

# 迁移旧的输出
mv test_data/output/* build/boot/

# 或清理并重新构建
python3 scripts/build_all.py --clean
python3 scripts/build_all.py
```

### Q4: 下载速度慢

**问题**：从 GitHub 下载源码很慢

**解决方案：**
```bash
# 方案 1: 使用 GitHub 镜像（修改 build_uboot.py 中的 UBOOT_REPO）

# 方案 2: 手动克隆后再编译
git clone --depth=1 https://github.com/orangepi-xunlong/OrangePiRK3399_uboot.git components/uboot
python3 scripts/build_uboot.py --skip-download

# 方案 3: 使用代理
export https_proxy=http://your-proxy:port
python3 scripts/build_uboot.py
```

## 📊 构建产物说明

### idbloader.img (约 150 KB)

- **内容**：DDR 初始化代码 + miniloader
- **用途**：RK3399 BootROM 加载的第一个镜像
- **烧写位置**：扇区 64（偏移 32KB）

### uboot.img (约 4 MB)

- **内容**：U-Boot bootloader（含 4 个备份拷贝）
- **用途**：引导 Linux 内核
- **烧写位置**：扇区 24576（偏移 12MB）

### u-boot.bin (约 500-800 KB)

- **内容**：编译生成的 U-Boot 二进制
- **用途**：uboot.img 的原始输入
- **位置**：`build/boot/u-boot.bin`

## 🔄 迁移指南（从旧版本）

如果你使用的是旧的目录结构，迁移步骤：

### 1. 迁移配置文件

```bash
# 已自动迁移到 configs/
# 如果需要手动迁移：
cp -r test_data/RKBOOT configs/
cp -r test_data/RKTRUST configs/
```

### 2. 更新构建命令

**旧版本：**
```bash
python3 scripts/build_bootloader.py \
  --config test_data/RKBOOT/RK3399MINIALL.ini \
  --uboot test_data/u-boot.bin \
  --output test_data/output
```

**新版本：**
```bash
# 使用默认路径（推荐）
python3 scripts/build_bootloader.py

# 或显式指定
python3 scripts/build_bootloader.py \
  --config configs/RKBOOT/RK3399MINIALL.ini \
  --output build/boot
```

### 3. 更新烧写命令

**旧版本：**
```bash
sudo ./scripts/flash_bootloader.sh /dev/sdX test_data/output
```

**新版本：**
```bash
# 自动检测构建目录
sudo ./scripts/flash_bootloader.sh /dev/sdX

# 或显式指定
sudo ./scripts/flash_bootloader.sh /dev/sdX build/boot
```

## 🎯 下一步计划

### 已完成
- ✅ 目录结构重组
- ✅ U-Boot 源码下载和编译
- ✅ Bootloader 镜像打包
- ✅ 一键构建流程

### 计划中
- ⬜ Linux 内核编译集成
- ⬜ Rootfs 构建
- ⬜ 完整镜像生成（GPT 分区表）
- ⬜ 多芯片支持（RK3588/RK3568）

## 📚 参考资源

- **项目文档**：
  - [固件打包原理](docs/bootloader_build_guide.md)
  - [构建脚本使用](docs/build_script_usage.md)

- **原始项目**：
  - OrangePi RK3399 构建系统：`/home/lyc/Desktop/OrangePiRK3399_Merged`
  - U-Boot 源码：https://github.com/orangepi-xunlong/OrangePiRK3399_uboot

- **Rockchip 文档**：
  - U-Boot 开发指南
  - RK3399 技术参考手册
