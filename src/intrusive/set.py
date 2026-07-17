"""
Intrusive ordered set / multiset — shared red-black tree (pure Python).

Links and hook→owner back-references are always weak: collections never
keep member objects alive. Callers must retain strong references; GC
auto-unlinks when the last strong ref drops.

IntrusiveSet: unique keys.
IntrusiveMultiSet: duplicate keys allowed (equal_range / count).
"""
from __future__ import annotations

import weakref
from operator import attrgetter
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    Optional,
    Type,
    TypeVar,
    Union,
)

K = TypeVar("K")
T = TypeVar("T")

_RED = True
_BLACK = False


class SetMemberHook(Generic[K]):
    """
    Hook for intrusive set/multiset membership. Holds an immutable key.

    Key is set on insert; the only mutation path is change_key(), which
    rebalances via remove + reinsert.
    """

    __slots__ = (
        "_key",
        "_key_type",
        "_owner_ref",
        "_left",
        "_right",
        "_parent",
        "_color",
        "_container",
        "__weakref__",
    )

    def __init__(self, key_type: Optional[Type[K]] = None) -> None:
        self._key: Optional[K] = None
        self._key_type: Optional[Type[K]] = key_type
        self._owner_ref: Optional[weakref.ref[Any]] = None
        self._left: Any = None
        self._right: Any = None
        self._parent: Any = None
        self._color: bool = _BLACK
        self._container: Any = None

    @property
    def key(self) -> Optional[K]:
        return self._key

    def _deref(self, cell: Any) -> Any:
        if cell is None:
            return None
        return cell()

    def _container_obj(self) -> Optional[_IntrusiveRBTreeBase[Any, Any]]:
        return self._deref(self._container)

    def _is_linked(self) -> bool:
        return self._container_obj() is not None

    def _get_left(self) -> Optional[SetMemberHook[K]]:
        return self._deref(self._left)

    def _get_right(self) -> Optional[SetMemberHook[K]]:
        return self._deref(self._right)

    def _get_parent(self) -> Optional[SetMemberHook[K]]:
        return self._deref(self._parent)

    def _get_owner(self) -> Optional[Any]:
        if self._owner_ref is None:
            return None
        return self._owner_ref()

    def _validate_key(self, key: K) -> None:
        if self._key_type is not None and not isinstance(key, self._key_type):
            raise TypeError(
                f"Key must be of type {self._key_type.__name__}, "
                f"got {type(key).__name__}"
            )

    def change_key(self, new_key: K) -> None:
        """Update key; if linked, atomically reinsert at the new position."""
        self._validate_key(new_key)

        if not self._is_linked():
            self._key = new_key
            return

        container = self._container_obj()
        if container is None:
            self._key = new_key
            return

        container._reinsert_with_new_key(self, new_key)

    def _clear_links(self) -> None:
        self._left = None
        self._right = None
        self._parent = None
        self._container = None
        self._key = None
        self._color = _BLACK

    def _unlink(self) -> bool:
        if not self._is_linked():
            self._clear_links()
            return False
        container = self._container_obj()
        if container is not None:
            container._remove_node(self)
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
        return f"SetMemberHook(key={self._key!r}, {linked}, owner={owner!r})"


class _NilNode(SetMemberHook[Any]):
    """Black sentinel leaf for the red-black tree."""

    __slots__ = ("_owner_tree",)

    def __init__(self, owner_tree: _IntrusiveRBTreeBase[Any, Any]) -> None:
        object.__setattr__(self, "_key", None)
        object.__setattr__(self, "_key_type", None)
        object.__setattr__(self, "_owner_ref", None)
        object.__setattr__(self, "_color", _BLACK)
        object.__setattr__(self, "_owner_tree", owner_tree)
        object.__setattr__(self, "_container", None)
        object.__setattr__(self, "_left", None)
        object.__setattr__(self, "_right", None)
        object.__setattr__(self, "_parent", None)

    def __del__(self) -> None:
        pass


