"""Unit tests for MemberListHook."""

from __future__ import annotations

from intrusive import IntrusiveList, MemberListHook

from tests.models import Task


def test_new_hook_is_unlinked() -> None:
    hook = MemberListHook()
    assert hook._is_linked() is False
    assert hook._get_owner() is None
    assert hook._get_next() is None
    assert hook._get_prev() is None
    assert "unlinked" in repr(hook)


def test_hook_binds_owner_on_first_insert() -> None:
    lst = IntrusiveList[Task](lambda t: t.hook)
    task = Task("A")
    lst.push_back(task)

    assert task.hook._get_owner() is task
    assert task.hook._is_linked() is True
    assert "linked" in repr(task.hook)


def test_hook_owner_survives_remove() -> None:
    lst = IntrusiveList[Task](lambda t: t.hook)
    task = Task("A")
    lst.push_back(task)
    lst.remove(task)

    assert task.hook._is_linked() is False
    assert task.hook._get_owner() is task


def test_unlink_when_not_linked_is_noop() -> None:
    hook = MemberListHook()
    assert hook._unlink() is False
