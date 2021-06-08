import django_filters

from .models import SiteMessage


class SiteMsgFilter(django_filters.FilterSet):
    has_read = django_filters.BooleanFilter(field_name='m2m_sitemessageusers__has_read')

    class Meta:
        model = SiteMessage
        fields = ('has_read',)
