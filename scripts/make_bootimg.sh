#!/bin/bash
#
# Generate boot.img from kernel Image
#
# This script packages the kernel Image and device tree into boot.img
# format required by RK3399 bootloader.
#
# Usage:
#   ./make_bootimg.sh [dtb_name]
#
# Example:
#   ./make_bootimg.sh rk3399-orangepi-4
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths
KERNEL_SRC="$PROJECT_ROOT/components/kernel"
BUILD_DIR="$PROJECT_ROOT/build/kernel"
IMAGE="$BUILD_DIR/Image"
DTBS_DIR="$BUILD_DIR/dtbs"

# Default DTB (can be overridden)
DTB_NAME="${1:-rk3399-orangepi-4}"
DTB_FILE="$DTBS_DIR/${DTB_NAME}.dtb"

# Output
RESOURCE_IMG="$BUILD_DIR/resource.img"
BOOT_IMG="$BUILD_DIR/boot.img"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   Generate boot.img for RK3399${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Check if kernel Image exists
if [ ! -f "$IMAGE" ]; then
    echo -e "${RED}✗ Kernel Image not found: $IMAGE${NC}"
    echo "Please build kernel first:"
    echo "  python3 scripts/build_kernel.py"
    exit 1
fi
echo -e "${GREEN}✓${NC} Kernel Image found"

# Check if DTB exists
if [ ! -f "$DTB_FILE" ]; then
    echo -e "${YELLOW}⚠${NC} DTB not found: $DTB_FILE"
    echo ""
    echo "Available DTBs:"
    ls -1 "$DTBS_DIR"/*.dtb 2>/dev/null | xargs -n1 basename || echo "  No DTBs found"
    echo ""
    echo "Usage: $0 [dtb_name]"
    echo "Example: $0 rk3399-orangepi-4"
    exit 1
fi
echo -e "${GREEN}✓${NC} DTB found: $DTB_NAME"

# Check if tools exist
if [ ! -x "$KERNEL_SRC/scripts/resource_tool" ]; then
    echo -e "${RED}✗ resource_tool not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} resource_tool found"

if [ ! -x "$KERNEL_SRC/scripts/mkbootimg" ]; then
    echo -e "${RED}✗ mkbootimg not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} mkbootimg found"

echo ""
echo "Generating boot.img..."
echo ""

# Step 1: Generate resource.img from DTB
echo -e "${CYAN}[1/2]${NC} Generating resource.img from DTB..."
cd "$BUILD_DIR"
"$KERNEL_SRC/scripts/resource_tool" "$DTB_FILE" 2>&1 | grep -v "^$" || true

if [ -f "$RESOURCE_IMG" ]; then
    SIZE=$(stat -c%s "$RESOURCE_IMG")
    SIZE_KB=$((SIZE / 1024))
    echo -e "${GREEN}  ✓ resource.img generated (${SIZE_KB} KB)${NC}"
else
    echo -e "${RED}  ✗ Failed to generate resource.img${NC}"
    exit 1
fi

# Step 2: Generate boot.img from Image + resource.img
echo ""
echo -e "${CYAN}[2/2]${NC} Generating boot.img from Image + resource.img..."

# Kernel command line - specify rootfs partition
# Using mmcblk0p4 (SD card partition 4 on RK3399)
# Note: Based on boot log, mmc0=mmcblk0=SD card, mmc1=mmcblk1=eMMC
CMDLINE="earlycon=uart8250,mmio32,0xff1a0000 swiotlb=1 console=ttyFIQ0 root=/dev/mmcblk0p4 rootwait rootfstype=ext4 rw"

"$KERNEL_SRC/scripts/mkbootimg" \
    --kernel "$IMAGE" \
    --second "$RESOURCE_IMG" \
    --cmdline "$CMDLINE" \
    -o "$BOOT_IMG"

if [ -f "$BOOT_IMG" ]; then
    SIZE=$(stat -c%s "$BOOT_IMG")
    SIZE_MB=$(echo "scale=1; $SIZE / 1024 / 1024" | bc)
    echo -e "${GREEN}  ✓ boot.img generated (${SIZE_MB} MB)${NC}"
else
    echo -e "${RED}  ✗ Failed to generate boot.img${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}✓ boot.img generation complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo "Output: $BOOT_IMG"
echo ""
echo "Next steps:"
echo "  1. Flash boot.img to SD card:"
echo "     sudo ./scripts/flash_bootloader.sh"
echo ""
echo "  2. Or manually flash to sector 49152:"
echo "     sudo dd if=$BOOT_IMG of=/dev/sdX seek=49152 bs=512 conv=notrunc,fsync"
echo ""
