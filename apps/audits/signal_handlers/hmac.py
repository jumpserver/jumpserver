from django.db.models.signals import post_save

from common.utils import get_logger
from common.utils.verify_hmac import hmac_handler

logger = get_logger(__file__)

SENDER_HMAC_MAP = {}


def _get_sender_hmac_map():
    if not SENDER_HMAC_MAP:
        from audits.models import (
            OperateLog, UserLoginLog, FTPLog, PasswordChangeLog,
            OperateLogHmac, UserLoginLogHmac, FTPLogHmac, PasswordChangeLogHmac,
        )
        SENDER_HMAC_MAP.update({
            OperateLog: OperateLogHmac,
            UserLoginLog: UserLoginLogHmac,
            FTPLog: FTPLogHmac,
            PasswordChangeLog: PasswordChangeLogHmac,
        })
    return SENDER_HMAC_MAP


def on_audit_log_save(sender, instance, created, **kwargs):
    if not created or not hmac_handler.enable:
        return
    sender_map = _get_sender_hmac_map()
    hmac_model = sender_map.get(sender)
    if hmac_model:
        hmac_handler.create_hmac_record(hmac_model, instance.id, instance)


def setup_hmac_signals():
    from audits.models import OperateLog, UserLoginLog, FTPLog, PasswordChangeLog
    for model in [OperateLog, UserLoginLog, FTPLog, PasswordChangeLog]:
        post_save.connect(on_audit_log_save, sender=model, dispatch_uid=f'hmac_{model.__name__}')


setup_hmac_signals()
