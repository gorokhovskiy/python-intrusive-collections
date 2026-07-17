"""Performance comparison: owned DLL vs intrusive MemberListHook list."""

from __future__ import annotations

import gc
import os
import time
import tracemalloc
from dataclasses import dataclass

import pytest

from intrusive import IntrusiveList, MemberListHook

from tests.perf.owned_list import OwnedDoublyLinkedList

# Default to 1_000_000; override with INTRUSIVE_PERF_N (e.g. 100000 for quicker runs).
PERF_N = int(os.environ.get("INTRUSIVE_PERF_N", "1000000"))


@dataclass(slots=True)
class OwnedItem:
    value: int


class IntrusiveItem:
    __slots__ = ("value", "hook", "__weakref__")

    def __init__(self, value: int) -> None:
        self.value = value
        self.hook = MemberListHook()


@dataclass(frozen=True)
class OpResult:
    name: str
    owned_s: float
    intrusive_s: float
    owned_mem_kib: float | None = None
    intrusive_mem_kib: float | None = None

    @property
    def speedup(self) -> float:
        if self.intrusive_s <= 0:
            return float("inf")
        return self.owned_s / self.intrusive_s


def _timed(fn) -> tuple[float, object]:
    gc.collect()
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    return elapsed, result


def _measure_push_back(n: int) -> OpResult:
    owned_items = [OwnedItem(i) for i in range(n)]
    intrusive_items = [IntrusiveItem(i) for i in range(n)]

    owned = OwnedDoublyLinkedList[OwnedItem]()
    intrusive = IntrusiveList[IntrusiveItem]("hook")

    owned_s, _ = _timed(lambda: [owned.push_back(item) for item in owned_items])
    intrusive_s, _ = _timed(
        lambda: [intrusive.push_back(item) for item in intrusive_items]
    )

    assert len(owned) == n
    assert len(intrusive) == n
    # Keep builders alive until asserts; then drop explicitly.
    del owned_items, intrusive_items, owned, intrusive
    return OpResult("push_back", owned_s, intrusive_s)


def _measure_iterate(n: int) -> OpResult:
    owned = OwnedDoublyLinkedList[OwnedItem]()
    intrusive = IntrusiveList[IntrusiveItem]("hook")
    owned_items = [OwnedItem(i) for i in range(n)]
    intrusive_items = [IntrusiveItem(i) for i in range(n)]
    for item in owned_items:
        owned.push_back(item)
    for item in intrusive_items:
        intrusive.push_back(item)

    owned_s, owned_sum = _timed(lambda: sum(item.value for item in owned))
    intrusive_s, intrusive_sum = _timed(
        lambda: sum(item.value for item in intrusive)
    )

    expected = n * (n - 1) // 2
    assert owned_sum == expected
    assert intrusive_sum == expected
    del owned_items, intrusive_items, owned, intrusive
    return OpResult("iterate", owned_s, intrusive_s)


def _measure_pop_front(n: int) -> OpResult:
    owned = OwnedDoublyLinkedList[OwnedItem]()
    intrusive = IntrusiveList[IntrusiveItem]("hook")
    owned_items = [OwnedItem(i) for i in range(n)]
    intrusive_items = [IntrusiveItem(i) for i in range(n)]
    for item in owned_items:
        owned.push_back(item)
    for item in intrusive_items:
        intrusive.push_back(item)

    def drain_owned() -> int:
        count = 0
        while owned.pop_front() is not None:
            count += 1
        return count

    def drain_intrusive() -> int:
        count = 0
        while intrusive.pop_front() is not None:
            count += 1
        return count

    owned_s, owned_count = _timed(drain_owned)
    intrusive_s, intrusive_count = _timed(drain_intrusive)
    assert owned_count == n
    assert intrusive_count == n
    del owned_items, intrusive_items, owned, intrusive
    return OpResult("pop_front_all", owned_s, intrusive_s)


