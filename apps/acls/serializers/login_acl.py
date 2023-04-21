from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.serializers import BulkModelSerializer, MethodSerializer
from common.serializers.fields import ObjectRelatedField
from users.models import User
from .base import ActionAclSerializer
from .rules import RuleSerializer
from ..models import LoginACL

__all__ = [
    "LoginACLSerializer",
]

common_help_text = _(
    "With * indicating a match all. "
)


class LoginACLSerializer(ActionAclSerializer, BulkModelSerializer):
    user = ObjectRelatedField(queryset=User.objects, label=_("User"))
    reviewers = ObjectRelatedField(
        queryset=User.objects, label=_("Reviewers"), many=True, required=False
    )
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

    def get_rules_serializer(self):
        return RuleSerializer()
