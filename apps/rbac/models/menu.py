import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class MenuPermission(models.Model):
    """ 附加权限位类，用来定义无资源类的权限，不做实体资源 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    class Meta:
        default_permissions = []
        verbose_name = _('Menu permission')
        permissions = [
            ('view_console', _('Can view console view')),
            ('view_pam', _('Can view pam view')),
            ('view_audit', _('Can view audit view')),
            ('view_workbench', _('Can view workbench view')),
            ('view_webterminal', _('Can view web terminal')),
            ('view_filemanager', _('Can view file manager')),
            ('view_systemtools', _('Can view System Tools')),
            ('view_userloginreport', _('Can view user login report')),
            ('view_userchangepasswordreport', _('Can view user change password report')),
            ('view_assetstatisticsreport', _('Can view asset statistics report')),
            ('view_assetactivityreport', _('Can view asset activity report')),
            ('view_accountstatisticsreport', _('Can view account statistics report')),
            ('view_accountautomationreport', _('Can view account automation report')),
        ]
