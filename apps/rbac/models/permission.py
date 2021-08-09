import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.auth.models import ContentType as DjangoContentType

__all__ = ['Permission', 'ContentType']


class ContentType(DjangoContentType):

    class Meta:
        proxy = True


class Permission(DjangoPermission):
    """ 权限类 """
    class Meta:
        proxy = True

    @property
    def app_label_codename(self):
        return '%s.%s' % (self.content_type.app_label, self.codename)

    @classmethod
    def get_permissions(cls, scope):
        # TODO: 根据类型过滤出对应的权限位并返回
        return cls.objects.all()


class ExtraPermission(models.Model):
    """ 附加权限位类，用来定义无资源类的权限，不做实体资源 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        default_permissions = []
        permissions = [
            ('view_adminview', _('Can view admin view')),
            ('view_auditview', _('Can view audit view')),
            ('view_userview', _('Can view user view')),
        ]
