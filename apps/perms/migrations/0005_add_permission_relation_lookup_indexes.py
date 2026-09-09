from django.db import migrations, models


INDEXES = (
    (
        'perms_ap_user_perm_idx',
        'perms',
        'AssetPermission',
        'users',
        ('user', 'assetpermission'),
    ),
    (
        'perms_ap_ug_group_perm_idx',
        'perms',
        'AssetPermission',
        'user_groups',
        ('usergroup', 'assetpermission'),
    ),
    (
        'assets_an_node_asset_idx',
        'assets',
        'Asset',
        'nodes',
        ('node', 'asset'),
    ),
)


def add_permission_relation_lookup_indexes(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for name, app_label, model_name, field_name, fields in INDEXES:
            model = apps.get_model(app_label, model_name)
            through = getattr(model, field_name).through
            constraints = schema_editor.connection.introspection.get_constraints(
                cursor, through._meta.db_table
            )
            if name in constraints:
                continue
            schema_editor.add_index(
                through,
                models.Index(fields=fields, name=name),
            )


def remove_permission_relation_lookup_indexes(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        for name, app_label, model_name, field_name, fields in reversed(INDEXES):
            model = apps.get_model(app_label, model_name)
            through = getattr(model, field_name).through
            constraints = schema_editor.connection.introspection.get_constraints(
                cursor, through._meta.db_table
            )
            if name not in constraints:
                continue
            schema_editor.remove_index(
                through,
                models.Index(fields=fields, name=name),
            )


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0028_enforce_unique_favorite_asset'),
        ('perms', '0004_remove_userassetgrantedtreenoderelation'),
    ]

    operations = [
        migrations.RunPython(
            add_permission_relation_lookup_indexes,
            reverse_code=remove_permission_relation_lookup_indexes,
        ),
    ]
