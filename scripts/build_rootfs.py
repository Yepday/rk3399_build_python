#!/usr/bin/env python3
"""
RK3399 Root Filesystem Builder

This script builds a minimal Ubuntu-based root filesystem for RK3399 devices.
Based on the OrangePi build system but modernized with Python.

Usage:
    python3 scripts/build_rootfs.py [options]

Options:
    --distro DISTRO    Ubuntu distribution (bionic, focal, jammy)
    --type TYPE        Image type (server, desktop)
    --mirror MIRROR    Ubuntu mirror (cn, official, default)
    --clean            Clean existing rootfs before building
"""

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
BUILD_DIR = PROJECT_ROOT / "build"
ROOTFS_DIR = BUILD_DIR / "rootfs"
KERNEL_DIR = PROJECT_ROOT / "components" / "kernel"
EXTERNAL_DIR = PROJECT_ROOT / "external"

# Ubuntu distributions configuration
DISTROS = {
    "bionic": {
        "version": "18.04.5",
        "codename": "bionic",
        "mirrors": {
            "official": "http://ports.ubuntu.com",
            "cn": "http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports",
            "default": "http://ports.ubuntu.com"
        },
        "tarball": "ubuntu-base-18.04.5-base-arm64.tar.gz"
    },
    "focal": {
        "version": "20.04.5",
        "codename": "focal",
        "mirrors": {
            "official": "http://ports.ubuntu.com",
            "cn": "http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports",
            "default": "http://ports.ubuntu.com"
        },
        "tarball": "ubuntu-base-20.04.5-base-arm64.tar.gz"
    },
    "jammy": {
        "version": "22.04.3",
        "codename": "jammy",
        "mirrors": {
            "official": "http://ports.ubuntu.com",
            "cn": "http://mirrors.tuna.tsinghua.edu.cn/ubuntu-ports",
            "default": "http://ports.ubuntu.com"
        },
        "tarball": "ubuntu-base-22.04.3-base-arm64.tar.gz"
    }
}


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_info(msg: str):
    """Print info message"""
    print(f"{Colors.CYAN}[INFO]{Colors.NC} {msg}")


def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")


def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)


