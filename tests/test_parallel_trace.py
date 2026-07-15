import math
import os
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing import get_context

import numpy as np
import pytest


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


def trace_batch(batch):
    system = build_simple_system(build=0)
    return trace_batch_with_system(system, batch)


def trace_batch_with_system(system, batch):
    import KrakenOS as Kos

    results = []
    for ray in batch:
        system.Trace(ray["origin"], ray["direction"], ray["wavelength"])
        result = Kos.extract_ray_result(system, copy=True)
        result["index"] = ray["index"]
        results.append(result)
    return results


def trace_batch_with_worker_system(batch):
    if _WORKER_SYSTEM is None:
        raise RuntimeError("Worker system was not initialized")
    return trace_batch_with_system(_WORKER_SYSTEM, batch)


def chunked(items, chunk_size):
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def worker_counts_to_test():
    return [min(2, os.cpu_count() or 2)]


def trace_sequential(rays):
    system = build_simple_system(build=0)
    start = time.perf_counter()
    results = trace_batch_with_system(system, rays)
    elapsed = time.perf_counter() - start
    return sorted(results, key=lambda item: item["index"]), elapsed


def trace_parallel(rays, workers=2, batch_size=25, return_flat=False):
    """Materialize worker batches. Prefer ``trace_parallel_into_raykeeper``.

    ``return_flat=True`` builds a sorted list and drops the group list so both
    are not retained together.
    """
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

    if return_flat:
        results = [result for group in grouped_results for result in group]
        del grouped_results
        return sorted(results, key=lambda item: item["index"]), total_elapsed, trace_elapsed

    return (None, total_elapsed, trace_elapsed, grouped_results)


def result_last_lmn(result):
    if not result["R_LMN"]:
        return None
    candidate = np.asarray(result["R_LMN"][-1], dtype=float)
    if not candidate.size:
        return None
    return candidate


def assert_results_match(sequential, parallel):
    assert len(sequential) == len(parallel)
    for seq, par in zip(sequential, parallel):
        assert seq["index"] == par["index"]
        assert seq["val"] == par["val"]
        assert len(seq["XYZ"]) == len(par["XYZ"])
        assert seq["SURFACE"] == par["SURFACE"]
        assert np.allclose(np.asarray(seq["XYZ"], dtype=float)[-1], np.asarray(par["XYZ"], dtype=float)[-1], rtol=1e-10, atol=1e-10)
        assert np.isclose(np.asarray(seq["TOP"], dtype=float), np.asarray(par["TOP"], dtype=float), rtol=1e-10, atol=1e-10)

        seq_lmn = result_last_lmn(seq)
        par_lmn = result_last_lmn(par)
        if seq_lmn is None or par_lmn is None:
            assert seq_lmn is None and par_lmn is None
        else:
            assert np.allclose(seq_lmn, par_lmn, rtol=1e-10, atol=1e-10)


def run_bounded_ordered_batches(n_batches, max_in_flight, submit_batch, ingest_batch):
    """Submit/consume batches with ``pending + ready`` capped at ``max_in_flight``.

    Batches are ingested in input order.  Returns the peak of
    ``len(pending) + len(ready)`` observed during the run.
    """
    if max_in_flight < 1:
        raise ValueError("max_in_flight must be >= 1")

    next_submit = 0
    next_ingest = 0
    pending = {}
    ready = {}
    peak_in_flight = 0

    def _submit_more():
        nonlocal next_submit
        while (
            next_submit < n_batches
            and len(pending) + len(ready) < max_in_flight
        ):
            future = submit_batch(next_submit)
            pending[future] = next_submit
            next_submit += 1

    def _note_peak():
        nonlocal peak_in_flight
        peak_in_flight = max(peak_in_flight, len(pending) + len(ready))

    _submit_more()
    _note_peak()
    while pending or ready:
        if pending:
            done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in done:
                batch_index = pending.pop(future)
                ready[batch_index] = future.result()
                _note_peak()
        while next_ingest in ready:
            ingest_batch(next_ingest, ready.pop(next_ingest))
            next_ingest += 1
        _submit_more()
        _note_peak()
    return peak_in_flight


def trace_parallel_into_raykeeper(rays, workers, batch_size, max_in_flight=None):
    """Trace rays in parallel with a bounded in-flight batch window.

    At most ``max_in_flight`` (default ``2 * workers``) batches may be in
    ``pending`` or ``ready`` combined.  Completed batches are ingested in
    input order via a small reorder buffer, so peak retained worker results
    stay bounded even when later batches finish before earlier ones.
    """
    import KrakenOS as Kos

    batches = chunked(rays, batch_size)
    if max_in_flight is None:
        max_in_flight = max(1, workers * 2)
    elif max_in_flight < 1:
        raise ValueError("max_in_flight must be >= 1")

    total_start = time.perf_counter()
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=get_context("spawn"),
        initializer=init_worker_system,
    ) as pool:
        list(pool.map(trace_batch_with_worker_system, make_warmup_batches(workers)))

        system = build_simple_system(build=0)
        rk = Kos.raykeeper(system)

        trace_start = time.perf_counter()
        run_bounded_ordered_batches(
            len(batches),
            max_in_flight,
            submit_batch=lambda index: pool.submit(
                trace_batch_with_worker_system, batches[index]
            ),
            ingest_batch=lambda _index, batch: rk.extend_results(batch),
        )
        trace_elapsed = time.perf_counter() - trace_start

    total_elapsed = time.perf_counter() - total_start
    return rk, total_elapsed, trace_elapsed


