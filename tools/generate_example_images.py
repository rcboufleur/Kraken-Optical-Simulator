#!/usr/bin/env python3
"""Generate selected 2D and 3D images for the KrakenOS examples manual.

This script creates a curated set of stable images under `docs/assets/examples`.
It does not execute every example file. Instead, it recreates small, reliable
scenes that represent key examples and can run in a documentation workflow.

Usage:

    python tools/generate_example_images.py --all
    python tools/generate_example_images.py --list
"""

from __future__ import annotations

import argparse
import contextlib
import io
import subprocess
import sys
from importlib import resources
from pathlib import Path

import matplotlib


matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "docs" / "assets" / "examples"

sys.path.insert(0, str(REPO_ROOT))
import KrakenOS as Kos  # noqa: E402


def quiet_call(func, *args, **kwargs):
    """Run noisy KrakenOS setup code while keeping generator output readable."""
    with contextlib.redirect_stdout(io.StringIO()):
        return func(*args, **kwargs)


def save_current_figure(path: Path, dpi: int = 160) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    figure = plt.gcf()
    figure.tight_layout()
    figure.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(figure)


def build_doublet():
    object_plane = Kos.surf(Thickness=10.0, Glass="AIR", Diameter=30.0)

    first_surface = Kos.surf()
    first_surface.Rc = 92.84706570002484
    first_surface.Thickness = 6.0
    first_surface.Glass = "BK7"
    first_surface.Diameter = 30.0

    second_surface = Kos.surf()
    second_surface.Rc = -30.71608670000159
    second_surface.Thickness = 3.0
    second_surface.Glass = "F2"
    second_surface.Diameter = 30.0

    last_surface = Kos.surf()
    last_surface.Rc = -78.19730726078505
    last_surface.Thickness = 97.37604742910693
    last_surface.Glass = "AIR"
    last_surface.Diameter = 30.0

    image_plane = Kos.surf(Thickness=0.0, Glass="AIR", Diameter=12.0)
    image_plane.Name = "Image plane"

    return quiet_call(
        Kos.system,
        [object_plane, first_surface, second_surface, last_surface, image_plane],
        Kos.Setup(),
    )


def trace_pupil_bundle(system, wavelength: float = 0.55):
    rays = Kos.raykeeper(system)
    pupil = Kos.PupilCalc(system, 1, wavelength, "EPD", 20.0)
    pupil.Samp = 5
    pupil.Ptype = "hexapolar"
    pupil.FieldType = "angle"
    pupil.FieldX = 0.0
    pupil.FieldY = 0.0
    x, y, z, l, m, n = pupil.Pattern2Field()
    Kos.TraceLoop(x, y, z, l, m, n, wavelength, rays, clean=1)
    return rays


def save_display2d(system, rays, path: Path, view: int = 0, arrow: int = 0) -> None:
    old_show = plt.show
    try:
        plt.show = lambda *args, **kwargs: None
        Kos.display2d(system, rays, view, arrow, figsize=(10, 4))
        save_current_figure(path)
    finally:
        plt.show = old_show


