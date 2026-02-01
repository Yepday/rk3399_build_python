# Clean 和 Distclean 功能指南

本文档说明如何使用项目的清理功能，类似于 `make clean` 和 `make distclean`。

## 快速开始

### Clean（清理编译产物，保留源码）

```bash
# 清理 build/ 目录，但保留 U-Boot、kernel 源码和工具链
python3 scripts/clean.py --clean

# 或通过 build_all.py
python3 scripts/build_all.py --clean
```

**删除的内容**：
- `build/boot/` - 编译的 bootloader 镜像（idbloader.img, uboot.img）
- `build/kernel/` - 编译的 kernel 镜像和设备树（Image, dtbs/, System.map）
- `build/image/` - 完整镜像文件

**保留的内容**：
- `components/uboot/` - U-Boot 源代码（可快速重新编译）
- `components/kernel/` - Linux kernel 源代码（可快速重新编译）
- `components/toolchain/` - 交叉编译工具链
- `components/firmware/` - Rockchip 固件文件
- 所有配置文件和脚本

**用途**：
- 快速清理编译产物（释放 ~50MB 空间）
- 保留源码以便快速重新构建
- 适合日常开发工作流

### Distclean（完全清理，重置为初始项目状态）

```bash
# 删除所有下载的源码和编译产物，只保留最初的项目
python3 scripts/clean.py --distclean

# 或通过 build_all.py
python3 scripts/build_all.py --distclean
```

**删除的内容**：
- `build/` - 所有编译产物
- `components/uboot/` - U-Boot 源代码
- `components/kernel/` - Linux kernel 源代码
- `components/toolchain/` - 交叉编译工具链

**保留的内容**：
- `components/firmware/` - Rockchip 固件文件（后续构建必需）
- `configs/` - INI 配置文件（后续构建必需）
- `scripts/` - 所有构建脚本
- `docs/` - 文档
- 所有项目元数据文件（CLAUDE.md, PROGRESS.md, README.md 等）

**用途**：
- 完全清理项目，释放大量空间（~6GB）
- 重置为初始状态后重新从头构建
- 适合提交到源代码仓库前的清理

## 使用方式详解

### 方式 1: 独立 clean.py 脚本

#### 交互式模式（推荐）
```bash
python3 scripts/clean.py
```
会显示菜单让你选择：
- `[1]` clean - 清理编译产物
- `[2]` distclean - 深度清理
- `[q]` 退出

#### 直接指定模式
```bash
# 清理 build 目录
python3 scripts/clean.py --clean

# 深度清理
python3 scripts/clean.py --distclean
```

#### Dry-run 模式（预览）
```bash
# 预览会删除什么，但不实际删除
python3 scripts/clean.py --clean --dry-run
python3 scripts/clean.py --distclean --dry-run
```

### 方式 2: 通过 build_all.py

```bash
# 清理编译产物
python3 scripts/build_all.py --clean

# 深度清理
python3 scripts/build_all.py --distclean
```

## 工作流示例

### 示例 1：日常开发

```bash
# 完整构建一次
python3 scripts/build_all.py

# 测试完毕，清理临时文件
python3 scripts/build_all.py --clean

# 下次需要构建时（代码有改动）
python3 scripts/build_all.py --skip-download
```

这样做的优势：
- 保留了已下载的源码
- 只重新编译有改动的部分
- 节省时间和带宽

### 示例 2：提交到 Git 前清理

```bash
# 彻底清理项目，去掉所有编译产物
python3 scripts/build_all.py --distclean

# 验证项目大小
du -sh .

# 现在可以提交到 Git
git add .
git commit -m "Clean build artifacts before commit"
```

### 示例 3：完整重新构建

```bash
# 深度清理
python3 scripts/build_all.py --distclean

# 从头开始构建（会重新下载所有源码）
python3 scripts/build_all.py

# 最后清理（可选）
python3 scripts/build_all.py --clean
```

## 清理前后的磁盘使用情况

### Clean 操作

```
清理前:
build/boot/     4.9 MB  (idbloader.img, uboot.img, u-boot.bin)
build/kernel/  48.8 MB  (Image, dtbs/, System.map)
总计:          ~53.7 MB

清理后:
components/    ~5.2 GB  (uboot源码、kernel源码、工具链)
configs/       ~1 MB    (配置文件)
```

