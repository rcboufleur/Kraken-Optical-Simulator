#!/usr/bin/env python3
"""Interactive 2D and 3D display example for KrakenOS.

This example builds a small achromatic doublet, traces a bundle of rays at
three wavelengths, and opens the new interactive display tools.

Controls in the 3D window:
    0 : full view
    1 : quarter cut
    2 : half cut
    r : show/hide rays
    s : show/hide surfaces
    e : show/hide red edges
    m : show/hide masks
    l : show/hide side faces
    p : save screenshot as krakenos_display3d.png

The 2D window includes Matplotlib controls for view, rays, surfaces, arrows,
ray count, equal-axis scaling, grid, and saving a PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# -----------------------------------------------------------------------------
# Import KrakenOS from installation, or from the repository root when running
# this example inside the Examples directory.
# -----------------------------------------------------------------------------
try:
    import KrakenOS as Kos
except ImportError:
    this_file = Path(__file__).resolve()
    repo_root = this_file.parents[1]
    sys.path.insert(0, str(repo_root))
    import KrakenOS as Kos


# -----------------------------------------------------------------------------
# Optical system: simple cemented doublet
# -----------------------------------------------------------------------------
def build_doublet():
    object_plane = Kos.surf()
    object_plane.Rc = 0.0
    object_plane.Thickness = 0.1
    object_plane.Glass = "AIR"
    object_plane.Diameter = 30.0
    object_plane.Name = "Object"

    lens_1 = Kos.surf()
    lens_1.Rc = 92.847
    lens_1.Thickness = 6.0
    lens_1.Glass = "BK7"
    lens_1.Diameter = 30.0
    lens_1.Name = "BK7 front"

    lens_2 = Kos.surf()
    lens_2.Rc = -30.716
    lens_2.Thickness = 3.0
    lens_2.Glass = "F2"
    lens_2.Diameter = 30.0
    lens_2.Name = "F2 interface"

    lens_3 = Kos.surf()
    lens_3.Rc = -78.19
    lens_3.Thickness = 97.37
    lens_3.Glass = "AIR"
    lens_3.Diameter = 30.0
    lens_3.Name = "Back surface"

    image_plane = Kos.surf()
    image_plane.Rc = 0.0
    image_plane.Thickness = 0.0
    image_plane.Glass = "AIR"
    image_plane.Diameter = 18.0
    image_plane.Name = "Image plane"
    image_plane.Nm_Pos = (-10, 10)

    surfaces = [object_plane, lens_1, lens_2, lens_3, image_plane]
    config = Kos.Setup()

    # Newer KrakenOS versions may support build=0 for lightweight sequential
    # tracing. Fall back to the classic constructor if needed.
    try:
        system = Kos.system(surfaces, config, build=0)
    except TypeError:
        system = Kos.system(surfaces, config)

    return system


# -----------------------------------------------------------------------------
# Ray bundle
# -----------------------------------------------------------------------------
def trace_ray_bundle(system):
    rays = Kos.raykeeper(system)

    wavelengths_um = [0.4861, 0.5876, 0.6563]  # F, d, C Fraunhofer lines
    heights_mm = np.linspace(-12.0, 12.0, 17)

    for wavelength in wavelengths_um:
        for y in heights_mm:
            source = [0.0, float(y), 0.0]
            direction = [0.0, 0.0, 1.0]
            system.Trace(source, direction, wavelength)
            rays.push()

    return rays


# -----------------------------------------------------------------------------
# Run example
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    doublet = build_doublet()
    rays = trace_ray_bundle(doublet)

    # Interactive 2D display with controls inside the Matplotlib window.
    Kos.display2d_interactive(
        doublet,
        rays,
        view=0,
        arrow=0,
        nrays=0,
        grid=True,
        title="Interactive KrakenOS 2D display",
    )

    # Interactive 3D display with PyVista sliders and keyboard shortcuts.
    Kos.display3d_interactive(
        doublet,
        rays,
        view=2,
        opacity=0.75,
        ray_width=2.0,
        nrays=0,
        text="KrakenOS interactive display",
    )
