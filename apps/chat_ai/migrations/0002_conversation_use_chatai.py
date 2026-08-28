from django.db import migrations


BUILTIN_USER_ROLE_IDS = (
    '00000000-0000-0000-0000-000000000002',  # SystemAuditor
    '00000000-0000-0000-0000-000000000003',  # SystemUser
    '00000000-0000-0000-0000-000000000006',  # OrgAuditor
    '00000000-0000-0000-0000-000000000007',  # OrgUser
)


def get_chat_ai_permission(apps, database):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('rbac', 'Permission')

    content_type, _ = ContentType.objects.using(database).get_or_create(
        app_label='chat_ai',
        model='conversation',
    )
    permission, _ = Permission.objects.using(database).get_or_create(
        content_type_id=content_type.id,
        codename='use_chatai',
        defaults={'name': 'Can use Chat AI'},
    )
    return permission


def grant_chat_ai_permission(apps, schema_editor):
    Role = apps.get_model('rbac', 'Role')
    RolePermission = Role.permissions.through
    database = schema_editor.connection.alias
    permission = get_chat_ai_permission(apps, database)
    role_ids = Role.objects.using(database).filter(
        id__in=BUILTIN_USER_ROLE_IDS,
        builtin=True,
    ).values_list('id', flat=True)

    RolePermission.objects.using(database).bulk_create(
        [
            RolePermission(role_id=role_id, permission_id=permission.id)
            for role_id in role_ids
        ],
        ignore_conflicts=True,
    )


def revoke_chat_ai_permission(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')
    RolePermission = Role.permissions.through
    database = schema_editor.connection.alias
    permission = Permission.objects.using(database).filter(
        content_type__app_label='chat_ai',
        content_type__model='conversation',
        codename='use_chatai',
    ).first()
    if permission is None:
        return

    RolePermission.objects.using(database).filter(
        role_id__in=BUILTIN_USER_ROLE_IDS,
        permission_id=permission.id,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('chat_ai', '0001_initial'),
        ('rbac', '0005_report_create_delete_permissions'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='conversation',
            options={
                'ordering': ('-date_updated',),
                'permissions': [('use_chatai', 'Can use Chat AI')],
                'verbose_name': 'Chat AI conversation',
            },
        ),
        migrations.RunPython(
            grant_chat_ai_permission,
            revoke_chat_ai_permission,
        ),
    ]
