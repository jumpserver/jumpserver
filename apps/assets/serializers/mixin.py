from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class CategoryDisplayMixin(serializers.Serializer):
    category_display = serializers.ReadOnlyField(
        source='get_category_display', label=_("Category display")
    )
    type_display = serializers.ReadOnlyField(
        source='get_type_display', label=_("Type display")
    )
