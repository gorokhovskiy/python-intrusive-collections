"""Intrusive list and set/multiset with member hooks."""

from .list import (
    IntrusiveList,
    IntrusiveListMixin,
    MemberListHook,
    intrusive_list_hook,
)
from .set import (
    IntrusiveMultiSet,
    IntrusiveSet,
    IntrusiveSetMixin,
    SetMemberHook,
    intrusive_set_hook,
)

__all__ = [
    "IntrusiveList",
    "IntrusiveListMixin",
    "MemberListHook",
    "intrusive_list_hook",
    "IntrusiveSet",
    "IntrusiveMultiSet",
    "IntrusiveSetMixin",
    "SetMemberHook",
    "intrusive_set_hook",
]

__version__ = "0.1.0"
