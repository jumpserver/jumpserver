from copy import deepcopy
from typing import Callable

from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.mixins import DestroyModelMixin, RetrieveModelMixin
from rest_framework.response import Response

from common.db.fields import EncryptJsonDictTextField
from common.exceptions import JMSException


class CommonStorageModelMixin(models.Model):
    id: str
    type: str
    meta: dict
    objects: models.Manager

    name = models.CharField(max_length=128, verbose_name=_("Name"), unique=True)
    meta = EncryptJsonDictTextField(default={})
    is_default = models.BooleanField(default=False, verbose_name=_("Default"))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def config(self):
        config = deepcopy(self.meta)
        config['TYPE'] = self.type
        return config

    def set_to_default(self):
        self.is_default = True
        self.save(update_fields=["is_default"])
        self.__class__.objects.select_for_update().filter(is_default=True).exclude(
            id=self.id
        ).update(is_default=False)

    @classmethod
    def default(cls):
        objs = cls.objects.filter(is_default=True)
        if not objs:
            objs = cls.objects.filter(name="default", type="server")
        if not objs:
            objs = cls.objects.all()
        return objs.first()


class StorageDestroyModelMixin(DestroyModelMixin):
    def perform_destroy(self, instance):
        if instance.type_null_or_server or instance.is_default:
            raise JMSException(detail=_('Deleting the default storage is not allowed'))
        if used_by := instance.used_by():
            names = ', '.join(list(used_by))
            raise JMSException(detail=_('Cannot delete storage that is being used: {}').format(names))
        return super().perform_destroy(instance)


class StorageTestConnectiveMixin(RetrieveModelMixin):
    get_object: Callable

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            is_valid = instance.is_valid()
        except Exception as e:
            is_valid = False
            msg = _("Test failure: {}".format(str(e)))
        else:
            if is_valid:
                msg = _("Test successful")
            else:
                msg = _("Test failure: Please check configuration")
        return Response({'is_valid': is_valid, 'msg': msg})
