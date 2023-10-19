from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.models.base import BaseACL
from common.serializers.fields import JSONManyToManyField, LabeledChoiceField
from orgs.models import Organization
from ..const import ActionChoices

common_help_text = _(
    "With * indicating a match all. "
)


class ACLUsersSerializer(serializers.Serializer):
    username_group = serializers.ListField(
        default=["*"],
        child=serializers.CharField(max_length=128),
        label=_("Username"),
        help_text=common_help_text,
    )


class ACLAssetsSerializer(serializers.Serializer):
    address_group_help_text = _(
        "With * indicating a match all. "
        "Such as: "
        "192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64"
        " (Domain name support)"
    )

    name_group = serializers.ListField(
        default=["*"],
        child=serializers.CharField(max_length=128),
        label=_("Name"),
        help_text=common_help_text,
    )
    address_group = serializers.ListField(
        default=["*"],
        child=serializers.CharField(max_length=1024),
        label=_("IP/Host"),
        help_text=address_group_help_text,
    )


class ACLAccountsSerializer(serializers.Serializer):
    username_group = serializers.ListField(
        default=["*"],
        child=serializers.CharField(max_length=128),
        label=_("Username"),
        help_text=common_help_text,
    )


class ActionAclSerializer(serializers.Serializer):
    action = LabeledChoiceField(
        choices=ActionChoices.choices, default=ActionChoices.reject, label=_("Action")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_action_choices()

    class Meta:
        action_choices_exclude = [ActionChoices.warning]

    def set_action_choices(self):
        field_action = self.fields.get("action")
        if not field_action:
            return
        if not settings.XPACK_LICENSE_IS_VALID:
            field_action._choices.pop(ActionChoices.review, None)
        for choice in self.Meta.action_choices_exclude:
            field_action._choices.pop(choice, None)


class BaseACLSerializer(ActionAclSerializer, serializers.Serializer):
    class Meta(ActionAclSerializer.Meta):
        model = BaseACL
        fields_mini = ["id", "name"]
        fields_small = fields_mini + [
            "is_active", "priority", "action",
            "date_created", "date_updated",
            "comment", "created_by", "org_id",
        ]
        fields_m2m = ["reviewers", ]
        fields = fields_small + fields_m2m
        extra_kwargs = {
            "priority": {"default": 50},
            "is_active": {"default": True},
            'reviewers': {'label': _('Recipients')},
        }

    def validate_reviewers(self, reviewers):
        action = self.initial_data.get('action')
        if not action and self.instance:
            action = self.instance.action
        if action != ActionChoices.review:
            return reviewers
        org_id = self.fields["org_id"].default()
        org = Organization.get_instance(org_id)
        if not org:
            error = _("The organization `{}` does not exist".format(org_id))
            raise serializers.ValidationError(error)
        users = org.get_members()
        valid_reviewers = list(set(reviewers) & set(users))
        if not valid_reviewers:
            error = _(
                "None of the reviewers belong to Organization `{}`".format(org.name)
            )
            raise serializers.ValidationError(error)
        return valid_reviewers


class BaseUserACLSerializer(BaseACLSerializer):
    users = JSONManyToManyField(label=_('User'))

    class Meta(BaseACLSerializer.Meta):
        fields = BaseACLSerializer.Meta.fields + ['users']


class BaseUserAssetAccountACLSerializer(BaseUserACLSerializer):
    assets = JSONManyToManyField(label=_('Asset'))
    accounts = serializers.ListField(label=_('Account'))

    class Meta(BaseUserACLSerializer.Meta):
        fields = BaseUserACLSerializer.Meta.fields + ['assets', 'accounts']
