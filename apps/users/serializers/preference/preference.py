from django.utils.translation import gettext_lazy as _

from settings.serializers import BaseSerializerWithFieldLabel
from .koko import KokoSerializer
from .lina import LinaSerializer
from .luna import LunaSerializer

__all__ = [
    'PreferenceSerializer',
]


class PreferenceSerializer(
    BaseSerializerWithFieldLabel,
    LinaSerializer,
    LunaSerializer,
    KokoSerializer
):
    PREFIX_TITLE = _('Preference')
    CACHE_KEY = 'PREFERENCE_FIELDS_MAPPING'
