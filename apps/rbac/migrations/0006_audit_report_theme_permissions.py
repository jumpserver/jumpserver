from django.db import migrations


REPORT_PERMISSIONS = [
    ('view_auditreport', 'Can view comprehensive audit report'),
    ('view_activityreport', 'Can view operations activity report'),
    ('view_securityreport', 'Can view security event report'),
    ('view_inventoryreport', 'Can view asset and account overview'),
    ('view_accountreport', 'Can view account operations report'),
]


def preserve_audit_report_access(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Role = apps.get_model('rbac', 'Role')
    db = schema_editor.connection.alias
    content_type, _ = ContentType.objects.using(db).get_or_create(
        app_label='rbac', model='menupermission',
    )
    # Previously every audit-console role could open any theme for which the
    # user had source permissions. Preserve that access without granting data.
    role_ids = list(Role.objects.using(db).filter(
        permissions__content_type=content_type, permissions__codename='view_audit',
    ).values_list('id', flat=True).distinct())
    bindings = Role.permissions.through
    for codename, name in REPORT_PERMISSIONS:
        permission, _ = Permission.objects.using(db).get_or_create(
            content_type=content_type, codename=codename, defaults={'name': name},
        )
        bindings.objects.using(db).bulk_create([
            bindings(role_id=role_id, permission_id=permission.pk) for role_id in role_ids
        ], batch_size=1000, ignore_conflicts=True)


def remove_audit_report_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.using(schema_editor.connection.alias).filter(
        content_type__app_label='rbac', content_type__model='menupermission',
        codename__in=[codename for codename, _ in REPORT_PERMISSIONS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '0005_report_create_delete_permissions'),
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
                    ('view_jdmc', 'Can view jdmc console'),
                    ('view_systemtools', 'Can view System Tools'),
                    ('view_auditreport', 'Can view comprehensive audit report'),
                    ('view_activityreport', 'Can view operations activity report'),
                    ('view_securityreport', 'Can view security event report'),
                    ('view_inventoryreport', 'Can view asset and account overview'),
                    ('view_accountreport', 'Can view account operations report'),
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
        migrations.RunPython(preserve_audit_report_access, remove_audit_report_permissions),
    ]
