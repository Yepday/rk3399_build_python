"""
Main CLI entry point for rkpyimg.

Usage:
    rkpyimg --help
    rkpyimg pack --help
    rkpyimg inspect <image>
    rkpyimg build --board orangepi-rk3399 -o output.img
"""

from __future__ import annotations

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


@main.command()
@click.argument("image", type=click.Path(exists=True))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def inspect(image: str, verbose: bool) -> None:
    """
    Inspect a Rockchip firmware image.

    Shows header information, partitions, and checksums.
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    # TODO: Implement image inspection
    console.print(f"[yellow]Inspecting: {image}[/yellow]")
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.option("--input", "-i", "input_file", required=True,
              type=click.Path(exists=True), help="Input binary file")
@click.option("--output", "-o", "output_file", required=True,
              type=click.Path(), help="Output image file")
@click.option("--type", "-t", "image_type",
              type=click.Choice(["uboot", "trust", "loader"]),
              default="uboot", help="Image type")
@click.option("--chip", "-c", default="RK3399", help="Chip type")
@click.option("--addr", "-a", default="0x200000", help="Load address (hex)")
def pack(
    input_file: str,
    output_file: str,
    image_type: str,
    chip: str,
    addr: str,
) -> None:
    """
    Pack a binary into Rockchip image format.

    Equivalent to loaderimage --pack command.
    """
    from rich.console import Console

    console = Console()
    load_addr = int(addr, 16) if addr.startswith("0x") else int(addr)

    console.print(f"[cyan]Packing {input_file} -> {output_file}[/cyan]")
    console.print(f"  Type: {image_type}")
    console.print(f"  Chip: {chip}")
    console.print(f"  Load address: 0x{load_addr:08X}")

    # TODO: Implement packing
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.option("--ini", "-i", required=True,
              type=click.Path(exists=True), help="INI configuration file")
@click.option("--output", "-o", type=click.Path(), help="Output file (overrides INI)")
@click.option("--type", "-t", "merge_type",
              type=click.Choice(["boot", "trust"]),
              required=True, help="Merger type")
def merge(ini: str, output: str | None, merge_type: str) -> None:
    """
    Merge binaries using INI configuration.

    Equivalent to boot_merger or trust_merger commands.
    """
    from rich.console import Console

    console = Console()

    console.print(f"[cyan]Merging using {ini}[/cyan]")
    console.print(f"  Type: {merge_type}_merger")
    if output:
        console.print(f"  Output: {output}")

    # TODO: Implement merging
    console.print("[red]Not yet implemented[/red]")


@main.command()
@click.option("--board", "-b", required=True, help="Board name (e.g., orangepi-rk3399)")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output image")
@click.option("--size", "-s", default=2048, type=int, help="Image size in MB")
@click.option("--idbloader", type=click.Path(exists=True), help="idbloader.img path")
@click.option("--uboot", type=click.Path(exists=True), help="uboot.img path")
@click.option("--trust", type=click.Path(exists=True), help="trust.img path")
@click.option("--boot", type=click.Path(exists=True), help="boot.img path")
@click.option("--rootfs", type=click.Path(exists=True), help="rootfs path")
def build(
    board: str,
    output: str,
    size: int,
    idbloader: str | None,
    uboot: str | None,
    trust: str | None,
    boot: str | None,
    rootfs: str | None,
) -> None:
    """
    Build a complete bootable image.

    Assembles all components into a flashable image with GPT partitions.
    """
    from rich.console import Console
    from rkpyimg.image import ImageBuilder

    console = Console()

    console.print(f"[cyan]Building image for {board}[/cyan]")
    console.print(f"  Output: {output}")
    console.print(f"  Size: {size} MB")

    builder = ImageBuilder(board=board)

    if idbloader:
        builder.set_idbloader(idbloader)
    if uboot:
        builder.set_uboot(uboot)
    if trust:
        builder.set_trust(trust)
    if boot:
        builder.set_boot(boot)
    if rootfs:
        builder.set_rootfs(rootfs)

    console.print(builder.info())

    # TODO: Implement building
    console.print("[red]Not yet implemented[/red]")


if __name__ == "__main__":
    main()
