# core/thread_safe.py

import threading
from typing import Generic, TypeVar

T = TypeVar('T')

class ThreadSafeVariable(Generic[T]):
    """
    A thread-safe variable class that provides synchronized access
    to its value.
    """
    def __init__(self, initial_value: T = None):
        self._value = initial_value
        self._lock = threading.Lock()

    def get(self) -> T:
        with self._lock:
            return self._value

    def set(self, new_value: T) -> None:
        with self._lock:
            self._value = new_value

    def update(self, func) -> None:
        """
        Update the value using a provided function.
        The function should take the current value and return the new value.
        """
        with self._lock:
            self._value = func(self._value)
