import uuid

import django.db.models.deletion
from django.db import migrations, models


BUILTIN_USER_ROLE_IDS = (
    '00000000-0000-0000-0000-000000000002',  # SystemAuditor
    '00000000-0000-0000-0000-000000000003',  # SystemUser
    '00000000-0000-0000-0000-000000000006',  # OrgAuditor
    '00000000-0000-0000-0000-000000000007',  # OrgUser
)


def initialize_runtime_store(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')
    RuntimeStore = apps.get_model('chat_ai', 'RuntimeStore')
    RolePermission = Role.permissions.through
    database = schema_editor.connection.alias

    RuntimeStore.objects.using(database).get_or_create(key='default')
    content_type, _ = ContentType.objects.using(database).get_or_create(
        app_label='chat_ai',
        model='runtimestore',
    )
    permission, _ = Permission.objects.using(database).get_or_create(
        content_type_id=content_type.id,
        codename='use_chatai',
        defaults={'name': 'Can use Chat AI'},
    )
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


def revoke_runtime_store_permission(apps, schema_editor):
    Permission = apps.get_model('rbac', 'Permission')
    Role = apps.get_model('rbac', 'Role')
    RolePermission = Role.permissions.through
    database = schema_editor.connection.alias
    permission = Permission.objects.using(database).filter(
        content_type__app_label='chat_ai',
        content_type__model='runtimestore',
        codename='use_chatai',
    ).first()
    if permission is None:
        return

    RolePermission.objects.using(database).filter(
        role_id__in=BUILTIN_USER_ROLE_IDS,
        permission_id=permission.id,
    ).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('rbac', '0005_report_create_delete_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='RuntimeStore',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('key', models.CharField(default='default', max_length=64, unique=True)),
                ('revision', models.PositiveBigIntegerField(default=0)),
                ('snapshot_revision', models.PositiveBigIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Chat AI runtime store',
                'db_table': 'chat_ai_runtime_store',
                'default_permissions': (),
                'permissions': (('use_chatai', 'Can use Chat AI'),),
            },
        ),
        migrations.CreateModel(
            name='RuntimeStoreRecord',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('revision', models.PositiveBigIntegerField()),
                ('commit_id', models.UUIDField(unique=True)),
                ('snapshot', models.BooleanField(default=False)),
                ('record', models.TextField()),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='records',
                    to='chat_ai.runtimestore',
                    verbose_name='Runtime store',
                )),
            ],
            options={
                'verbose_name': 'Chat AI runtime store record',
                'db_table': 'chat_ai_runtime_store_record',
                'default_permissions': (),
                'ordering': ('revision',),
                'indexes': [
                    models.Index(
                        fields=['store', 'snapshot', '-revision'],
                        name='chat_ai_rt_snap_rev_idx',
                    ),
                ],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('store', 'revision'),
                        name='chat_ai_rt_store_rev_uniq',
                    ),
                ],
            },
        ),
        migrations.RunPython(
            initialize_runtime_store,
            revoke_runtime_store_permission,
        ),
    ]
