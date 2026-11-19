"""Estado provisional/confirmado, canales vivos y señales de eventos limitadas."""

import asyncio
from collections import defaultdict

from backend.app.persistence.sqlite_store import Store


class RunManager:
    def __init__(self, store: Store):
        self.store = store
        self.subscribers = defaultdict(set)
        self.tasks = {}

    def last_good(self) -> dict | None:
        run_id = self.store.get_meta("last_good_run")
        return self.store.get_run(run_id) if run_id else None

    async def broadcast(self, run_id: str, event: dict) -> None:
        self.store.event(run_id, event.get("type", "unknown"), event)
        for q in tuple(self.subscribers[run_id]):
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(event)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q = asyncio.Queue(maxsize=120)
        self.subscribers[run_id].add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        self.subscribers[run_id].discard(q)

    def launch(self, run_id: str, coro) -> None:
        if run_id in self.tasks and not self.tasks[run_id].done():
            raise ValueError("Corrida en ejecución")
        task = asyncio.create_task(coro)
        self.tasks[run_id] = task
        task.add_done_callback(lambda result: self.tasks.pop(run_id, None))
