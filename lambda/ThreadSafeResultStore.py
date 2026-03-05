from typing import Dict, Generic, TypeVar, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ThreadSafeResultStore(Generic[T]):
    """Thread-safe storage for results from parallel tasks"""

    def __init__(self) -> None:
        self._results: Dict[str, T] = {}
        self._lock = Lock()

    def store(self, key: str, value: T) -> None:
        """Thread-safe store operation"""
        with self._lock:
            self._results[key] = value
            logger.info(f"Stored result for key: {key}")

    def get(self, key: str) -> Optional[T]:
        """Thread-safe get operation"""
        with self._lock:
            return self._results.get(key)

    def get_all(self) -> Dict[str, T]:
        """Thread-safe get all results"""
        with self._lock:
            return self._results.copy()
