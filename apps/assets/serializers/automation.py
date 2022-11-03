from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.utils import get_logger

from assets.models import ChangeSecretRecord

logger = get_logger(__file__)


class ChangeSecretRecordBackUpSerializer(serializers.ModelSerializer):
    asset = serializers.SerializerMethodField(label=_('Asset'))
    account = serializers.SerializerMethodField(label=_('Account'))
    is_success = serializers.SerializerMethodField(label=_('Is success'))

    class Meta:
        model = ChangeSecretRecord
        fields = [
            'id', 'asset', 'account', 'old_secret', 'new_secret',
            'status', 'error', 'is_success'
        ]

    @staticmethod
    def get_asset(instance):
        return str(instance.asset)

    @staticmethod
    def get_account(instance):
        return str(instance.account)

    @staticmethod
    def get_is_success(obj):
        if obj.status == 'success':
            return _("Success")
        return _("Failed")
