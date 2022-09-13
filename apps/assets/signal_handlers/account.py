from django.dispatch import receiver
from django.db.models.signals import pre_save

from common.utils import get_logger
from ..models import Account

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_create(sender, instance, **kwargs):
    # Todo: 是否只有更改密码的时候才有版本增加, bitwarden 只有再改密码的时候，
    #  才会有版本，代表的是 password_version
    # 升级版本号
    instance.version += 1
    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id
