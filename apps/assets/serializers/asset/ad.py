from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import AD
from .common import AssetSerializer

__all__ = ['ADSerializer']


class ADSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = AD
        fields = AssetSerializer.Meta.fields + [
            'domain_name',
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'domain_name': {
                'help_text': _(
                    'The domain name of the Active Directory'
                ),
                'label': _('Domain name')}
        }
