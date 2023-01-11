import copy
from accounts.models import PushAccountAutomation
from .change_secret import (
    ChangeSecretAutomationSerializer, ChangeSecretUpdateAssetSerializer,
    ChangeSecretUpdateNodeSerializer
)


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    # dynamic_username = serializers.BooleanField(label=_('Dynamic username'), default=False)
    # triggers = TreeChoicesField(
    #     choice_cls=TriggerChoice, label=_('Triggers'),
    #     default=TriggerChoice.all(),
    # )
    # action = LabeledChoiceField(
    #     choices=PushAccountActionChoice.choices, label=_('Action'),
    #     default=PushAccountActionChoice.create_and_push
    # )

    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation
        fields = copy.copy(ChangeSecretAutomationSerializer.Meta.fields)
        fields.remove('recipients')

        # fields = ChangeSecretAutomationSerializer.Meta.fields + [
        #     'dynamic_username', 'triggers', 'action'
        # ]

    # def validate_username(self, value):
    #     if self.initial_data.get('dynamic_username'):
    #         value = '@USER'
    #     queryset = self.Meta.model.objects.filter(username=value)
    #     if self.instance:
    #         queryset = queryset.exclude(id=self.instance.id)
    #     if queryset.exists():
    #         raise serializers.ValidationError(_('Username already exists'))
    #     return value
    #
    # def validate_dynamic_username(self, value):
    #     if not value:
    #         return value
    #     queryset = self.Meta.model.objects.filter(username='@USER')
    #     if self.instance:
    #         queryset = queryset.exclude(id=self.instance.id)
    #     if queryset.exists():
    #         raise serializers.ValidationError(_('Dynamic username already exists'))
    #     return value
    #
    # def validate_triggers(self, value):
    #     # Now triggers readonly, set all
    #     return TriggerChoice.all()
    #
    # def get_field_names(self, declared_fields, info):
    #     fields = super().get_field_names(declared_fields, info)
    #     excludes = [
    #         'recipients', 'is_periodic', 'interval', 'crontab',
    #         'periodic_display', 'assets', 'nodes'
    #     ]
    #     fields = [f for f in fields if f not in excludes]
    #     fields[fields.index('accounts')] = 'username'
    #     return fields


class PushAccountUpdateAssetSerializer(ChangeSecretUpdateAssetSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateAssetSerializer.Meta.fields


class PushAccountUpdateNodeSerializer(ChangeSecretUpdateNodeSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateNodeSerializer.Meta.fields
