"""
Intrusive doubly linked list — member hook variant (pure Python).

Links and the hook→owner back-reference are always weak: collections never
keep member objects alive. Callers must retain strong references; dropping
the last one lets GC unlink the object via hook.__del__.

Objects hold MemberListHook attributes and can sit in multiple lists via
different hooks. The list auto-binds hook → owner (weakly) on first insert.
"""

from __future__ import annotations

import weakref
from operator import attrgetter
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Optional,
    TypeVar,
    Union,
)

T = TypeVar("T")


class MemberListHook:
    """
    Hook attribute that lets an object participate in an IntrusiveList.

    Stores a weak back-reference to its owner and weak neighbor links so
    neither the hook nor the list owns the parent object.
    """

    __slots__ = (
        "_owner_ref",
        "_next",
        "_prev",
        "_list",
        "__weakref__",
    )

    def __init__(self) -> None:
        self._owner_ref: Optional[weakref.ref[Any]] = None
        self._next: Optional[weakref.ref[MemberListHook]] = None
        self._prev: Optional[weakref.ref[MemberListHook]] = None
        self._list: Optional[weakref.ref[IntrusiveList[Any]]] = None

    def _list_obj(self) -> Optional[IntrusiveList[Any]]:
        return self._list() if self._list is not None else None

    def _is_linked(self) -> bool:
        return self._list_obj() is not None

    def _get_next(self) -> Optional[MemberListHook]:
        return self._next() if self._next is not None else None

    def _get_prev(self) -> Optional[MemberListHook]:
        return self._prev() if self._prev is not None else None

    def _get_owner(self) -> Optional[Any]:
        return self._owner_ref() if self._owner_ref is not None else None

    def _clear_links(self) -> None:
        self._next = None
        self._prev = None
        self._list = None

    def _unlink(self) -> bool:
        if not self._is_linked():
            self._clear_links()
            return False

        list_obj = self._list_obj()
        if list_obj is not None:
            list_obj._remove_node(self)
        else:
            self._clear_links()
        return True

    def __del__(self) -> None:
        try:
            self._unlink()
        except Exception:
            pass

    def __repr__(self) -> str:
        owner = self._get_owner()
        linked = "linked" if self._is_linked() else "unlinked"
        return f"MemberListHook(owner={owner!r}, {linked})"


class _SentinelNode(MemberListHook):
    """Circular sentinel that anchors the list."""

    __slots__ = ("_owner_list",)

    def __init__(self, owner_list: IntrusiveList[Any]) -> None:
        super().__init__()
        self._owner_list = owner_list
        self._next = weakref.ref(self)
        self._prev = weakref.ref(self)

    def __del__(self) -> None:
        pass


