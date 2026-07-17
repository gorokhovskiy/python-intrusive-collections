"""Shared fixtures for IntrusiveList tests."""

from __future__ import annotations

import pytest

from intrusive import IntrusiveList

from tests.models import Job, Task


@pytest.fixture
def task_list() -> IntrusiveList[Task]:
    return IntrusiveList[Task]("hook")


@pytest.fixture
def weak_task_list() -> IntrusiveList[Task]:
    """Alias kept for older GC tests — same weak-only semantics."""
    return IntrusiveList[Task]("hook")


@pytest.fixture
def tasks() -> list[Task]:
    """Three named tasks with strong refs retained by the fixture."""
    return [Task("A"), Task("B"), Task("C")]


@pytest.fixture
def filled_task_list(
    task_list: IntrusiveList[Task], tasks: list[Task]
) -> tuple[IntrusiveList[Task], list[Task]]:
    task_list.extend(tasks)
    return task_list, tasks


@pytest.fixture
def filled_weak_task_list(
    weak_task_list: IntrusiveList[Task], tasks: list[Task]
) -> tuple[IntrusiveList[Task], list[Task]]:
    weak_task_list.extend(tasks)
    return weak_task_list, tasks


@pytest.fixture
def priority_list() -> IntrusiveList[Job]:
    return IntrusiveList[Job]("priority_hook")


@pytest.fixture
def work_list() -> IntrusiveList[Job]:
    return IntrusiveList[Job]("work_hook")


@pytest.fixture
def weak_priority_list() -> IntrusiveList[Job]:
    return IntrusiveList[Job]("priority_hook")


@pytest.fixture
def weak_work_list() -> IntrusiveList[Job]:
    return IntrusiveList[Job]("work_hook")


@pytest.fixture
def jobs() -> list[Job]:
    return [Job("Compile", 3), Job("Test", 1), Job("Deploy", 2)]
