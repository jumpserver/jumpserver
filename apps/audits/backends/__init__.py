from typing import Any

from audits.const import LogType, LogStorageType as LSType
from common.utils import get_logger
from common.plugins.es import InvalidElasticsearch
from .es import (
    OperateLogStore as ESOperateLogStore,
    LoginLogStore as ESLoginLogStore,
    FTPLogStore as ESFTPLogStore,
    PasswordChangeLogStore as ESPwdChangeLogStore,
)
from .db import (
    OperateLogStore as DBOperateLogStore,
    LoginLogStore as DBLoginLogStore,
    FTPLogStore as DBFTPLogStore,
    PasswordChangeLogStore as DBPwdChangeLogStore,
)


logger = get_logger(__file__)


_global_log_storage: dict[str: Any] = {
    LogType.operate_log: None,
    LogType.login_log: None,
    LogType.ftp_log: None,
    LogType.password_change_log: None
}

log_type_mapping = {
    LogType.operate_log: {
        LSType.server: DBOperateLogStore, LSType.es: ESOperateLogStore
    },
    LogType.login_log: {
        LSType.server: DBLoginLogStore, LSType.es: ESLoginLogStore
    },
    LogType.ftp_log: {
        LSType.server: DBFTPLogStore, LSType.es: ESFTPLogStore
    },
    LogType.password_change_log: {
        LSType.server: DBPwdChangeLogStore, LSType.es: ESPwdChangeLogStore
    },
}


def refresh_log_storage():
    from audits.models import LogStorage

    for log_type in _global_log_storage.keys():
        _global_log_storage[log_type] = None

    for storage in LogStorage.objects.exclude(type=LSType.server):
        for log_type in list(storage.meta.get('LOG_TYPES', [])):
            try:
                log_storage: Any = log_type_mapping[log_type][storage.type](storage.config)
                _global_log_storage[log_type] = log_storage
            except InvalidElasticsearch:
                logger.warning('Invalid Elasticsearch logs storage type: %s' % log_type)

    for log_type, storage in _global_log_storage.items():
        if not storage:
            server_storage: Any = log_type_mapping[log_type][LSType.server]()
            _global_log_storage[log_type] = server_storage


def get_log_storage(log_type, backend=None, backend_kwargs=None):
    if backend:
        params = backend_kwargs or {}
        return log_type_mapping[log_type][backend](**params)

    if _global_log_storage[log_type] is not None:
        log_storage = _global_log_storage[log_type]
    else:
        refresh_log_storage()
        default = log_type_mapping[log_type][LSType.server]()
        log_storage = _global_log_storage.get(log_type, default)

    if not log_storage.ping(timeout=3):
        logger.warning('Switch default log storage. Type: %s' % log_type)
        log_storage = log_type_mapping[log_type][LSType.server]()
    return log_storage
