from django.db import migrations
from django.db.models import Count


def enforce_unique_favorite_asset(apps, schema_editor):
    favorite_asset = apps.get_model('assets', 'FavoriteAsset')

    duplicate_groups = (
        favorite_asset.objects.values('user_id', 'asset_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )
    for group in duplicate_groups.iterator(chunk_size=1000):
        favorite_ids = list(
            favorite_asset.objects.filter(
                user_id=group['user_id'], asset_id=group['asset_id']
            )
            .order_by('-date_updated', '-date_created', 'id')
            .values_list('id', flat=True)
        )
        favorite_asset.objects.filter(id__in=favorite_ids[1:]).delete()

    connection = schema_editor.connection
    table_name = favorite_asset._meta.db_table
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table_name)
    unique_columns = {
        tuple(constraint['columns'])
        for constraint in constraints.values()
        if constraint.get('unique')
    }
    old_fields = ('user', 'asset', 'folder')
    new_fields = ('user', 'asset')
    old_columns = tuple(
        favorite_asset._meta.get_field(field).column for field in old_fields
    )
    new_columns = tuple(
        favorite_asset._meta.get_field(field).column for field in new_fields
    )

    if old_columns in unique_columns:
        schema_editor.alter_unique_together(
            favorite_asset, {old_fields}, set()
        )
    if new_columns not in unique_columns:
        schema_editor.alter_unique_together(
            favorite_asset, set(), {new_fields}
        )


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0027_web_allowed_urls'),
    ]

    operations = [
        migrations.RunPython(
            enforce_unique_favorite_asset,
            reverse_code=migrations.RunPython.noop,
            atomic=False,
        ),
    ]
