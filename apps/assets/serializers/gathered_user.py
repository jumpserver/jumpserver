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
            'present', 'date_created', 'date_updated'
        ]
        read_only_fields = fields
        labels = {
            'hostname': _("Hostname"),
            'ip': "IP"
        }
