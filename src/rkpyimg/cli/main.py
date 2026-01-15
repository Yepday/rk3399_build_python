"""
Main CLI entry point for rkpyimg.

Provides a unified interface to Rockchip firmware packing tools:
- loaderimage: Pack/unpack U-Boot and Trust binaries
- boot-merger: Merge DDR init and miniloader into idbloader.img
- trust-merger: Merge BL31/BL32 into trust.img

Usage:
    rkpyimg --help
    rkpyimg loaderimage --help
    rkpyimg boot-merger --help
    rkpyimg trust-merger --help
"""

from __future__ import annotations

import sys
import click
from pathlib import Path

from rkpyimg import __version__


@click.group()
@click.version_option(version=__version__, prog_name="rkpyimg")
def main() -> None:
    """
    Rockchip firmware packing tools in pure Python.

    This tool provides Python implementations of Rockchip's proprietary
    firmware packing tools (boot_merger, trust_merger, loaderimage).
    """
    pass


# ========== loaderimage command ==========
@main.group("loaderimage")
def loaderimage_cli() -> None:
    """
    Pack/unpack U-Boot and Trust binaries into Rockchip format.

    Equivalent to the original 'loaderimage' tool.
    """
    pass


@loaderimage_cli.command("pack")
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.argument("load_addr", required=False)
@click.option("--type", "-t", "image_type",
              type=click.Choice(["uboot", "trust"]),
              default="uboot",
              help="Image type (default: uboot)")
@click.option("--size", nargs=2, type=int, metavar="KB NUM",
              help="Size in KB and number of copies")
@click.option("--version", type=int, default=0,
              help="Version number for rollback protection")
