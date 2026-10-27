from .workflow import WorkflowACLSerializerMixin
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from common.serializers import MethodSerializer
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from django.conf import settings
from rest_framework import serializers
from users.models import User
from ..const import ActionChoices
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from .rules import RuleSerializer
from ..models import LoginAssetACL

__all__ = ["LoginAssetACLSerializer"]


class LoginAssetACLSerializer(WorkflowACLSerializerMixin, BaseSerializer, BulkOrgResourceModelSerializer):
    rules = MethodSerializer(label=_('Rule'))
    action = LabeledChoiceField(
        choices=((ActionChoices.accept, _('Allow')), (ActionChoices.reject, _('Reject'))),
        default=ActionChoices.reject,
        label=_('Action'),
        help_text=_(
            'Allow applies the connection controls; Reject blocks the connection.'
        ),
    )
    accounts = serializers.ListField(
        child=serializers.CharField(), label=_('Account'),
        help_text=_(
            'Account usernames or @ALL (all accounts), @SPEC with specified usernames, '
            "and @USER (the current user's same-name account)."
        ),
    )
    recipients = ObjectRelatedField(
        queryset=User.objects.all(), many=True, required=False, label=_('Recipients'),
    )

    class Meta(BaseSerializer.Meta):
        model = LoginAssetACL
        fields = BaseSerializer.Meta.fields + ['rules', 'review_duration', 'workflow', 'recipients', *LoginAssetACL.CONTROL_FIELDS]
        extra_kwargs = {
            **BaseSerializer.Meta.extra_kwargs,
            'priority': {
                **BaseSerializer.Meta.extra_kwargs['priority'],
                'help_text': _(
                    '1-100; lower values have higher priority.\n'
                    'Select the highest-priority group from the rules that match. '
                    'Any Reject in that group blocks the connection; '
                    'if all Allow, combine their enabled connection controls.'
                ),
            },
            'reviewers': {
                'label': _('Reviewers'),
                'help_text': _(
                    'Select reviewers when approval is enabled. Connections are blocked if no reviewers are available.'
                ),
            },
            'review_duration': {
                'label': _('Exemption period'),
                'help_text': _(
                    'After approval, allow reconnects by the same user to the same asset and account under this '
                    'rule for this many hours. 0 requires approval every time. Changes do not affect existing exemptions.'
                ),
            },
            'reason_enabled': {
                'label': _('Connection reason'),
                'help_text': _(
                    'Enter a reason before connecting.'
                ),
            },
            'mfa_enabled': {
                'label': _('MFA verification'),
                'help_text': _(
                    'Verify an enrolled MFA code before connecting. '
                    'Block connections if no code-based MFA method is enrolled.'
                ),
            },
            'face_verify_enabled': {
                'label': _('Face verification'),
                'help_text': _(
                    "Verify the user's face before connecting. Requires system face recognition and an enrolled face."
                ),
            },
            'review_enabled': {
                'label': _('Require approval'),
                'help_text': _(
                    'Require approval before connecting, except during a valid exemption period.'
                ),
            },
            'notice_enabled': {
                'label': _('Send notification'),
                'help_text': _(
                    'Notify the selected recipients when a user requests an asset connection. '
                    'A notification does not mean the connection succeeded.'
                ),
            },
            'push_account_enabled': {
                'label': pgettext_lazy('Asset connection ACL', 'Push account'),
                'help_text': _(
                    'Automatically provision only same-name accounts before their first connection; '
                    'reuse existing managed accounts without provisioning them again. '
                    'Requires account provisioning support on the asset platform.'
                ),
            },
            'face_online_enabled': {
                'label': pgettext_lazy('Asset connection ACL', 'Face online'),
                'help_text': _(
                    "Web Terminal only: verify the user's face before connecting and monitor throughout the session. "
                    'Requires system face recognition and an enrolled face.'
                ),
            },
            'change_secret_enabled': {
                'label': _('Rotate password'),
                'help_text': _(
                    "Rotate the connected account's secret after the session ends. Requires system rotation "
                    'after session end and automatic rotation on an active account.'
                ),
            },
        }

    def get_rules_serializer(self):
        return RuleSerializer()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        action = attrs.get('action', getattr(self.instance, 'action', ActionChoices.reject))
        review_enabled = attrs.get('review_enabled', getattr(self.instance, 'review_enabled', False))
        workflow = attrs.get('workflow', getattr(self.instance, 'workflow', None))
        if action == ActionChoices.accept and review_enabled and not workflow:
            reviewers = attrs.get('reviewers')
            if reviewers is None:
                reviewers = self.instance.reviewers.all() if self.instance else []
            org_id = attrs.get('org_id', getattr(self.instance, 'org_id', None)) or self.fields['org_id'].default()
            available = LoginAssetACL.filter_available_reviewers(reviewers, org_id)
            if not available:
                raise serializers.ValidationError({
                    'reviewers': _('Select at least one active, unexpired reviewer from this organization.'),
                })
            if 'reviewers' in attrs:
                attrs['reviewers'] = available
        notice_enabled = attrs.get('notice_enabled', getattr(self.instance, 'notice_enabled', False))
        if action == ActionChoices.accept and notice_enabled:
            recipients = attrs.get('recipients')
            if recipients is None:
                recipients = self.instance.recipients.all() if self.instance else []
            if not recipients:
                raise serializers.ValidationError({
                    'recipients': _('Select at least one notification recipient.'),
                })
        for field in ('review_enabled', 'face_verify_enabled', 'face_online_enabled', 'change_secret_enabled'):
            if attrs.get(field) and not settings.XPACK_LICENSE_IS_VALID:
                raise serializers.ValidationError({field: _('A valid license is required')})
        for field in ('face_verify_enabled', 'face_online_enabled'):
            if attrs.get(field) and not settings.FACE_RECOGNITION_ENABLED:
                raise serializers.ValidationError({field: _('Face recognition is disabled')})
        if attrs.get('change_secret_enabled') and not settings.CHANGE_SECRET_AFTER_SESSION_END:
            raise serializers.ValidationError({'change_secret_enabled': _('Secret rotation after session end is disabled')})
        return attrs
