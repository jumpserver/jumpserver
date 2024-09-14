# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from .mixin import ScopeSerializerMixin
from ..const import Scope
from ..models import AdHoc


class AdHocSerializer(ScopeSerializerMixin, CommonBulkModelSerializer):
    creator = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = AdHoc
        read_only_field = ["id", "creator", "date_created", "date_updated"]
        fields = read_only_field + ["id", "name", "scope", "module", "args", "comment"]
