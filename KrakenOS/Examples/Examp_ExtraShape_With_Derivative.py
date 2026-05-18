#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: user-defined ExtraData surface with an analytical derivative.

KrakenOS keeps the classic user-defined surface API:

    ExtraData = [surface_function, coefficients]

That form still works and uses the numerical derivative fallback.  This example
shows the optional faster form:

    ExtraData = [surface_function, coefficients, derivative_function]

The derivative function must return ``(dzdx, dzdy)`` for the same sag function.
KrakenOS then uses it for surface normals and Newton intersection derivatives.

What this example teaches:
- how to define a custom sag function;
- how to provide its analytical derivative;
- how to compare the analytical path against the numerical fallback;
- how this remains transparent to the normal ``system.Trace`` workflow.

Expected output:
- maximum difference between the analytical and numerical paths;
- simple timing comparison for the same deterministic ray fan.
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos


def cosine_surface(x, y, coef):
    """Return a smooth 2D cosine sag perturbation."""
    period, amplitude = coef
    k = 2.0 * np.pi / period
    return amplitude * np.cos(k * x) * np.cos(k * y)


def cosine_surface_derivative(x, y, coef):
    """Return dz/dx and dz/dy for ``cosine_surface``."""
    period, amplitude = coef
    k = 2.0 * np.pi / period
    dzdx = -amplitude * k * np.sin(k * x) * np.cos(k * y)
    dzdy = -amplitude * k * np.cos(k * x) * np.sin(k * y)
    return dzdx, dzdy


def build_system(use_derivative):
    obj = Kos.surf()
    obj.Glass = "AIR"
    obj.Thickness = 10.0
    obj.Diameter = 30.0

    custom = Kos.surf()
    custom.Glass = "BK7"
    custom.Thickness = 15.0
    custom.Diameter = 30.0
    custom.Name = "Cosine ExtraData"

    coef = [12.0, 0.08]
    if use_derivative:
        custom.ExtraData = [cosine_surface, coef, cosine_surface_derivative]
    else:
        custom.ExtraData = [cosine_surface, coef]

    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 30.0
    image.Name = "Image plane"

    return Kos.system([obj, custom, image], Kos.Setup(), build=0)


def generate_rays():
    rays = []
    for x in np.linspace(-5.0, 5.0, 21):
        for y in np.linspace(-5.0, 5.0, 21):
            rays.append(([float(x), float(y), 0.0], [0.0, 0.0, 1.0], 0.55))
    return rays


def trace_results(system, rays):
    results = []
    start = time.perf_counter()
    for origin, direction, wavelength in rays:
        system.Trace(origin, direction, wavelength)
        results.append(Kos.extract_ray_result(system))
    elapsed = time.perf_counter() - start
    return results, elapsed


def last_vector(result, key):
    values = result[key]
    if not values:
        return np.asarray([np.nan, np.nan, np.nan])
    return np.asarray(values[-1], dtype=float)


def max_result_difference(left, right, key):
    differences = []
    for left_result, right_result in zip(left, right):
        differences.append(np.linalg.norm(last_vector(left_result, key) - last_vector(right_result, key)))
    return max(differences)


def main():
    rays = generate_rays()

    analytical_system = build_system(use_derivative=True)
    numerical_system = build_system(use_derivative=False)

    analytical_results, analytical_time = trace_results(analytical_system, rays)
    numerical_results, numerical_time = trace_results(numerical_system, rays)

    max_xyz_difference = max_result_difference(analytical_results, numerical_results, "XYZ")
    max_lmn_difference = max_result_difference(analytical_results, numerical_results, "R_LMN")

    print("\nExtraData analytical derivative example")
    print(f"Rays traced: {len(rays)}")
    print(f"Analytical derivative time: {analytical_time:.6f} s")
    print(f"Numerical fallback time:    {numerical_time:.6f} s")
    print(f"Max final XYZ difference:   {max_xyz_difference:.6e}")
    print(f"Max final LMN difference:   {max_lmn_difference:.6e}")
    print("\nUse ExtraData = [f, coef, df] when you can provide dz/dx and dz/dy.")
    print("Use ExtraData = [f, coef] when you want KrakenOS to keep the numerical fallback.")


if __name__ == "__main__":
    main()
