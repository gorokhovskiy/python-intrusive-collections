"""IntrusiveMultiSet tests (shared RB tree with IntrusiveSet)."""

from __future__ import annotations

import gc

import pytest

from intrusive import IntrusiveMultiSet, IntrusiveSet, SetMemberHook


class Task:
    def __init__(self, name: str) -> None:
        self.name = name
        self.hook = SetMemberHook[int](int)

    def __repr__(self) -> str:
        return f"Task({self.name!r})"


def test_duplicate_keys_allowed() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    a, b, c = Task("A"), Task("B"), Task("C")
    assert s.insert(a, key=10)
    assert s.insert(b, key=10)
    assert s.insert(c, key=20)

    assert len(s) == 3
    assert list(s) == [a, b, c] or list(s) == [b, a, c]
    # Equals are adjacent and ordered among themselves by insertion-to-right.
    keys = [t.hook.key for t in s]
    assert keys == [10, 10, 20]


def test_count_and_equal_range() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    tasks = [Task(str(i)) for i in range(5)]
    for t in tasks[:3]:
        s.insert(t, key=1)
    s.insert(tasks[3], key=2)
    s.insert(tasks[4], key=1)

    assert s.count(1) == 4
    assert s.count(2) == 1
    assert s.count(9) == 0
    assert set(s.equal_range(1)) == set(tasks[:3] + [tasks[4]])
    assert list(s.equal_range(2)) == [tasks[3]]


def test_lower_upper_bound() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    a, b, c, d = Task("A"), Task("B"), Task("C"), Task("D")
    s.insert(a, key=10)
    s.insert(b, key=20)
    s.insert(c, key=20)
    s.insert(d, key=30)

    assert s.lower_bound(20) in (b, c)
    assert s.lower_bound(20).hook.key == 20  # type: ignore[union-attr]
    assert s.upper_bound(20) is d
    assert s.lower_bound(25) is d
    assert s.upper_bound(30) is None
    assert s.lower_bound(5) is a


def test_change_key_allows_duplicate_target() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    s.insert(a, key=1)
    s.insert(b, key=2)
    b.hook.change_key(1)
    assert s.count(1) == 2
    assert s.count(2) == 0
    assert set(s.equal_range(1)) == {a, b}


def test_set_still_rejects_duplicate_key() -> None:
    unique = IntrusiveSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    assert unique.insert(a, key=1)
    assert unique.insert(b, key=1) is False


def test_multiset_change_key_same_noop() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    t = Task("A")
    s.insert(t, key=5)
    t.hook.change_key(5)
    assert len(s) == 1
    assert t.hook.key == 5


def test_multiset_remove_one_of_duplicates() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    s.insert(a, key=1)
    s.insert(b, key=1)
    assert s.remove(a)
    assert list(s) == [b]
    assert s.count(1) == 1


def test_multiset_ephemeral_is_collected() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    s.insert(Task("kept"), key=1)
    gc.collect()
    assert list(s) == []
    s.compact()
    assert len(s) == 0


def test_multiset_gc() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    s.insert(a, key=1)
    s.insert(b, key=1)
    del b
    gc.collect()
    assert list(s) == [a]
    s.compact()
    assert len(s) == 1


def test_already_linked_rejected() -> None:
    s = IntrusiveMultiSet[int, Task]("hook")
    t = Task("A")
    assert s.insert(t, key=1)
    assert s.insert(t, key=2) is False
