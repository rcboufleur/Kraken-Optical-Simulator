import numpy as np

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


def scalar_trace_results(system, origins, directions, wavelength):
    hits = []
    output_directions = []
    active = []
    for origin, direction in zip(origins, directions):
        system.Trace(origin, direction, wavelength)
        active.append(system.val == 1)
        hits.append(np.asarray(system.XYZ[-1], dtype=float))
        output_directions.append(np.asarray(system.R_LMN[-1], dtype=float))
    return {
        "active": np.asarray(active, dtype=bool),
        "final_hits": np.asarray(hits, dtype=float),
        "final_directions": np.asarray(output_directions, dtype=float),
    }


def test_trace_bundle_matches_scalar_trace_for_simple_lens():
    system = build_simple_lens_system()
    origins = np.array(
        [
            [-4.0, -3.0, 0.0],
            [-2.0, 1.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.5, -2.5, 0.0],
            [4.0, 3.0, 0.0],
        ],
        dtype=float,
    )
    l = np.array([0.0, 0.005, -0.005, 0.01, -0.01])
    m = np.array([0.0, -0.004, 0.006, -0.005, 0.005])
    n = np.sqrt(1.0 - (l * l) - (m * m))
    directions = np.column_stack([l, m, n])
    wavelength = 0.55

    bundle = trace_bundle(system, origins, directions, wavelength)
    scalar = scalar_trace_results(system, origins, directions, wavelength)

    assert np.array_equal(bundle["active"], scalar["active"])
    assert np.all(bundle["active"])
    assert np.allclose(bundle["final_hits"], scalar["final_hits"], rtol=1e-8, atol=1e-8)
    assert np.allclose(
        bundle["final_directions"], scalar["final_directions"], rtol=1e-8, atol=1e-8
    )