def loaderimage_pack(
    input_file: str,
    output_file: str,
    load_addr: str | None,
    image_type: str,
    size: tuple[int, int] | None,
    version: int,
) -> None:
    """
    Pack binary into Rockchip loader image format.

    \b
    Examples:
      # Pack U-Boot
      rkpyimg loaderimage pack u-boot.bin uboot.img 0x200000

      # Pack U-Boot with size limit
      rkpyimg loaderimage pack u-boot.bin uboot.img 0x200000 --size 1024 1

      # Pack Trust OS
      rkpyimg loaderimage pack trust.bin trust.img --type trust
    """
    from rkpyimg.tools.loaderimage import pack_loader_image

    # Parse load address
    if load_addr:
        load_addr_int = int(load_addr, 16) if load_addr.startswith("0x") else int(load_addr)
    else:
        load_addr_int = 0x8400000 if image_type == "trust" else 0x200000

    # Parse size options
    max_size = size[0] * 1024 if size else None
    num_copies = size[1] if size else None

    try:
        result = pack_loader_image(
            input_file,
            output_file,
            load_addr_int,
            image_type=image_type,  # type: ignore
            version=version,
            max_size=max_size,
            num_copies=num_copies,
        )
        click.echo(f"✓ Packed: {result}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@loaderimage_cli.command("unpack")
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
def loaderimage_unpack(input_file: str, output_file: str) -> None:
    """
    Unpack Rockchip loader image.

    \b
    Examples:
      rkpyimg loaderimage unpack uboot.img u-boot.bin
      rkpyimg loaderimage unpack trust.img trust.bin
    """
    from rkpyimg.tools.loaderimage import unpack_loader_image

    try:
        unpack_loader_image(input_file, output_file)
        click.echo(f"✓ Unpacked: {output_file}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@loaderimage_cli.command("info")
@click.argument("image_file", type=click.Path(exists=True))
def loaderimage_info(image_file: str) -> None:
    """
    Show loader image information.

    \b
    Examples:
      rkpyimg loaderimage info uboot.img
    """
    from rkpyimg.tools.loaderimage import get_loader_info

    try:
        get_loader_info(image_file)
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


# ========== boot-merger command ==========
@main.group("boot-merger")
def boot_merger_cli() -> None:
    """
    Merge DDR init and miniloader into idbloader.img.

    Equivalent to the original 'boot_merger' tool.
    """
    pass


@boot_merger_cli.command("pack")
@click.argument("ini_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(),
              help="Output file (overrides INI config)")
@click.option("--rc4", is_flag=True,
              help="Enable RC4 encryption")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
def boot_merger_pack(
    ini_file: str,
    output: str | None,
    rc4: bool,
    verbose: bool,
) -> None:
    """
    Pack DDR and miniloader from INI configuration.

    \b
    Examples:
      rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini
      rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini -o idbloader.img
      rkpyimg boot-merger pack RKBOOT/RK3399MINIALL.ini --rc4
    """
    from rkpyimg.tools.boot_merger import BootMerger
    from rkpyimg.core.ini_parser import RKBootConfig

    try:
        merger = BootMerger.from_ini(ini_file)
        merger.enable_rc4 = rc4

        if not merger.validate_binaries():
            click.echo("✗ Error: Some binaries are missing!", err=True)
            sys.exit(1)

        output_path = output or merger.config.output_path
        result = merger.pack(output_path)
        click.echo(f"✓ Packed: {result}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@boot_merger_cli.command("unpack")
@click.argument("image_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(),
              help="Output directory (default: unpacked)")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
def boot_merger_unpack(
    image_file: str,
    output: str | None,
    verbose: bool,
) -> None:
    """
    Unpack boot merger image.

    \b
    Examples:
      rkpyimg boot-merger unpack idbloader.img
      rkpyimg boot-merger unpack idbloader.img -o output_dir
    """
    from rkpyimg.tools.boot_merger import BootMerger
    from rkpyimg.core.ini_parser import RKBootConfig

    try:
        output_dir = output or "unpacked"
        merger = BootMerger(config=RKBootConfig())  # Dummy config for unpack
        merger.unpack(image_file, output_dir)
        click.echo(f"✓ Unpacked to: {output_dir}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ========== trust-merger command ==========
@main.group("trust-merger")
def trust_merger_cli() -> None:
    """
    Merge BL31/BL32 into trust.img.

    Equivalent to the original 'trust_merger' tool.
    """
    pass


@trust_merger_cli.command("pack")
@click.argument("ini_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(),
              help="Output file (overrides INI config)")
@click.option("--rsa", type=int, default=4,
              help="RSA mode: 0=none, 1=1024, 2=2048, 3=2048 PSS, 4=2048 new (default: 4)")
@click.option("--sha", type=int, default=2,
              help="SHA mode: 0=none, 1=SHA1, 2=SHA256 (default), 3=SHA512")
@click.option("--size", type=int, default=1024,
              help="Trust image size in KB (default: 1024)")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
def trust_merger_pack(
    ini_file: str,
    output: str | None,
    rsa: int,
    sha: int,
    size: int,
    verbose: bool,
) -> None:
    """
    Pack BL31/BL32 from INI configuration.

    \b
    Examples:
      rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini
      rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini -o trust.img
      rkpyimg trust-merger pack RKTRUST/RK3399TRUST.ini --rsa 4 --sha 2
    """
    from rkpyimg.tools.trust_merger import TrustMerger

    try:
        merger = TrustMerger.from_ini(ini_file)
        merger.set_rsa_mode(rsa)
        merger.set_sha_mode(sha)
        merger.size = size

        output_path = output or merger.config.output_path
        result = merger.pack(output_path)
        click.echo(f"✓ Packed: {result}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@trust_merger_cli.command("unpack")
@click.argument("image_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(),
              help="Output directory (default: current)")
@click.option("--verbose", "-v", is_flag=True,
              help="Verbose output")
def trust_merger_unpack(
    image_file: str,
    output: str | None,
    verbose: bool,
) -> None:
    """
    Unpack trust image.

    \b
    Examples:
      rkpyimg trust-merger unpack trust.img
      rkpyimg trust-merger unpack trust.img -o output_dir
    """
    from rkpyimg.tools.trust_merger import TrustMerger

    try:
        output_dir = output or "."
        files = TrustMerger.unpack(image_file, output_dir)
        click.echo(f"✓ Unpacked {len(files)} components to: {output_dir}")
        for name, path in files.items():
            click.echo(f"  - {name}: {path}")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
