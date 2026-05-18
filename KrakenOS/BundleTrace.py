"""Experimental vectorized sequential ray-bundle tracing helpers.

This module is intentionally internal for now.  It is not imported from
``KrakenOS.__init__`` and should not be treated as public API yet.  The goal is
to gather the bundle-tracing prototype in one place while preserving the
existing scalar ``system.Trace()`` workflow.

Current scope:

- sequential ``build=0`` systems;
- ordinary analytical surfaces with analytical derivatives;
- circular aperture checks;
- refractive/mirror Snell physics following the current scalar implementation.

Out of scope for this first experimental module:

- STL and non-sequential tracing;
- UDA/mask geometry beyond the simple circular aperture contract;
- numerical derivative fallback inside a bundle;
- raykeeper integration.
"""

import numpy as np


def transform_points_bundle(matrix, points):
    """Apply a KrakenOS homogeneous transform matrix to many points."""

    matrix = np.asarray(matrix, dtype=float)
    points = np.asarray(points, dtype=float)
    homogeneous = np.column_stack(
        [points[:, 0], points[:, 1], points[:, 2], np.ones(points.shape[0])]
    )
    return homogeneous @ matrix.T


def transform_directions_bundle(matrix, directions):
    """Apply a KrakenOS homogeneous transform matrix to many directions."""

    matrix = np.asarray(matrix, dtype=float)
    directions = np.asarray(directions, dtype=float)
    homogeneous = np.column_stack(
        [
            directions[:, 0],
            directions[:, 1],
            directions[:, 2],
            np.zeros(directions.shape[0]),
        ]
    )
    return homogeneous @ matrix.T


def solve_hit_bundle(surface, px1, py1, pz1, l, m, n, case=0, tolerance=1e-9):
    """Solve ray-surface intersections for a bundle using vectorized Newton."""

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
            raise RuntimeError(
                "Bundle tracing currently requires analytical derivatives for all rays."
            )
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
    """Return local analytical normals for many surface hit points."""

    derivative = surface.sigma_derivative(x, y, 0)
    if derivative is None:
        raise RuntimeError(
            "Bundle tracing currently requires analytical derivatives for normals."
        )
    dzdx, dzdy = derivative
    normals = np.column_stack([dzdx, dzdy, -np.ones_like(z)])
    return normals / np.linalg.norm(normals, axis=1)[:, None]


def aperture_active_mask(surface, x, y):
    """Return the simple circular aperture active mask for a ray bundle."""

    scale, center_y, center_x = surface.SubAperture
    radial_distance = np.sqrt(((x - center_x) ** 2.0) + ((y - center_y) ** 2.0))
    diameter_at_point = 2.0 * radial_distance
    return (
        (diameter_at_point <= surface.Diameter * scale)
        & (diameter_at_point >= surface.InDiameter * scale)
    )


def inter_normal_bundle(system, starts, stops, surface_index):
    """Experimental bundle equivalent of the simple sequential InterNormal path."""

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

    return active, global_hits, global_normals, local_hits, local_direction


def snell_refraction_bundle(incident, normals, n1, n2):
    """Vectorized form of the current scalar Snell/reflection calculation."""

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
    return transmitted, np.abs(n2_effective), sign, angles


def trace_bundle(system, origins, directions, wavelength):
    """Trace a bundle through a simple sequential system.

    This is experimental and intentionally narrower than ``system.Trace``.
    """

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
        hit_active, hits, normals, _local_hits, _local_directions = inter_normal_bundle(
            system, ray_origins, stops, surface_index
        )
        active = active & hit_active

        current_n = system.N_Prec[surface_index]
        next_directions, _current_n, _sign, _angles = snell_refraction_bundle(
            ray_directions, normals, previous_n, current_n
        )

        ray_origins[active] = hits[active]
        ray_directions[active] = next_directions[active]
        final_hits[active] = hits[active]
        final_directions[active] = next_directions[active]
        previous_n = current_n

    return {
        "active": active,
        "final_hits": final_hits,
        "final_directions": final_directions,
    }
