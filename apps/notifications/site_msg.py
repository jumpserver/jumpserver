from django.db.models import F, Q
from django.db import transaction

from common.utils.timezone import local_now
from common.utils import get_logger
from users.models import User
from .models import SiteMessage as SiteMessageModel, SiteMessageUsers

logger = get_logger(__file__)


class SiteMessageUtil:

    @classmethod
    def send_msg(cls, subject, message, user_ids=(), group_ids=(),
                 sender=None, is_broadcast=False):
        if not any((user_ids, group_ids, is_broadcast)):
            raise ValueError('No recipient is specified')

        logger.info(f'Site message send: '
                    f'user_ids={user_ids} '
                    f'group_ids={group_ids} '
                    f'subject={subject} '
                    f'message={message}')
        with transaction.atomic():
            site_msg = SiteMessageModel.objects.create(
                subject=subject, message=message,
                is_broadcast=is_broadcast, sender=sender,
            )

            if is_broadcast:
                user_ids = User.objects.all().values_list('id', flat=True)
            else:
                if group_ids:
                    site_msg.groups.add(*group_ids)

                    user_ids_from_group = User.groups.through.objects.filter(
                        usergroup_id__in=group_ids
                    ).values_list('user_id', flat=True)
                    user_ids = [*user_ids, *user_ids_from_group]

            site_msg.users.add(*user_ids)

    @classmethod
    def get_user_all_msgs(cls, user_id):
        site_msgs = SiteMessageModel.objects.filter(
            m2m_sitemessageusers__user_id=user_id
        ).distinct().annotate(
            has_read=F('m2m_sitemessageusers__has_read'),
            read_at=F('m2m_sitemessageusers__read_at')
        ).order_by('-date_created')

        return site_msgs

    @classmethod
    def get_user_all_msgs_count(cls, user_id):
        site_msgs_count = SiteMessageModel.objects.filter(
            m2m_sitemessageusers__user_id=user_id
        ).distinct().count()
        return site_msgs_count

    @classmethod
    def filter_user_msgs(cls, user_id, has_read=False):
        site_msgs = SiteMessageModel.objects.filter(
            m2m_sitemessageusers__user_id=user_id,
            m2m_sitemessageusers__has_read=has_read
        ).distinct().annotate(
            has_read=F('m2m_sitemessageusers__has_read'),
            read_at=F('m2m_sitemessageusers__read_at')
        ).order_by('-date_created')

        return site_msgs

    @classmethod
    def get_user_unread_msgs_count(cls, user_id):
        site_msgs_count = SiteMessageModel.objects.filter(
            m2m_sitemessageusers__user_id=user_id,
            m2m_sitemessageusers__has_read=False
        ).distinct().count()
        return site_msgs_count

    @classmethod
    def mark_msgs_as_read(cls, user_id, msg_ids=None):
        q = Q(user_id=user_id) & Q(has_read=False)
        if msg_ids is not None:
            q &= Q(sitemessage_id__in=msg_ids)
        site_msg_users = SiteMessageUsers.objects.filter(q)

        for site_msg_user in site_msg_users:
            site_msg_user.has_read = True
            site_msg_user.read_at = local_now()

        SiteMessageUsers.objects.bulk_update(
            site_msg_users, fields=('has_read', 'read_at'))
