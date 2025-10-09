from common.serializers.fields import LabeledChoiceField
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer
from common.serializers.mixin import CommonBulkModelSerializer
from ..models import DataMaskingRule
from django.utils.translation import gettext_lazy as _

__all__ = ['DataMaskingRuleSerializer']

from ..models.data_masking import MaskingMethod


class DataMaskingRuleSerializer(BaseSerializer, CommonBulkModelSerializer):
    masking_method = LabeledChoiceField(
        choices=MaskingMethod, default=MaskingMethod.fixed_char, label=_('Masking Method')
    )

    class Meta(BaseSerializer.Meta):
        model = DataMaskingRule
        fields = BaseSerializer.Meta.fields + ['fields_pattern', 'masking_method', 'mask_pattern']
