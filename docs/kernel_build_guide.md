# Linux Kernel Build Guide for RK3399

This guide explains how to build the Linux kernel for Rockchip RK3399 development boards using the automated build system.

## Overview

The kernel build system is fully integrated with the main build pipeline. You can:
- Build kernel independently using `scripts/build_kernel.py`
- Build kernel as part of the complete system using `scripts/build_all.py`

## Quick Start

### Option 1: Build Everything at Once

```bash
# Download, compile U-Boot and kernel, then pack bootloader images
python3 scripts/build_all.py

# Same, but skip kernel build (use existing kernel)
python3 scripts/build_all.py --skip-kernel-build

# Skip both U-Boot and kernel compilation
python3 scripts/build_all.py --skip-download --skip-uboot-build --skip-kernel-build
```

### Option 2: Build Kernel Separately

```bash
# Download and compile kernel from scratch
python3 scripts/build_kernel.py

# Compile kernel (assume source already downloaded)
python3 scripts/build_kernel.py --skip-download

# Only configure kernel, don't compile
python3 scripts/build_kernel.py --config-only

# Skip kernel modules compilation
python3 scripts/build_kernel.py --no-modules

# Clean all kernel sources and build artifacts
python3 scripts/build_kernel.py --clean
```

## Build Process Details

### Phase 1: Download Kernel Source

The script downloads Linux kernel from OrangePi's GitHub:
- Repository: `https://github.com/orangepi-xunlong/OrangePiRK3399_kernel.git`
- Branch: `master`
- Destination: `components/kernel/`

This uses shallow clone (`--depth=1`) to minimize download size (~500MB).

### Phase 2: Check Toolchain

The script uses the ARM cross-compiler (aarch64-linux-gnu) to compile the kernel for ARM64.

Priority order:
1. System-installed toolchain (`aarch64-linux-gnu-gcc` in PATH)
2. Downloaded Linaro GCC 6.3.1 (from `components/toolchain/`)

If no toolchain is found, you need to run:
```bash
python3 scripts/build_uboot.py
```
This downloads the required Linaro GCC 6.3.1 toolchain.

### Phase 3: Configure Kernel

Uses the RK3399-specific defconfig:
```bash
make rk3399_linux_defconfig
```

This applies pre-configured options for RK3399 SoC support.

### Phase 4-6: Compile

Compiles three components:
1. **Kernel Image** - ARM64 raw kernel binary (arch/arm64/boot/Image)
2. **Device Tree Blobs** - Hardware description files (.dtb)
3. **Kernel Modules** - Loadable kernel modules (optional, skippable with `--no-modules`)

Uses all available CPU cores for parallel compilation (e.g., `-j24` on 24-core system).

### Phase 7-8: Copy Output

Copies compiled binaries to `build/kernel/`:
```
build/kernel/
├── Image              # Raw kernel binary (~20-30 MB)
├── System.map         # Kernel symbol map
└── dtbs/              # Device tree blobs
    ├── rk3399-*.dtb
    └── ...
```

## Output Files

After successful build, you'll have:

### Bootloader Images (build/boot/)
- `idbloader.img` - DDR init + miniloader (~150 KB)
- `uboot.img` - U-Boot bootloader (~4 MB)

### Kernel Images (build/kernel/)
- `Image` - Compiled kernel binary (~20-30 MB)
- `System.map` - Kernel symbol table
- `dtbs/` - Device tree blobs for RK3399 and variants

## Kernel Configuration

To customize kernel configuration:

```bash
# Configure kernel interactively
cd components/kernel
make menuconfig
cd ../../

# Then compile with your custom config
python3 scripts/build_kernel.py --skip-download
```

## Troubleshooting

### Kernel Download Fails
```bash
# Check git connectivity
git clone --depth=1 https://github.com/orangepi-xunlong/OrangePiRK3399_kernel.git

# Clean and retry
python3 scripts/build_kernel.py --clean
python3 scripts/build_kernel.py
```

### Compilation Errors

Most compilation errors are due to missing cross-compiler:

```bash
# Ensure toolchain is downloaded
python3 scripts/build_uboot.py
```

### Insufficient Disk Space

Kernel source + build takes ~2-3 GB. Clean when needed:

```bash
python3 scripts/build_kernel.py --clean
```

## Build Times

Typical build times on multi-core systems:
- Kernel download: 30-60 seconds
- Kernel configuration: 10 seconds
- Kernel compilation: 5-10 minutes (24 cores)
- Modules compilation: 3-5 minutes
- Total: ~10-20 minutes

## Kernel Version

The default kernel is from OrangePi's repository:
- Version: Linux 4.4.x (legacy)
- Optimized for RK3399
- Pre-configured with necessary drivers and patches

## Next Steps

After building the kernel:

1. **Use in Complete System Build**
   ```bash
   python3 scripts/build_all.py
   ```

2. **Create Boot Image**
   - Use the `Image` file as the kernel binary
   - Include device tree binary in boot partition

3. **Build Rootfs**
   - Create root filesystem
   - Package with kernel and bootloader

4. **Write to Storage**
   - Create SD card image with all three: bootloader, kernel, rootfs
   - Flash to SD card or eMMC

## Architecture Reference

```
RK3399 Boot Flow:
BootROM → DDR Init → Miniloader → BL31 (ATF) → U-Boot → Kernel → System
         ├─────────────────────┬──────────────────────┤ │
         idbloader.img         trust.img            uboot.img

Kernel Build:
Source → Configure → Compile → Device Tree → Output
(master)  (defconfig) (arm64)   (dtbs)       (Image + dtbs)
```

## References

- Kernel source: https://github.com/orangepi-xunlong/OrangePiRK3399_kernel
- Defconfig: `arch/arm64/configs/rk3399_linux_defconfig`
- Device Tree: `arch/arm64/boot/dts/rockchip/rk3399*.dtsi`
