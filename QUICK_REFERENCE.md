# Boot 分区替换快速参考

## 📊 分区信息

| 分区 | 名称 | 起始扇区 | 大小 | 内容 |
|------|------|----------|------|------|
| - | 引导区 | 0 | ~12MB | idbloader.img |
| 1 | uboot | 24576 | 4MB | uboot.img |
| 2 | trust | 32768 | 4MB | trust.img |
| **3** | **boot** | **49152** | **32MB** | **boot.img (目标)** |
| 4 | rootfs | 376832 | 2.9GB | 根文件系统 |

## 🚀 快速替换

### 使用脚本（推荐）

```bash
./replace_boot.sh original.img new_boot.img output.img
```

### 手动 dd 命令

```bash
# 备份
cp original.img backup.img

# 替换
dd if=/dev/zero of=original.img bs=512 seek=49152 count=65536 conv=notrunc
dd if=new_boot.img of=original.img bs=512 seek=49152 conv=notrunc

# 验证
dd if=original.img bs=512 skip=49152 count=1 2>/dev/null | hexdump -C | head -1
```

## ⚠️ 重要提醒

1. ✅ boot.img ≤ 32MB
2. ✅ Android Boot Image 格式
3. ✅ 替换前备份原镜像
4. ✅ 验证 magic: "ANDROID!" (41 4e 44 52 4f 49 44 21)

## 🔧 验证命令

```bash
# 检查格式
file new_boot.img

# 检查大小
ls -lh new_boot.img

# 验证替换
dd if=modified.img bs=512 skip=49152 count=1 2>/dev/null | hexdump -C | grep ANDROID
```

---
完整文档: BOOT_REPLACE_GUIDE.md
