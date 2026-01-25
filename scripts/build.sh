#!/bin/bash
#
# Rockchip Bootloader Build Script (Shell Wrapper)
#
# This script is a convenient wrapper around build_bootloader.py
#

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Run Python build script
cd "$PROJECT_ROOT"

echo -e "${CYAN}Starting bootloader build...${NC}\n"

python3 "${SCRIPT_DIR}/build_bootloader.py" "$@"

exit $?
