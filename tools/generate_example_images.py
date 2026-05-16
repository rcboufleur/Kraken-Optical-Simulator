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
import warnings
from importlib import resources
from pathlib import Path

import matplotlib


matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize


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


def trace_circular_bundle(system, wavelengths=(0.55,), radius: float = 8.0, samples: int = 7):
    rays = Kos.raykeeper(system)
    for j in range(-samples, samples + 1):
        for i in range(-samples, samples + 1):
            x0 = (i / samples) * radius
            y0 = (j / samples) * radius
            if np.hypot(x0, y0) <= radius:
                for wavelength in wavelengths:
                    system.Trace([x0, y0, 0.0], [0.0, 0.0, 1.0], wavelength)
                    rays.push()
    return rays


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


def generate_dispersion_abbe_2d() -> None:
    system = build_doublet()
    rays = trace_circular_bundle(system, wavelengths=(0.40, 0.55, 0.70), radius=7.0, samples=4)
    save_display2d(system, rays, ASSET_DIR / "Examp_Dispersion_By_AbbeNumber_2d.png")


def generate_rms_best_focus_2d() -> None:
    system = build_doublet()
    rays = trace_pupil_bundle(system)
    x, y, z, l, m, n = rays.pick(-1, coordinates="local")
    shifts = np.linspace(-4.0, 4.0, 121)
    rms_values = [Kos.R_RMS_delta(shift, l, m, n, x, y) for shift in shifts]
    result = scipy.optimize.minimize_scalar(Kos.R_RMS_delta, args=(l, m, n, x, y), bracket=(-1.0, 1.0))
    best_shift = result.x
    best_x = ((l / n) * best_shift) + x
    best_y = ((m / n) * best_shift) + y

    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(shifts, rms_values, color="navy")
    axes[0].axvline(best_shift, color="firebrick", linestyle="--", label=f"Best focus {best_shift:.3f} mm")
    axes[0].set_title("RMS through focus")
    axes[0].set_xlabel("Image-plane shift (mm)")
    axes[0].set_ylabel("RMS radius (mm)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].scatter(x, y, s=16, label="Nominal plane")
    axes[1].scatter(best_x, best_y, s=16, label="Best focus")
    axes[1].set_title("Spot before and after refocus")
    axes[1].set_xlabel("X (mm)")
    axes[1].set_ylabel("Y (mm)")
    axes[1].axis("equal")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_RMS_BestFocus_2d.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_reverse_trace_2d() -> None:
    system = build_doublet()
    rays = Kos.raykeeper(system)
    source = np.asarray([0.0, 4.0, 0.0])
    system.Trace(source, [0.0, 0.0, 1.0], 0.55)
    rays.push()
    image_hit = np.asarray(system.XYZ[-1])
    system.RvTrace(image_hit, [0.0, 0.0, -1.0], 0.55, 3)
    rays.push()
    save_display2d(system, rays, ASSET_DIR / "Examp_Reverse_Trace_2d.png", arrow=1)


def generate_perfect_lens_2d() -> None:
    object_plane = Kos.surf(Thickness=50.0, Glass="AIR", Diameter=30.0)
    lens_1 = Kos.surf(Thin_Lens=100.0, Thickness=150.0, Glass="AIR", Diameter=30.0)
    lens_2 = Kos.surf(Thin_Lens=50.0, Thickness=100.0, Glass="AIR", Diameter=30.0)
    image_plane = Kos.surf(Thickness=0.0, Glass="AIR", Diameter=100.0, Name="Image plane")
    system = quiet_call(Kos.system, [object_plane, lens_1, lens_2, image_plane], Kos.Setup())
    rays = trace_circular_bundle(system, wavelengths=(0.45,), radius=9.0, samples=5)
    x, y, *_ = rays.pick(-1)

    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    old_show = plt.show
    try:
        plt.show = lambda *args, **kwargs: None
        plt.figure(figure.number)
        Kos.display2d(system, rays, 0, arrow=0, figsize=(5, 4))
        layout_figure = plt.gcf()
        layout_figure.savefig(ASSET_DIR / "Examp_Perfect_lens_2d.png", dpi=160, bbox_inches="tight")
        plt.close(layout_figure)
    finally:
        plt.show = old_show

    figure, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(x, y, marker="x")
    ax.set_title("Ideal-lens image-plane hits")
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.axis("equal")
    ax.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_Perfect_lens_plot.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_perfect_lens_telescope_2d() -> None:
    object_plane = Kos.surf(Thickness=120.0, Diameter=120.0)
    objective = Kos.surf(Thin_Lens=1000.0, Thickness=1020.0, Diameter=120.0)
    objective.Name = "Objective"
    eyepiece = Kos.surf(Thin_Lens=20.0, Thickness=50.0, Diameter=20.0)
    eyepiece.Name = "Eyepiece"
    image_plane = Kos.surf(Diameter=60.0, Name="Image plane")
    system = quiet_call(Kos.system, [object_plane, objective, eyepiece, image_plane], Kos.Setup())
    rays = Kos.raykeeper(system)
    pupil = Kos.PupilCalc(system, 1, 0.45, "EPD", objective.Diameter)
    pupil.Samp, pupil.Ptype, pupil.FieldType = 2, "fanx", "angle"
    for field_x in (-0.25, 0.0, 0.25):
        pupil.FieldX = field_x
        x, y, z, l, m, n = pupil.Pattern2Field()
        Kos.TraceLoop(x, y, z, l, m, n, 0.45, rays, clean=0)
    save_display2d(system, rays, ASSET_DIR / "Examp_Perfect_lens_Telescope_2d.png", view=1, arrow=1)


def generate_prism_refraction_2d() -> None:
    object_plane = Kos.surf(Thickness=10.0, Diameter=30.0)
    prism_1 = Kos.surf(Rc=0.0, Thickness=13.0, Glass="BK7", Diameter=30.0)
    prism_1.TiltX = 20.0
    prism_1.AxisMove = 0
    prism_2 = Kos.surf(Rc=0.0, Thickness=10.0, Glass="AIR", Diameter=30.0)
    prism_2.TiltX = -20.0
    prism_2.AxisMove = 0
    image_plane = Kos.surf(Thickness=0.0, Glass="AIR", Diameter=30.0, Name="Image plane")
    system = quiet_call(Kos.system, [object_plane, prism_1, prism_2, image_plane], Kos.Setup())
    rays = trace_circular_bundle(system, wavelengths=(0.40, 0.55, 0.70), radius=5.0, samples=3)
    save_display2d(system, rays, ASSET_DIR / "Examp_Refraction_Prism_2d.png")


def generate_flat_mirror_2d() -> None:
    system = build_doublet()
    # Rebuild with a fold mirror so the reflected ray path is visible.
    object_plane = Kos.surf(Thickness=10.0, Glass="AIR", Diameter=30.0)
    first = Kos.surf(Rc=92.84706570002484, Thickness=6.0, Glass="BK7", Diameter=30.0)
    second = Kos.surf(Rc=-30.71608670000159, Thickness=3.0, Glass="F2", Diameter=30.0)
    third = Kos.surf(Rc=-78.19730726078505, Thickness=57.37604742910693, Glass="AIR", Diameter=30.0)
    mirror = Kos.surf(Thickness=-40.0, Glass="MIRROR", Diameter=30.0, Name="45 degree fold mirror")
    mirror.TiltX = 45.0
    mirror.AxisMove = 2.0
    image_plane = Kos.surf(Thickness=0.0, Glass="AIR", Diameter=8.0, Name="Image plane")
    system = quiet_call(Kos.system, [object_plane, first, second, third, mirror, image_plane], Kos.Setup())
    rays = trace_circular_bundle(system, wavelengths=(0.45, 0.55, 0.65), radius=6.0, samples=3)
    save_display2d(system, rays, ASSET_DIR / "Examp_Flat_Mirror_45Deg_2d.png")


def generate_glass_catalog_order_2d() -> None:
    config = Kos.Setup()
    glass_name = "LAF2"
    matches = []
    for index, catalog_path in enumerate(config.GlassCat):
        try:
            content = Path(catalog_path).read_text(encoding="utf-8")
        except UnicodeError:
            content = Path(catalog_path).read_text(encoding="utf-16")
        if f"NM {glass_name} " in content:
            matches.append((index + 1, Path(catalog_path).name))

    first = matches[:8]
    labels = [name for _, name in first]
    positions = [pos for pos, _ in first]
    figure, ax = plt.subplots(figsize=(9, 4))
    ax.barh(range(len(labels)), positions, color="steelblue")
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("Catalog priority position")
    ax.set_title(f"Catalogs containing {glass_name}")
    ax.grid(axis="x", alpha=0.3)
    for row, position in enumerate(positions):
        ax.text(position + 0.2, row, f"#{position}", va="center")
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_Glass_Catalog_Order_2d.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_metal_mirror_energy_2d() -> None:
    def trace_mirror(coating_index):
        setup = Kos.Setup()
        gold_path = resources.files("KrakenOS") / "Cat" / "Gold.csv"
        setup.LoadMetal(gold_path, "Gold", 1)
        object_plane = Kos.surf(Thickness=100.0, Diameter=10.0)
        mirror = Kos.surf(Rc=-200.0, Thickness=-100.0, Glass="MIRROR", Diameter=20.0)
        mirror.CoatingMet = coating_index
        image_plane = Kos.surf(Thickness=0.0, Glass="AIR", Diameter=20.0, Name="Return plane")
        system = quiet_call(Kos.system, [object_plane, mirror, image_plane], setup)
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.5876)
        return [(float(system.RP[0]) + float(system.RS[0])) / 2.0, float(system.TT)]

    aluminum = trace_mirror(0)
    gold = trace_mirror(1)
    x = np.arange(2)
    width = 0.36
    figure, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x - width / 2, [aluminum[0], gold[0]], width, label="Average reflection")
    ax.bar(x + width / 2, [aluminum[1], gold[1]], width, label="Total transmission")
    ax.set_xticks(x, ["Aluminum", "Gold"])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Energy fraction")
    ax.set_title("Metal mirror energy comparison")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    figure.tight_layout()
    figure.savefig(ASSET_DIR / "Examp_Metal_Mirror_Energy_2d.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def generate_surfblock_basics_2d() -> None:
    catalog_path = resources.files("KrakenOS") / "LensCat" / "THORLABS.ZMF"
    with contextlib.redirect_stdout(io.StringIO()):
        catalog = Kos.zmf2dict([catalog_path])
    object_plane = Kos.surf(Diameter=25.4, Thickness=20.0)
    image_plane = Kos.surf(Diameter=25.4, Thickness=0.0, Name="Image plane")
    lens_list = [
        object_plane,
        Kos.SurfBlock(catalog["AC254-050-A"], name="achromat"),
        Kos.SurfBlock(catalog["LA1509-A"], name="plano_convex"),
        image_plane,
    ]
    surfaces = Kos.alignment(lens_list, {"achromat": 35.0, "plano_convex": 50.0})
    system = quiet_call(Kos.system, surfaces, Kos.Setup())
    rays = Kos.raykeeper(system)
    for y_source in (-2.0, 0.0, 2.0):
        system.Trace([0.0, y_source, 0.0], [0.0, 0.0, 1.0], 0.55)
        rays.push()
    save_display2d(system, rays, ASSET_DIR / "Examp_SurfBlock_Basics_2d.png")


GENERATORS = {
    "Examp_Ray_2d": generate_ray_2d,
    "Examp_Doublet_Lens_Pupil_2d": generate_doublet_pupil_2d,
    "Examp_Doublet_Lens_Pupil_3d": generate_doublet_pupil_3d,
    "Examp_PSF_MTF_From_Zernike_2d": generate_psf_mtf_2d,
    "Examp_Coating_Energy_Basics_2d": generate_coating_energy_2d,
    "Examp_Lens_Catalog_Basics_2d": generate_lens_catalog_2d,
    "Examp_Dispersion_By_AbbeNumber_2d": generate_dispersion_abbe_2d,
    "Examp_RMS_BestFocus_2d": generate_rms_best_focus_2d,
    "Examp_Reverse_Trace_2d": generate_reverse_trace_2d,
    "Examp_Perfect_lens_2d": generate_perfect_lens_2d,
    "Examp_Perfect_lens_Telescope_2d": generate_perfect_lens_telescope_2d,
    "Examp_Refraction_Prism_2d": generate_prism_refraction_2d,
    "Examp_Flat_Mirror_45Deg_2d": generate_flat_mirror_2d,
    "Examp_Glass_Catalog_Order_2d": generate_glass_catalog_order_2d,
    "Examp_Metal_Mirror_Energy_2d": generate_metal_mirror_energy_2d,
    "Examp_SurfBlock_Basics_2d": generate_surfblock_basics_2d,
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
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Failed to use notebook backend:*")
            warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"KrakenOS\.Physics")
            GENERATORS[name]()

    if not args.no_manual:
        regenerate_manual()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
