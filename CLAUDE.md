# CLAUDE.md

本文件为 Claude Code 提供项目指导，确保跨会话的工作连续性。

## 项目概述

**rkpyimg** 是一个用纯 Python 实现的 Rockchip 固件打包工具链，旨在替代官方 C 语言工具（boot_merger, trust_merger, loaderimage 等）。

### 核心价值
- **首个 Python 实现**：填补 Rockchip 工具链 Python 生态空白
- **跨平台**：Windows/Linux/macOS 均可运行
- **现代化**：Python 3.10+、类型注解、现代包管理
- **教育价值**：详细文档化二进制格式和打包原理

### 目标用户
- OrangePi/Firefly/Radxa 等 Rockchip 开发板用户
- Armbian 贡献者
- 嵌入式 Linux 学习者
- 需要自定义固件的开发者

## 项目结构

```
rkpyimg/
├── CLAUDE.md              # Claude Code 指导（本文件）
├── PROGRESS.md            # 工作进度记录（每次会话更新）
├── README.md              # 项目说明（面向用户）
├── pyproject.toml         # Python 项目配置
├── src/
│   └── rkpyimg/
│       ├── __init__.py
│       ├── core/              # 核心功能模块
│       │   ├── __init__.py
│       │   ├── header.py      # Rockchip Header 处理
│       │   ├── ini_parser.py  # INI 配置文件解析
│       │   └── checksum.py    # CRC/校验和计算
│       ├── tools/             # 官方工具 Python 实现
│       │   ├── __init__.py
│       │   ├── boot_merger.py   # boot_merger 实现
│       │   ├── trust_merger.py  # trust_merger 实现
│       │   └── loaderimage.py   # loaderimage 实现
│       ├── image/             # 镜像构建
│       │   ├── __init__.py
│       │   ├── partition.py   # GPT 分区处理
│       │   └── builder.py     # 镜像构建器
│       └── cli/               # 命令行接口
│           ├── __init__.py
│           └── main.py
├── tests/                 # 单元测试
│   ├── test_header.py
│   ├── test_ini_parser.py
│   └── ...
└── docs/                  # 详细文档
    ├── rk_header_format.md    # Header 格式说明
    ├── ini_file_format.md     # INI 文件格式
    └── packing_theory.md      # 打包原理深度解析
```

## 开发命令

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 类型检查
mypy src/

# 格式化
ruff format src/ tests/
ruff check src/ tests/ --fix

# CLI 运行
python -m rkpyimg --help
rkpyimg pack --help
```

## 核心技术细节

### Rockchip 固件打包原理

Rockchip SoC 的 BootROM 需要特定格式的固件镜像。关键点：

#### 1. RK Header 格式（所有镜像共用）
```
偏移量    大小    说明
0x000     4B      Magic: 0x0FF0AA55（小端）
0x004     4B      保留
0x008     4B      Chip ID (如 RK33)
0x00C     4B      代码大小
0x010     4B      加载地址
0x014     ...     其他元数据
```

#### 2. loaderimage 工具功能
将 u-boot.bin 封装为 uboot.img：
- 添加 RK Header
- 计算并添加 CRC 校验
- 支持指定加载地址和芯片类型

命令格式：
```bash
loaderimage --pack --uboot u-boot.bin uboot.img 0x200000 --size 1024 1
```

#### 3. boot_merger 工具功能
合并 DDR 初始化代码 + miniloader → idbloader.img/loader.bin

读取 RKBOOT/*.ini 配置：
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

#### 4. trust_merger 工具功能
合并 BL31(ATF) + BL32(OP-TEE) → trust.img

读取 RKTRUST/*.ini 配置：
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

### 支持的 Rockchip SoC

| 芯片 | 状态 | 说明 |
|------|------|------|
| RK3399 | 优先 | OrangePi RK3399, Firefly |
| RK3588/RK3588S | 计划中 | OrangePi 5 |
| RK3568/RK3566 | 计划中 | 主流中端 |
| RK3328 | 计划中 | Rock64 |
| RK3308 | 计划中 | 低功耗音频 |

## 开发路线图

### Phase 1: 核心差异化（当前）
- [ ] RK Header 解析/生成 (core/header.py)
- [ ] INI 配置解析 (core/ini_parser.py)
- [ ] CRC/校验和计算 (core/checksum.py)
- [ ] loaderimage Python 实现 (tools/loaderimage.py)
- [ ] boot_merger Python 实现 (tools/boot_merger.py)
- [ ] trust_merger Python 实现 (tools/trust_merger.py)

### Phase 2: 完整构建
- [ ] GPT 分区创建 (image/partition.py)
- [ ] 镜像写入 (image/builder.py)
- [ ] CLI 接口 (cli/main.py)
- [ ] 端到端构建流程

### Phase 3: 生态完善
- [ ] 多芯片支持扩展
- [ ] GitHub Actions CI/CD
- [ ] PyPI 发布
- [ ] 文档网站

## 参考资源

### 完整原构建项目（优先参考）
**位置**：`/home/lyc/Desktop/OrangePiRK3399_Merged`

这是一个完整的 OrangePi RK3399 构建项目，包含所有必需的组件和配置文件：
- 完整的 RKBOOT/*.ini 配置文件
- 完整的 RKTRUST/*.ini 配置文件
- 所有二进制组件（DDR init、miniloader、BL31、BL32 等）
- 完整的构建脚本和工具链

**使用规则**：
- 当构建项目时缺少组件或配置，可以从此项目中查找和复制
- 可以用来验证 Python 实现的输出是否正确
- 参考其目录结构和文件组织方式

### 原始 C 代码（参考实现）
位于 `/home/lyc/Desktop/build_rk3399/uboot/tools/rockchip/`:
- `loaderimage.c` - loader 镜像打包
- `boot_merger.c` - boot 合并器
- `trust_merger.c` - trust 合并器

### 参考文档
- `/home/lyc/Desktop/build_rk3399/uboot/固件打包原理深度解析.md`
- `/home/lyc/Desktop/build_rk3399/uboot/docs/loader镜像打包教程.md`
- `/home/lyc/Desktop/build_rk3399/uboot/docs/trust镜像打包教程.md`
- `/home/lyc/Desktop/build_rk3399/uboot/docs/uboot镜像打包教程.md`

### 关键数据结构（来自 C 源码）

```c
// loaderimage.c 中的 header 结构
struct header_info {
    uint32_t magic;      // 0x0FF0AA55
    uint8_t  reserved[4];
    uint32_t signature;  // 芯片 ID
    uint32_t check_size;
    uint32_t load_addr;
    // ...
};

// boot_merger.c 中的 loader entry
typedef struct {
    char name[20];
    char path[256];
    uint32_t offset;
    uint32_t size;
    uint32_t addr;
} entry_t;
```

## 工作流程

### 每次会话开始时
1. 阅读 `PROGRESS.md` 了解上次进度
2. 阅读本文件了解项目结构和技术细节
3. 继续未完成的任务

### 每次会话结束时
1. 更新 `PROGRESS.md` 记录完成的工作
2. 记录下一步计划
3. 记录遇到的问题或疑点

### 开发原则
1. **渐进式开发**：先实现最小可用功能，再逐步扩展
2. **类型注解**：所有公开 API 必须有类型注解
3. **文档同步**：代码和文档同步更新
4. **参考 C 源码**：实现时对照原始 C 代码确保兼容性
5. **暂时跳过单元测试**：当前环境 Python 版本较低，暂不运行测试
