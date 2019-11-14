# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from ..models import GatheredUser


class GatheredUserSerializer(OrgResourceModelSerializerMixin):
    class Meta:
        model = GatheredUser
        fields = [
            'id', 'asset', 'hostname', 'ip', 'username',
            'date_last_login', 'ip_last_login',
            'present', 'date_created', 'date_updated'
        ]
        read_only_fields = fields
        labels = {
            'hostname': _("Hostname"),
            'ip': "IP"
        }
