import numpy as np
from KrakenOS.BundleTrace import (
    aperture_active_mask,
    local_normals_bundle,
    numerical_derivative_bundle,
    solve_hit_bundle,
)


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


def scalar_surface_normals(surface, x, y, z):
    from KrakenOS.HitOnSurf import Hit_Solver

    solver = Hit_Solver([surface])
    solver.vj = 0
    return np.asarray(
        [solver.SurfDer(float(px), float(py), float(pz)) for px, py, pz in zip(x, y, z)],
        dtype=float,
    )


def assert_bundle_normals_match_scalar(surface, x, y, z, atol=1e-8):
    bundle = local_normals_bundle(surface, x, y, z)
    scalar = scalar_surface_normals(surface, x, y, z)

    assert np.allclose(bundle, scalar, rtol=1e-6, atol=atol)


def test_solve_hit_bundle_matches_scalar_for_simple_plane():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.build_surface_function()

    px1 = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    py1 = np.array([1.5, -0.5, 0.0, 0.5, -1.5])
    pz1 = np.zeros_like(px1)
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

    x = np.array([-6.0, -5.0, -2.0, 0.0, 2.0, 5.0, 6.0])
    y = np.zeros_like(x)
    active = aperture_active_mask(surface, x, y)

    assert active.tolist() == [False, True, True, True, True, True, False]
    assert len(active) == len(x)


def test_solve_hit_bundle_falls_back_for_zernike_axis_derivative_limit():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Diameter = 30.0
    surface.ZNK = np.zeros(36)
    surface.ZNK[2] = 0.007
    surface.build_surface_function()

    px1 = np.array([0.0, 1.0])
    py1 = np.array([0.0, 1.0])
    pz1 = np.zeros_like(px1)
    l = np.zeros_like(px1)
    m = np.zeros_like(px1)
    n = np.ones_like(px1)

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)
    x, y, z = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    assert_bundle_normals_match_scalar(surface, x, y, z)


def test_solve_hit_bundle_falls_back_for_axicon_apex_derivative_limit():
    import KrakenOS as Kos

    surface = Kos.surf()
    surface.Diameter = 30.0
    surface.Axicon = 2.0
    surface.build_surface_function()

    px1 = np.array([0.0, 1.0])
    py1 = np.array([0.0, 1.0])
    pz1 = np.zeros_like(px1)
    l = np.zeros_like(px1)
    m = np.zeros_like(px1)
    n = np.ones_like(px1)

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)
    x, y, z = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    assert_bundle_normals_match_scalar(surface, x, y, z)


def test_solve_hit_bundle_falls_back_for_extra_data_without_derivative():
    import KrakenOS as Kos

    def user_surface(x, y, data):
        return data[0] * x * y

    surface = Kos.surf()
    surface.Diameter = 30.0
    surface.ExtraData = [user_surface, [0.25]]
    surface.build_surface_function()

    px1 = np.array([1.0, 2.0])
    py1 = np.array([1.0, 2.0])
    pz1 = np.zeros_like(px1)
    l = np.zeros_like(px1)
    m = np.zeros_like(px1)
    n = np.ones_like(px1)

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)
    x, y, z = solve_hit_bundle(surface, px1, py1, pz1, l, m, n)
    assert_bundle_normals_match_scalar(surface, x, y, z)


def test_numerical_derivative_bundle_handles_vectorized_extra_data():
    import KrakenOS as Kos

    def user_surface(x, y, data):
        return data[0] * x * y

    surface = Kos.surf()
    surface.Diameter = 30.0
    surface.ExtraData = [user_surface, [0.25]]
    surface.build_surface_function()

    x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    y = np.array([2.0, 1.0, 0.5, -1.0, -2.0])

    derivative = numerical_derivative_bundle(surface, x, y)

    assert derivative is not None
    dzdx, dzdy = derivative
    assert np.allclose(dzdx, 0.25 * y, rtol=1e-8, atol=1e-8)
    assert np.allclose(dzdy, 0.25 * x, rtol=1e-8, atol=1e-8)


def test_solve_hit_bundle_uses_vectorized_numerical_fallback_for_angled_extra_data():
    import KrakenOS as Kos

    def user_surface(x, y, data):
        return data[0] * x * y

    surface = Kos.surf()
    surface.Diameter = 30.0
    surface.ExtraData = [user_surface, [0.025]]
    surface.build_surface_function()

    px1 = np.array([-2.0, -1.0, 1.0, 2.0])
    py1 = np.array([1.5, -0.5, 0.5, -1.5])
    pz1 = np.zeros_like(px1)
    l = np.array([0.01, -0.015, 0.02, -0.01])
    m = np.array([-0.01, 0.02, -0.015, 0.01])
    n = np.sqrt(1.0 - (l * l) - (m * m))

    assert_bundle_matches_scalar(surface, px1, py1, pz1, l, m, n)
