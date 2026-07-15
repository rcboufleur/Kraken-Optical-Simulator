#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: parallel-ready sequential ray tracing with build=0.

This example shows the recommended pattern for tracing independent rays in
parallel without passing a KrakenOS system, PyVista object, or VTK object
between processes.

What this example teaches:
- use ``system(..., build=0)`` for lightweight sequential tracing;
- build one independent optical system inside each worker process;
- trace batches of rays instead of launching one process per ray;
- return only serializable numerical ray results from workers;
- rebuild a ``raykeeper`` in the parent process with ``extend_results``.

Didactic note:
- multiprocessing has startup overhead, especially on Windows. The total
  parallel time can be slower for small ray counts, even when the warm tracing
  section is faster. This example prints both values so the difference is clear.
"""

import math
import os
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing import get_context
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))


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


def chunked(items, chunk_size):
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


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


def trace_sequential(rays):
    system = build_simple_system(build=0)
    start = time.perf_counter()
    results = trace_batch_with_system(system, rays)
    elapsed = time.perf_counter() - start
    return sorted(results, key=lambda item: item["index"]), elapsed


def trace_parallel(rays, workers, batch_size=25, return_flat=False):
    """Trace rays in parallel with bounded batches.

    Prefer ``trace_parallel_into_raykeeper`` for production: it streams each
    completed batch into a raykeeper and drops the batch immediately.

    This helper materializes all worker batches (needed for timing/validation).
    ``return_flat=True`` builds a sorted list from those batches and drops the
    group list so both are not retained together.
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


def check_results_match(sequential, parallel):
    if len(sequential) != len(parallel):
        return False

    for seq, par in zip(sequential, parallel):
        if seq["index"] != par["index"] or seq["val"] != par["val"]:
            return False
        if seq["SURFACE"] != par["SURFACE"]:
            return False
        if not np.allclose(np.asarray(seq["XYZ"], dtype=float)[-1], np.asarray(par["XYZ"], dtype=float)[-1]):
            return False

        seq_lmn = result_last_lmn(seq)
        par_lmn = result_last_lmn(par)
        if seq_lmn is None or par_lmn is None:
            if seq_lmn is not None or par_lmn is not None:
                return False
        elif not np.allclose(seq_lmn, par_lmn):
            return False

    return True


def trace_parallel_into_raykeeper(rays, workers, batch_size, max_in_flight=None):
    """Trace rays in parallel with a bounded in-flight batch window.

    At most ``max_in_flight`` (default ``2 * workers``) batches may be in
    ``pending`` or ``ready`` combined.  Completed batches are ingested in
    input order via a small reorder buffer so peak retained worker results
    stay bounded.
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
        next_submit = 0
        next_ingest = 0
        pending = {}
        ready = {}

        def _submit_more():
            nonlocal next_submit
            while (
                next_submit < len(batches)
                and len(pending) + len(ready) < max_in_flight
            ):
                future = pool.submit(trace_batch_with_worker_system, batches[next_submit])
                pending[future] = next_submit
                next_submit += 1

        _submit_more()
        while pending or ready:
            if pending:
                done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in done:
                    batch_index = pending.pop(future)
                    ready[batch_index] = future.result()
            while next_ingest in ready:
                batch = ready.pop(next_ingest)
                rk.extend_results(batch)
                next_ingest += 1
            _submit_more()
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
    """Ingest one batch at a time to limit peak retained result dicts."""
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


def main():
    ray_count = 1000
    workers = min(4, os.cpu_count() or 1)
    batch_size = 25  # bounded batches → low peak IPC retention
    rays = generate_rays(ray_count)

    sequential, sequential_time = trace_sequential(rays)

    # Production path: stream batches into raykeeper (no global result list).
    rk, stream_total, stream_trace = trace_parallel_into_raykeeper(
        rays, workers, batch_size
    )
    stream_speedup = sequential_time / stream_trace if stream_trace else float("inf")

    classic = build_classic_raykeeper(rays)
    raykeepers_match = (
        classic.nrays == rk.nrays
        and np.array_equal(classic.vld, rk.vld)
        and len(classic.XYZ) == len(rk.XYZ)
    )

    # Timing-only materializing path (bounded batch_size; results discarded).
    _, parallel_total_time, parallel_trace_time, _ = trace_parallel(
        rays, workers, batch_size=batch_size, return_flat=False
    )
    total_speedup = sequential_time / parallel_total_time if parallel_total_time else float("inf")
    warm_speedup = sequential_time / parallel_trace_time if parallel_trace_time else float("inf")

    print("\nParallel sequential tracing example")
    print(f"Rays: {ray_count}")
    print(f"CPU count: {os.cpu_count()}")
    print(f"Workers: {workers}")
    print(f"Batch size: {batch_size}")
    print(f"Sequential warm trace time: {sequential_time:.6f} s")
    print(f"Streaming total time:       {stream_total:.6f} s")
    print(f"Streaming warm trace time:  {stream_trace:.6f} s")
    print(f"Streaming trace speedup:    {stream_speedup:.3f}x")
    print(f"Materialize total time:     {parallel_total_time:.6f} s")
    print(f"Materialize warm trace:     {parallel_trace_time:.6f} s")
    print(f"Materialize total speedup:  {total_speedup:.3f}x")
    print(f"Materialize warm speedup:   {warm_speedup:.3f}x")
    print(f"Streaming vs classic match: {raykeepers_match}")
    print(f"Streaming raykeeper rays:   {rk.nrays}")
    print(
        "\nFor small ray counts, total parallel time can be slower because Windows "
        "must start worker processes. The warm trace time is the useful number "
        "when workers remain alive and trace many batches."
    )


if __name__ == "__main__":
    main()
