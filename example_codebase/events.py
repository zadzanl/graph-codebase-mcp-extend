from typing import Callable

class EventBus:
    """簡易 Publish–Subscribe 實作"""
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type: str, handler: Callable):
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data):
        for handler in self._subscribers.get(event_type, []):
            handler(data) 