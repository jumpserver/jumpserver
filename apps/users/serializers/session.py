from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from audits.const import LoginTypeChoices
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from users.models import User
from ..models import UserSession


class UserSessionSerializer(serializers.ModelSerializer):
    type = LabeledChoiceField(choices=LoginTypeChoices.choices, label=_("Type"))
    user = ObjectRelatedField(required=False, queryset=User.objects, label=_('User'))
    is_current_user_session = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields_mini = ['id']
        fields_small = fields_mini + [
            'type', 'ip', 'city', 'user_agent', 'user', 'is_current_user_session',
            'backend', 'backend_display', 'date_created', 'date_expired'
        ]
        fields = fields_small
        extra_kwargs = {
            "backend_display": {"label": _("Authentication backend")},
        }

    def get_is_current_user_session(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return request.session.session_key == obj.key