def build_raykeeper_from_results(results):
    import KrakenOS as Kos

    system = build_simple_system(build=0)
    rays = Kos.raykeeper(system)
    rays.extend_results(sorted(results, key=lambda item: item["index"]))
    return rays


def build_raykeeper_from_batches(grouped_results):
    """Ingest batches as they arrive to avoid retaining one giant result list."""
    import KrakenOS as Kos

    system = build_simple_system(build=0)
    rays = Kos.raykeeper(system)
    for batch in grouped_results:
        rays.extend_results(sorted(batch, key=lambda item: item["index"]))
    return rays


def build_classic_raykeeper(rays_to_trace):
    import KrakenOS as Kos

    system = build_simple_system(build=0)
    rays = Kos.raykeeper(system)
    for ray in rays_to_trace:
        system.Trace(ray["origin"], ray["direction"], ray["wavelength"])
        rays.push()
    return rays


def assert_raykeepers_match(reference, candidate):
    assert reference.nrays == candidate.nrays
    np.testing.assert_equal(reference.vld, candidate.vld)
    assert len(reference.XYZ) == len(candidate.XYZ)
    assert len(reference.R_LMN) == len(candidate.R_LMN)
    assert len(reference.CC) == len(candidate.CC)
    for ref_xyz, cand_xyz in zip(reference.XYZ, candidate.XYZ):
        assert np.allclose(ref_xyz.astype(float), cand_xyz.astype(float), rtol=1e-10, atol=1e-10)
    for ref_lmn, cand_lmn in zip(reference.R_LMN, candidate.R_LMN):
        assert np.allclose(ref_lmn.astype(float), cand_lmn.astype(float), rtol=1e-10, atol=1e-10)
    for ref_hits, cand_hits in zip(reference.CC, candidate.CC):
        assert np.allclose(ref_hits.astype(float), cand_hits.astype(float), rtol=1e-10, atol=1e-10)


def test_parallel_sequential_trace_matches_serial_results():
    ray_count = 100
    batch_size = 25
    rays = generate_rays(ray_count)

    sequential, sequential_time = trace_sequential(rays)
    classic_raykeeper = build_classic_raykeeper(rays)

    print(
        "\nparallel trace prototype:"
        f"\n  rays={ray_count}"
        f"\n  cpu_count={os.cpu_count()}"
        f"\n  sequential_warm={sequential_time:.6f}s"
        "\n  workers  batch_size  parallel_total  parallel_warm_trace  total_speedup  warm_speedup"
    )

    for workers in worker_counts_to_test():
        # Flat path for dict-level equivalence (small N; does not retain groups).
        parallel, parallel_total_time, parallel_trace_time = trace_parallel(
            rays, workers=workers, batch_size=batch_size, return_flat=True
        )
        assert_results_match(sequential, parallel)

        # End-to-end production path: stream batches into raykeeper.
        streamed_raykeeper, _, _ = trace_parallel_into_raykeeper(
            rays, workers=workers, batch_size=batch_size
        )
        assert_raykeepers_match(classic_raykeeper, streamed_raykeeper)

        total_speedup = sequential_time / parallel_total_time if parallel_total_time else float("inf")
        warm_speedup = sequential_time / parallel_trace_time if parallel_trace_time else float("inf")
        print(
            f"  {workers:7d}  {batch_size:10d}  "
            f"{parallel_total_time:14.6f}s  {parallel_trace_time:19.6f}s  "
            f"{total_speedup:13.3f}x  {warm_speedup:12.3f}x"
        )


