from collections import defaultdict
from typing import Callable, Any

class EventBus:
    """Simple event bus to decouple UI components."""
    def __init__(self):
        self._subscribers = defaultdict(set)

    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        self._subscribers[event_type].add(callback)

    def emit(self, event_type: str, data: Any = None):
        for callback in self._subscribers[event_type]:
            callback(data)