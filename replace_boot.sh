#!/bin/bash
#
# Rockchip RK3399 镜像 Boot 分区替换脚本
# 用途：将新的 boot.img 替换到完整镜像中
#
# 使用方法:
#   ./replace_boot.sh <原始镜像> <新boot.img> <输出镜像>
#
# 示例:
#   ./replace_boot.sh original.img new_boot.img output.img
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
if [ $# -ne 3 ]; then
    echo "用法: $0 <原始镜像> <新boot.img> <输出镜像>"
    echo ""
    echo "示例:"
    echo "  $0 original.img new_boot.img output.img"
    echo ""
    echo "分区信息:"
    echo "  Boot 分区位于扇区 49152, 大小 65536 扇区 (32MB)"
    exit 1
fi

ORIGINAL_IMG="$1"
NEW_BOOT_IMG="$2"
OUTPUT_IMG="$3"

# 检查输入文件
if [ ! -f "$ORIGINAL_IMG" ]; then
    print_error "原始镜像文件不存在: $ORIGINAL_IMG"
    exit 1
fi

if [ ! -f "$NEW_BOOT_IMG" ]; then
    print_error "新 boot.img 文件不存在: $NEW_BOOT_IMG"
    exit 1
fi

# Boot 分区参数 (根据分区表)
BOOT_START=49152      # 扇区起始位置
BOOT_SIZE=65536       # 扇区数量 (32MB)
SECTOR_SIZE=512       # 扇区大小

# 计算字节偏移
BOOT_OFFSET=$((BOOT_START * SECTOR_SIZE))
BOOT_BYTES=$((BOOT_SIZE * SECTOR_SIZE))

# 检查 boot.img 大小
BOOT_IMG_SIZE=$(stat -c%s "$NEW_BOOT_IMG")
if [ $BOOT_IMG_SIZE -gt $BOOT_BYTES ]; then
    print_error "boot.img 过大！"
    echo "  boot.img 大小: $BOOT_IMG_SIZE 字节"
    echo "  最大允许: $BOOT_BYTES 字节 (32MB)"
    exit 1
fi

print_info "开始替换 boot 分区..."
echo "  原始镜像: $ORIGINAL_IMG"
echo "  新 boot.img: $NEW_BOOT_IMG ($(numfmt --to=iec-i --suffix=B $BOOT_IMG_SIZE))"
echo "  输出镜像: $OUTPUT_IMG"
echo "  Boot 分区: 扇区 $BOOT_START, 大小 $BOOT_SIZE 扇区 (32MB)"
echo ""

# 方案选择
print_info "选择替换方案:"
echo "  [1] 直接替换 (推荐) - 复制原镜像并替换 boot 分区"
echo "  [2] 原地替换 - 直接修改原镜像 (危险!)"
echo ""
read -p "请选择方案 [1-2]: " choice

case $choice in
    1)
        # 方案1: 复制后替换
        print_info "步骤 1/3: 复制原始镜像到输出文件..."
        if [ "$ORIGINAL_IMG" = "$OUTPUT_IMG" ]; then
            print_error "原始镜像和输出镜像不能相同！请使用方案2进行原地替换。"
            exit 1
        fi
        cp "$ORIGINAL_IMG" "$OUTPUT_IMG"
        
        print_info "步骤 2/3: 清空 boot 分区区域..."
        dd if=/dev/zero of="$OUTPUT_IMG" bs=512 seek=$BOOT_START count=$BOOT_SIZE conv=notrunc status=none
        
        print_info "步骤 3/3: 写入新 boot.img..."
        dd if="$NEW_BOOT_IMG" of="$OUTPUT_IMG" bs=512 seek=$BOOT_START conv=notrunc status=progress
        ;;
    2)
        # 方案2: 原地替换
        print_warn "警告: 这将直接修改原始镜像！"
        read -p "确定要继续吗? [y/N]: " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            print_info "操作已取消"
            exit 0
        fi
        
        OUTPUT_IMG="$ORIGINAL_IMG"
        
        print_info "步骤 1/2: 清空 boot 分区区域..."
        dd if=/dev/zero of="$OUTPUT_IMG" bs=512 seek=$BOOT_START count=$BOOT_SIZE conv=notrunc status=none
        
        print_info "步骤 2/2: 写入新 boot.img..."
        dd if="$NEW_BOOT_IMG" of="$OUTPUT_IMG" bs=512 seek=$BOOT_START conv=notrunc status=progress
        ;;
    *)
        print_error "无效的选择"
        exit 1
        ;;
esac

echo ""
print_info "✅ Boot 分区替换完成！"
echo ""
print_info "验证信息:"

# 验证替换结果
VERIFY_MAGIC=$(dd if="$OUTPUT_IMG" bs=512 skip=$BOOT_START count=1 2>/dev/null | hexdump -C | head -1 | awk '{print $2$3$4$5$6$7$8$9}')
if [ "$VERIFY_MAGIC" = "414e44524f494421" ]; then
    print_info "  ✓ Boot 分区 magic 验证通过 (ANDROID!)"
else
    print_warn "  ⚠ Boot 分区 magic 验证失败"
fi

# 显示分区表
print_info "  分区表:"
parted "$OUTPUT_IMG" unit s print 2>/dev/null | grep -E "^ [0-9]"

echo ""
print_info "输出镜像: $OUTPUT_IMG"
print_info "现在可以使用此镜像烧录到 SD 卡或 eMMC"
