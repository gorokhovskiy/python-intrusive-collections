"""Core IntrusiveList insert / remove / query operations."""

from __future__ import annotations

import pytest

from intrusive import IntrusiveList, MemberListHook

from tests.models import Task


def test_empty_list_defaults(task_list: IntrusiveList[Task]) -> None:
    assert list(task_list) == []
    assert list(reversed(task_list)) == []
    assert len(task_list) == 0
    assert task_list.size == 0
    assert task_list.empty()
    assert task_list.front() is None
    assert task_list.back() is None
    assert task_list.pop_front() is None
    assert task_list.pop_back() is None


def test_push_back_and_iteration(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, b, c = tasks

    assert list(lst) == [a, b, c]
    assert list(reversed(lst)) == [c, b, a]
    assert len(lst) == 3
    assert lst.size == 3
    assert lst.front() is a
    assert lst.back() is c
    assert not lst.empty()
    assert a in lst and b in lst and c in lst


def test_push_front(task_list: IntrusiveList[Task], tasks: list[Task]) -> None:
    a, b, _ = tasks
    task_list.push_front(a)
    task_list.push_front(b)
    assert list(task_list) == [b, a]


def test_remove_and_reinsert(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, b, c = tasks

    assert lst.remove(a) is True
    assert list(lst) == [b, c]
    assert a not in lst
    assert lst.remove(a) is False

    lst.push_front(a)
    assert list(lst) == [a, b, c]


def test_insert_after_before(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, b, c = tasks
    d, e = Task("D"), Task("E")

    lst.insert_after(a, d)
    assert list(lst) == [a, d, b, c]

    lst.insert_before(c, e)
    assert list(lst) == [a, d, b, e, c]


def test_insert_after_last_and_before_first(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, _, c = tasks
    front, back = Task("front"), Task("back")

    lst.insert_before(a, front)
    lst.insert_after(c, back)
    assert list(lst) == [front, a, tasks[1], c, back]


def test_pop_front_back(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    a, b, c = tasks

    assert lst.pop_front() is a
    assert lst.pop_back() is c
    assert list(lst) == [b]
    assert lst.pop_front() is b
    assert lst.empty()


def test_clear_keeps_objects_alive(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, tasks = filled_task_list
    lst.clear()
    assert list(lst) == []
    assert len(lst) == 0
    assert all(task not in lst for task in tasks)
    # Objects remain usable and can be re-inserted.
    for task in tasks:
        lst.push_back(task)
    assert list(lst) == tasks


def test_contains_rejects_unrelated_objects(
    task_list: IntrusiveList[Task],
) -> None:
    assert object() not in task_list
    assert Task("orphan") not in task_list


def test_repr_lists_members(
    filled_task_list: tuple[IntrusiveList[Task], list[Task]],
) -> None:
    lst, _ = filled_task_list
    text = repr(lst)
    assert text.startswith("IntrusiveList([")
    assert "Task('A')" in text
    assert "Task('C')" in text


def test_extend(task_list: IntrusiveList[Task], tasks: list[Task]) -> None:
    task_list.extend(tasks)
    assert list(task_list) == tasks
    assert len(task_list) == 3


def test_string_hook_accessor() -> None:
    lst = IntrusiveList[Task]("hook")
    task = Task("A")
    lst.push_back(task)
    assert list(lst) == [task]


def test_hook_as_object_without_accessor() -> None:
    lst: IntrusiveList[MemberListHook] = IntrusiveList()
    h1, h2 = MemberListHook(), MemberListHook()
    lst.push_back(h1)
    lst.push_back(h2)
    assert list(lst) == [h1, h2]
    assert len(lst) == 2


def test_missing_accessor_raises_for_plain_object() -> None:
    lst: IntrusiveList[object] = IntrusiveList()
    with pytest.raises(TypeError, match="no accessor provided"):
        lst.push_back(object())


def test_bad_accessor_raises() -> None:
    lst = IntrusiveList[Task](lambda t: "not-a-hook")  # type: ignore[arg-type, return-value]
    with pytest.raises(TypeError, match="did not return a MemberListHook"):
        lst.push_back(Task("A"))