class IntrusiveList(Generic[T]):
    """
    Intrusive doubly linked list using member hooks.

    Never owns members: all links are weak. Keep strong references to
    inserted objects yourself; GC auto-unlinks when the last strong ref drops.

    Usage:
        lst = IntrusiveList[Task]("hook")
        task = Task("A")  # retain this
        lst.push_back(task)
    """

    def __init__(
        self,
        hook_accessor: Optional[Union[str, Callable[[T], MemberListHook]]] = None,
    ) -> None:
        if isinstance(hook_accessor, str):
            self._hook_accessor = attrgetter(hook_accessor)
        else:
            self._hook_accessor = hook_accessor

        self._sentinel: _SentinelNode = _SentinelNode(self)
        self._size: int = 0

    def _get_hook(self, obj: T) -> MemberListHook:
        if self._hook_accessor is None:
            if isinstance(obj, MemberListHook):
                return obj
            raise TypeError(
                f"Object {obj!r} is not a MemberListHook and no accessor provided"
            )

        hook = self._hook_accessor(obj)
        if not isinstance(hook, MemberListHook):
            raise TypeError(
                f"Hook accessor did not return a MemberListHook, got {type(hook)}"
            )
        return hook

    def _get_object_from_hook(self, hook: MemberListHook) -> Optional[T]:
        if isinstance(hook, _SentinelNode):
            return None
        return hook._get_owner()  # type: ignore[return-value]

    def _bind_hook_to_owner(self, hook: MemberListHook, owner: T) -> None:
        bound = hook._get_owner()
        if bound is None and hook._owner_ref is None:
            hook._owner_ref = weakref.ref(owner)
        elif bound is None and hook._owner_ref is not None:
            # Sticky identity after owner was collected — treat as unbound.
            hook._owner_ref = weakref.ref(owner)
        elif bound is not None and bound is not owner:
            raise RuntimeError(
                f"Hook already bound to different object {bound!r}. "
                f"Each MemberListHook instance can only belong to one object."
            )
        elif hook._owner_ref is None:
            hook._owner_ref = weakref.ref(owner)

    def _require_in_this_list(self, hook: MemberListHook) -> None:
        if hook._list_obj() is not self:
            raise ValueError("Existing object is not in this list")

    def _link(
        self, hook: MemberListHook, prev_hook: MemberListHook, next_hook: MemberListHook
    ) -> None:
        hook._prev = weakref.ref(prev_hook)
        hook._next = weakref.ref(next_hook)
        hook._list = weakref.ref(self)

        prev_hook._next = weakref.ref(hook)
        next_hook._prev = weakref.ref(hook)

    def _insert_between(
        self, obj: T, prev_hook: MemberListHook, next_hook: MemberListHook
    ) -> None:
        hook = self._get_hook(obj)

        if hook._is_linked():
            raise RuntimeError(f"Object is already in a list: {obj!r}")

        self._bind_hook_to_owner(hook, obj)
        self._link(hook, prev_hook, next_hook)
        self._size += 1

    def push_front(self, obj: T) -> None:
        """Insert at front. O(1)"""
        self._insert_between(
            obj, self._sentinel, self._sentinel._get_next() or self._sentinel
        )

    def push_back(self, obj: T) -> None:
        """Insert at back. O(1)"""
        self._insert_between(
            obj, self._sentinel._get_prev() or self._sentinel, self._sentinel
        )

    def extend(self, objects: Iterable[T]) -> None:
        """Append many objects."""
        for obj in objects:
            hook = self._get_hook(obj)
            if hook._is_linked():
                raise RuntimeError(f"Object is already in a list: {obj!r}")
            self._bind_hook_to_owner(hook, obj)
            prev_hook = self._sentinel._get_prev() or self._sentinel
            self._link(hook, prev_hook, self._sentinel)
            self._size += 1

    def insert_after(self, existing_obj: T, new_obj: T) -> None:
        """Insert new_obj after existing_obj. O(1)"""
        existing_hook = self._get_hook(existing_obj)
        self._require_in_this_list(existing_hook)
        next_hook = existing_hook._get_next() or self._sentinel
        self._insert_between(new_obj, existing_hook, next_hook)

    def insert_before(self, existing_obj: T, new_obj: T) -> None:
        """Insert new_obj before existing_obj. O(1)"""
        existing_hook = self._get_hook(existing_obj)
        self._require_in_this_list(existing_hook)
        prev_hook = existing_hook._get_prev() or self._sentinel
        self._insert_between(new_obj, prev_hook, existing_hook)

    def _remove_node(self, hook: MemberListHook) -> None:
        prev_hook = hook._get_prev() or self._sentinel
        next_hook = hook._get_next() or self._sentinel

        prev_hook._next = weakref.ref(next_hook)
        next_hook._prev = weakref.ref(prev_hook)

        hook._clear_links()
        self._size = max(0, self._size - 1)

    def remove(self, obj: T) -> bool:
        """Remove object from list. O(1). Returns True if it was present."""
        hook = self._get_hook(obj)
        if hook._list_obj() is not self:
            return False
        self._remove_node(hook)
        return True

    def pop_front(self) -> Optional[T]:
        """Remove and return first live object, or None if empty."""
        while True:
            first = self._sentinel._get_next()
            if first is None or isinstance(first, _SentinelNode):
                return None
            obj = self._get_object_from_hook(first)
            self._remove_node(first)
            if obj is not None:
                return obj

    def pop_back(self) -> Optional[T]:
        """Remove and return last live object, or None if empty."""
        while True:
            last = self._sentinel._get_prev()
            if last is None or isinstance(last, _SentinelNode):
                return None
            obj = self._get_object_from_hook(last)
            self._remove_node(last)
            if obj is not None:
                return obj

    def __contains__(self, obj: object) -> bool:
        try:
            hook = self._get_hook(obj)  # type: ignore[arg-type]
        except (TypeError, AttributeError):
            return False
        return hook._list_obj() is self

    def __iter__(self) -> Iterator[T]:
        """Iterate live owners, skipping nodes whose owners were collected."""
        current = self._sentinel._get_next()
        while current is not None and not isinstance(current, _SentinelNode):
            nxt = current._get_next()
            obj = self._get_object_from_hook(current)
            if obj is not None:
                yield obj
            current = nxt

    def __reversed__(self) -> Iterator[T]:
        current = self._sentinel._get_prev()
        while current is not None and not isinstance(current, _SentinelNode):
            prev = current._get_prev()
            obj = self._get_object_from_hook(current)
            if obj is not None:
                yield obj
            current = prev

    def __len__(self) -> int:
        return self._size

    @property
    def size(self) -> int:
        return self._size

    def front(self) -> Optional[T]:
        current = self._sentinel._get_next()
        while current is not None and not isinstance(current, _SentinelNode):
            obj = self._get_object_from_hook(current)
            if obj is not None:
                return obj
            current = current._get_next()
        return None

    def back(self) -> Optional[T]:
        current = self._sentinel._get_prev()
        while current is not None and not isinstance(current, _SentinelNode):
            obj = self._get_object_from_hook(current)
            if obj is not None:
                return obj
            current = current._get_prev()
        return None

    def empty(self) -> bool:
        return self.front() is None

    def clear(self) -> None:
        current = self._sentinel._get_next()
        while current is not None and not isinstance(current, _SentinelNode):
            nxt = current._get_next()
            current._clear_links()
            current = nxt
        self._sentinel._next = weakref.ref(self._sentinel)
        self._sentinel._prev = weakref.ref(self._sentinel)
        self._size = 0

    def compact(self) -> int:
        """
        Remove nodes whose owners are gone.

        Returns the number of nodes removed. Usually needed only if hooks
        lingered after GC before __del__ ran.
        """
        removed = 0
        current = self._sentinel._get_next()
        while current is not None and not isinstance(current, _SentinelNode):
            nxt = current._get_next()
            if self._get_object_from_hook(current) is None:
                self._remove_node(current)
                removed += 1
            current = nxt
        return removed

    def __repr__(self) -> str:
        items = list(self)
        return f"IntrusiveList([{', '.join(repr(x) for x in items)}])"


def intrusive_list_hook(attr_name: str = "list_hook"):
    """
    Class decorator that injects a MemberListHook attribute.

    Usage:
        @intrusive_list_hook("my_hook")
        class Task:
            def __init__(self, name):
                self.name = name
    """

    def decorator(cls):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            object.__setattr__(self, attr_name, MemberListHook())
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator


class IntrusiveListMixin:
    """
    Mixin that provides a default list_hook.

    Usage:
        class Task(IntrusiveListMixin):
            def __init__(self, name):
                super().__init__()
                self.name = name
    """

    def __init__(self) -> None:
        self.list_hook: MemberListHook = MemberListHook()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"