def _measure_remove_every_other(n: int) -> OpResult:
    owned = OwnedDoublyLinkedList[OwnedItem]()
    intrusive = IntrusiveList[IntrusiveItem]("hook")
    owned_items = [OwnedItem(i) for i in range(n)]
    intrusive_items = [IntrusiveItem(i) for i in range(n)]

    owned_nodes = [owned.push_back(item) for item in owned_items]
    for item in intrusive_items:
        intrusive.push_back(item)

    # Remove even indices — O(1) per removal for both (node handle / object hook).
    owned_targets = owned_nodes[::2]
    intrusive_targets = intrusive_items[::2]

    owned_s, _ = _timed(
        lambda: [owned.remove_node(node) for node in owned_targets]
    )
    intrusive_s, _ = _timed(
        lambda: [intrusive.remove(item) for item in intrusive_targets]
    )

    assert len(owned) == n - len(owned_targets)
    assert len(intrusive) == n - len(intrusive_targets)
    del owned_items, intrusive_items, owned_nodes, owned, intrusive
    return OpResult("remove_every_other", owned_s, intrusive_s)


def _measure_peak_memory_for_populated_lists(n: int) -> OpResult:
    gc.collect()
    tracemalloc.start()
    owned = OwnedDoublyLinkedList[OwnedItem]()
    owned_items = [OwnedItem(i) for i in range(n)]
    for item in owned_items:
        owned.push_back(item)
    _, owned_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del owned, owned_items
    gc.collect()

    tracemalloc.start()
    intrusive = IntrusiveList[IntrusiveItem]("hook")
    intrusive_items = [IntrusiveItem(i) for i in range(n)]
    for item in intrusive_items:
        intrusive.push_back(item)
    _, intrusive_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del intrusive, intrusive_items
    gc.collect()

    return OpResult(
        "peak_memory_populated",
        owned_s=0.0,
        intrusive_s=0.0,
        owned_mem_kib=owned_peak / 1024,
        intrusive_mem_kib=intrusive_peak / 1024,
    )


def _print_report(n: int, results: list[OpResult]) -> None:
    print("\n" + "=" * 78)
    print(f"Performance comparison — N={n:,} objects")
    print("=" * 78)
    print(
        f"{'operation':<22} {'owned (s)':>12} {'intrusive (s)':>14} "
        f"{'owned/intr':>12}"
    )
    print("-" * 78)
    for row in results:
        if row.name == "peak_memory_populated":
            continue
        print(
            f"{row.name:<22} {row.owned_s:12.4f} {row.intrusive_s:14.4f} "
            f"{row.speedup:12.2f}x"
        )

    mem = next((r for r in results if r.name == "peak_memory_populated"), None)
    if mem is not None and mem.owned_mem_kib is not None:
        ratio = mem.owned_mem_kib / mem.intrusive_mem_kib if mem.intrusive_mem_kib else 0
        print("-" * 78)
        print(
            f"{'peak_memory_kib':<22} {mem.owned_mem_kib:12.1f} "
            f"{mem.intrusive_mem_kib:14.1f} {ratio:12.2f}x"
        )
    print("=" * 78)
    print(
        "Notes: owned list keeps strong refs via nodes; intrusive collections "
        "use weak links only and never own member objects (callers retain refs)."
    )
    print("Ratio > 1 means intrusive was faster (or leaner for memory).")
    print("=" * 78 + "\n")


@pytest.mark.perf
@pytest.mark.slow
def test_owned_vs_intrusive_performance() -> None:
    """Compare owned DLL vs intrusive list on millions of objects."""
    n = PERF_N
    assert n >= 1_000, "PERF_N too small for a meaningful comparison"

    results = [
        _measure_push_back(n),
        _measure_iterate(n),
        _measure_pop_front(n),
        _measure_remove_every_other(n),
        _measure_peak_memory_for_populated_lists(n),
    ]
    _print_report(n, results)

    # Sanity: both implementations completed the workload.
    for row in results:
        if row.name == "peak_memory_populated":
            assert row.owned_mem_kib is not None and row.owned_mem_kib > 0
            assert row.intrusive_mem_kib is not None and row.intrusive_mem_kib > 0
        else:
            assert row.owned_s > 0
            assert row.intrusive_s > 0
