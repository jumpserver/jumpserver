from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from terminal.const import TaskNameType as SessionTaskChoices


class LockTaskSessionSerializer(serializers.Serializer):

    session_id = serializers.CharField(max_length=40, label=_('Session id'))
    task_name = serializers.ChoiceField(choices=SessionTaskChoices.choices, label=_('Task name'))
