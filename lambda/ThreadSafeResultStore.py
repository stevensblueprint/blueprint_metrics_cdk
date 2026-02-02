from typing import Any, Dict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class ThreadSafeResultStore:
    """Thread-safe storage for results from parallel tasks"""

    def __init__(self):
        self._results: Dict[str, Any] = {}
        self._lock = Lock()

    def store(self, key: str, value: Any) -> None:
        """Thread-safe store operation"""
        with self._lock:
            self._results[key] = value
            logger.info(f"Stored result for key: {key}")

    def get(self, key: str) -> Any:
        """Thread-safe get operation"""
        with self._lock:
            return self._results.get(key)

    def get_all(self) -> Dict[str, Any]:
        """Thread-safe get all results"""
        with self._lock:
            return self._results.copy()