### Distclean 操作

```
清理前:
build/         53.7 MB  (编译产物)
components/    ~6.1 GB  (uboot/kernel/toolchain 源码)
总计:          ~6.2 GB

清理后:
components/firmware/ ~50 MB (固件文件，必需保留)
configs/            ~1 MB  (配置文件，必需保留)
scripts/            ~1 MB  (脚本)
其他项目文件         ~1 MB
```

## 常见问题

### Q: 我可以跳过工具链下载吗？

不建议。工具链是编译 U-Boot 和 kernel 的必需组件。`distclean` 会删除它，但 `clean` 会保留。

### Q: 能否只删除 kernel 而不删除 U-Boot？

目前不支持选择性删除。如果需要，可以手动删除：
```bash
rm -rf build/kernel
rm -rf components/kernel
```

### Q: Distclean 后如何快速重新构建？

```bash
# Distclean 后
python3 scripts/build_all.py

# 这会重新下载所有源码和工具链，然后编译
```

### Q: 清理操作会删除我的 SD 卡镜像吗？

不会。清理只作用于 `build/`、`components/` 目录。你烧写到 SD 卡的镜像不会受影响。

### Q: 能否恢复已删除的文件？

可以，通过 Git：
```bash
git checkout components/  # 恢复 source 文件
git checkout build/       # 恢复 build 文件（如果已提交）
```

## 命令参考

| 命令 | 说明 | 删除大小 |
|------|------|--------|
| `python3 scripts/clean.py` | 交互式菜单 | - |
| `python3 scripts/clean.py --clean` | 清理编译产物 | ~54 MB |
| `python3 scripts/clean.py --distclean` | 深度清理 | ~6.2 GB |
| `python3 scripts/clean.py --clean --dry-run` | 预览 clean | - |
| `python3 scripts/clean.py --distclean --dry-run` | 预览 distclean | - |
| `python3 scripts/build_all.py --clean` | 通过 build_all 清理 | ~54 MB |
| `python3 scripts/build_all.py --distclean` | 通过 build_all 深度清理 | ~6.2 GB |

## 技术细节

### 清理流程

1. **识别要删除的路径**
   - Clean: `build/boot`, `build/kernel`, `build/image`
   - Distclean: 上述 + `components/uboot`, `components/kernel`, `components/toolchain`

2. **计算磁盘占用**
   - 递归遍历每个目录
   - 计算总大小（以便显示要释放的空间）

3. **用户确认**
   - Clean: 单次确认
   - Distclean: 双重确认（安全考虑）

4. **执行删除**
   - 使用 Python `shutil.rmtree()` 递归删除目录
   - 或 `Path.unlink()` 删除单个文件

5. **反馈信息**
   - 显示每个删除的项目及其大小
   - 总计释放的空间
   - 后续操作建议

### Dry-run 模式

添加 `--dry-run` 标志会：
- 列出要删除的所有项目
- 计算总大小
- **不执行实际删除**
- 用于验证删除前的预览

示例：
```bash
python3 scripts/clean.py --distclean --dry-run
# 输出: [DRY RUN] Would remove ...（不实际删除）
```

## 与 Make 工具的对比

| 操作 | Make | rkpyimg |
|------|------|---------|
| 清理编译产物 | `make clean` | `python3 scripts/clean.py --clean` |
| 深度清理 | `make distclean` | `python3 scripts/clean.py --distclean` |
| 预览删除 | - | `python3 scripts/clean.py --clean --dry-run` |
| 交互式菜单 | - | `python3 scripts/clean.py` |

## 安全特性

1. **Distclean 双重确认**
   - 第一次：显示删除清单，用户选择继续
   - 第二次：要求输入 "distclean" 文本确认

2. **Dry-run 模式**
   - 始终可以先用 `--dry-run` 预览

3. **保留关键文件**
   - `components/firmware/` 始终保留（构建必需）
   - `configs/` 始终保留（配置文件必需）

4. **错误处理**
   - 权限错误时给出清晰提示
   - 删除失败时停止并报告

## 后续改进建议

1. 支持选择性清理（`--keep-toolchain` 等标志）
2. 清理历史日志文件
3. 自动清理临时编译文件
4. 与 Git hook 集成（提交前自动清理）
