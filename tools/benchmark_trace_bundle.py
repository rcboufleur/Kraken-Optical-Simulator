"""Benchmark scalar Trace loop against the experimental TraceBundle helper.

Run from the repository root:

    python tools/benchmark_trace_bundle.py

Optional:

    python tools/benchmark_trace_bundle.py --rays 100 1000 5000
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from KrakenOS.BundleTrace import trace_bundle


def build_simple_lens_system():
    import KrakenOS as Kos

    obj = Kos.surf()
    obj.Glass = "AIR"
    obj.Thickness = 10.0
    obj.Diameter = 30.0

    lens_front = Kos.surf()
    lens_front.Rc = 80.0
    lens_front.Glass = "BK7"
    lens_front.Thickness = 5.0
    lens_front.Diameter = 30.0

    lens_back = Kos.surf()
    lens_back.Rc = -80.0
    lens_back.Glass = "AIR"
    lens_back.Thickness = 20.0
    lens_back.Diameter = 30.0

    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 30.0

    return Kos.system([obj, lens_front, lens_back, image], Kos.Setup(), build=0)


def generate_rays(count, radius=6.0):
    index = np.arange(count, dtype=float)
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    radial = radius * np.sqrt((index + 0.5) / count)
    theta = index * golden_angle
    origins = np.column_stack(
        [radial * np.cos(theta), radial * np.sin(theta), np.zeros(count)]
    )
    l = 0.01 * np.sin(np.linspace(0.0, 2.0 * np.pi, count, endpoint=False))
    m = 0.01 * np.cos(np.linspace(0.0, 2.0 * np.pi, count, endpoint=False))
    n = np.sqrt(1.0 - (l * l) - (m * m))
    directions = np.column_stack([l, m, n])
    return origins, directions


def scalar_trace(system, origins, directions, wavelength):
    active = np.empty(origins.shape[0], dtype=bool)
    hits = np.empty_like(origins)
    output_directions = np.empty_like(directions)
    for index, (origin, direction) in enumerate(zip(origins, directions)):
        system.Trace(origin, direction, wavelength)
        active[index] = system.val == 1
        hits[index] = np.asarray(system.XYZ[-1], dtype=float)
        output_directions[index] = np.asarray(system.R_LMN[-1], dtype=float)
    return active, hits, output_directions


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
    scalar_active, scalar_hits, scalar_directions = scalar
    bundle_active = bundle["active"]
    bundle_hits = bundle["final_hits"]
    bundle_directions = bundle["final_directions"]
    if not np.array_equal(scalar_active, bundle_active):
        raise AssertionError("active mask mismatch")
    active = scalar_active
    if not np.allclose(scalar_hits[active], bundle_hits[active], rtol=1e-8, atol=1e-8):
        raise AssertionError("final hit mismatch")
    if not np.allclose(
        scalar_directions[active], bundle_directions[active], rtol=1e-8, atol=1e-8
    ):
        raise AssertionError("final direction mismatch")


def run_benchmark(ray_counts):
    print("KrakenOS TraceBundle prototype benchmark")
    print("This measures a simple sequential refractive lens, not the full KrakenOS API.")
    print("rays  scalar_trace_s  trace_bundle_s  speedup")
    for count in ray_counts:
        origins, directions = generate_rays(count)
        scalar_system = build_simple_lens_system()
        bundle_system = build_simple_lens_system()
        scalar, scalar_time = time_call(
            lambda: scalar_trace(scalar_system, origins, directions, 0.55)
        )
        bundle, bundle_time = time_call(
            lambda: trace_bundle(bundle_system, origins, directions, 0.55)
        )
        assert_results_match(scalar, bundle)
        speedup = scalar_time / bundle_time if bundle_time else float("inf")
        print(f"{count:5d}  {scalar_time:14.6f}  {bundle_time:14.6f}  {speedup:7.2f}x")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rays", nargs="+", type=int, default=[100, 1000, 5000])
    args = parser.parse_args()
    run_benchmark(args.rays)


if __name__ == "__main__":
    main()
