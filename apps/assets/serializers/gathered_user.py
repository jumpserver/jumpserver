# -*- coding: utf-8 -*-
#

from ..models import GatheredUser

from orgs.mixins.serializers import OrgResourceModelSerializerMixin


class GatheredUserSerializer(OrgResourceModelSerializerMixin):
    class Meta:
        model = GatheredUser
        fields = [
            'id', 'asset', 'hostname', 'ip', 'username',
            'present', 'date_created', 'date_updated'
        ]
        read_only_fields = fields
