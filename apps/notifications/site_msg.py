from django.db import transaction

from common.utils import get_logger
from common.utils.timezone import local_now
from users.models import User
from .models import MessageContent as SiteMessageModel, SiteMessage

logger = get_logger(__file__)


class SiteMessageUtil:

    @classmethod
    def send_msg(cls, subject, message, user_ids=(), group_ids=(),
                 sender=None, is_broadcast=False):
        if not any((user_ids, group_ids, is_broadcast)):
            raise ValueError('No recipient is specified')

        with transaction.atomic():
            site_msg = SiteMessageModel.objects.create(
                subject=subject, message=message,
                is_broadcast=is_broadcast, sender=sender,
            )

            if is_broadcast:
                user_ids = User.objects.all().values_list('id', flat=True)
            elif group_ids:
                site_msg.groups.add(*group_ids)

                user_ids_from_group = User.groups.through.objects.filter(
                    usergroup_id__in=group_ids
                ).values_list('user_id', flat=True)
                user_ids = [*user_ids, *user_ids_from_group]

            site_msg.users.add(*user_ids)

    @classmethod
    def get_user_all_msgs(cls, user_id):
        site_msg_rels = SiteMessage.objects \
            .filter(user=user_id) \
            .prefetch_related('content') \
            .order_by('-date_created')
        return site_msg_rels

    @classmethod
    def get_user_all_msgs_count(cls, user_id):
        site_msgs_count = SiteMessage.objects.filter(
            user_id=user_id
        ).distinct().count()
        return site_msgs_count

    @classmethod
    def filter_user_msgs(cls, user_id, has_read=False):
        return cls.get_user_all_msgs(user_id).filter(has_read=has_read)

    @classmethod
    def get_user_unread_msgs_count(cls, user_id):
        site_msgs_count = SiteMessage.objects \
            .filter(user=user_id, has_read=False) \
            .values_list('content', flat=True) \
            .distinct().count()
        return site_msgs_count

    @classmethod
    def mark_msgs_as_read(cls, user_id, msg_ids=None):
        site_msgs = SiteMessage.objects.filter(user_id=user_id)
        if msg_ids:
            site_msgs = site_msgs.filter(id__in=msg_ids)
        site_msgs.update(has_read=True, read_at=local_now())
