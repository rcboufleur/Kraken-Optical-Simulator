import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

import numpy as np


_WORKER_SYSTEM = None


def build_simple_system(build=0):
    import KrakenOS as Kos

    obj = Kos.surf()
    obj.Glass = "AIR"
    obj.Thickness = 10
    obj.Diameter = 30

    lens_front = Kos.surf()
    lens_front.Rc = 80
    lens_front.Glass = "BK7"
    lens_front.Thickness = 5
    lens_front.Diameter = 30

    lens_back = Kos.surf()
    lens_back.Rc = -80
    lens_back.Glass = "AIR"
    lens_back.Thickness = 20
    lens_back.Diameter = 30

    image = Kos.surf()
    image.Glass = "AIR"
    image.Thickness = 0
    image.Diameter = 30

    return Kos.system([obj, lens_front, lens_back, image], Kos.Setup(), build=build)


def init_worker_system():
    global _WORKER_SYSTEM
    _WORKER_SYSTEM = build_simple_system(build=0)


def generate_rays(count):
    side = math.ceil(math.sqrt(count))
    span = np.linspace(-6.0, 6.0, side)
    rays = []
    index = 0
    for x in span:
        for y in span:
            if index >= count:
                break
            rays.append(
                {
                    "index": index,
                    "origin": [float(x), float(y), 0.0],
                    "direction": [0.0, 0.0, 1.0],
                    "wavelength": 0.55,
                }
            )
            index += 1
        if index >= count:
            break
    return rays


def make_warmup_batches(workers):
    return [
        [
            {
                "index": -worker_index - 1,
                "origin": [0.0, 0.0, 0.0],
                "direction": [0.0, 0.0, 1.0],
                "wavelength": 0.55,
            }
        ]
        for worker_index in range(workers)
    ]


def extract_trace_result(system, ray_index):
    xyz = np.asarray(system.XYZ, dtype=float)
    ray_hits = np.asarray(system.ray_SurfHits, dtype=float)
    last_lmn = None
    if system.R_LMN:
        last_lmn = np.asarray(system.R_LMN[-1], dtype=float).tolist()

    return {
        "index": ray_index,
        "valid": bool(system.val),
        "xyz": xyz.tolist(),
        "ray_hits": ray_hits.tolist(),
        "last_xyz": xyz[-1].tolist(),
        "last_lmn": last_lmn,
        "wavelength": float(system.WAV),
        "top": float(system.TOP),
        "n_hits": int(len(system.XYZ)),
        "surfaces": np.asarray(system.SURFACE).tolist(),
    }


def trace_batch(batch):
    system = build_simple_system(build=0)
    return trace_batch_with_system(system, batch)


def trace_batch_with_system(system, batch):
    results = []
    for ray in batch:
        system.Trace(ray["origin"], ray["direction"], ray["wavelength"])
        results.append(extract_trace_result(system, ray["index"]))
    return results


def trace_batch_with_worker_system(batch):
    if _WORKER_SYSTEM is None:
        raise RuntimeError("Worker system was not initialized")
    return trace_batch_with_system(_WORKER_SYSTEM, batch)


def chunked(items, chunk_size):
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def worker_counts_to_test():
    cpu_count = os.cpu_count() or 2
    candidates = [1, 2, 4, 8, 16, cpu_count]
    return sorted({workers for workers in candidates if 1 <= workers <= cpu_count})


def trace_sequential(rays):
    system = build_simple_system(build=0)
    start = time.perf_counter()
    results = trace_batch_with_system(system, rays)
    elapsed = time.perf_counter() - start
    return sorted(results, key=lambda item: item["index"]), elapsed


def trace_parallel(rays, workers=2, batch_size=25):
    batches = chunked(rays, batch_size)
    total_start = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=get_context("spawn"),
        initializer=init_worker_system,
    ) as pool:
        list(pool.map(trace_batch_with_worker_system, make_warmup_batches(workers)))
        trace_start = time.perf_counter()
        grouped_results = list(pool.map(trace_batch_with_worker_system, batches))
        trace_elapsed = time.perf_counter() - trace_start
    total_elapsed = time.perf_counter() - total_start
    results = [result for group in grouped_results for result in group]
    return sorted(results, key=lambda item: item["index"]), total_elapsed, trace_elapsed


def assert_results_match(sequential, parallel):
    assert len(sequential) == len(parallel)
    for seq, par in zip(sequential, parallel):
        assert seq["index"] == par["index"]
        assert seq["valid"] == par["valid"]
        assert seq["n_hits"] == par["n_hits"]
        assert seq["surfaces"] == par["surfaces"]
        assert np.allclose(seq["last_xyz"], par["last_xyz"], rtol=1e-10, atol=1e-10)
        assert np.isclose(seq["top"], par["top"], rtol=1e-10, atol=1e-10)
        if seq["last_lmn"] is None or par["last_lmn"] is None:
            assert seq["last_lmn"] == par["last_lmn"]
        else:
            assert np.allclose(seq["last_lmn"], par["last_lmn"], rtol=1e-10, atol=1e-10)


def test_parallel_sequential_trace_matches_serial_results():
    ray_count = 1000
    rays = generate_rays(ray_count)

    sequential, sequential_time = trace_sequential(rays)

    print(
        "\nparallel trace prototype:"
        f"\n  rays={ray_count}"
        f"\n  cpu_count={os.cpu_count()}"
        f"\n  sequential_warm={sequential_time:.6f}s"
        "\n  workers  batch_size  parallel_total  parallel_warm_trace  total_speedup  warm_speedup"
    )

    for workers in worker_counts_to_test():
        batch_size = max(1, math.ceil(ray_count / workers))
        parallel, parallel_total_time, parallel_trace_time = trace_parallel(
            rays,
            workers=workers,
            batch_size=batch_size,
        )

        assert_results_match(sequential, parallel)

        total_speedup = sequential_time / parallel_total_time if parallel_total_time else float("inf")
        warm_speedup = sequential_time / parallel_trace_time if parallel_trace_time else float("inf")
        print(
            f"  {workers:7d}  {batch_size:10d}  "
            f"{parallel_total_time:14.6f}s  {parallel_trace_time:19.6f}s  "
            f"{total_speedup:13.3f}x  {warm_speedup:12.3f}x"
        )
