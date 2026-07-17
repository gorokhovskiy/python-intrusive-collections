"""GC semantics — collections never own members; callers retain strong refs."""

from __future__ import annotations

import gc

from intrusive import IntrusiveList

from tests.models import Job, MixinTask, Task


def test_gc_unlinks_deleted_member(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, b, c = tasks
    tasks.remove(b)
    del b
    gc.collect()

    assert list(lst) == [a, c]
    lst.compact()
    assert len(lst) == 2


def test_ephemeral_push_is_collected() -> None:
    lst = IntrusiveList[Task]("hook")
    lst.push_back(Task("ephemeral"))
    gc.collect()

    assert list(lst) == []
    lst.compact()
    assert lst.empty()
    assert len(lst) == 0


def test_mixin_temps_collected() -> None:
    lst = IntrusiveList[MixinTask]("list_hook")
    lst.push_back(MixinTask("gone"))
    gc.collect()
    assert list(lst) == []

    m1 = MixinTask("Mixin1")
    m2 = MixinTask("Mixin2")
    lst.push_back(m1)
    lst.push_back(m2)
    assert list(lst) == [m1, m2]


def test_mass_delete_clears_list() -> None:
    lst = IntrusiveList[Job]("priority_hook")
    jobs = [Job(f"J{i}", i) for i in range(5)]
    lst.extend(jobs)

    del jobs
    gc.collect()

    assert list(lst) == []
    lst.compact()
    assert lst.empty()
    assert len(lst) == 0


def test_delete_middle_preserves_neighbors() -> None:
    lst = IntrusiveList[Task]("hook")
    a, b, c, d = Task("A"), Task("B"), Task("C"), Task("D")
    lst.extend((a, b, c, d))

    del c
    gc.collect()

    assert list(lst) == [a, b, d]
    assert lst.front() is a
    assert lst.back() is d
