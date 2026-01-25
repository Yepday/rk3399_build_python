#!/bin/bash
#
# RK3399 Bootloader 烧写脚本
#
# 用法:
#   sudo ./flash_bootloader.sh                    # 自动检测设备
#   sudo ./flash_bootloader.sh <设备>            # 指定设备
#   sudo ./flash_bootloader.sh <设备> <构建目录> # 指定设备和构建目录
#
# 示例:
#   sudo ./flash_bootloader.sh /dev/mmcblk0
#   sudo ./flash_bootloader.sh /dev/sdb build/boot
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 扇区位置定义（来自 OrangePi RK3399 实际配置）
LOADER1_START=64      # idbloader.img 位置 (32KB 偏移)
UBOOT_START=24576     # uboot.img 位置 (12MB 偏移) - OrangePi 配置
TRUST_START=32768     # trust.img 位置 (16MB 偏移) - OrangePi 配置

# 函数：列出可能的 SD 卡设备
list_devices() {
    echo -e "${CYAN}检测到的存储设备:${NC}"
    echo ""

    # 使用 lsblk 列出所有块设备
    lsblk -d -o NAME,SIZE,TYPE,TRAN,MODEL | grep -E "NAME|disk" | while read line; do
        if echo "$line" | grep -q "NAME"; then
            echo -e "${BOLD}$line${NC}"
        else
            echo "$line"
        fi
    done
    echo ""
}

# 函数：检测可移动存储设备
detect_removable_devices() {
    local devices=()

    # 查找可移动设备（USB 或 MMC）
    for dev in /sys/block/sd* /sys/block/mmcblk*; do
        [ -e "$dev" ] || continue

        device_name=$(basename "$dev")
        device_path="/dev/$device_name"

        # 检查是否为可移动设备或 MMC 设备
        if [ -f "$dev/removable" ]; then
            removable=$(cat "$dev/removable")
            if [ "$removable" = "1" ]; then
                devices+=("$device_path")
            fi
        elif [[ "$device_name" == mmcblk* ]]; then
            devices+=("$device_path")
        fi
    done

    echo "${devices[@]}"
}

