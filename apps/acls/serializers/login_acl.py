from django.utils.translation import ugettext as _
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from common.drf.serializers import MethodSerializer
from common.drf.fields import ObjectRelatedField
from jumpserver.utils import has_valid_xpack_license
from users.models import User
from ..models import LoginACL
from .rules import RuleSerializer

__all__ = ['LoginACLSerializer', ]

common_help_text = _('Format for comma-delimited string, with * indicating a match all. ')


class LoginACLSerializer(BulkModelSerializer):
    user = ObjectRelatedField(queryset=User.objects, label=_('User'))
    reviewers = ObjectRelatedField(
        queryset=User.objects, label=_('Reviewers'), many=True, required=False
    )
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))
    reviewers_amount = serializers.IntegerField(read_only=True, source='reviewers.count')
    rules = MethodSerializer()

    class Meta:
        model = LoginACL
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'priority', 'rules', 'action', 'action_display', 'is_active', 'user',
            'date_created', 'date_updated', 'reviewers_amount', 'comment', 'created_by',
        ]
        fields_fk = ['user']
        fields_m2m = ['reviewers']
        fields = fields_small + fields_fk + fields_m2m
        extra_kwargs = {
            'priority': {'default': 50},
            'is_active': {'default': True},
            "reviewers": {'allow_null': False, 'required': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_action_choices()

    def set_action_choices(self):
        action = self.fields.get('action')
        if not action:
            return
        choices = action._choices
        if not has_valid_xpack_license():
            choices.pop(LoginACL.ActionChoices.confirm, None)
        action._choices = choices

    def get_rules_serializer(self):
        return RuleSerializer()

    def get_reviewers_display(self, obj):
        return ','.join([str(user) for user in obj.reviewers.all()])
