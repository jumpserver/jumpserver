import json

from django.utils.functional import LazyObject
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.utils.connection import RedisPubSub
from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import SiteMessage


logger = get_logger(__name__)


def new_site_msg_pub_sub():
    return RedisPubSub('notifications.SiteMessageCome')


class NewSiteMsgSubPub(LazyObject):
    def _setup(self):
        self._wrapped = new_site_msg_pub_sub()


new_site_msg_chan = NewSiteMsgSubPub()


@receiver(post_save, sender=SiteMessage)
@on_transaction_commit
def on_site_message_create(sender, instance, created, **kwargs):
    if not created:
        return
    logger.debug('New site msg created, publish it')
    user_ids = instance.users.all().values_list('id', flat=True)
    user_ids = [str(i) for i in user_ids]
    data = {
        'id': str(instance.id),
        'subject': instance.subject,
        'message': instance.message,
        'users': user_ids
    }
    data = json.dumps(data)
    new_site_msg_chan.publish(data)