# 函数：交互式选择设备
select_device() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}   SD 卡设备选择${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""

    list_devices

    local devices=($(detect_removable_devices))

    if [ ${#devices[@]} -eq 0 ]; then
        echo -e "${YELLOW}未检测到可移动存储设备（SD卡/USB）${NC}"
        echo ""
        echo "请确认："
        echo "  1. SD 卡已正确插入"
        echo "  2. SD 卡读卡器已连接"
        echo ""
        read -p "插入 SD 卡后按回车继续，或输入 'q' 退出: " input
        if [ "$input" = "q" ] || [ "$input" = "Q" ]; then
            exit 0
        fi
        select_device  # 递归重新检测
        return
    fi

    echo -e "${GREEN}检测到以下可移动设备:${NC}"
    for i in "${!devices[@]}"; do
        dev="${devices[$i]}"
        size=$(blockdev --getsize64 "$dev" 2>/dev/null || echo 0)
        size_mb=$((size / 1024 / 1024))
        model=$(lsblk -dno MODEL "$dev" 2>/dev/null || echo "Unknown")
        echo "  [$((i+1))] $dev - ${size_mb} MB - $model"
    done
    echo ""

    if [ ${#devices[@]} -eq 1 ]; then
        echo -e "${CYAN}只检测到一个设备，自动选择: ${devices[0]}${NC}"
        DEVICE="${devices[0]}"
    else
        read -p "请选择设备 [1-${#devices[@]}]: " selection

        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le ${#devices[@]} ]; then
            DEVICE="${devices[$((selection-1))]}"
        else
            echo -e "${RED}无效的选择${NC}"
            exit 1
        fi
    fi
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    echo "示例: sudo $0"
    exit 1
fi

# 解析参数
if [ $# -ge 1 ]; then
    DEVICE=$1
else
    # 没有参数，自动检测设备
    select_device
fi

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 确定构建目录（优先使用新结构）
if [ -n "$2" ]; then
    BUILD=$2
else
    # 优先使用新的目录结构 build/boot
    if [ -d "$PROJECT_ROOT/build/boot" ] && [ -f "$PROJECT_ROOT/build/boot/idbloader.img" ]; then
        BUILD="$PROJECT_ROOT/build/boot"
    # 回退到旧的目录结构
    elif [ -d "$PROJECT_ROOT/test_data/output" ] && [ -f "$PROJECT_ROOT/test_data/output/idbloader.img" ]; then
        BUILD="$PROJECT_ROOT/test_data/output"
    else
        echo -e "${RED}错误: 未找到构建目录${NC}"
        echo "请先构建镜像："
        echo "  python3 scripts/build_all.py           # 一键构建（推荐）"
        echo "或："
        echo "  python3 scripts/build_bootloader.py    # 仅构建 bootloader"
        echo ""
        echo "或指定构建目录："
        echo "  sudo $0 $DEVICE <构建目录>"
        exit 1
    fi
fi

# 检查设备是否存在
if [ ! -e "$DEVICE" ]; then
    echo -e "${RED}错误: 设备不存在: $DEVICE${NC}"
    exit 1
fi

# 检查设备是否为整个磁盘（不是分区）
if [[ "$DEVICE" =~ [0-9]$ ]]; then
    echo -e "${YELLOW}警告: 您选择的设备 $DEVICE 似乎是一个分区${NC}"
    echo "应该选择整个磁盘设备，例如："
    echo "  /dev/sdb (不是 /dev/sdb1)"
    echo "  /dev/mmcblk0 (不是 /dev/mmcblk0p1)"
    echo ""
    read -p "是否继续? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ] && [ "$CONTINUE" != "y" ]; then
        exit 0
    fi
fi

# 定义镜像路径
# 支持多种目录结构：uboot/ 子目录或直接在构建目录下
if [ -f "$BUILD/uboot/idbloader.img" ]; then
    IDBLOADER="$BUILD/uboot/idbloader.img"
    UBOOT="$BUILD/uboot/uboot.img"
    TRUST="$BUILD/uboot/trust.img"
else
    IDBLOADER="$BUILD/idbloader.img"
    UBOOT="$BUILD/uboot.img"
    # trust.img 可能在构建目录或项目根目录
    if [ -f "$BUILD/trust.img" ]; then
        TRUST="$BUILD/trust.img"
    elif [ -f "$PROJECT_ROOT/trust.img" ]; then
        TRUST="$PROJECT_ROOT/trust.img"
    else
        TRUST=""  # trust.img 不存在（可选）
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   RK3399 Bootloader 烧写工具${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "构建目录: ${GREEN}$BUILD${NC}"
echo -e "目标设备: ${GREEN}$DEVICE${NC}"
echo ""

# 检查镜像文件
echo "检查镜像文件..."
ALL_EXIST=true

if [ -f "$IDBLOADER" ]; then
    SIZE=$(stat -c%s "$IDBLOADER")
    SIZE_KB=$((SIZE / 1024))
    echo -e "  ${GREEN}✓${NC} idbloader.img: ${SIZE_KB} KB"
else
    echo -e "  ${RED}✗${NC} idbloader.img: 不存在"
    ALL_EXIST=false
fi

if [ -f "$UBOOT" ]; then
    SIZE=$(stat -c%s "$UBOOT")
    SIZE_KB=$((SIZE / 1024))
    echo -e "  ${GREEN}✓${NC} uboot.img: ${SIZE_KB} KB"
else
    echo -e "  ${RED}✗${NC} uboot.img: 不存在"
    ALL_EXIST=false
fi

if [ -n "$TRUST" ] && [ -f "$TRUST" ]; then
    SIZE=$(stat -c%s "$TRUST")
    SIZE_KB=$((SIZE / 1024))
    echo -e "  ${GREEN}✓${NC} trust.img: ${SIZE_KB} KB (可选)"
else
    echo -e "  ${YELLOW}⚠${NC} trust.img: 不存在 (可选，不影响基本启动)"
fi

if [ "$ALL_EXIST" = false ]; then
    echo ""
    echo -e "${RED}错误: 必需的镜像文件不存在${NC}"
    echo ""
    echo "请先构建镜像："
    echo "  python3 scripts/build_all.py           # 一键构建（推荐）"
    echo "或："
    echo "  python3 scripts/build_bootloader.py    # 仅构建 bootloader"
    exit 1
fi

# 检查设备大小
echo ""
DEVICE_SIZE=$(blockdev --getsize64 $DEVICE 2>/dev/null || echo 0)
DEVICE_SIZE_MB=$((DEVICE_SIZE / 1024 / 1024))
DEVICE_SIZE_GB=$((DEVICE_SIZE_MB / 1024))

echo "设备信息:"
if [ $DEVICE_SIZE_GB -gt 0 ]; then
    echo -e "  大小: ${DEVICE_SIZE_GB} GB (${DEVICE_SIZE_MB} MB)"
else
    echo -e "  大小: ${DEVICE_SIZE_MB} MB"
fi

if [ $DEVICE_SIZE_MB -lt 100 ]; then
    echo -e "  ${RED}✗ 警告: 设备太小 (< 100MB)，可能不是有效的 SD 卡${NC}"
    read -p "是否继续? (yes/no): " CONTINUE
    if [ "$CONTINUE" != "yes" ] && [ "$CONTINUE" != "y" ]; then
        exit 0
    fi
fi

# 检查并卸载已挂载的分区
echo ""
MOUNTED=$(mount | grep "$DEVICE" || true)
if [ -n "$MOUNTED" ]; then
    echo -e "${YELLOW}检测到已挂载的分区:${NC}"
    echo "$MOUNTED" | while read line; do
        echo "  $line"
    done
    echo ""
    read -p "是否自动卸载所有分区? (yes/no): " UNMOUNT

    if [ "$UNMOUNT" = "yes" ] || [ "$UNMOUNT" = "y" ]; then
        echo "正在卸载分区..."
        # 卸载所有相关分区
        for partition in ${DEVICE}*; do
            if mount | grep -q "$partition"; then
                echo "  卸载: $partition"
                umount "$partition" 2>/dev/null || true
            fi
        done
        echo -e "${GREEN}✓ 所有分区已卸载${NC}"
    else
        echo -e "${YELLOW}请手动卸载分区后重试${NC}"
        exit 0
    fi
fi

# 确认烧写
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}${BOLD}⚠️  警告: 此操作将覆写设备上的 bootloader 区域！${NC}"
echo -e "${CYAN}========================================${NC}"
echo "将要烧写到 $DEVICE:"
echo ""
echo -e "  ${CYAN}[1]${NC} idbloader.img → 扇区 $LOADER1_START (偏移 $((LOADER1_START * 512 / 1024)) KB)"
echo -e "  ${CYAN}[2]${NC} uboot.img     → 扇区 $UBOOT_START (偏移 $((UBOOT_START * 512 / 1024 / 1024)) MB)"
if [ -n "$TRUST" ] && [ -f "$TRUST" ]; then
    echo -e "  ${CYAN}[3]${NC} trust.img     → 扇区 $TRUST_START (偏移 $((TRUST_START * 512 / 1024 / 1024)) MB)"
fi
echo ""
echo -e "${RED}${BOLD}这将覆盖设备上的引导区域！${NC}"
echo -e "${YELLOW}请确认设备路径正确无误${NC}"
echo ""

read -p "确认继续烧写? (输入 'yes' 继续): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}操作已取消${NC}"
    exit 0
fi

# 开始烧写
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   开始烧写 Bootloader${NC}"
echo -e "${CYAN}========================================${NC}"

# 1. 烧写 idbloader
echo ""
echo -e "${CYAN}[1/2]${NC} 烧写 idbloader.img..."
echo "  源文件: $IDBLOADER"
echo "  目标: $DEVICE (扇区 $LOADER1_START)"
if dd if=$IDBLOADER of=$DEVICE seek=$LOADER1_START conv=notrunc,fsync bs=512 status=progress 2>&1; then
    echo -e "${GREEN}  ✓ idbloader.img 烧写成功${NC}"
else
    echo -e "${RED}  ✗ idbloader.img 烧写失败${NC}"
    exit 1
fi

# 2. 烧写 uboot
echo ""
echo -e "${CYAN}[2/2]${NC} 烧写 uboot.img..."
echo "  源文件: $UBOOT"
echo "  目标: $DEVICE (扇区 $UBOOT_START)"
if dd if=$UBOOT of=$DEVICE seek=$UBOOT_START conv=notrunc,fsync bs=512 status=progress 2>&1; then
    echo -e "${GREEN}  ✓ uboot.img 烧写成功${NC}"
else
    echo -e "${RED}  ✗ uboot.img 烧写失败${NC}"
    exit 1
fi

# 3. 烧写 trust (如果存在)
if [ -n "$TRUST" ] && [ -f "$TRUST" ]; then
    echo ""
    echo -e "${CYAN}[3/3]${NC} 烧写 trust.img (可选)..."
    echo "  源文件: $TRUST"
    echo "  目标: $DEVICE (扇区 $TRUST_START)"
    if dd if=$TRUST of=$DEVICE seek=$TRUST_START conv=notrunc,fsync bs=512 status=progress 2>&1; then
        echo -e "${GREEN}  ✓ trust.img 烧写成功${NC}"
    else
        echo -e "${YELLOW}  ⚠ trust.img 烧写失败（不影响基本启动）${NC}"
    fi
fi

# 同步到磁盘
echo ""
echo "正在同步数据到磁盘..."
sync
echo -e "${GREEN}✓ 数据同步完成${NC}"

# 完成
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}${BOLD}✓ 所有 Bootloader 组件烧写完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${BOLD}下一步操作:${NC}"
echo -e "  ${CYAN}1.${NC} 安全弹出 SD 卡"
echo "     sync 已完成，可以安全拔出"
echo ""
echo -e "  ${CYAN}2.${NC} 插入 RK3399 开发板"
echo "     将 SD 卡插入开发板的 SD 卡槽"
echo ""
echo -e "  ${CYAN}3.${NC} 上电启动"
echo "     连接串口查看启动日志（波特率 1500000）"
echo ""
echo -e "${GREEN}提示:${NC}"
echo "  - 如果无法启动，检查串口输出"
echo "  - 确认 SD 卡插入正确（金属触点朝下）"
echo "  - 如需完整系统，还需烧写 rootfs 分区"
echo ""
