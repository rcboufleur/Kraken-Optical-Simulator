"""Benchmark scalar Trace loop against a vectorized TraceBundle prototype.

This is an exploratory benchmark, not a correctness test. It keeps the
TraceBundle prototype outside KrakenOS' public API while measuring whether the
bundle approach still helps once transforms, intersections, normals, aperture
masks, and Snell physics are included.

Run from the repository root:

    python tools/benchmark_trace_bundle.py

Optional:

    python tools/benchmark_trace_bundle.py --rays 100 1000 5000
"""

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def transform_points_bundle(matrix, points):
    matrix = np.asarray(matrix, dtype=float)
    homogeneous = np.column_stack(
        [points[:, 0], points[:, 1], points[:, 2], np.ones(points.shape[0])]
    )
    return homogeneous @ matrix.T


def solve_hit_bundle(surface, px1, py1, pz1, l, m, n, case=0, tolerance=1e-9):
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


def local_normals_bundle(surface, x, y, z):
    dzdx, dzdy = surface.sigma_derivative(x, y, 0)
    normals = np.column_stack([dzdx, dzdy, -np.ones_like(z)])
    return normals / np.linalg.norm(normals, axis=1)[:, None]


def aperture_active_mask(surface, x, y):
    scale, center_y, center_x = surface.SubAperture
    radial_distance = np.sqrt(((x - center_x) ** 2.0) + ((y - center_y) ** 2.0))
    diameter_at_point = 2.0 * radial_distance
    return (
        (diameter_at_point <= surface.Diameter * scale)
        & (diameter_at_point >= surface.InDiameter * scale)
    )


def inter_normal_bundle(system, starts, stops, surface_index):
    surface = system.SDT[surface_index]
    start_local = transform_points_bundle(system.Pr3D.TRANS_1A[surface_index], starts)[:, :3]
    stop_local = transform_points_bundle(system.Pr3D.TRANS_1A[surface_index], stops)[:, :3]
    segment = stop_local - start_local
    local_direction = segment / np.linalg.norm(segment, axis=1)[:, None]

    px0 = start_local[:, 0]
    py0 = start_local[:, 1]
    pz0 = start_local[:, 2]
    l = local_direction[:, 0]
    m = local_direction[:, 1]
    n = local_direction[:, 2]

    px1 = ((l / n) * (-pz0)) + px0
    py1 = ((m / n) * (-pz0)) + py0
    pz1 = np.zeros_like(px1)

    hit_x, hit_y, hit_z = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    active = aperture_active_mask(surface, hit_x, hit_y)
    local_hits = np.column_stack([hit_x, hit_y, hit_z])
    global_hits = transform_points_bundle(system.Pr3D.TRANS_2A[surface_index], local_hits)[:, :3]

    local_normals = local_normals_bundle(surface, hit_x, hit_y, hit_z)
    normal_reference_z = 10000000.0
    normal_p1_x = (
        ((normal_reference_z - hit_z) * (local_normals[:, 0] / local_normals[:, 2]))
        + hit_x
    )
    normal_p1_y = (
        ((normal_reference_z - hit_z) * (local_normals[:, 1] / local_normals[:, 2]))
        + hit_y
    )
    normal_p1 = np.column_stack(
        [normal_p1_x, normal_p1_y, np.full_like(hit_z, normal_reference_z)]
    )
    global_p1 = transform_points_bundle(system.Pr3D.TRANS_2A[surface_index], normal_p1)[:, :3]
    global_p2 = transform_points_bundle(system.Pr3D.TRANS_2A[surface_index], local_hits)[:, :3]
    global_normals = -(global_p1 - global_p2)
    global_normals = global_normals / np.linalg.norm(global_normals, axis=1)[:, None]

    return active, global_hits, global_normals


def snell_refraction_bundle(incident, normals, n1, n2):
    nv = np.asarray(normals, dtype=float).copy()
    iv = np.asarray(incident, dtype=float)
    cos = np.sum(nv * iv, axis=1)
    angles = np.rad2deg(np.arccos(np.clip(cos, -1.0, 1.0)))
    flip = angles <= 90.0
    nv[flip] = -nv[flip]
    angles[~flip] = 180.0 - angles[~flip]

    sign = np.ones(iv.shape[0])
    n2_effective = np.full(iv.shape[0], n2, dtype=float)
    if n2 == -1.0:
        n2_effective[:] = -n1
        sign[:] = -1.0

    nn = n1 / n2_effective
    cross = np.cross(nv, iv)
    d22 = np.sum(cross * cross, axis=1)
    tir = ((nn * nn) * d22) > 1.0
    if np.any(tir):
        n2_effective[tir] = -n1
        nn = n1 / n2_effective
        sign[tir] = -1.0

    c1 = np.sum(nv * iv, axis=1)
    c1 = np.where(c1 < 0.0, np.sum((-nv) * iv, axis=1), c1)
    ip = (nn * nn) * (1.0 - (c1 * c1))
    c2 = np.sqrt(1.0 - ip)
    transmitted = (nn[:, None] * iv) + (((nn * c1) - c2)[:, None] * nv)
    return transmitted


def trace_bundle(system, origins, directions, wavelength):
    system.Wave = wavelength
    system._system__WavePrecalc()

    ray_origins = np.asarray(origins, dtype=float).copy()
    ray_directions = np.asarray(directions, dtype=float).copy()
    active = np.ones(ray_origins.shape[0], dtype=bool)
    previous_n = system.N_Prec[0]
    final_hits = np.array(ray_origins, copy=True)
    final_directions = np.array(ray_directions, copy=True)

    for surface_index in range(1, system.n):
        stops = ray_origins + (ray_directions * 999999999.9)
        hit_active, hits, normals = inter_normal_bundle(system, ray_origins, stops, surface_index)
        active = active & hit_active

        current_n = system.N_Prec[surface_index]
        next_directions = snell_refraction_bundle(
            ray_directions, normals, previous_n, current_n
        )

        ray_origins[active] = hits[active]
        ray_directions[active] = next_directions[active]
        final_hits[active] = hits[active]
        final_directions[active] = next_directions[active]
        previous_n = current_n

    return active, final_hits, final_directions


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
    bundle_active, bundle_hits, bundle_directions = bundle
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
        scalar, scalar_time = time_call(lambda: scalar_trace(scalar_system, origins, directions, 0.55))
        bundle, bundle_time = time_call(lambda: trace_bundle(bundle_system, origins, directions, 0.55))
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
