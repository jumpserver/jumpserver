import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Permission as DjangoPermission

__all__ = ['Permission']


class Permission(DjangoPermission):
    """ 权限类 """
    class Meta:
        proxy = True

    @classmethod
    def get_permissions(cls, scope):
        # TODO: 根据类型过滤出对应的权限位并返回
        permissions = cls.objects.all()
        for permission in permissions:
            permission.name = _(permission.name)
        return permissions


class ExtraPermissionBit(models.Model):
    """ 附加权限位类，用来定义无资源类的权限，不做实体资源 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        default_permissions = []
        permissions = [
            # TODO: 添加附加权限位 (针对没有实体资源的操作权限)
            ('test_define_extra_permission_bit', _('Test define extra permission bit'))
        ]