class _IntrusiveRBTreeBase(Generic[K, T]):
    """Shared red-black tree + hook linking for set and multiset."""

    _unique_keys: bool = True
    _collection_name: str = "IntrusiveRBTree"

    def __init__(
        self,
        hook_accessor: Union[str, Callable[[T], SetMemberHook[K]]],
        key_extractor: Optional[Callable[[T], K]] = None,
    ) -> None:
        if isinstance(hook_accessor, str):
            self._hook_accessor: Callable[[T], SetMemberHook[K]] = attrgetter(
                hook_accessor
            )
        else:
            self._hook_accessor = hook_accessor

        self._key_extractor = key_extractor
        self._nil: _NilNode = _NilNode(self)
        self._root: SetMemberHook[K] = self._nil
        self._size: int = 0

    def _store(self, obj: Any) -> Any:
        if obj is None:
            return None
        return weakref.ref(obj)

    def _is_nil(self, node: Optional[SetMemberHook[K]]) -> bool:
        return node is None or node is self._nil or isinstance(node, _NilNode)

    def _get_hook(self, obj: T) -> SetMemberHook[K]:
        hook = self._hook_accessor(obj)
        if not isinstance(hook, SetMemberHook):
            raise TypeError(
                f"Accessor did not return SetMemberHook, got {type(hook)}"
            )
        return hook

    def _get_object(self, hook: SetMemberHook[K]) -> Optional[T]:
        if self._is_nil(hook):
            return None
        return hook._get_owner()  # type: ignore[return-value]

    def _resolve_key(self, obj: T, key: Optional[K]) -> K:
        if key is not None:
            return key
        if self._key_extractor is not None:
            return self._key_extractor(obj)
        raise ValueError("Key must be provided or key_extractor must be set")

    def _bind_hook(self, hook: SetMemberHook[K], obj: T, key: K) -> None:
        bound = hook._get_owner()
        if bound is None:
            hook._owner_ref = weakref.ref(obj)
        elif bound is not obj:
            raise RuntimeError("Hook already bound to different object")

        hook._validate_key(key)
        hook._key = key

    def _set_parent(self, node: SetMemberHook[K], parent: SetMemberHook[K]) -> None:
        node._parent = self._store(parent)

    def _left_rotate(self, x: SetMemberHook[K]) -> None:
        y = x._get_right()
        if self._is_nil(y) or y is None:
            return

        y_left = y._get_left() or self._nil
        x._right = self._store(y_left)
        if not self._is_nil(y_left):
            y_left._parent = self._store(x)

        x_parent = x._get_parent() or self._nil
        y._parent = self._store(x_parent)

        if self._is_nil(x_parent):
            self._root = y
        elif x is x_parent._get_left():
            x_parent._left = self._store(y)
        else:
            x_parent._right = self._store(y)

        y._left = self._store(x)
        x._parent = self._store(y)

    def _right_rotate(self, y: SetMemberHook[K]) -> None:
        x = y._get_left()
        if self._is_nil(x) or x is None:
            return

        x_right = x._get_right() or self._nil
        y._left = self._store(x_right)
        if not self._is_nil(x_right):
            x_right._parent = self._store(y)

        y_parent = y._get_parent() or self._nil
        x._parent = self._store(y_parent)

        if self._is_nil(y_parent):
            self._root = x
        elif y is y_parent._get_right():
            y_parent._right = self._store(x)
        else:
            y_parent._left = self._store(x)

        x._right = self._store(y)
        y._parent = self._store(x)

    def _insert_fixup(self, z: SetMemberHook[K]) -> None:
        while True:
            parent = z._get_parent()
            if self._is_nil(parent) or parent is None or parent._color == _BLACK:
                break

            grandparent = parent._get_parent()
            if self._is_nil(grandparent) or grandparent is None:
                break

            if parent is grandparent._get_left():
                uncle = grandparent._get_right() or self._nil
                if not self._is_nil(uncle) and uncle._color == _RED:
                    parent._color = _BLACK
                    uncle._color = _BLACK
                    grandparent._color = _RED
                    z = grandparent
                else:
                    if z is parent._get_right():
                        z = parent
                        self._left_rotate(z)
                        parent = z._get_parent()
                        grandparent = (
                            parent._get_parent() if parent is not None else None
                        )
                    if parent is not None:
                        parent._color = _BLACK
                    if grandparent is not None and not self._is_nil(grandparent):
                        grandparent._color = _RED
                        self._right_rotate(grandparent)
            else:
                uncle = grandparent._get_left() or self._nil
                if not self._is_nil(uncle) and uncle._color == _RED:
                    parent._color = _BLACK
                    uncle._color = _BLACK
                    grandparent._color = _RED
                    z = grandparent
                else:
                    if z is parent._get_left():
                        z = parent
                        self._right_rotate(z)
                        parent = z._get_parent()
                        grandparent = (
                            parent._get_parent() if parent is not None else None
                        )
                    if parent is not None:
                        parent._color = _BLACK
                    if grandparent is not None and not self._is_nil(grandparent):
                        grandparent._color = _RED
                        self._left_rotate(grandparent)

        self._root._color = _BLACK

    def _find_hook(self, key: K) -> SetMemberHook[K]:
        """Return any node with equal key, or nil."""
        current: SetMemberHook[K] = self._root
        while not self._is_nil(current):
            assert current._key is not None
            if key == current._key:
                return current
            if key < current._key:
                current = current._get_left() or self._nil
            else:
                current = current._get_right() or self._nil
        return self._nil

    def _lower_bound_hook(self, key: K) -> SetMemberHook[K]:
        """First node with key >= key, or nil."""
        result: SetMemberHook[K] = self._nil
        current: SetMemberHook[K] = self._root
        while not self._is_nil(current):
            assert current._key is not None
            if current._key >= key:
                result = current
                current = current._get_left() or self._nil
            else:
                current = current._get_right() or self._nil
        return result

    def _upper_bound_hook(self, key: K) -> SetMemberHook[K]:
        """First node with key > key, or nil."""
        result: SetMemberHook[K] = self._nil
        current: SetMemberHook[K] = self._root
        while not self._is_nil(current):
            assert current._key is not None
            if current._key > key:
                result = current
                current = current._get_left() or self._nil
            else:
                current = current._get_right() or self._nil
        return result

    def _successor(self, node: SetMemberHook[K]) -> SetMemberHook[K]:
        right = node._get_right() or self._nil
        if not self._is_nil(right):
            return self._minimum(right)
        current = node
        parent = current._get_parent() or self._nil
        while not self._is_nil(parent) and current is parent._get_right():
            current = parent
            parent = parent._get_parent() or self._nil
        return parent

    def _transplant(self, u: SetMemberHook[K], v: SetMemberHook[K]) -> None:
        u_parent = u._get_parent() or self._nil
        if self._is_nil(u_parent):
            self._root = v
        elif u is u_parent._get_left():
            u_parent._left = self._store(v)
        else:
            u_parent._right = self._store(v)

        v._parent = self._store(u_parent)

    def _minimum(self, node: SetMemberHook[K]) -> SetMemberHook[K]:
        current = node
        while True:
            left = current._get_left() or self._nil
            if self._is_nil(left):
                return current
            current = left

    def _maximum(self, node: SetMemberHook[K]) -> SetMemberHook[K]:
        current = node
        while True:
            right = current._get_right() or self._nil
            if self._is_nil(right):
                return current
            current = right

    def _delete_fixup(self, x: SetMemberHook[K]) -> None:
        while x is not self._root and x._color == _BLACK:
            parent = x._get_parent()
            if parent is None or self._is_nil(parent):
                break

            if x is parent._get_left():
                w = parent._get_right() or self._nil
                if not self._is_nil(w) and w._color == _RED:
                    w._color = _BLACK
                    parent._color = _RED
                    self._left_rotate(parent)
                    w = parent._get_right() or self._nil

                w_left = (
                    (w._get_left() or self._nil) if not self._is_nil(w) else self._nil
                )
                w_right = (
                    (w._get_right() or self._nil) if not self._is_nil(w) else self._nil
                )
                if (self._is_nil(w_left) or w_left._color == _BLACK) and (
                    self._is_nil(w_right) or w_right._color == _BLACK
                ):
                    if not self._is_nil(w):
                        w._color = _RED
                    x = parent
                else:
                    if self._is_nil(w_right) or w_right._color == _BLACK:
                        if not self._is_nil(w_left):
                            w_left._color = _BLACK
                        if not self._is_nil(w):
                            w._color = _RED
                            self._right_rotate(w)
                        w = parent._get_right() or self._nil
                    if not self._is_nil(w):
                        w._color = parent._color
                        parent._color = _BLACK
                        wr = w._get_right() or self._nil
                        if not self._is_nil(wr):
                            wr._color = _BLACK
                        self._left_rotate(parent)
                    x = self._root
            else:
                w = parent._get_left() or self._nil
                if not self._is_nil(w) and w._color == _RED:
                    w._color = _BLACK
                    parent._color = _RED
                    self._right_rotate(parent)
                    w = parent._get_left() or self._nil

                w_right = (
                    (w._get_right() or self._nil) if not self._is_nil(w) else self._nil
                )
                w_left = (
                    (w._get_left() or self._nil) if not self._is_nil(w) else self._nil
                )
                if (self._is_nil(w_right) or w_right._color == _BLACK) and (
                    self._is_nil(w_left) or w_left._color == _BLACK
                ):
                    if not self._is_nil(w):
                        w._color = _RED
                    x = parent
                else:
                    if self._is_nil(w_left) or w_left._color == _BLACK:
                        if not self._is_nil(w_right):
                            w_right._color = _BLACK
                        if not self._is_nil(w):
                            w._color = _RED
                            self._left_rotate(w)
                        w = parent._get_left() or self._nil
                    if not self._is_nil(w):
                        w._color = parent._color
                        parent._color = _BLACK
                        wl = w._get_left() or self._nil
                        if not self._is_nil(wl):
                            wl._color = _BLACK
                        self._right_rotate(parent)
                    x = self._root

        x._color = _BLACK

    def _remove_node(self, z: SetMemberHook[K]) -> None:
        y = z
        y_original_color = y._color
        left = z._get_left() or self._nil
        right = z._get_right() or self._nil

        if self._is_nil(left):
            x = right
            self._transplant(z, x)
        elif self._is_nil(right):
            x = left
            self._transplant(z, x)
        else:
            y = self._minimum(right)
            y_original_color = y._color
            x = y._get_right() or self._nil

            if y._get_parent() is z:
                x._parent = self._store(y)
            else:
                self._transplant(y, x)
                y._right = self._store(right)
                if not self._is_nil(right):
                    right._parent = self._store(y)

            self._transplant(z, y)
            y._left = self._store(left)
            if not self._is_nil(left):
                left._parent = self._store(y)
            y._color = z._color

        if y_original_color == _BLACK:
            self._delete_fixup(x)

        z._clear_links()
        self._size = max(0, self._size - 1)

        if self._size == 0:
            self._root = self._nil

    def _insert_node(self, obj: T, actual_key: K) -> bool:
        hook = self._get_hook(obj)
        if hook._is_linked():
            return False
        if self._unique_keys and not self._is_nil(self._find_hook(actual_key)):
            return False

        self._bind_hook(hook, obj, actual_key)

        y: SetMemberHook[K] = self._nil
        x: SetMemberHook[K] = self._root
        while not self._is_nil(x):
            y = x
            assert x._key is not None
            if actual_key < x._key:
                x = x._get_left() or self._nil
            else:
                # Equal keys go right (multiset); unique path never sees equals.
                x = x._get_right() or self._nil

        self._set_parent(hook, y)
        if self._is_nil(y):
            self._root = hook
        else:
            assert y._key is not None
            if actual_key < y._key:
                y._left = self._store(hook)
            else:
                y._right = self._store(hook)

        hook._left = self._store(self._nil)
        hook._right = self._store(self._nil)
        hook._color = _RED
        hook._container = self._store(self)

        self._size += 1
        self._insert_fixup(hook)
        return True

    def _reinsert_with_new_key(self, hook: SetMemberHook[K], new_key: K) -> None:
        if hook._key == new_key:
            return

        obj = hook._get_owner()
        if obj is None:
            hook._key = new_key
            return

        if self._unique_keys:
            existing = self._find_hook(new_key)
            if not self._is_nil(existing):
                raise ValueError(f"Key {new_key!r} already present in set")

        self._remove_node(hook)
        if not self._insert_node(obj, new_key):  # type: ignore[arg-type]
            hook._key = new_key
            raise RuntimeError("Failed to reinsert after change_key")

    def insert(self, obj: T, key: Optional[K] = None) -> bool:
        actual_key = self._resolve_key(obj, key)
        return self._insert_node(obj, actual_key)

    def remove(self, obj: T) -> bool:
        hook = self._get_hook(obj)
        if hook._container_obj() is not self:
            return False
        self._remove_node(hook)
        return True

    def find(self, key: K) -> Optional[T]:
        hook = self._find_hook(key)
        if self._is_nil(hook):
            return None
        return self._get_object(hook)

    def contains(self, obj: T) -> bool:
        try:
            hook = self._get_hook(obj)
        except (TypeError, AttributeError):
            return False
        return hook._container_obj() is self

    def __contains__(self, obj: object) -> bool:
        try:
            return self.contains(obj)  # type: ignore[arg-type]
        except (TypeError, AttributeError):
            return False

    def _inorder(self, node: SetMemberHook[K]) -> Iterator[T]:
        if self._is_nil(node):
            return
        left = node._get_left() or self._nil
        if not self._is_nil(left):
            yield from self._inorder(left)
        obj = self._get_object(node)
        if obj is not None:
            yield obj
        right = node._get_right() or self._nil
        if not self._is_nil(right):
            yield from self._inorder(right)

    def _reverse_inorder(self, node: SetMemberHook[K]) -> Iterator[T]:
        if self._is_nil(node):
            return
        right = node._get_right() or self._nil
        if not self._is_nil(right):
            yield from self._reverse_inorder(right)
        obj = self._get_object(node)
        if obj is not None:
            yield obj
        left = node._get_left() or self._nil
        if not self._is_nil(left):
            yield from self._reverse_inorder(left)

    def __iter__(self) -> Iterator[T]:
        yield from self._inorder(self._root)

    def __reversed__(self) -> Iterator[T]:
        yield from self._reverse_inorder(self._root)

    def __len__(self) -> int:
        return self._size

    @property
    def size(self) -> int:
        return self._size

    def empty(self) -> bool:
        return self._root is self._nil or self._size == 0

    def min(self) -> Optional[T]:
        if self.empty():
            return None
        return self._get_object(self._minimum(self._root))

    def max(self) -> Optional[T]:
        if self.empty():
            return None
        return self._get_object(self._maximum(self._root))

    def clear(self) -> None:
        for obj in list(self):
            self.remove(obj)

    def compact(self) -> int:
        """Remove nodes whose owners are gone. Returns how many were removed."""
        dead: list[SetMemberHook[K]] = []

        def walk(node: SetMemberHook[K]) -> None:
            if self._is_nil(node):
                return
            left = node._get_left() or self._nil
            right = node._get_right() or self._nil
            walk(left)
            walk(right)
            if self._get_object(node) is None:
                dead.append(node)

        walk(self._root)
        for hook in dead:
            if hook._container_obj() is self:
                self._remove_node(hook)
        return len(dead)

    def __repr__(self) -> str:
        items = list(self)
        return f"{self._collection_name}([{', '.join(repr(x) for x in items)}])"


