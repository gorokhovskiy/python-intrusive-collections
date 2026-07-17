"""Edge cases and error handling."""

from __future__ import annotations

import pytest

from intrusive import IntrusiveList, MemberListHook

from tests.models import Task


def test_double_insert_raises(task_list: IntrusiveList[Task]) -> None:
    task = Task("A")
    task_list.push_back(task)
    with pytest.raises(RuntimeError, match="already in a list"):
        task_list.push_back(task)


def test_insert_requires_membership() -> None:
    lst = IntrusiveList[Task](lambda t: t.hook)
    other = IntrusiveList[Task](lambda t: t.hook)
    a, b = Task("A"), Task("B")
    other.push_back(a)

    with pytest.raises(ValueError, match="not in this list"):
        lst.insert_after(a, b)

    with pytest.raises(ValueError, match="not in this list"):
        lst.insert_before(a, b)


def test_insert_on_unlinked_object_raises(task_list: IntrusiveList[Task]) -> None:
    orphan, newbie = Task("orphan"), Task("newbie")
    with pytest.raises(ValueError, match="not in this list"):
        task_list.insert_after(orphan, newbie)


def test_remove_from_wrong_list_returns_false() -> None:
    left = IntrusiveList[Task](lambda t: t.hook)
    right = IntrusiveList[Task](lambda t: t.hook)
    task = Task("A")
    left.push_back(task)

    assert right.remove(task) is False
    assert task in left
    assert list(left) == [task]


def test_hook_cannot_rebind_to_other_owner() -> None:
    shared = MemberListHook()

    class Holder:
        def __init__(self, name: str, hook: MemberListHook) -> None:
            self.name = name
            self.hook = hook

    lst = IntrusiveList[Holder](lambda h: h.hook)
    a = Holder("A", shared)
    b = Holder("B", shared)

    lst.push_back(a)
    lst.remove(a)

    with pytest.raises(RuntimeError, match="already bound"):
        lst.push_back(b)


def test_same_owner_reinsert_after_remove_is_allowed(
    task_list: IntrusiveList[Task],
) -> None:
    task = Task("A")
    task_list.push_back(task)
    task_list.remove(task)
    task_list.push_back(task)
    assert list(task_list) == [task]


def test_cannot_insert_same_hook_into_two_lists_at_once() -> None:
    left = IntrusiveList[Task](lambda t: t.hook)
    right = IntrusiveList[Task](lambda t: t.hook)
    task = Task("A")
    left.push_back(task)

    with pytest.raises(RuntimeError, match="already in a list"):
        right.push_back(task)
