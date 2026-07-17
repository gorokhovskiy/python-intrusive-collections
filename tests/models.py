"""Shared member types used across IntrusiveList tests."""

from __future__ import annotations

from intrusive import IntrusiveListMixin, MemberListHook, intrusive_list_hook


class Task:
    """Manual hook member used by most list tests."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.hook = MemberListHook()

    def __repr__(self) -> str:
        return f"Task({self.name!r})"


class Job:
    """Object with two hooks for multi-list tests."""

    def __init__(self, name: str, priority: int = 0) -> None:
        self.name = name
        self.priority = priority
        self.priority_hook = MemberListHook()
        self.work_hook = MemberListHook()

    def __repr__(self) -> str:
        return f"Job({self.name!r}, priority={self.priority})"


@intrusive_list_hook("task_hook")
class DecoratedTask:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"DecoratedTask({self.name!r})"


class MixinTask(IntrusiveListMixin):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def __repr__(self) -> str:
        return f"MixinTask({self.name!r})"
