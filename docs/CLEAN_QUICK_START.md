# 快速参考：Clean 和 Distclean 功能

## 最常用的命令

### 清理编译产物，保留源码（类似 `make clean`）
```bash
python3 scripts/clean.py --clean
python3 scripts/build_all.py --clean
```
- 删除：`build/` 目录（~54MB）
- 保留：所有源代码和工具链
- 用时：1-2秒

### 完全清理，重置项目（类似 `make distclean`）
```bash
python3 scripts/clean.py --distclean
python3 scripts/build_all.py --distclean
```
- 删除：源码、工具链、编译产物（~6.2GB）
- 保留：初始项目状态
- 用时：10-20秒

### 预览删除（推荐先做这个）
```bash
python3 scripts/clean.py --clean --dry-run
python3 scripts/clean.py --distclean --dry-run
```
- 显示会删除什么，但不实际删除
- 推荐在执行前先用 dry-run 预览

### 交互式菜单
```bash
python3 scripts/clean.py
```
会显示菜单，让你选择 clean、distclean 或 quit

## 工作流示例

### 日常开发流程
```bash
# 完整构建
python3 scripts/build_all.py

# 测试完毕，清理临时文件
python3 scripts/build_all.py --clean

# 代码改动后快速重新构建（源码已保留）
python3 scripts/build_all.py --skip-download
```

### 提交到 Git 前清理
```bash
# 深度清理（去掉所有编译产物和下载的源码）
python3 scripts/build_all.py --distclean

# 查看项目大小
du -sh .

# 提交到 Git
git add .
git commit -m "Clean build artifacts"
```

### 完整从头构建
```bash
# 深度清理
python3 scripts/build_all.py --distclean

# 从头开始（会重新下载所有源码）
python3 scripts/build_all.py

# 完成后清理（可选）
python3 scripts/build_all.py --clean
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/clean.py` | 独立的清理工具（新增） |
| `scripts/build_all.py` | 主构建脚本（已更新） |
| `docs/clean_guide.md` | 详细使用指南 |

## 详细文档

完整的文档请查看：`docs/clean_guide.md`

主要涵盖：
- 详细的清理流程说明
- 工作流示例
- 常见问题解答
- 与 Make 工具的对比
- 安全特性说明
