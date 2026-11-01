import asyncio
from collections import defaultdict
from typing import Any, TypeVar
T = TypeVar("T")

class EventBus:
    """Small typed-by-convention asynchronous pub/sub bus."""
    def __init__(self): self._subs: dict[type, list[asyncio.Queue]] = defaultdict(list)
    def subscribe(self, event_type: type[T]) -> asyncio.Queue[T]:
        q: asyncio.Queue[T] = asyncio.Queue(); self._subs[event_type].append(q); return q
    async def publish(self, event: Any) -> None:
        for q in tuple(self._subs[type(event)]): await q.put(event)
