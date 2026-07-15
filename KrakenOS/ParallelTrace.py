"""Bounded parallel batch scheduling helpers."""

from concurrent.futures import FIRST_COMPLETED, wait


def resolve_max_in_flight(workers, max_in_flight=None):
    """Return a positive in-flight window size (default ``2 * workers``)."""
    if max_in_flight is None:
        return max(1, int(workers) * 2)
    if max_in_flight < 1:
        raise ValueError("max_in_flight must be >= 1")
    return max_in_flight


def run_bounded_ordered_batches(n_batches, max_in_flight, submit_batch, ingest_batch):
    """Submit/consume batches with ``pending + ready`` capped at ``max_in_flight``.

    Batches are ingested in input order.  Returns the peak of
    ``len(pending) + len(ready)`` observed during the run.

    ``max_in_flight`` must be an explicit positive integer; use
    :func:`resolve_max_in_flight` to apply the default ``2 * workers``.
    """
    if max_in_flight is None or max_in_flight < 1:
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