class IntrusiveSet(_IntrusiveRBTreeBase[K, T]):
    """Intrusive ordered set — keys are unique."""

    _unique_keys = True
    _collection_name = "IntrusiveSet"


class IntrusiveMultiSet(_IntrusiveRBTreeBase[K, T]):
    """
    Intrusive ordered multiset — duplicate keys allowed.

    Equal keys are stored in sorted order (new equals go to the right).
    Extra APIs: count, equal_range, lower_bound, upper_bound.
    """

    _unique_keys = False
    _collection_name = "IntrusiveMultiSet"

    def count(self, key: K) -> int:
        return sum(1 for _ in self.equal_range(key))

    def lower_bound(self, key: K) -> Optional[T]:
        """First object with key >= key, or None."""
        hook = self._lower_bound_hook(key)
        if self._is_nil(hook):
            return None
        return self._get_object(hook)

    def upper_bound(self, key: K) -> Optional[T]:
        """First object with key > key, or None."""
        hook = self._upper_bound_hook(key)
        if self._is_nil(hook):
            return None
        return self._get_object(hook)

    def equal_range(self, key: K) -> Iterator[T]:
        """Yield all objects with the given key, in tree order."""
        items: list[T] = []
        start = self._lower_bound_hook(key)
        end = self._upper_bound_hook(key)
        current = start
        while not self._is_nil(current) and current is not end:
            obj = self._get_object(current)
            nxt = self._successor(current)
            if obj is not None:
                items.append(obj)
            current = nxt
        yield from items


def intrusive_set_hook(
    key_type: Optional[Type[Any]] = None, attr_name: str = "set_hook"
):
    """Class decorator that injects a SetMemberHook attribute."""

    def decorator(cls):
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            object.__setattr__(self, attr_name, SetMemberHook(key_type))
            original_init(self, *args, **kwargs)

        cls.__init__ = new_init
        return cls

    return decorator


class IntrusiveSetMixin(Generic[K]):
    """Mixin providing a default set_hook."""

    def __init__(self) -> None:
        self.set_hook: SetMemberHook[K] = SetMemberHook()
