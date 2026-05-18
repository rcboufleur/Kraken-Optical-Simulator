import numpy as np

from KrakenOS.BundleTrace import inter_normal_bundle


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

    hit_active, global_hits, global_normals, local_hits, local_directions = inter_normal_bundle(
        system, starts, stops, surface_index=1
    )
    bundle = {
        "active": hit_active,
        "global_hits": global_hits,
        "local_hits": local_hits,
        "global_normals": global_normals,
        "local_directions": local_directions,
    }
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
