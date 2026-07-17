"""IntrusiveSet unit tests."""

from __future__ import annotations

import gc

import pytest

from intrusive import (
    IntrusiveSet,
    IntrusiveSetMixin,
    SetMemberHook,
    intrusive_set_hook,
)


class Task:
    def __init__(self, name: str) -> None:
        self.name = name
        self.hook = SetMemberHook[int](int)

    def __repr__(self) -> str:
        return f"Task({self.name!r})"


class Job:
    def __init__(self, name: str) -> None:
        self.name = name
        self.priority_hook = SetMemberHook[int](int)
        self.queue_hook = SetMemberHook[int](int)

    def __repr__(self) -> str:
        return f"Job({self.name!r})"


def test_insert_sorted_iteration() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t1, t2, t3, t4 = Task("Compile"), Task("Test"), Task("Deploy"), Task("Lint")

    assert s.insert(t1, key=30)
    assert s.insert(t2, key=10)
    assert s.insert(t3, key=50)
    assert s.insert(t4, key=20)

    assert list(s) == [t2, t4, t1, t3]
    assert list(reversed(s)) == [t3, t1, t4, t2]
    assert len(s) == 4
    assert s.min() is t2
    assert s.max() is t3


def test_find_and_contains() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t = Task("A")
    s.insert(t, key=7)

    assert s.find(7) is t
    assert s.find(8) is None
    assert t in s
    assert Task("B") not in s


def test_unique_key_and_double_insert() -> None:
    s = IntrusiveSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    assert s.insert(a, key=1)
    assert s.insert(a, key=2) is False  # already linked
    assert a.hook.key == 1
    assert s.insert(b, key=1) is False  # duplicate key
    assert b not in s


def test_change_key_reorders() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t1, t2, t3 = Task("A"), Task("B"), Task("C")
    s.insert(t1, key=10)
    s.insert(t2, key=20)
    s.insert(t3, key=30)

    t1.hook.change_key(25)
    assert list(s) == [t2, t1, t3]
    assert s.find(10) is None
    assert s.find(25) is t1
    assert t1.hook.key == 25


def test_change_key_same_is_noop() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t = Task("A")
    s.insert(t, key=5)
    t.hook.change_key(5)
    assert list(s) == [t]
    assert len(s) == 1


def test_change_key_conflict_raises() -> None:
    s = IntrusiveSet[int, Task]("hook")
    a, b = Task("A"), Task("B")
    s.insert(a, key=1)
    s.insert(b, key=2)
    with pytest.raises(ValueError, match="already present"):
        a.hook.change_key(2)


def test_change_key_type_check() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t = Task("A")
    s.insert(t, key=1)
    with pytest.raises(TypeError):
        t.hook.change_key("bad")  # type: ignore[arg-type]


def test_remove_and_reinsert() -> None:
    s = IntrusiveSet[int, Task]("hook")
    t = Task("A")
    s.insert(t, key=1)
    assert s.remove(t) is True
    assert t not in s
    assert t.hook.key is None
    assert s.insert(t, key=2)
    assert t.hook.key == 2


def test_key_extractor() -> None:
    class Item:
        def __init__(self, name: str, prio: int) -> None:
            self.name = name
            self.prio = prio
            self.hook = SetMemberHook[int]()

        def __repr__(self) -> str:
            return f"Item({self.name!r})"

    s = IntrusiveSet[int, Item]("hook", key_extractor=lambda i: i.prio)
    a, b = Item("A", 2), Item("B", 1)
    assert s.insert(a)
    assert s.insert(b)
    assert list(s) == [b, a]


def test_clear_empty_min_max() -> None:
    s = IntrusiveSet[int, Task]("hook")
    assert s.empty()
    assert s.min() is None
    assert s.max() is None

    tasks = [Task(str(i)) for i in range(5)]
    for i, t in enumerate(tasks):
        s.insert(t, key=i)

    s.clear()
    assert s.empty()
    assert list(s) == []
    assert len(s) == 0


def test_multi_set_change_key_isolated() -> None:
    priority = IntrusiveSet[int, Job]("priority_hook")
    queue = IntrusiveSet[int, Job]("queue_hook")
    j1, j2, j3 = Job("A"), Job("B"), Job("C")

    priority.insert(j1, key=3)
    priority.insert(j2, key=1)
    priority.insert(j3, key=2)

    queue.insert(j1, key=1)
    queue.insert(j2, key=3)
    queue.insert(j3, key=2)

    assert list(priority) == [j2, j3, j1]
    assert list(queue) == [j1, j3, j2]

    j3.priority_hook.change_key(5)
    assert list(priority) == [j2, j1, j3]
    assert list(queue) == [j1, j3, j2]


def test_gc_unlinks() -> None:
    s = IntrusiveSet[int, Task]("hook")
    a, b, c = Task("A"), Task("B"), Task("C")
    s.insert(a, key=1)
    s.insert(b, key=2)
    s.insert(c, key=3)

    del b
    gc.collect()

    assert list(s) == [a, c]
    s.compact()
    assert len(s) == 2
    assert s.find(2) is None


def test_ephemeral_insert_is_collected() -> None:
    s = IntrusiveSet[int, Task]("hook")
    s.insert(Task("kept"), key=1)
    gc.collect()
    assert list(s) == []
    s.compact()
    assert len(s) == 0


def test_decorator_and_mixin() -> None:
    @intrusive_set_hook(int, "prio_hook")
    class Decorated:
        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"Decorated({self.name!r})"

    d = Decorated("D")
    assert isinstance(d.prio_hook, SetMemberHook)
    s = IntrusiveSet[int, Decorated]("prio_hook")
    s.insert(d, key=42)
    assert list(s) == [d]

    class Mixed(IntrusiveSetMixin[int]):
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

    m = Mixed("M")
    ms = IntrusiveSet[int, Mixed]("set_hook")
    ms.insert(m, key=9)
    assert list(ms) == [m]


def test_many_insert_remove_order() -> None:
    s = IntrusiveSet[int, Task]("hook")
    tasks = [Task(str(i)) for i in range(50)]
    for i, t in enumerate(tasks):
        assert s.insert(t, key=i)

    for i in range(0, 50, 2):
        assert s.remove(tasks[i])

    remaining = [tasks[i] for i in range(1, 50, 2)]
    assert list(s) == remaining
    assert len(s) == 25
