from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.serializers import BulkModelSerializer, MethodSerializer
from jumpserver.utils import has_valid_xpack_license
from users.models import User
from .rules import RuleSerializer
from ..models import LoginACL

__all__ = [
    "LoginACLSerializer",
]

common_help_text = _(
    "Format for comma-delimited string, with * indicating a match all. "
)


class LoginACLSerializer(BulkModelSerializer):
    user = ObjectRelatedField(queryset=User.objects, label=_("User"))
    reviewers = ObjectRelatedField(
        queryset=User.objects, label=_("Reviewers"), many=True, required=False
    )
    action = LabeledChoiceField(choices=LoginACL.ActionChoices.choices)
    reviewers_amount = serializers.IntegerField(
        read_only=True, source="reviewers.count", label=_("Reviewers amount")
    )
    rules = MethodSerializer(label=_('Rule'))

    class Meta:
        model = LoginACL
        fields_mini = ["id", "name"]
        fields_small = fields_mini + [
            "priority", "user", "rules", "action",
            "is_active", "date_created", "date_updated",
            "comment", "created_by",
        ]
        fields_fk = ["user"]
        fields_m2m = ["reviewers", "reviewers_amount"]
        fields = fields_small + fields_fk + fields_m2m
        extra_kwargs = {
            "priority": {"default": 50},
            "is_active": {"default": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_action_choices()

    def set_action_choices(self):
        action = self.fields.get("action")
        if not action:
            return
        choices = action.choices
        if not has_valid_xpack_license():
            choices.pop(LoginACL.ActionChoices.review, None)
        action.choices = choices

    def get_rules_serializer(self):
        return RuleSerializer()
