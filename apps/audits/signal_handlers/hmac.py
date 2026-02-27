from django.db.models.signals import post_save
from django.dispatch import receiver

from common.utils import get_logger
from common.utils.verify_hmac import hmac_handler

logger = get_logger(__name__)

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


@receiver(post_save, sender='audits.OperateLog')
@receiver(post_save, sender='audits.UserLoginLog')
@receiver(post_save, sender='audits.FTPLog')
@receiver(post_save, sender='audits.PasswordChangeLog')
def on_audit_log_save(sender, instance, created, **kwargs):
    if not hmac_handler.enable:
        return
    sender_map = _get_sender_hmac_map()
    hmac_model = sender_map.get(sender)
    if not hmac_model:
        return
    if created:
        hmac_handler.create_hmac_record(hmac_model, instance.id, instance)
    else:
        hmac_handler.update_hmac_record(hmac_model, instance.id, instance)