"""API styles: manual hooks, decorator injection, and mixin."""

from __future__ import annotations

from intrusive import IntrusiveList, MemberListHook, intrusive_list_hook

from tests.models import DecoratedTask, MixinTask, Task


def test_manual_hook_style() -> None:
    lst = IntrusiveList[Task](lambda t: t.hook)
    t1, t2 = Task("A"), Task("B")
    lst.push_back(t1)
    lst.push_back(t2)
    assert list(lst) == [t1, t2]


def test_decorator_injects_named_hook() -> None:
    d1, d2 = DecoratedTask("D1"), DecoratedTask("D2")
    assert isinstance(d1.task_hook, MemberListHook)

    lst = IntrusiveList[DecoratedTask](lambda t: t.task_hook)
    lst.push_back(d1)
    lst.push_back(d2)
    assert list(lst) == [d1, d2]


def test_decorator_custom_attr_name() -> None:
    @intrusive_list_hook("queue_hook")
    class Queued:
        def __init__(self, name: str) -> None:
            self.name = name

    item = Queued("Q")
    assert isinstance(item.queue_hook, MemberListHook)

    lst = IntrusiveList[Queued](lambda q: q.queue_hook)
    lst.push_back(item)
    assert list(lst) == [item]


def test_mixin_style_with_retained_refs() -> None:
    lst = IntrusiveList[MixinTask](lambda t: t.list_hook)
    m1 = MixinTask("M1")
    m2 = MixinTask("M2")
    lst.push_back(m1)
    lst.push_back(m2)
    assert list(lst) == [m1, m2]
    assert isinstance(m1.list_hook, MemberListHook)
