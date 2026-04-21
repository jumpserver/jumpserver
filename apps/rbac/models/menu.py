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
            ('view_jdmc', _('Can view jdmc console')),
            ('view_systemtools', _('Can view System Tools')),
            ('view_userloginreport', _('Can view user login report')),
            ('add_userloginreport', _('Can create user login report')),
            ('delete_userloginreport', _('Can delete user login report')),
            ('view_userchangepasswordreport', _('Can view user change password report')),
            ('add_userchangepasswordreport', _('Can create user change password report')),
            ('delete_userchangepasswordreport', _('Can delete user change password report')),
            ('view_assetstatisticsreport', _('Can view asset statistics report')),
            ('add_assetstatisticsreport', _('Can create asset statistics report')),
            ('delete_assetstatisticsreport', _('Can delete asset statistics report')),
            ('view_assetactivityreport', _('Can view asset activity report')),
            ('add_assetactivityreport', _('Can create asset activity report')),
            ('delete_assetactivityreport', _('Can delete asset activity report')),
            ('view_accountstatisticsreport', _('Can view account statistics report')),
            ('add_accountstatisticsreport', _('Can create account statistics report')),
            ('delete_accountstatisticsreport', _('Can delete account statistics report')),
            ('view_accountautomationreport', _('Can view account automation report')),
            ('add_accountautomationreport', _('Can create account automation report')),
            ('delete_accountautomationreport', _('Can delete account automation report')),
        ]
