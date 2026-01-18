# 变更日志

本文件记录 rkpyimg 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 新增
- 完整的测试环境和验证报告
- VERIFICATION_REPORT.md - 详细的功能验证文档

### 修复
- boot_merger.py: 修复 struct.pack 格式字符串错误
  - code471_offset: B → I (4 bytes)
  - code472_offset: B → I (4 bytes)
  - loader_offset: B → I (4 bytes)

### 测试
- ✅ boot_merger.py 完整验证（pack/unpack）
- ✅ trust_merger.py 完整验证（pack/unpack）
- ✅ loaderimage.py 完整验证（pack/unpack/info）
- ✅ 往返测试通过（数据完整性 100%）

---

## [0.1.0] - 2026-01-15

### 新增
- cli/main.py - 统一命令行接口
  - `rkpyimg loaderimage` 子命令组
  - `rkpyimg boot-merger` 子命令组
  - `rkpyimg trust-merger` 子命令组
- README.md 完整使用文档
  - 三个工具的详细使用示例
  - 完整固件构建流程
  - Python API 文档

### 改进
- 所有工具支持友好的错误提示
- 添加符号反馈（✓/✗）
- 支持详细输出模式

---

## [0.0.3] - 2026-01-15

### 新增
- tools/trust_merger.py - trust_merger 完整实现
  - TrustMerger 类（pack/unpack）
  - ELF 文件解析（32/64-bit）
  - PT_LOAD 段自动提取
  - SHA256 哈希计算
  - RSA/SHA 模式配置
  - 命令行接口
- core/checksum.py: 添加 sha256_hash() 函数

### 技术细节
- Trust 镜像结构：TRUST_HEADER (2048 bytes)
- Component Data: SHA256 + Load Address
- ELF segment 自动解析
- 2048 字节对齐

---

## [0.0.2] - 2026-01-08

### 新增
- tools/boot_merger.py - boot_merger 完整实现
  - BootMerger 类（pack/unpack）
  - RKTime、RKBootHeader、RKBootEntry 数据结构
  - get_bcd()、get_chip_type()、align_size() 工具函数
  - RC4 加密框架（暂禁用）
  - 命令行接口

### 技术细节
- 镜像布局：Header (102B) + Entries (54B×N) + Data (aligned 2048B)
- CRC32 校验和
- BCD 版本编码
- 宽字符名称编码

---

## [0.0.1] - 2026-01-06

### 新增
- 项目初始化
  - 目录结构（src/rkpyimg/）
  - pyproject.toml 配置
  - CLAUDE.md 项目指南
  - PROGRESS.md 进度记录
  - README.md 项目说明

- core/header.py - RK Header 基础框架
- core/ini_parser.py - INI 配置解析
  - RKBootConfig 类（RKBOOT/*.ini）
  - RKTrustConfig 类（RKTRUST/*.ini）
  - BinaryEntry 数据结构
- core/checksum.py - CRC32 校验和
  - crc32_rk() - Rockchip CRC32 算法

- tools/loaderimage.py - loaderimage 实现
  - SecondLoaderHeader 数据结构
  - pack_uboot() / pack_trust()
  - unpack_loader_image()
  - get_loader_info()
  - 命令行接口

- core/rc4.py - RC4 加密/解密
  - rc4_encrypt() / rc4_decrypt()
  - rc4_encrypt_blocks() / rc4_decrypt_blocks()

### 文档
- docs/固件打包原理深度解析.md（参考）
- docs/loader镜像打包教程.md（参考）
- docs/trust镜像打包教程.md（参考）

---

## 变更分类说明

- **新增**: 新功能
- **改进**: 现有功能的改进
- **修复**: Bug 修复
- **废弃**: 即将移除的功能
- **移除**: 已移除的功能
- **安全**: 安全相关的修复
- **测试**: 测试相关的变更
- **文档**: 仅文档的变更
- **性能**: 性能改进
- **重构**: 代码重构（不改变功能）
