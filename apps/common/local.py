import contextvars
import re
from typing import Any, Dict


class AsyncLocal:
    """
    一个异步环境下安全的上下文存储对象，用于替代 werkzeug.local.Local。
    内部使用一个 ContextVar 来存储一个字典。
    """

    def __init__(self, context_var_name: str = "_async_local_storage"):
        self._storage: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
            context_var_name,
            default={}
        )

    def set(self, key: str, value: Any) -> None:
        current_data = self._storage.get().copy()
        current_data[key] = value
        self._storage.set(current_data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._storage.get().get(key, default)

    def delete(self, key: str) -> None:
        current_data = self._storage.get().copy()
        if key in current_data:
            del current_data[key]
            self._storage.set(current_data)

    def clear(self) -> None:
        self._storage.set({})


thread_local = AsyncLocal()
exclude_encrypted_fields = ('secret_type', 'secret_strategy', 'password_rules')
similar_encrypted_pattern = re.compile(
    'password|secret|token|passphrase|private|key|cert', re.IGNORECASE
)


def _find(attr):
    return getattr(thread_local, attr, None)
