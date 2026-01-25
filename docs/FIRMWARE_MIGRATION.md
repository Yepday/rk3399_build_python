# 固件文件迁移说明

## 迁移完成

固件文件已从 `test_data/` 迁移到标准位置 `components/firmware/rk33/`

### 新的固件位置

```
components/firmware/rk33/
├── rk3399_ddr_800MHz_v1.15.bin      # DDR 初始化代码 (69 KB)
├── rk3399_miniloader_v1.15.bin      # Miniloader/SPL (75 KB)
├── rk3399_usbplug_v1.06.bin         # USB 烧录插件 (50 KB)
└── rk3399_bl31_v1.36.elf            # ARM Trusted Firmware (1.3 MB)
```

### 配置文件位置

```
configs/RKBOOT/
└── RK3399MINIALL.ini                # Boot 配置文件

configs/RKTRUST/
└── RK3399TRUST.ini                  # Trust 配置文件
```

**注意：** configs/ 目录只包含配置文件，不包含固件二进制文件。

### 搜索路径优先级

`build_bootloader.py` 按以下顺序查找固件文件：

1. **components/firmware/rk33/** (标准位置，优先)
2. **configs/RKBOOT/bin/rk33/** (INI 相对路径，自动回退)
3. test_data/rk33/ (legacy，向后兼容)
4. test_data/RKBOOT/bin/rk33/ (legacy，向后兼容)

脚本会自动在这些位置查找，即使 INI 文件中指定的路径不存在也能正常工作。

### 验证

构建脚本已验证可以正确找到新位置的固件文件：

```bash
$ python3 scripts/build_bootloader.py --skip-uboot
# 输出显示：
#   Found alternative: components/firmware/rk33/rk3399_ddr_800MHz_v1.15.bin
#   Found alternative: components/firmware/rk33/rk3399_miniloader_v1.15.bin
```

### test_data/ 清理状态

**已删除（迁移后不再需要）：**
- ❌ test_data/RKBOOT/ (已迁移到 configs/)
- ❌ test_data/RKTRUST/ (已迁移到 configs/)
- ❌ test_data/output/ (已迁移到 build/boot/)
- ❌ test_data/rk33/ (已迁移到 components/firmware/)
- ❌ test_data/bin/ (已迁移到 components/firmware/)

**保留（参考用途）：**
- ✅ test_data/u-boot.bin (参考二进制，可选保留)
- ✅ test_data/VERIFICATION_REPORT.md (硬件验证报告)

### 优势

1. **清晰的职责划分**
   - `build/` - 构建产物（临时）
   - `components/` - 源码和固件（可缓存）
   - `configs/` - 配置文件（版本控制）

2. **统一的组件管理**
   - U-Boot 源码 → `components/uboot/`
   - 工具链 → `components/toolchain/`
   - 固件 → `components/firmware/`

3. **向后兼容**
   - 脚本仍支持旧的 `test_data/` 位置
   - 自动回退机制保证兼容性

4. **可扩展性**
   - 易于添加其他芯片的固件（如 rk3588/）
   - 易于版本管理和更新

## 后续清理

确认一切正常后，可以完全删除 `test_data/` 目录：

```bash
# 保留参考文件（可选）
mv test_data/u-boot.bin components/firmware/
mv test_data/VERIFICATION_REPORT.md docs/

# 删除整个 test_data/ 目录
rm -rf test_data/
```
