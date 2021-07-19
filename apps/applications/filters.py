from django_filters import rest_framework as filters

from .models import Application
from applications import const


class ApplicationFilter(filters.FilterSet):
    type = filters.MultipleChoiceFilter(choices=const.ApplicationTypeChoices.choices)

    class Meta:
        model = Application
        fields = ['id', 'name', 'category', 'type', 'comment']
