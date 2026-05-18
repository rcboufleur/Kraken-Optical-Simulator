#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: bundle tracing a user ExtraData surface without derivative.

This example uses the classic KrakenOS user-defined surface convention:

    ExtraData = [surface_function, coefficients]

No analytical derivative is provided.  The scalar ``system.Trace()`` path keeps
using the historical numerical derivative.  The experimental ``trace_bundle()``
path uses an internal vectorized numerical derivative when the surface function
can evaluate NumPy arrays.

What this example teaches:
- how to define a user ``ExtraData`` surface without ``dz/dx`` and ``dz/dy``;
- how to trace the same ray set with scalar ``system.Trace()`` and bundled
  ``trace_bundle()``;
- how to load bundled rays into ``raykeeper`` with ``extend_bundle_result()``;
- how to compare final spot position, direction, RMS, and timing.

Didactic note:
- ``trace_bundle()`` is still experimental and is imported explicitly from
  ``KrakenOS.BundleTrace``.
- Analytical derivatives remain the preferred path when available.  This
  example demonstrates the faster numerical fallback for compatible user
  surfaces.
"""

import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))

import KrakenOS as Kos
from KrakenOS.BundleTrace import trace_bundle


def user_surface(x, y, coef):
    """Smooth user sag function that supports scalar and NumPy array inputs."""

    period, amplitude = coef
    k = 2.0 * np.pi / period
    return amplitude * np.cos(k * x) * np.cos(k * y)


def build_system():
    # Object plane.
    p_obj = Kos.surf()
    p_obj.Glass = "AIR"
    p_obj.Thickness = 10.0
    p_obj.Diameter = 30.0
    p_obj.Name = "Object"

    # User-defined refracting surface.  Notice that ExtraData has only
    # [function, coefficients].  No analytical derivative is supplied here.
    user_shape = Kos.surf()
    user_shape.Glass = "BK7"
    user_shape.Thickness = 8.0
    user_shape.Diameter = 30.0
    user_shape.ExtraData = [user_surface, [12.0, 0.08]]
    user_shape.Name = "ExtraData surface"

    # Exit plane from glass to air.
    exit_surface = Kos.surf()
    exit_surface.Glass = "AIR"
    exit_surface.Thickness = 30.0
    exit_surface.Diameter = 30.0
    exit_surface.Name = "Exit"

    # Image plane.
    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 30.0
    image.Name = "Image"

    return Kos.system([p_obj, user_shape, exit_surface, image], Kos.Setup(), build=0)


def generate_rays(samples=41, radius=8.0):
    origins = []
    for x in np.linspace(-radius, radius, samples):
        for y in np.linspace(-radius, radius, samples):
            if np.sqrt((x * x) + (y * y)) <= radius:
                origins.append([x, y, 0.0])

    origins = np.asarray(origins, dtype=float)
    directions = np.tile(np.asarray([0.0, 0.0, 1.0]), (len(origins), 1))
    return origins, directions


def scalar_trace(system, origins, directions, wavelength):
    active = []
    final_hits = []
    final_directions = []

    start = time.perf_counter()
    for origin, direction in zip(origins, directions):
        system.Trace(origin, direction, wavelength)
        valid = system.val == 1
        active.append(valid)
        final_hits.append(np.asarray(system.XYZ[-1], dtype=float))
        if valid:
            final_directions.append(np.asarray(system.R_LMN[-1], dtype=float))
        else:
            final_directions.append(np.zeros(3))
    elapsed = time.perf_counter() - start

    return {
        "active": np.asarray(active, dtype=bool),
        "final_hits": np.asarray(final_hits, dtype=float),
        "final_directions": np.asarray(final_directions, dtype=float),
        "elapsed": elapsed,
    }


def bundle_trace_to_raykeeper(system, origins, directions, wavelength):
    start = time.perf_counter()
    bundle = trace_bundle(system, origins, directions, wavelength, keep_history=True)
    elapsed = time.perf_counter() - start

    rays = Kos.raykeeper(system)
    rays.extend_bundle_result(bundle, wavelength)
    bundle["elapsed"] = elapsed
    return bundle, rays


def spot_metrics(points):
    cen_x = np.mean(points[:, 0])
    cen_y = np.mean(points[:, 1])
    dx = points[:, 0] - cen_x
    dy = points[:, 1] - cen_y
    radius = np.sqrt((dx * dx) + (dy * dy))
    return {
        "centroid": (cen_x, cen_y),
        "rms": np.sqrt(np.mean(radius * radius)),
        "max_radius": np.max(radius),
    }


def main():
    wavelength = 0.55
    origins, directions = generate_rays()

    scalar_system = build_system()
    bundle_system = build_system()

    scalar = scalar_trace(scalar_system, origins, directions, wavelength)
    bundle, bundle_rays = bundle_trace_to_raykeeper(
        bundle_system, origins, directions, wavelength
    )

    active = scalar["active"]
    bundle_x, bundle_y, bundle_z, bundle_l, bundle_m, bundle_n = bundle_rays.pick(-1)
    bundle_hits_from_raykeeper = np.column_stack([bundle_x, bundle_y, bundle_z])
    bundle_directions_from_raykeeper = np.column_stack([bundle_l, bundle_m, bundle_n])

    max_hit_error = np.max(
        np.abs(bundle_hits_from_raykeeper - scalar["final_hits"][active])
    )
    max_direction_error = np.max(
        np.abs(bundle_directions_from_raykeeper - scalar["final_directions"][active])
    )

    scalar_metrics = spot_metrics(scalar["final_hits"][active])
    bundle_metrics = spot_metrics(bundle_hits_from_raykeeper)
    speedup = scalar["elapsed"] / bundle["elapsed"] if bundle["elapsed"] > 0.0 else float("inf")

    print("\nExtraData bundle numerical derivative example")
    print("ExtraData uses [surface_function, coefficients] without analytical derivative.")
    print(f"Rays traced: {len(origins)}")
    print(f"Active rays: {np.count_nonzero(active)}")
    print(f"Scalar Trace time: {scalar['elapsed']:.6f} s")
    print(f"Bundle Trace time: {bundle['elapsed']:.6f} s")
    print(f"Speedup: {speedup:.3f}x")
    print(f"Rays stored in raykeeper from bundle: {bundle_rays.nrays}")
    print(f"Same active mask: {np.array_equal(bundle['active'], scalar['active'])}")
    print(f"Max final hit error: {max_hit_error:.3e} mm")
    print(f"Max final direction error: {max_direction_error:.3e}")
    print(f"Scalar RMS spot: {scalar_metrics['rms']:.6e} mm")
    print(f"Bundle RMS spot: {bundle_metrics['rms']:.6e} mm")

    fig, ax = plt.subplots(1, 1, figsize=(6, 5), constrained_layout=True)
    ax.plot(bundle_x, bundle_y, "x", markersize=4)
    ax.set_title("ExtraData rays traced as one bundle")
    ax.set_xlabel("image x [mm]")
    ax.set_ylabel("image y [mm]")
    ax.axis("equal")
    ax.grid(True, alpha=0.25)
    plt.show()


if __name__ == "__main__":
    main()
