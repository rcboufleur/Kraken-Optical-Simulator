import numpy as np

from KrakenOS.BundleTrace import transform_directions_bundle, transform_points_bundle


def transform_points_scalar(matrix, points):
    return np.asarray([np.asarray(matrix.dot([x, y, z, 1.0])).ravel() for x, y, z in points])


def transform_directions_scalar(matrix, directions):
    return np.asarray(
        [np.asarray(matrix.dot([l, m, n, 0.0])).ravel() for l, m, n in directions]
    )


def build_tilted_decentered_system():
    import KrakenOS as Kos

    obj = Kos.surf()
    obj.Glass = "AIR"
    obj.Thickness = 15.0
    obj.Diameter = 40.0

    tilted = Kos.surf()
    tilted.Rc = 80.0
    tilted.Glass = "BK7"
    tilted.Thickness = 5.0
    tilted.Diameter = 40.0
    tilted.TiltX = 7.0
    tilted.TiltY = -3.0
    tilted.TiltZ = 11.0
    tilted.DespX = 1.5
    tilted.DespY = -2.0
    tilted.DespZ = 0.25

    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 40.0

    return Kos.system([obj, tilted, image], Kos.Setup(), build=0)


def test_bundle_point_transform_matches_scalar_krakenos_matrix():
    system = build_tilted_decentered_system()
    matrix = system.Pr3D.TRANS_1A[1]
    points = np.array(
        [
            [-5.0, -2.0, 0.0],
            [-1.0, 3.0, 2.0],
            [0.0, 0.0, 5.0],
            [2.5, -4.0, 7.0],
            [6.0, 1.0, 9.0],
        ],
        dtype=float,
    )

    scalar = transform_points_scalar(matrix, points)
    bundle = transform_points_bundle(matrix, points)

    assert np.allclose(bundle, scalar, rtol=1e-12, atol=1e-12)


def test_bundle_direction_transform_matches_scalar_krakenos_matrix():
    system = build_tilted_decentered_system()
    matrix = system.Pr3D.TRANS_1A[1]
    directions = np.array(
        [
            [0.0, 0.0, 1.0],
            [0.01, -0.02, 0.9997499687421851],
            [-0.03, 0.01, 0.999499874937461],
            [0.02, 0.02, 0.999599919967984],
        ],
        dtype=float,
    )

    scalar = transform_directions_scalar(matrix, directions)
    bundle = transform_directions_bundle(matrix, directions)

    assert np.allclose(bundle, scalar, rtol=1e-12, atol=1e-12)
    assert np.allclose(bundle[:, 3], 0.0, rtol=0.0, atol=1e-12)
