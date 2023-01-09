from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PortRangeValidator:
    def __init__(self, start=1, end=65535):
        self.start = start
        self.end = end
        self.error_message = _("Invalid port range, should be like and within {}-{}").format(start, end)

    def __call__(self, data):
        try:
            _range = data.split('-')
            if len(_range) != 2:
                raise ValueError('')
            _range = [int(i) for i in _range]
            if _range[0] > _range[1]:
                raise ValueError('')
            if _range[0] < self.start or _range[1] > self.end:
                raise ValueError('')
        except ValueError:
            raise ValidationError(self.error_message)
