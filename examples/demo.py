"""Demonstrate IntrusiveList APIs while retaining strong owner references."""

from __future__ import annotations

import gc

from intrusive import (
    IntrusiveList,
    IntrusiveListMixin,
    MemberListHook,
    intrusive_list_hook,
)


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def demo_manual() -> None:
    section("Manual Hook Creation")

    class TaskManual:
        def __init__(self, name: str) -> None:
            self.name = name
            self.hook = MemberListHook()

        def __repr__(self) -> str:
            return f"TaskManual({self.name!r})"

    task_list = IntrusiveList[TaskManual]("hook")
    t1 = TaskManual("Alpha")
    t2 = TaskManual("Beta")
    t3 = TaskManual("Gamma")

    task_list.extend((t1, t2, t3))
    print(f"List: {list(task_list)}")
    print(f"Size: {len(task_list)}")

    print("\nDeleting t2 (GC auto-unlink)...")
    del t2
    gc.collect()
    print(f"After GC: {list(task_list)}")


def demo_decorator() -> None:
    section("@intrusive_list_hook Decorator")

    @intrusive_list_hook("task_hook")
    class TaskDecorated:
        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"TaskDecorated({self.name!r})"

    td = TaskDecorated("Decorated")
    print(f"Auto-created hook: {td.task_hook}")

    dec_list = IntrusiveList[TaskDecorated]("task_hook")
    d1 = TaskDecorated("D1")
    d2 = TaskDecorated("D2")
    dec_list.extend((d1, d2))
    print(f"Decorated list: {list(dec_list)}")


def demo_mixin() -> None:
    section("IntrusiveListMixin")

    class TaskMixin(IntrusiveListMixin):
        def __init__(self, name: str) -> None:
            super().__init__()
            self.name = name

        def __repr__(self) -> str:
            return f"TaskMixin({self.name!r})"

    mixin_list = IntrusiveList[TaskMixin]("list_hook")
    m1 = TaskMixin("Mixin1")
    m2 = TaskMixin("Mixin2")
    mixin_list.extend((m1, m2))
    print(f"Mixin list: {list(mixin_list)}")


def demo_multi_list() -> None:
    section("Same Object in Multiple Lists")

    class Job:
        def __init__(self, name: str, priority: int) -> None:
            self.name = name
            self.priority = priority
            self.priority_hook = MemberListHook()
            self.work_hook = MemberListHook()

        def __repr__(self) -> str:
            return f"Job({self.name!r}, priority={self.priority})"

    priority_list = IntrusiveList[Job]("priority_hook")
    work_list = IntrusiveList[Job]("work_hook")

    j1 = Job("Compile", 3)
    j2 = Job("Test", 1)
    j3 = Job("Deploy", 2)

    priority_list.extend((j1, j2, j3))
    work_list.extend((j2, j3, j1))

    print(f"Priority list: {list(priority_list)}")
    print(f"Work list:     {list(work_list)}")

    print(f"\nDeleting j2 ({j2.name}) from BOTH lists...")
    del j2
    gc.collect()

    print(f"Priority after: {list(priority_list)}")
    print(f"Work after:     {list(work_list)}")


def demo_ops() -> None:
    section("Advanced Operations")

    class Job:
        def __init__(self, name: str) -> None:
            self.name = name
            self.hook = MemberListHook()

        def __repr__(self) -> str:
            return f"Job({self.name!r})"

    lst = IntrusiveList[Job]("hook")
    a, b, c, d = Job("A"), Job("B"), Job("C"), Job("D")

    lst.extend((a, b, c))
    print(f"Initial: {list(lst)}")

    lst.insert_after(a, d)
    print(f"After insert D after A: {list(lst)}")

    lst.remove(b)
    print(f"After remove B: {list(lst)}")
    print(f"Front: {lst.front()}")
    print(f"Back: {lst.back()}")
    print(f"Popped front: {lst.pop_front()}")
    print(f"After pop: {list(lst)}")


def main() -> None:
    print("=" * 70)
    print("IntrusiveList — Demo (weak links, no ownership)")
    print("=" * 70)
    demo_manual()
    demo_decorator()
    demo_mixin()
    demo_multi_list()
    demo_ops()
    print("\n" + "=" * 70)
    print("All demos passed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
