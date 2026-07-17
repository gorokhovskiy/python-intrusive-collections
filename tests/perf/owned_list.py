"""Baseline owned doubly linked list (list owns nodes + values)."""

from __future__ import annotations

from typing import Generic, Iterator, Optional, TypeVar

T = TypeVar("T")


class OwnedNode(Generic[T]):
    __slots__ = ("value", "next", "prev")

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: Optional[OwnedNode[T]] = None
        self.prev: Optional[OwnedNode[T]] = None


class OwnedDoublyLinkedList(Generic[T]):
    """
    Classic doubly linked list where the list owns nodes.

    Nodes hold strong references to values, so inserted objects stay
    alive for as long as they remain in the list.
    """

    __slots__ = ("_head", "_tail", "_size")

    def __init__(self) -> None:
        self._head: Optional[OwnedNode[T]] = None
        self._tail: Optional[OwnedNode[T]] = None
        self._size = 0

    def push_back(self, value: T) -> OwnedNode[T]:
        node = OwnedNode(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            node.prev = self._tail
            self._tail.next = node
            self._tail = node
        self._size += 1
        return node

    def push_front(self, value: T) -> OwnedNode[T]:
        node = OwnedNode(value)
        if self._head is None:
            self._head = self._tail = node
        else:
            node.next = self._head
            self._head.prev = node
            self._head = node
        self._size += 1
        return node

    def remove_node(self, node: OwnedNode[T]) -> None:
        prev_node = node.prev
        next_node = node.next
        if prev_node is None:
            self._head = next_node
        else:
            prev_node.next = next_node
        if next_node is None:
            self._tail = prev_node
        else:
            next_node.prev = prev_node
        node.prev = None
        node.next = None
        self._size -= 1

    def pop_front(self) -> Optional[T]:
        if self._head is None:
            return None
        node = self._head
        value = node.value
        self.remove_node(node)
        return value

    def pop_back(self) -> Optional[T]:
        if self._tail is None:
            return None
        node = self._tail
        value = node.value
        self.remove_node(node)
        return value

    def clear(self) -> None:
        self._head = None
        self._tail = None
        self._size = 0

    def __iter__(self) -> Iterator[T]:
        current = self._head
        while current is not None:
            yield current.value
            current = current.next

    def __len__(self) -> int:
        return self._size

    def empty(self) -> bool:
        return self._size == 0
