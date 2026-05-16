#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: coating table and ray energy terms.

This example builds a tiny air-to-air system with a coated flat surface. The
geometry is intentionally simple so the output can focus on the coating table
format and the reflected/transmitted energy terms stored by KrakenOS.

What this example teaches:
- how to define a coating table as `[R, A, W, THETA]`
- how KrakenOS chooses the nearest wavelength and angle sample
- where reflected and transmitted S/P energy terms are stored
- how total transmission is accumulated in `system.TT`

Expected output:
- coating lookup values for two incidence-angle samples
- traced ray energy terms for one coated surface

Units:
- distances are in millimeters
- wavelengths are in micrometers
- coating angles are in degrees
"""

import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos


def as_float_list(values):
    """Convert NumPy scalar values to plain Python floats for clean printing."""
    return [float(value) for value in values]


def as_float_tuple(values):
    """Convert coating lookup output to a clean tuple for printing."""
    return tuple(float(value) if index < 4 else int(value) for index, value in enumerate(values))


def build_coated_system():
    object_plane = Kos.surf()
    object_plane.Thickness = 10.0
    object_plane.Glass = "AIR"
    object_plane.Diameter = 10.0
    object_plane.Drawing = 0

    coated_surface = Kos.surf()
    coated_surface.Thickness = 10.0
    coated_surface.Glass = "AIR"
    coated_surface.Diameter = 10.0

    # Coating table format:
    # R     = reflectivity values indexed by angle row and wavelength column
    # A     = absorption values with the same shape
    # W     = wavelength samples
    # THETA = incidence-angle samples
    reflectivity = [
        [0.20, 0.40, 0.60],
        [0.30, 0.50, 0.70],
    ]
    absorption = [
        [0.00, 0.00, 0.00],
        [0.00, 0.00, 0.00],
    ]
    wavelengths = [0.45, 0.55, 0.65]
    angles = [0.0, 45.0]
    coated_surface.Coating = [reflectivity, absorption, wavelengths, angles]

    image_plane = Kos.surf()
    image_plane.Thickness = 0.0
    image_plane.Glass = "AIR"
    image_plane.Diameter = 10.0
    image_plane.Name = "Image plane"

    return Kos.system([object_plane, coated_surface, image_plane], Kos.Setup())


system = build_coated_system()
rays = Kos.raykeeper(system)

normal_lookup = system.CoatingFun(system.SDT[1].Coating, Theta=2.0, wav=0.55)
tilted_lookup = system.CoatingFun(system.SDT[1].Coating, Theta=43.0, wav=0.55)

print("Nearest normal-incidence coating lookup (Rp, Rs, Tp, Ts, valid):", as_float_tuple(normal_lookup))
print("Nearest 45-degree coating lookup (Rp, Rs, Tp, Ts, valid):", as_float_tuple(tilted_lookup))

system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
rays.push()

print("Surface RP terms:", as_float_list(system.RP))
print("Surface RS terms:", as_float_list(system.RS))
print("Surface TP terms:", as_float_list(system.TP))
print("Surface TS terms:", as_float_list(system.TS))
print("Per-surface transmission factors:", as_float_list(system.TTBE))
print("Accumulated total transmission:", float(system.TT))

# Optional didactic display:
# Kos.display2d(system, rays, 0)
