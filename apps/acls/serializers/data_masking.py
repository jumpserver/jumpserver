from django.utils.translation import gettext_lazy as _

from acls.models import MaskingMethod, DataMaskingRule
from common.serializers.fields import LabeledChoiceField
from common.serializers.mixin import CommonBulkModelSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseUserAssetAccountACLSerializer as BaseSerializer

__all__ = ['DataMaskingRuleSerializer']


class DataMaskingRuleSerializer(BaseSerializer, BulkOrgResourceModelSerializer):
    masking_method = LabeledChoiceField(
        choices=MaskingMethod.choices, default=MaskingMethod.fixed_char, label=_('Masking Method')
    )

    class Meta(BaseSerializer.Meta):
        model = DataMaskingRule
        fields = BaseSerializer.Meta.fields + ['fields_pattern', 'masking_method', 'mask_pattern']
