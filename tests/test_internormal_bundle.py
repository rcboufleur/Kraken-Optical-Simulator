import numpy as np


def transform_points_bundle(matrix, points):
    matrix = np.asarray(matrix, dtype=float)
    homogeneous = np.column_stack(
        [
            points[:, 0],
            points[:, 1],
            points[:, 2],
            np.ones(points.shape[0], dtype=float),
        ]
    )
    return homogeneous @ matrix.T


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
        assert derivative is not None
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
    derivative = surface.sigma_derivative(x, y, 0)
    assert derivative is not None
    dzdx, dzdy = derivative
    normals = np.column_stack([dzdx, dzdy, -np.ones_like(z)])
    return normals / np.linalg.norm(normals, axis=1)[:, None]


def aperture_active_mask(surface, x, y):
    scale, center_y, center_x = surface.SubAperture
    radial_distance = np.sqrt(((x - center_x) ** 2.0) + ((y - center_y) ** 2.0))
    diameter_at_point = 2.0 * radial_distance
    outer_limit = surface.Diameter * scale
    inner_limit = surface.InDiameter * scale
    return (diameter_at_point <= outer_limit) & (diameter_at_point >= inner_limit)


def inter_normal_bundle(system, starts, stops, surface_index):
    """Test-local prototype for the sequential TypeTotal == 0 InterNormal path."""

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

    hit_homogeneous = np.column_stack(
        [hit_x, hit_y, hit_z, np.ones_like(hit_x)]
    )
    global_hits = hit_homogeneous @ np.asarray(system.Pr3D.TRANS_2A[surface_index], dtype=float).T

    local_normals = local_normals_bundle(surface, hit_x, hit_y, hit_z)
    normal_reference_z = 10000000.0
    normal_p1_x = ((normal_reference_z - hit_z) * (local_normals[:, 0] / local_normals[:, 2])) + hit_x
    normal_p1_y = ((normal_reference_z - hit_z) * (local_normals[:, 1] / local_normals[:, 2])) + hit_y
    normal_p1 = np.column_stack(
        [normal_p1_x, normal_p1_y, np.full_like(hit_z, normal_reference_z)]
    )
    normal_p2 = local_hits
    global_p1 = transform_points_bundle(system.Pr3D.TRANS_2A[surface_index], normal_p1)[:, :3]
    global_p2 = transform_points_bundle(system.Pr3D.TRANS_2A[surface_index], normal_p2)[:, :3]
    global_normals = -(global_p1 - global_p2)
    global_normals = global_normals / np.linalg.norm(global_normals, axis=1)[:, None]

    return {
        "active": active,
        "global_hits": global_hits[:, :3],
        "local_hits": local_hits,
        "global_normals": global_normals,
        "local_directions": local_direction,
    }


def scalar_inter_normal(system, starts, stops, surface_index):
    outputs = [
        system.INORM.InterNormal(start, stop, surface_index, surface_index)
        for start, stop in zip(starts, stops)
    ]
    active = np.asarray([output[0] != 0 for output in outputs])
    normals = np.asarray([output[1] for output in outputs], dtype=float)
    global_hits = np.asarray([output[2] for output in outputs], dtype=float)
    local_hits = np.asarray([output[4] for output in outputs], dtype=float)
    local_directions = np.asarray([output[5] for output in outputs], dtype=float)
    return {
        "active": active,
        "global_hits": global_hits,
        "local_hits": local_hits,
        "global_normals": normals,
        "local_directions": local_directions,
    }


def build_bundle_test_system():
    import KrakenOS as Kos

    obj = Kos.surf()
    obj.Glass = "AIR"
    obj.Thickness = 15.0
    obj.Diameter = 40.0

    surface = Kos.surf()
    surface.Rc = 80.0
    surface.k = -0.2
    surface.AspherData = np.zeros(200)
    surface.AspherData[0] = 1e-8
    surface.Glass = "BK7"
    surface.Thickness = 5.0
    surface.Diameter = 14.0
    surface.TiltX = 7.0
    surface.TiltY = -3.0
    surface.TiltZ = 11.0
    surface.DespX = 1.5
    surface.DespY = -2.0
    surface.DespZ = 0.25

    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 40.0

    return Kos.system([obj, surface, image], Kos.Setup(), build=0)


def make_test_rays():
    starts = np.array(
        [
            [-3.0, -2.0, 0.0],
            [-1.0, 0.5, 0.0],
            [0.0, 0.0, 0.0],
            [1.5, -1.0, 0.0],
            [3.0, 2.0, 0.0],
            [9.0, 0.0, 0.0],
        ],
        dtype=float,
    )
    directions = np.array(
        [
            [0.00, 0.00, 1.0],
            [0.01, -0.01, 0.9998999949994999],
            [-0.01, 0.02, 0.9997499687421851],
            [0.02, 0.01, 0.9997499687421851],
            [-0.015, -0.005, 0.9998749921865234],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    stops = starts + directions * 1.0e6
    return starts, stops


def test_inter_normal_bundle_matches_scalar_for_simple_sequential_surface():
    system = build_bundle_test_system()
    starts, stops = make_test_rays()

    bundle = inter_normal_bundle(system, starts, stops, surface_index=1)
    scalar = scalar_inter_normal(system, starts, stops, surface_index=1)

    assert np.array_equal(bundle["active"], scalar["active"])
    active = bundle["active"]
    assert np.allclose(
        bundle["global_hits"][active], scalar["global_hits"][active], rtol=1e-9, atol=1e-9
    )
    assert np.allclose(
        bundle["local_hits"][active], scalar["local_hits"][active], rtol=1e-9, atol=1e-9
    )
    assert np.allclose(
        bundle["global_normals"][active],
        scalar["global_normals"][active],
        rtol=1e-9,
        atol=1e-9,
    )
    assert np.allclose(
        bundle["local_directions"], scalar["local_directions"], rtol=1e-12, atol=1e-12
    )
    assert bundle["active"].tolist() == [True, True, True, True, True, False]
