import json
from datetime import datetime
import uuid

from django.utils.translation import ugettext_lazy as _
from django.conf import settings


class ModelJSONFieldEncoder(json.JSONEncoder):
    """ 解决一些类型的字段不能序列化的问题 """

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(settings.DATETIME_DISPLAY_FORMAT)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, type(_("ugettext_lazy"))):
            return str(obj)
        else:
            return super().default(obj)
