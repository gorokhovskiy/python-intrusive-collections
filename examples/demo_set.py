"""Demonstrate IntrusiveSet with immutable typed keys."""

from __future__ import annotations

import gc

from intrusive import IntrusiveSet, SetMemberHook, intrusive_set_hook


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    print("=" * 70)
    print("IntrusiveSet — Demo (weak links, no ownership)")
    print("=" * 70)

    section("Basic Insert & Lookup")

    class Task:
        def __init__(self, name: str) -> None:
            self.name = name
            self.hook = SetMemberHook[int](int)

        def __repr__(self) -> str:
            return f"Task({self.name!r})"

    task_set = IntrusiveSet[int, Task]("hook")
    t1, t2, t3, t4 = Task("Compile"), Task("Test"), Task("Deploy"), Task("Lint")
    task_set.insert(t1, key=30)
    task_set.insert(t2, key=10)
    task_set.insert(t3, key=50)
    task_set.insert(t4, key=20)

    print(f"Set (sorted): {list(task_set)}")
    print(f"Size: {len(task_set)}")
    print(f"Min: {task_set.min()}  Max: {task_set.max()}")
    print(f"Find 20: {task_set.find(20)}")

    section("change_key()")
    print(f"Before: {list(task_set)}")
    t4.hook.change_key(40)
    print(f"After change_key(40): {list(task_set)}")
    print(f"Find 40: {task_set.find(40)}  Find 20: {task_set.find(20)}")

    section("GC auto-unlink")
    a, b, c = Task("A"), Task("B"), Task("C")
    task_set.clear()
    task_set.insert(a, key=1)
    task_set.insert(b, key=2)
    task_set.insert(c, key=3)
    print(f"Before: {list(task_set)}")
    del b
    gc.collect()
    print(f"After del B: {list(task_set)}")

    section("Multiple Sets Per Object")

    class Job:
        def __init__(self, name: str) -> None:
            self.name = name
            self.priority_hook = SetMemberHook[int](int)
            self.queue_hook = SetMemberHook[int](int)

        def __repr__(self) -> str:
            return f"Job({self.name!r})"

    priority_set = IntrusiveSet[int, Job]("priority_hook")
    queue_set = IntrusiveSet[int, Job]("queue_hook")
    j1, j2, j3 = Job("A"), Job("B"), Job("C")
    priority_set.insert(j1, key=3)
    priority_set.insert(j2, key=1)
    priority_set.insert(j3, key=2)
    queue_set.insert(j1, key=1)
    queue_set.insert(j2, key=3)
    queue_set.insert(j3, key=2)
    print(f"Priority: {list(priority_set)}")
    print(f"Queue:    {list(queue_set)}")
    j3.priority_hook.change_key(5)
    print(f"After j3 priority→5: {list(priority_set)}")
    print(f"Queue unchanged:     {list(queue_set)}")

    section("Decorator")

    @intrusive_set_hook(int, "prio_hook")
    class DecoratedJob:
        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"DecoratedJob({self.name!r})"

    dj = DecoratedJob("Decorated")
    dec_set = IntrusiveSet[int, DecoratedJob]("prio_hook")
    dec_set.insert(dj, key=42)
    print(f"Set: {list(dec_set)}")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
