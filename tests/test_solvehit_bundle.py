import numpy as np


def solve_hit_bundle(surface, px1, py1, pz1, l, m, n, case=0, tolerance=1e-9):
    """Prototype vector Newton solver for a bundle of ray-surface hits.

    This helper deliberately lives in the test suite. It explores the bundle
    algorithm without changing KrakenOS' public scalar ``Trace()`` workflow.
    The equation is the same one used by ``Hit_Solver.SolveHit``:

        F(z) = sag(x(z), y(z)) - z

    with:

        x(z) = x0 + (z - z0) * L/N
        y(z) = y0 + (z - z0) * M/N

    The analytical line derivative is:

        dF/dz = dzdx * L/N + dzdy * M/N - 1
    """

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


def aperture_active_mask(surface, x, y):
    """Return active rays for the simple circular aperture contract.

    This mirrors the scalar sequential aperture idea for the future bundle
    tracer: rays outside the aperture are marked inactive, but remain in the
    original array positions so downstream ray data can preserve ray order.
    """

    sub_aperture = surface.SubAperture
    scale = sub_aperture[0]
    center_y = sub_aperture[1]
    center_x = sub_aperture[2]
    radial_distance = np.sqrt(((x - center_x) ** 2.0) + ((y - center_y) ** 2.0))
    diameter_at_point = 2.0 * radial_distance
    outer_limit = surface.Diameter * scale
    inner_limit = surface.InDiameter * scale
    return (diameter_at_point <= outer_limit) & (diameter_at_point >= inner_limit)


def solve_hit_bundle_with_aperture(surface, px1, py1, pz1, l, m, n):
    hit_x, hit_y, hit_z = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    active = aperture_active_mask(surface, hit_x, hit_y)
    return {
        "active": active,
        "x": hit_x,
        "y": hit_y,
        "z": hit_z,
    }


def scalar_solve_hits(surface, px1, py1, pz1, l, m, n):
    from KrakenOS.HitOnSurf import Hit_Solver

    solver = Hit_Solver([surface])
    solved = [
        solver.SolveHit(px, py, pz, lx, my, nz, 0)
        for px, py, pz, lx, my, nz in zip(px1, py1, pz1, l, m, n)
    ]
    return tuple(np.asarray(values, dtype=float) for values in zip(*solved))


def assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n):
    bundle = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    scalar = scalar_solve_hits(surface, px1, py1, pz1, l, m, n)

    for bundle_values, scalar_values in zip(bundle, scalar):
        assert np.allclose(bundle_values, scalar_values, rtol=1e-10, atol=1e-10)


def test_solve_hit_bundle_matches_scalar_for_simple_plane():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.build_surface_function()

    px1 = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    py1 = np.array([1.5, -0.5, 0.0, 0.5, -1.5])
    pz1 = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    l = np.array([0.0, 0.01, -0.02, 0.03, -0.04])
    m = np.array([0.0, -0.02, 0.01, -0.03, 0.04])
    n = np.sqrt(1.0 - (l * l) - (m * m))

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)


def test_solve_hit_bundle_matches_scalar_for_parabola():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Rc = -2000.0
    surface.k = -1.0
    surface.Diameter = 300.0
    surface.build_surface_function()

    px1 = np.array([-80.0, -40.0, 0.0, 40.0, 80.0])
    py1 = np.array([30.0, -60.0, 10.0, 70.0, -20.0])
    pz1 = np.zeros_like(px1)
    l = np.array([0.0, 0.01, -0.02, 0.015, -0.01])
    m = np.array([0.0, -0.015, 0.01, -0.005, 0.02])
    n = np.sqrt(1.0 - (l * l) - (m * m))

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)


def test_solve_hit_bundle_matches_scalar_for_mixed_surface():
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

    px1 = np.array([-10.0, -5.0, 1.0, 5.0, 10.0])
    py1 = np.array([6.0, -4.0, 3.0, 8.0, -6.0])
    pz1 = np.zeros_like(px1)
    l = np.array([0.0, 0.01, -0.02, 0.015, -0.01])
    m = np.array([0.0, -0.015, 0.01, -0.005, 0.02])
    n = np.sqrt(1.0 - (l * l) - (m * m))

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)


def test_bundle_aperture_mask_preserves_ray_order():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Diameter = 10.0
    surface.InDiameter = 0.0
    surface.build_surface_function()

    px1 = np.array([-6.0, -5.0, -2.0, 0.0, 2.0, 5.0, 6.0])
    py1 = np.zeros_like(px1)
    pz1 = np.zeros_like(px1)
    l = np.zeros_like(px1)
    m = np.zeros_like(px1)
    n = np.ones_like(px1)

    result = solve_hit_bundle_with_aperture(surface, px1, py1, pz1, l, m, n)

    assert result["active"].tolist() == [False, True, True, True, True, True, False]
    assert np.allclose(result["x"], px1)
    assert np.allclose(result["y"], py1)
    assert np.allclose(result["z"], pz1)
    assert len(result["active"]) == len(px1)