def print_warning(msg: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")


def run_command(cmd: list, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Run a shell command with error handling"""
    print_info(f"Running: {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        if check:
            raise
        return e


def check_root():
    """Check if running as root"""
    if os.geteuid() != 0:
        print_error("This script must be run as root")
        print_info("Try: sudo python3 scripts/build_rootfs.py")
        sys.exit(1)


def download_ubuntu_base(distro: str, mirror: str) -> Path:
    """
    Download Ubuntu base tarball if not already present

    Args:
        distro: Ubuntu distribution codename
        mirror: Mirror selection (cn, official, default)

    Returns:
        Path to downloaded tarball
    """
    config = DISTROS[distro]
    tarball_name = config["tarball"]
    tarball_path = BUILD_DIR / tarball_name

    if tarball_path.exists():
        print_info(f"Ubuntu base tarball already exists: {tarball_path}")
        return tarball_path

    # Construct download URL
    version = config["version"]
    base_url = f"http://cdimage.ubuntu.com/ubuntu-base/releases/{version}/release/{tarball_name}"

    print_info(f"Downloading Ubuntu {version} base from {base_url}")
    print_warning("This may take several minutes depending on your network speed...")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Download with progress
        urllib.request.urlretrieve(base_url, tarball_path)
        print_success(f"Downloaded: {tarball_path}")
        return tarball_path
    except Exception as e:
        print_error(f"Failed to download Ubuntu base: {e}")
        if tarball_path.exists():
            tarball_path.unlink()
        sys.exit(1)


def extract_rootfs(tarball: Path):
    """
    Extract Ubuntu base tarball to rootfs directory

    Args:
        tarball: Path to Ubuntu base tarball
    """
    print_info(f"Extracting {tarball.name} to {ROOTFS_DIR}")

    # Clean existing rootfs
    if ROOTFS_DIR.exists():
        print_warning(f"Removing existing rootfs: {ROOTFS_DIR}")
        shutil.rmtree(ROOTFS_DIR)

    ROOTFS_DIR.mkdir(parents=True, exist_ok=True)

    # Extract using tar
    run_command([
        "tar",
        "-xzf", str(tarball),
        "-C", str(ROOTFS_DIR)
    ])

    print_success("Rootfs extracted successfully")


def setup_qemu_static():
    """Setup QEMU static binary for ARM64 emulation"""
    qemu_static = Path("/usr/bin/qemu-aarch64-static")

    if not qemu_static.exists():
        print_error("qemu-aarch64-static not found")
        print_info("Install with: sudo apt-get install qemu-user-static")
        sys.exit(1)

    dest_qemu = ROOTFS_DIR / "usr" / "bin" / "qemu-aarch64-static"
    dest_qemu.parent.mkdir(parents=True, exist_ok=True)

    print_info("Copying QEMU static binary to rootfs")
    shutil.copy2(qemu_static, dest_qemu)


def mount_pseudo_filesystems():
    """Mount necessary pseudo-filesystems for chroot"""
    mounts = [
        ("/dev", ROOTFS_DIR / "dev", ["--bind"]),
        ("/dev/pts", ROOTFS_DIR / "dev/pts", ["--bind"]),
        ("proc", ROOTFS_DIR / "proc", ["-t", "proc"]),
        ("sysfs", ROOTFS_DIR / "sys", ["-t", "sysfs"]),
    ]

    print_info("Mounting pseudo-filesystems")
    for source, target, opts in mounts:
        target.mkdir(parents=True, exist_ok=True)
        try:
            run_command(["mount"] + opts + [source, str(target)])
        except subprocess.CalledProcessError:
            print_warning(f"Failed to mount {target} (may already be mounted)")


def umount_pseudo_filesystems():
    """Unmount pseudo-filesystems"""
    import time

    mounts = [
        ROOTFS_DIR / "sys",
        ROOTFS_DIR / "proc",
        ROOTFS_DIR / "dev/pts",
        ROOTFS_DIR / "dev",
    ]

    print_info("Unmounting pseudo-filesystems")
    for mount in mounts:
        # Try to unmount up to 3 times with lazy umount as fallback
        for attempt in range(3):
            try:
                result = subprocess.run(
                    ["umount", str(mount)],
                    check=False,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    break
                elif "busy" in result.stderr.lower() or "target is busy" in result.stderr.lower():
                    if attempt < 2:
                        print_warning(f"{mount} is busy, waiting...")
                        time.sleep(1)
                    else:
                        # Last attempt: use lazy umount
                        print_warning(f"{mount} still busy, using lazy umount")
                        subprocess.run(["umount", "-l", str(mount)], check=False)
                        break
            except Exception as e:
                if attempt == 2:
                    print_warning(f"Failed to unmount {mount}: {e}")
                pass


def write_apt_sources(distro: str, mirror: str):
    """
    Write APT sources.list for Ubuntu

    Args:
        distro: Ubuntu distribution codename
        mirror: Mirror URL
    """
    sources_list = ROOTFS_DIR / "etc" / "apt" / "sources.list"
    config = DISTROS[distro]
    codename = config["codename"]
    mirror_url = config["mirrors"][mirror]

    content = f"""# Ubuntu {codename} repositories
deb {mirror_url} {codename} main restricted universe multiverse
deb {mirror_url} {codename}-updates main restricted universe multiverse
deb {mirror_url} {codename}-security main restricted universe multiverse
deb {mirror_url} {codename}-backports main restricted universe multiverse
"""

    print_info("Writing APT sources.list")
    sources_list.write_text(content)


def configure_base_system(distro: str):
    """
    Configure base system in chroot

    Args:
        distro: Ubuntu distribution codename
    """
    print_info("Configuring base system")

    # Copy resolv.conf for network access
    shutil.copy2("/etc/resolv.conf", ROOTFS_DIR / "etc/resolv.conf")

    # Create configuration script
    config_script = ROOTFS_DIR / "tmp" / "configure_base.sh"
    config_script.parent.mkdir(parents=True, exist_ok=True)

    script_content = """#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C

echo "Updating package lists..."
apt-get update

echo "Installing base packages..."
apt-get install -y --no-install-recommends \\
    dosfstools curl xz-utils iw rfkill wpasupplicant \\
    openssh-server alsa-utils rsync u-boot-tools vim \\
    parted network-manager net-tools sudo \\
    systemd systemd-sysv udev kmod \\
    ca-certificates tzdata locales

echo "Configuring locales..."
locale-gen en_US.UTF-8

echo "Creating user orangepi..."
useradd -m -s /bin/bash -G sudo,adm,video,plugdev orangepi || true
echo "orangepi:orangepi" | chpasswd
echo "root:orangepi" | chpasswd

echo "Configuring hostname..."
echo "orangepi-rk3399" > /etc/hostname

echo "Configuring hosts file..."
cat > /etc/hosts << EOF
127.0.0.1   localhost
127.0.1.1   orangepi-rk3399

::1         localhost ip6-localhost ip6-loopback
fe00::0     ip6-localnet
ff00::0     ip6-mcastprefix
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

echo "Enabling services..."
systemctl enable systemd-networkd || true
systemctl enable ssh || true

echo "Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Base system configuration complete!"
"""

    config_script.write_text(script_content)
    config_script.chmod(0o755)

    # Execute in chroot
    mount_pseudo_filesystems()
    try:
        run_command([
            "chroot", str(ROOTFS_DIR),
            "/tmp/configure_base.sh"
        ])
        print_success("Base system configured")
    finally:
        # Cleanup temporary files
        config_script.unlink()
        (ROOTFS_DIR / "etc/resolv.conf").unlink(missing_ok=True)
        # IMPORTANT: Unmount pseudo-filesystems to prevent residual mounts
        umount_pseudo_filesystems()


def install_kernel_modules():
    """Install kernel modules to rootfs"""
    modules_src = KERNEL_DIR / "modules" / "lib" / "modules"
    modules_dst = ROOTFS_DIR / "lib" / "modules"

    if not modules_src.exists():
        print_warning("Kernel modules not found, skipping installation")
        print_info("Build kernel first: python3 scripts/build_kernel.py")
        return

    print_info("Installing kernel modules")
    modules_dst.parent.mkdir(parents=True, exist_ok=True)

    if modules_dst.exists():
        shutil.rmtree(modules_dst)

    shutil.copytree(modules_src, modules_dst, symlinks=True)
    print_success("Kernel modules installed")


def install_firmware():
    """Install firmware files to rootfs"""
    # Create firmware directory
    firmware_dst = ROOTFS_DIR / "lib" / "firmware"
    firmware_dst.mkdir(parents=True, exist_ok=True)

    # Check if external firmware exists
    firmware_src = EXTERNAL_DIR / "firmware"
    if firmware_src.exists():
        print_info("Installing firmware files")
        shutil.copytree(firmware_src, firmware_dst, dirs_exist_ok=True)
        print_success("Firmware installed")
    else:
        print_warning("External firmware not found, skipping")


def create_fstab():
    """Create /etc/fstab for the system"""
    print_info("Creating /etc/fstab")

    # For RK3399, we typically boot from eMMC or SD card with GPT partition
    fstab_content = """# /etc/fstab: static file system information
#
# <file system>  <mount point>  <type>  <options>         <dump>  <pass>
/dev/root        /              ext4    defaults,noatime  0       1
"""

    fstab_path = ROOTFS_DIR / "etc" / "fstab"
    fstab_path.write_text(fstab_content)


def configure_serial_console():
    """Configure serial console for RK3399"""
    print_info("Configuring serial console")

    # Add ttyFIQ0 to securetty for RK3399
    securetty = ROOTFS_DIR / "etc" / "securetty"
    with securetty.open('a') as f:
        f.write("ttyFIQ0\n")


def install_desktop(distro: str):
    """
    Install LXDE desktop environment

    Args:
        distro: Ubuntu distribution codename
    """
    print_info("Installing LXDE desktop environment")
    print_warning("This may take 10-20 minutes depending on network speed...")

    # Copy resolv.conf for network access
    shutil.copy2("/etc/resolv.conf", ROOTFS_DIR / "etc/resolv.conf")

    # Determine distribution type
    if distro in ["bionic", "xenial"]:
        dst_type = "Ubuntu"
    else:
        dst_type = "Debian"

    # Create desktop installation script
    desktop_script = ROOTFS_DIR / "tmp" / "install_desktop.sh"
    desktop_script.parent.mkdir(parents=True, exist_ok=True)

    script_content = f"""#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo ""
echo "========================================"
echo "Installing LXDE Desktop Environment"
echo "========================================"
echo ""

echo "Updating package lists..."
apt-get -y -q update

echo "Installing X.org and LXDE desktop..."
apt-get -y -q install xinit xserver-xorg
apt-get -y -q install lxde lightdm lightdm-gtk-greeter policykit-1 --no-install-recommends
apt-get -y -q install net-tools lxsession-logout

echo "Installing icon theme..."
if [ "{dst_type}" = "Ubuntu" ]; then
    apt-get -y -q install humanity-icon-theme --no-install-recommends
fi

echo "Installing audio support..."
apt-get -y -q install pulseaudio pulseaudio-utils alsa-oss alsa-utils alsa-tools libasound2-data pavucontrol

echo "Installing multimedia and utilities..."
apt-get -y -q install smplayer
apt-get -y -q install synaptic software-properties-gtk lxtask galculator policykit-1-gnome --no-install-recommends

echo "Installing network packages and browser..."
# For Ubuntu 20.04+, use Firefox as Chromium is only available via snap
# which is difficult to install in chroot environment
apt-get -y -q install firefox gvfs-fuse gvfs-backends --no-install-recommends || {{
    echo "Firefox installation failed, trying fallback browsers..."
    apt-get -y -q install midori gvfs-fuse gvfs-backends --no-install-recommends || {{
        echo "Browser installation failed, continuing without browser..."
        apt-get -y -q install gvfs-fuse gvfs-backends --no-install-recommends
    }}
}}
apt-get -y -q install network-manager-gnome

echo "Configuring desktop environment..."

# Configure X wrapper
if [ -f /etc/X11/Xwrapper.config ]; then
    sed -i 's/allowed_users=console/allowed_users=anybody/g' /etc/X11/Xwrapper.config
fi

# Configure LightDM greeter
if [ -f /etc/lightdm/lightdm-gtk-greeter.conf ]; then
    sed -i '/background=\\/usr/d' /etc/lightdm/lightdm-gtk-greeter.conf
fi

# Configure sound (set HDMI as default)
cat > /etc/asound.conf << 'ASOUND_EOF'
pcm.!default {{
    type hw
    card 1    # HDMI output
    device 0
}}
ctl.!default {{
    type hw
    card 1    # HDMI output
}}
ASOUND_EOF

# Configure PulseAudio
if [ -f /etc/pulse/default.pa ]; then
    sed -i 's/load-module module-udev-detect$/load-module module-udev-detect tsched=0/g' /etc/pulse/default.pa
fi

# Create groups if they don't exist
for group in fuse dialout cdrom dip plugdev netdev; do
    getent group $group &>/dev/null || groupadd $group
done

# Add user to groups (skip fuse if it still doesn't exist)
usermod -a -G adm,dialout,cdrom,dip,video,plugdev,netdev orangepi
getent group fuse &>/dev/null && usermod -a -G fuse orangepi || true

# Fix ownership
chown -R orangepi:orangepi /home/orangepi

echo "Cleaning up..."
apt-get -y autoremove
apt-get clean

echo ""
echo "========================================"
echo "Desktop installation complete!"
echo "========================================"
echo ""
"""

    desktop_script.write_text(script_content)
    desktop_script.chmod(0o755)

    # Execute in chroot
    mount_pseudo_filesystems()
    try:
        run_command([
            "chroot", str(ROOTFS_DIR),
            "/tmp/install_desktop.sh"
        ])
        print_success("LXDE desktop installed successfully")
    except Exception as e:
        print_error(f"Desktop installation failed: {e}")
        raise
    finally:
        # Cleanup temporary files
        desktop_script.unlink(missing_ok=True)
        (ROOTFS_DIR / "etc/resolv.conf").unlink(missing_ok=True)
        # IMPORTANT: Unmount pseudo-filesystems to prevent residual mounts
        umount_pseudo_filesystems()


def build_rootfs(distro: str, image_type: str, mirror: str, clean: bool = False):
    """
    Main build process for rootfs

    Args:
        distro: Ubuntu distribution codename
        image_type: Type of image (server or desktop)
        mirror: Mirror selection
        clean: Whether to clean existing rootfs
    """
    print_info("=" * 60)
    print_info(f"Building RK3399 Root Filesystem")
    print_info(f"  Distribution: Ubuntu {distro}")
    print_info(f"  Type: {image_type}")
    print_info(f"  Mirror: {mirror}")
    print_info("=" * 60)

    # Check root privileges
    check_root()

    # Create build directory
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Download Ubuntu base
        tarball = download_ubuntu_base(distro, mirror)

        # Extract rootfs
        extract_rootfs(tarball)

        # Setup QEMU for chroot
        setup_qemu_static()

        # Write APT sources
        write_apt_sources(distro, mirror)

        # Configure base system
        configure_base_system(distro)

        # Install kernel modules
        install_kernel_modules()

        # Install firmware
        install_firmware()

        # Create fstab
        create_fstab()

        # Configure serial console
        configure_serial_console()

        # Install desktop environment if requested
        if image_type == "desktop":
            install_desktop(distro)

        print_success("=" * 60)
        print_success("Root filesystem build complete!")
        print_success(f"Location: {ROOTFS_DIR}")
        if image_type == "desktop":
            print_success("Type: Desktop (LXDE)")
        else:
            print_success("Type: Server")
        print_success("=" * 60)

    except Exception as e:
        print_error(f"Build failed: {e}")
        sys.exit(1)
    finally:
        # Always cleanup mounts
        umount_pseudo_filesystems()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Build Ubuntu-based root filesystem for RK3399",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build Ubuntu 20.04 server image with China mirror
  sudo python3 scripts/build_rootfs.py --distro focal --type server --mirror cn

  # Build Ubuntu 18.04 server image with official mirror
  sudo python3 scripts/build_rootfs.py --distro bionic --type server --mirror official

  # Clean and rebuild
  sudo python3 scripts/build_rootfs.py --distro focal --clean
"""
    )

    parser.add_argument(
        "--distro",
        choices=list(DISTROS.keys()),
        default="focal",
        help="Ubuntu distribution (default: focal)"
    )

    parser.add_argument(
        "--type",
        choices=["server", "desktop"],
        default="desktop",
        help="Image type (default: desktop)"
    )

    parser.add_argument(
        "--mirror",
        choices=["cn", "official", "default"],
        default="cn",
        help="Ubuntu mirror (default: cn)"
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing rootfs before building"
    )

    args = parser.parse_args()

    build_rootfs(
        distro=args.distro,
        image_type=args.type,
        mirror=args.mirror,
        clean=args.clean
    )


if __name__ == "__main__":
    main()
