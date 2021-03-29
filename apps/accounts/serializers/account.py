from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.drf.serializers import MethodSerializer
from common.utils import get_object_or_none
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Account, AccountType


__all__ = ['AccountSerializer']


class AccountSerializer(BulkOrgResourceModelSerializer):
    attrs = MethodSerializer()

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'username', 'secret', 'address', 'type', 'attrs',
            'is_privileged', 'comment', 'safe'
        ]
        extra_kwargs = {
            'secret': {'read_only': True}
        }

    def get_attrs_serializer(self):
        if self.instance:
            account_type = self.instance.type
        else:
            tp = self.context['request'].query_params.get('account_type')
            account_type = get_object_or_none(AccountType, name=tp)

        if account_type:
            serializer = account_type.get_fields_definition_serializer()
        else:
            serializer = serializers.JSONField()

        return serializer