def test_extract_snapshot_copy_is_independent_after_pickle_roundtrip():
    import pickle

    import KrakenOS as Kos

    system = build_simple_system(build=0)
    system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    snapshot = Kos.extract_ray_result(system, copy=True)
    payload = pickle.dumps(snapshot)
    restored = pickle.loads(payload)

    system.Trace([1000.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays = Kos.raykeeper(system)
    rays.push_result(restored)

    assert rays.vld.tolist() == [1.0]
    assert not np.allclose(np.asarray(restored["XYZ"], dtype=float)[-1], [1000.0, 0.0, 0.0])
    assert not np.allclose(np.asarray(rays.XYZ[0], dtype=float)[-1], [1000.0, 0.0, 0.0])


def test_push_retains_stable_snapshot_after_next_trace():
    import KrakenOS as Kos

    system = build_simple_system(build=0)
    rays = Kos.raykeeper(system)
    system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays.push()

    xyz_a = np.asarray(rays.XYZ[0], dtype=float).copy()
    cc_a = np.asarray(rays.CC[0], dtype=float).copy()

    system.Trace([3.0, 1.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays.push()

    assert np.allclose(np.asarray(rays.XYZ[0], dtype=float), xyz_a)
    assert np.allclose(np.asarray(rays.CC[0], dtype=float), cc_a)
    assert not np.allclose(np.asarray(rays.XYZ[1], dtype=float), xyz_a)


def test_bounded_window_counts_pending_plus_ready():
    """Slow batch 0 must not let ready grow past max_in_flight."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    max_in_flight = 2
    n_batches = 8
    release_batch0 = threading.Event()
    later_lock = threading.Lock()
    later_done = 0
    ingested = []

    def work(batch_index):
        nonlocal later_done
        if batch_index == 0:
            assert release_batch0.wait(timeout=5.0)
            return [batch_index]
        with later_lock:
            later_done += 1
            # With the cap, only max_in_flight-1 later batches can finish while
            # batch 0 is still pending; release once that has happened.
            if later_done >= max_in_flight - 1:
                release_batch0.set()
        return [batch_index]

    with ThreadPoolExecutor(max_workers=4) as pool:
        peak = run_bounded_ordered_batches(
            n_batches,
            max_in_flight,
            submit_batch=lambda index: pool.submit(work, index),
            ingest_batch=lambda index, payload: ingested.append(index),
        )

    assert peak <= max_in_flight
    assert ingested == list(range(n_batches))


def test_max_in_flight_must_be_positive():
    with pytest.raises(ValueError, match="max_in_flight"):
        run_bounded_ordered_batches(
            1,
            0,
            submit_batch=lambda index: None,
            ingest_batch=lambda index, payload: None,
        )


def test_valid_and_invalid_views_are_read_only_sequences_with_live_updates():
    import KrakenOS as Kos

    system = build_simple_system(build=0)
    rays = Kos.raykeeper(system)
    for origin in ([0.0, 0.0, 0.0], [1000.0, 0.0, 0.0], [1.0, 0.0, 0.0]):
        system.Trace(origin, [0.0, 0.0, 1.0], 0.55)
        rays.push()

    valid_xyz = rays.valid_XYZ
    invalid_xyz = rays.invalid_XYZ
    assert rays._ray_valid == [True, False, True]
    assert [item is rays.XYZ[index] for item, index in zip(valid_xyz, (0, 2))] == [True, True]
    assert valid_xyz[0] is rays.XYZ[0]
    assert valid_xyz[-1] is rays.XYZ[2]
    assert [item is rays.XYZ[index] for item, index in zip(valid_xyz[:], (0, 2))] == [True, True]
    assert invalid_xyz[0] is rays.XYZ[1]
    assert invalid_xyz[-1] is rays.XYZ[1]
    assert invalid_xyz[:] == [rays.XYZ[1]]

    with pytest.raises(TypeError):
        valid_xyz[0] = rays.XYZ[1]
    with pytest.raises(AttributeError):
        valid_xyz.append(rays.XYZ[0])

    system.Trace([2.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays.push()
    assert len(valid_xyz) == 3
    assert valid_xyz[-1] is rays.XYZ[3]


def test_streaming_parallel_memory_scales_near_linearly():
    """Parent-process Python allocation scaling for bounded parallel ingestion.

    This is a regression signal for quadratic growth in the parent process; it
    does not measure worker-process or all native NumPy peak memory.
    """
    import tracemalloc

    workers = min(2, os.cpu_count() or 2)
    batch_size = 25

    def _trace_and_measure(ray_count):
        rays = generate_rays(ray_count)

        tracemalloc.start()
        # Take a snapshot *after* tracemalloc starts to isolate our allocations.
        _ = tracemalloc.take_snapshot()

        rk, _, _ = trace_parallel_into_raykeeper(rays, workers, batch_size)
        # Force NumPy to actually allocate the lazy caches so they count.
        _ = rk.vld
        _ = rk.valid_vld
        _ = rk.invalid_vld

        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        return rk, peak

    # --- Correctness: streaming must match classic tracing ---
    classic = build_classic_raykeeper(generate_rays(200))
    streamed, _peak_200 = _trace_and_measure(200)
    assert_raykeepers_match(classic, streamed)

    # --- Memory scaling: 2× rays should stay well under 3× peak ---
    _, peak_100 = _trace_and_measure(100)
    _, peak_200 = _trace_and_measure(200)

    ratio = peak_200 / peak_100 if peak_100 else float("inf")
    # Allow overhead; 3× is a generous guard against quadratic growth.
    assert ratio < 3.0, f"peak memory ratio {ratio:.2f}x — possible non-linear growth (peak_100={peak_100}, peak_200={peak_200})"
