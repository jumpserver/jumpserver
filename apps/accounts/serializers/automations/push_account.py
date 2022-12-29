from accounts.models import PushAccountAutomation
from .change_secret import ChangeSecretAutomationSerializer


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        excludes = ['recipients', 'is_periodic', 'interval', 'crontab']
        fields = [f for f in fields if f not in excludes]
        fields[fields.index('accounts')] = 'username'
        return fields
