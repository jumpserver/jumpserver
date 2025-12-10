from django.db import models

from acls.models import UserAssetAccountBaseACL
from common.utils import get_logger
from django.utils.translation import gettext_lazy as _

logger = get_logger(__file__)

__all__ = ['MaskingMethod', 'DataMaskingRule']


class MaskingMethod(models.TextChoices):
    fixed_char = "fixed_char", _("Fixed Character Replacement")  # 固定字符替换
    hide_middle = "hide_middle", _("Hide Middle Characters")  # 隐藏中间几位
    keep_prefix = "keep_prefix", _("Keep Prefix Only")  # 只保留前缀
    keep_suffix = "keep_suffix", _("Keep Suffix Only")  # 只保留后缀


class DataMaskingRule(UserAssetAccountBaseACL):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    fields_pattern = models.CharField(max_length=128, default='password', verbose_name=_("Fields pattern"))

    masking_method = models.CharField(
        max_length=32,
        choices=MaskingMethod.choices,
        default=MaskingMethod.fixed_char,
        verbose_name=_("Masking Method"),
    )
    mask_pattern = models.CharField(
        max_length=128,
        verbose_name=_("Mask Pattern"),
        default="######",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Data Masking Rule")
