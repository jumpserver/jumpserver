# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from common.drf.fields import ObjectRelatedField
from ..models import GatheredUser, Asset


class GatheredUserSerializer(OrgResourceModelSerializerMixin):
    asset = ObjectRelatedField(queryset=Asset.objects, label=_('Asset'))

    class Meta:
        model = GatheredUser
        fields_mini = ['id']
        fields_small = fields_mini + [
            'username', 'ip_last_login', 'present', 'name',
            'date_last_login', 'date_created', 'date_updated'
        ]
        fields_fk = ['asset', 'ip']
        fields = fields_small + fields_fk
        read_only_fields = fields
        extra_kwargs = {
            'name': {'label': _("Hostname")},
            'ip': {'label': 'IP'},
        }
