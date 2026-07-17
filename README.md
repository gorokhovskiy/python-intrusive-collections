# intrusive

Intrusive collections for Python — objects carry their own hooks and can sit in several lists or trees at once.

Inspired by [Boost.Intrusive](https://www.boost.org/doc/libs/release/doc/html/intrusive.html). A pure-Python port will not match C++ speed, but it makes the *intent* obvious when one object must belong to multiple collections simultaneously: each membership is an explicit hook on the object, erase is O(1) given the object, and you avoid parallel “object ↔ node” maps that drift out of sync.

## Why intrusive?

| Typical approach | Intrusive approach |
|------------------|--------------------|
| Separate node per list + lookup maps | Hook attributes on the object |
| Search to remove from a list | `list.remove(obj)` / `set.remove(obj)` in O(1) / O(log n) |
| One object identity, many containers | Same object, different hooks |

Use this when clarity and multi-collection membership matter more than squeezing every nanosecond out of a single hot queue (for that, prefer `collections.deque` or a plain list).

## Install

```bash
pip install -e ".[dev]"   # from a clone
```

Requires Python 3.10+.

## Quick start — list

```python
from intrusive import IntrusiveList, MemberListHook

class Job:
    def __init__(self, name: str):
        self.name = name
        self.priority_hook = MemberListHook()
        self.work_hook = MemberListHook()

priority = IntrusiveList[Job]("priority_hook")
work = IntrusiveList[Job]("work_hook")

job = Job("compile")
priority.push_back(job)
work.push_back(job)          # same object, two lists

priority.remove(job)         # still in work
```

Hook accessors accept an attribute name (`"hook"`) or a callable (`lambda j: j.hook`).

### Ownership

Collections use **weak links** only — they never keep member objects alive.
Retain strong references yourself; when the last one drops, GC unlinks the
object from every collection it belongs to.

## Quick start — set & multiset

```python
from intrusive import IntrusiveSet, IntrusiveMultiSet, SetMemberHook

class Task:
    def __init__(self, name: str):
        self.name = name
        self.hook = SetMemberHook[int](int)  # optional runtime key type

tasks = IntrusiveSet[int, Task]("hook")
t = Task("lint")
tasks.insert(t, key=20)
t.hook.change_key(40)        # only way to change key; reinserts in O(log n)

# Duplicates allowed:
bag = IntrusiveMultiSet[int, Task]("hook")
bag.insert(t, key=10)
# bag.count(10), bag.equal_range(10), bag.lower_bound / upper_bound
```

`IntrusiveSet` rejects duplicate keys; `IntrusiveMultiSet` allows them. Both share the same red-black tree implementation.

## API surface

| Type | Role |
|------|------|
| `MemberListHook` / `IntrusiveList` | Intrusive doubly linked list |
| `SetMemberHook` / `IntrusiveSet` | Ordered unique set (RB tree) |
| `IntrusiveMultiSet` | Ordered multiset |
| `intrusive_list_hook` / `intrusive_set_hook` | Decorators that inject hooks |
| `IntrusiveListMixin` / `IntrusiveSetMixin` | Mixins with a default hook |

## Examples & tests

```bash
python examples/demo.py
python examples/demo_set.py

pytest -q                          # unit tests
pytest tests/perf -m perf -s       # optional 1M-object comparison
```

## Design notes

- Hooks and tree/list links are always weak: **no ownership of parent objects**.
- Dropping the last strong reference to a member lets GC remove it from its collections (Boost-like auto-unlink).
- Keys on set hooks are immutable except via `change_key()`.
- This is a clarity-first library. Benchmarks vs a classic owned doubly linked list are in `tests/perf/` if you care about raw throughput.

## License

Licensed under the [Apache License 2.0](LICENSE).
