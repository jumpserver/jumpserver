from django.db import migrations


def migrate_app_perms_to_assets(apps, schema_editor):
    asset_permission_model = apps.get_model("perms", "AssetPermission")
    app_permission_model = apps.get_model("perms", "ApplicationPermission")

    count = 0
    bulk_size = 1000
    while True:
        app_perms = app_permission_model.objects.all()[count:bulk_size]
        if not app_perms:
            break
        count += len(app_perms)
        attrs = [
            'id', 'name', 'actions', 'is_active', 'date_start',
            'date_expired', 'created_by', 'from_ticket', 'comment',
            'org_id',
        ]
        asset_permissions = []

        for app_perm in app_perms:
            asset_permission = asset_permission_model()
            for attr in attrs:
                setattr(asset_permission, attr, getattr(app_perm, attr))
            asset_permission.name = f"App-{app_perm.name}"
            asset_permissions.append(asset_permission)
        asset_permission_model.objects.bulk_create(asset_permissions, ignore_conflicts=True)


def migrate_relations(apps, schema_editor):
    asset_permission_model = apps.get_model("perms", "AssetPermission")
    app_permission_model = apps.get_model("perms", "ApplicationPermission")
    m2m_names = [
        ('applications', 'assets', 'application_id', 'asset_id'),
        ('users', 'users', 'user_id', 'user_id'),
        ('user_groups', 'user_groups', 'usergroup_id', 'usergroup_id'),
        ('system_users', 'system_users', 'systemuser_id', 'systemuser_id'),
    ]

    for app_name, asset_name, app_attr, asset_attr in m2m_names:
        app_through = getattr(app_permission_model, app_name).through
        asset_through = getattr(asset_permission_model, asset_name).through

        count = 0
        bulk_size = 1000

        while True:
            app_permission_relations = app_through.objects.all()[count:bulk_size]
            if not app_permission_relations:
                break
            count += len(app_permission_relations)
            asset_through_relations = []

            for app_relation in app_permission_relations:
                asset_relation = asset_through()
                asset_relation.assetpermission_id = app_relation.applicationpermission_id
                setattr(asset_relation, asset_attr, getattr(app_relation, app_attr))
                asset_through_relations.append(asset_relation)

            asset_through.objects.bulk_create(asset_through_relations, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('perms', '0028_auto_20220316_2028'),
    ]

    operations = [
        migrations.RunPython(migrate_app_perms_to_assets),
        migrations.RunPython(migrate_relations),
    ]
