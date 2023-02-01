import django_filters

from common.drf.filters import BaseFilterSet
from .models import MessageContent


class SiteMsgFilter(BaseFilterSet):
    # 不用 Django 的关联表过滤，有个小bug，会重复关联相同表
    # SELECT DISTINCT * FROM `notifications_sitemessage`
    #   INNER JOIN `notifications_sitemessageusers` ON (`notifications_sitemessage`.`id` = `notifications_sitemessageusers`.`sitemessage_id`)
    #   INNER JOIN `notifications_sitemessageusers` T4 ON (`notifications_sitemessage`.`id` = T4.`sitemessage_id`)
    # WHERE (`notifications_sitemessageusers`.`user_id` = '40c8f140dfa246d4861b80f63cf4f6e3' AND NOT T4.`has_read`)
    # ORDER BY `notifications_sitemessage`.`date_created` DESC LIMIT 15;
    has_read = django_filters.BooleanFilter(method='do_nothing')

    class Meta:
        model = MessageContent
        fields = ('has_read',)
