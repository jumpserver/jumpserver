from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from ..const import Scope


class ScopeSerializerMixin(serializers.Serializer):
    scope = LabeledChoiceField(
        choices=Scope.choices, default=Scope.public, label=_("Scope")
    )
    disable_edit = serializers.SerializerMethodField()

    def get_disable_edit(self, obj):
        return obj.creator != self.context['request'].user
