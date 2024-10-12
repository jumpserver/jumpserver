from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from .base import BaseOperateStorage
from .es import OperateLogStore as ESOperateLogStore
from .db import OperateLogStore as DBOperateLogStore


logger = get_logger(__file__)

_global_op_log_storage: None | ESOperateLogStore | DBOperateLogStore = None
op_log_type_mapping = {
    'server': DBOperateLogStore, 'es': ESOperateLogStore
}


def _send_es_unavailable_alarm_msg():
    from terminal.notifications import StorageConnectivityMessage
    from terminal.const import CommandStorageType

    key = 'OPERATE_LOG_ES_UNAVAILABLE_KEY'
    if cache.get(key):
        return

    cache.set(key, 1, 60)
    errors = [{
        'msg': _("Connect failed"), 'name': f"{_('Operate log')}",
        'type': CommandStorageType.es.label
    }]
    StorageConnectivityMessage(errors).publish()
    # StorageConnectivityMessage(errors).publish_async()


def refresh_log_storage():
    global _global_op_log_storage
    _global_op_log_storage = None

    if settings.OPERATE_LOG_ELASTICSEARCH_CONFIG.get('HOSTS'):
        try:
            config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
            log_storage = op_log_type_mapping['es'](config)
            _global_op_log_storage = log_storage
        except Exception as e:
            _send_es_unavailable_alarm_msg()
            logger.warning('Invalid logs storage type: es, error: %s' % str(e))

    if not _global_op_log_storage:
        _global_op_log_storage = op_log_type_mapping['server']()


def get_operate_log_storage():
    if _global_op_log_storage is None:
        refresh_log_storage()

    log_storage = _global_op_log_storage
    if not log_storage.ping(timeout=3):
        if log_storage.get_type() == 'es':
            _send_es_unavailable_alarm_msg()
        logger.warning('Switch default operate log storage.')
        log_storage = op_log_type_mapping['server']()
    return log_storage
