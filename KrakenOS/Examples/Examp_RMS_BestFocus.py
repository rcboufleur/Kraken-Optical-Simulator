#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: RMS spot radius and best-focus shift.

This example builds a compact doublet, traces a ray bundle, measures the RMS
spot radius at the nominal image plane, estimates the axial best-focus shift,
and then traces the same bundle again after moving the image plane.

What this example teaches:
- how to use `PupilCalc` to generate a small ray bundle
- how to extract image-plane ray coordinates with `raykeeper.pick`
- how to calculate RMS spot radius with `Kos.RMS`
- how to estimate and apply a best-focus shift by minimizing RMS radius

Expected output:
- printed RMS radius before focus adjustment
- printed best-focus shift in millimeters
- printed RMS radius after focus adjustment

Didactic note:
- the `display2d` call near the end is intentionally commented. Uncomment it
  if you want to inspect the traced bundle graphically.

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import sys
from pathlib import Path

import scipy.optimize


sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos


def build_doublet():
    """Build a small cemented doublet used by several beginner examples."""
    object_plane = Kos.surf()
    object_plane.Thickness = 10.0
    object_plane.Glass = "AIR"
    object_plane.Diameter = 30.0

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

    last_lens_surface = Kos.surf()
    last_lens_surface.Rc = -78.19730726078505
    last_lens_surface.Thickness = 97.37604742910693
    last_lens_surface.Glass = "AIR"
    last_lens_surface.Diameter = 30.0

    image_plane = Kos.surf()
    image_plane.Thickness = 0.0
    image_plane.Glass = "AIR"
    image_plane.Diameter = 5.0
    image_plane.Name = "Image plane"

    surfaces = [
        object_plane,
        first_surface,
        second_surface,
        last_lens_surface,
        image_plane,
    ]
    return Kos.system(surfaces, Kos.Setup())


def trace_bundle(system, wavelength=0.55):
    """Trace a compact pupil fan through the system and return a raykeeper."""
    rays = Kos.raykeeper(system)

    pupil = Kos.PupilCalc(system, 1, wavelength, "EPD", 20.0)
    pupil.Samp = 9
    pupil.Ptype = "hexapolar"
    pupil.FieldType = "angle"
    pupil.FieldX = 0.0
    pupil.FieldY = 0.0

    x, y, z, l, m, n = pupil.Pattern2Field()
    Kos.TraceLoop(x, y, z, l, m, n, wavelength, rays, clean=1)
    return rays


def rms_at_image(rays):
    """Return RMS spot radius and ray data at the image plane."""
    x, y, z, l, m, n = rays.pick(-1, coordinates="local")
    rms_radius, centroid_x, centroid_y = Kos.RMS(x, y, z, l, m, n)
    return rms_radius, centroid_x, centroid_y, x, y, z, l, m, n


def best_focus_shift(x, y, l, m, n):
    """Find the axial image-plane shift that minimizes RMS spot radius."""
    result = scipy.optimize.minimize_scalar(
        Kos.R_RMS_delta,
        args=(l, m, n, x, y),
        bracket=(-1.0, 1.0),
    )
    if not result.success:
        raise RuntimeError("Best-focus minimization did not converge")
    return result.x


def main():
    doublet = build_doublet()
    initial_rays = trace_bundle(doublet)

    (
        initial_rms,
        initial_cx,
        initial_cy,
        x,
        y,
        z,
        l,
        m,
        n,
    ) = rms_at_image(initial_rays)

    focus_shift = best_focus_shift(x, y, l, m, n)

    print("Initial RMS radius (mm):", initial_rms)
    print("Initial centroid X/Y (mm):", initial_cx, initial_cy)
    print("Best-focus axial shift (mm):", focus_shift)

    # The image plane is reached after the last lens surface, so moving the
    # previous thickness changes the axial position of the final image plane.
    doublet.SDT[-2].Thickness = doublet.SDT[-2].Thickness + focus_shift
    doublet.SetData()
    doublet.SetSolid()

    focused_rays = trace_bundle(doublet)
    focused_rms, focused_cx, focused_cy, *_ = rms_at_image(focused_rays)

    print("Focused RMS radius (mm):", focused_rms)
    print("Focused centroid X/Y (mm):", focused_cx, focused_cy)
    print("RMS improvement factor:", initial_rms / focused_rms)

    # Optional didactic display:
    # Kos.display2d(doublet, focused_rays, 0)


if __name__ == "__main__":
    main()
