from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rbac', '0004_auto_20250626_1613'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='menupermission',
            options={
                'default_permissions': [],
                'permissions': [
                    ('view_console', 'Can view console view'),
                    ('view_pam', 'Can view pam view'),
                    ('view_audit', 'Can view audit view'),
                    ('view_workbench', 'Can view workbench view'),
                    ('view_webterminal', 'Can view web terminal'),
                    ('view_filemanager', 'Can view file manager'),
                    ('view_systemtools', 'Can view System Tools'),
                    ('view_userloginreport', 'Can view user login report'),
                    ('add_userloginreport', 'Can create user login report'),
                    ('delete_userloginreport', 'Can delete user login report'),
                    ('view_userchangepasswordreport', 'Can view user change password report'),
                    ('add_userchangepasswordreport', 'Can create user change password report'),
                    ('delete_userchangepasswordreport', 'Can delete user change password report'),
                    ('view_assetstatisticsreport', 'Can view asset statistics report'),
                    ('add_assetstatisticsreport', 'Can create asset statistics report'),
                    ('delete_assetstatisticsreport', 'Can delete asset statistics report'),
                    ('view_assetactivityreport', 'Can view asset activity report'),
                    ('add_assetactivityreport', 'Can create asset activity report'),
                    ('delete_assetactivityreport', 'Can delete asset activity report'),
                    ('view_accountstatisticsreport', 'Can view account statistics report'),
                    ('add_accountstatisticsreport', 'Can create account statistics report'),
                    ('delete_accountstatisticsreport', 'Can delete account statistics report'),
                    ('view_accountautomationreport', 'Can view account automation report'),
                    ('add_accountautomationreport', 'Can create account automation report'),
                    ('delete_accountautomationreport', 'Can delete account automation report'),
                ],
                'verbose_name': 'Menu permission',
            },
        ),
    ]
