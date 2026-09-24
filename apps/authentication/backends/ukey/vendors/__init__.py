from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class UKeyVendor(TextChoices):
    JI_DA = 'ji_da', _('JIT')
    LONG_MAI = 'long_mai', _('Longmai')
