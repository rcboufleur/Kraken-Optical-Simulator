"""Benchmark scalar and vectorized ray-surface intersection prototypes.

This is an exploratory benchmark, not a correctness test. It measures the
current scalar ``Hit_Solver.SolveHit`` loop against a vectorized Newton
prototype for surface intersections.

Run from the repository root:

    python tools/benchmark_solvehit_bundle.py

Optional:

    python tools/benchmark_solvehit_bundle.py --rays 100 1000 10000

Bundle tracing note:

    A future full ray-bundle tracer should not remove rays from the arrays when
    they miss an aperture or mask. It should keep one boolean ``active`` mask
    per ray. Rays that miss are marked inactive, preserving original ray order,
    while active rays continue to the next surface.
"""

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def solve_hit_bundle(surface, px1, py1, pz1, l, m, n, case=0, tolerance=1e-9):
    px1 = np.asarray(px1, dtype=float)
    py1 = np.asarray(py1, dtype=float)
    pz1 = np.asarray(pz1, dtype=float)
    l = np.asarray(l, dtype=float)
    m = np.asarray(m, dtype=float)
    n = np.asarray(n, dtype=float)

    ln = l / n
    mn = m / n
    z = np.array(pz1, dtype=float, copy=True)

    for _ in range(30):
        x = ((z - pz1) * ln) + px1
        y = ((z - pz1) * mn) + py1
        sag = surface.sigma_z(x, y, case)
        derivative = surface.sigma_derivative(x, y, case)
        if derivative is None:
            raise RuntimeError("benchmark surfaces must provide analytical derivatives")
        dzdx, dzdy = derivative
        function_value = sag - z
        function_derivative = (dzdx * ln) + (dzdy * mn) - 1.0
        next_z = z - (function_value / function_derivative)

        if np.all(np.abs(next_z - z) <= tolerance):
            z = next_z
            break
        z = next_z

    x = ((z - pz1) * ln) + px1
    y = ((z - pz1) * mn) + py1
    return x, y, z


def scalar_solve_hits(surface, px1, py1, pz1, l, m, n):
    from KrakenOS.HitOnSurf import Hit_Solver

    solver = Hit_Solver([surface])
    out_x = np.empty_like(px1, dtype=float)
    out_y = np.empty_like(py1, dtype=float)
    out_z = np.empty_like(pz1, dtype=float)

    for index, values in enumerate(zip(px1, py1, pz1, l, m, n)):
        out_x[index], out_y[index], out_z[index] = solver.SolveHit(*values, 0)

    return out_x, out_y, out_z


def build_parabola():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Rc = -2000.0
    surface.k = -1.0
    surface.Diameter = 300.0
    surface.build_surface_function()
    return surface


def build_mixed_surface():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Rc = 120.0
    surface.k = -0.35
    surface.AspherData = np.zeros(200)
    surface.AspherData[0] = 3e-8
    surface.AspherData[2] = -2e-14
    surface.ZNK = np.zeros(36)
    surface.ZNK[2] = 0.007
    surface.ZNK[5] = -0.003
    surface.Diameter = 80.0
    surface.build_surface_function()
    return surface


def generate_ray_bundle(count, radius):
    index = np.arange(count, dtype=float)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    radial = radius * np.sqrt((index + 0.5) / count)
    theta = index * golden_angle
    px1 = radial * np.cos(theta)
    py1 = radial * np.sin(theta)
    pz1 = np.zeros(count, dtype=float)

    # Small deterministic tilts keep the benchmark closer to a real ray bundle
    # while avoiding pathological grazing intersections.
    l = 0.02 * np.sin(np.linspace(0.0, 2.0 * np.pi, count, endpoint=False))
    m = 0.02 * np.cos(np.linspace(0.0, 2.0 * np.pi, count, endpoint=False))
    n = np.sqrt(1.0 - (l * l) - (m * m))
    return px1, py1, pz1, l, m, n


def time_call(callback, repeats=3):
    best = float("inf")
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = callback()
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
    return result, best


def assert_results_match(scalar, bundle):
    for scalar_values, bundle_values in zip(scalar, bundle):
        if not np.allclose(scalar_values, bundle_values, rtol=1e-10, atol=1e-10):
            raise AssertionError("bundle SolveHit result does not match scalar SolveHit")


def run_case(name, surface, ray_counts, radius):
    print(f"\n{name}")
    print("rays  scalar_loop_s  bundle_s  speedup")
    for count in ray_counts:
        rays = generate_ray_bundle(count, radius)
        scalar, scalar_time = time_call(lambda: scalar_solve_hits(surface, *rays))
        bundle, bundle_time = time_call(lambda: solve_hit_bundle(surface, *rays))
        assert_results_match(scalar, bundle)
        speedup = scalar_time / bundle_time if bundle_time else float("inf")
        print(f"{count:5d}  {scalar_time:13.6f}  {bundle_time:8.6f}  {speedup:7.2f}x")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rays", nargs="+", type=int, default=[100, 1000, 10000])
    args = parser.parse_args()

    print("KrakenOS SolveHit bundle benchmark")
    print("This measures only ray-surface intersection, not full Trace().")
    print("Future bundle tracing should keep inactive rays with a boolean active mask.")

    run_case("Parabolic/conic surface", build_parabola(), args.rays, radius=120.0)
    run_case("Mixed conic/asphere/Zernike surface", build_mixed_surface(), args.rays, radius=25.0)


if __name__ == "__main__":
    main()
