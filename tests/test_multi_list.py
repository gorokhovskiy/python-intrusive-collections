"""Same object participating in multiple IntrusiveLists."""

from __future__ import annotations

import gc

from intrusive import IntrusiveList

from tests.models import Job


def test_same_object_in_two_lists(
    priority_list: IntrusiveList[Job],
    work_list: IntrusiveList[Job],
    jobs: list[Job],
) -> None:
    j1, j2, j3 = jobs

    priority_list.extend(jobs)
    work_list.push_back(j2)
    work_list.push_back(j3)
    work_list.push_back(j1)

    assert list(priority_list) == [j1, j2, j3]
    assert list(work_list) == [j2, j3, j1]


def test_delete_removes_from_all_lists(
    priority_list: IntrusiveList[Job],
    work_list: IntrusiveList[Job],
    jobs: list[Job],
) -> None:
    j1, j2, j3 = jobs

    priority_list.extend(jobs)
    work_list.push_back(j2)
    work_list.push_back(j3)
    work_list.push_back(j1)

    jobs.remove(j2)
    del j2
    gc.collect()

    assert list(priority_list) == [j1, j3]
    assert list(work_list) == [j3, j1]
    priority_list.compact()
    work_list.compact()
    assert len(priority_list) == 2
    assert len(work_list) == 2


def test_remove_from_one_list_keeps_other(
    priority_list: IntrusiveList[Job],
    work_list: IntrusiveList[Job],
    jobs: list[Job],
) -> None:
    j1, j2, j3 = jobs
    for job in jobs:
        priority_list.push_back(job)
        work_list.push_back(job)

    assert priority_list.remove(j2) is True
    assert list(priority_list) == [j1, j3]
    assert list(work_list) == [j1, j2, j3]
    assert j2 in work_list
    assert j2 not in priority_list


def test_move_between_lists_via_remove_and_push() -> None:
    left = IntrusiveList[Job]("priority_hook")
    right = IntrusiveList[Job]("priority_hook")
    job = Job("migrant", 1)

    left.push_back(job)
    assert job in left

    left.remove(job)
    right.push_back(job)

    assert job not in left
    assert list(right) == [job]