def generate_ray_2d() -> None:
    system = build_doublet()
    rays = Kos.raykeeper(system)
    system.Trace([0.0, 8.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays.push()
    save_display2d(system, rays, ASSET_DIR / "Examp_Ray_2d.png", arrow=1)


def generate_doublet_pupil_2d() -> None:
    system = build_doublet()
    rays = trace_pupil_bundle(system)
    save_display2d(system, rays, ASSET_DIR / "Examp_Doublet_Lens_Pupil_2d.png")


def generate_doublet_pupil_3d() -> None:
    system = build_doublet()
    rays = trace_pupil_bundle(system)
    out = ASSET_DIR / "Examp_Doublet_Lens_Pupil_3d.png"
    try:
        quiet_call(
            Kos.display3d_colab,
            system,
            rays,
            0,
            filename=str(out),
            window_size=(1100, 700),
            show_grid=False,
            text="KrakenOS Doublet Pupil",
        )
    except Exception as exc:
        print(f"SKIP 3D image ({exc})")


def generate_psf_mtf_2d() -> None:
    coefficients = np.zeros(12)
    coefficients[0] = 1e-12
    coefficients[4] = 0.10
    coefficients[5] = 0.03

    focal_length = 100.0
    diameter = 20.0
    wavelength = 0.55
    psf = Kos.psf(coefficients, focal_length, diameter, wavelength, pixels=160, PupilSample=4, plot=0)
    mtf = Kos.calculate_mtf(coefficients, focal_length, diameter, wavelength)
    center = mtf.shape[0] // 2

    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].imshow(psf / np.max(psf), cmap="bone")
    axes[0].set_title("Normalized PSF")
    axes[0].set_axis_off()

    axes[1].plot(mtf[center, center:], color="navy", label="Tangential")
    axes[1].plot(mtf[center:, center], color="firebrick", label="Sagittal")
    axes[1].set_title("MTF profiles")
    axes[1].set_xlabel("Sample")
    axes[1].set_ylabel("MTF")
    axes[1].set_ylim(0, 1.05)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_PSF_MTF_From_Zernike_2d.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_coating_energy_2d() -> None:
    labels = ["RP", "RS", "TP", "TS"]
    normal = [0.4, 0.4, 0.6, 0.6]
    tilted = [0.5, 0.5, 0.5, 0.5]
    x = np.arange(len(labels))
    width = 0.36

    figure, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - width / 2, normal, width, label="Nearest 0 deg")
    ax.bar(x + width / 2, tilted, width, label="Nearest 45 deg")
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Energy fraction")
    ax.set_title("Coating lookup energy terms")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_Coating_Energy_Basics_2d.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_lens_catalog_2d() -> None:
    catalog_path = resources.files("KrakenOS") / "LensCat" / "THORLABS.ZMF"
    with contextlib.redirect_stdout(io.StringIO()):
        catalog = Kos.zmf2dict([catalog_path])
    surfaces = Kos.cat2surf(catalog["AC254-050-A"], Thickness=50.0, Glass="AIR")
    system = quiet_call(
        Kos.system,
        [Kos.surf(Thickness=20.0, Glass="AIR", Diameter=25.4)]
        + surfaces
        + [Kos.surf(Thickness=0.0, Glass="AIR", Diameter=25.4)],
        Kos.Setup(),
    )
    rays = Kos.raykeeper(system)
    for y in [-4.0, 0.0, 4.0]:
        system.Trace([0.0, y, 0.0], [0.0, 0.0, 1.0], 0.55)
        rays.push()
    save_display2d(system, rays, ASSET_DIR / "Examp_Lens_Catalog_Basics_2d.png")


GENERATORS = {
    "Examp_Ray_2d": generate_ray_2d,
    "Examp_Doublet_Lens_Pupil_2d": generate_doublet_pupil_2d,
    "Examp_Doublet_Lens_Pupil_3d": generate_doublet_pupil_3d,
    "Examp_PSF_MTF_From_Zernike_2d": generate_psf_mtf_2d,
    "Examp_Coating_Energy_Basics_2d": generate_coating_energy_2d,
    "Examp_Lens_Catalog_Basics_2d": generate_lens_catalog_2d,
}


def regenerate_manual() -> None:
    subprocess.run([sys.executable, str(REPO_ROOT / "tools" / "generate_examples_manual.py")], check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="Image generator names to run")
    parser.add_argument("--all", action="store_true", help="Run all curated image generators")
    parser.add_argument("--list", action="store_true", help="List available image generators")
    parser.add_argument("--no-manual", action="store_true", help="Do not regenerate docs/examples_manual.md")
    args = parser.parse_args(argv)

    if args.list:
        for name in GENERATORS:
            print(name)
        return 0

    selected = list(GENERATORS) if args.all else args.names
    if not selected:
        parser.error("use --all or provide one or more generator names")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / ".gitkeep").write_text("", encoding="utf-8")

    for name in selected:
        if name not in GENERATORS:
            raise SystemExit(f"Unknown image generator: {name}")
        print(f"Generating {name}")
        GENERATORS[name]()

    if not args.no_manual:
        regenerate_manual()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
