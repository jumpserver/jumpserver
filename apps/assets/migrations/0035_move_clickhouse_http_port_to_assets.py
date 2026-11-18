from django.db import migrations


def move_clickhouse_http_ports(apps, schema_editor):
    db = schema_editor.connection.alias
    assets = apps.get_model('assets', 'Asset')._base_manager.using(db)
    protocols = apps.get_model('assets', 'Protocol')._base_manager.using(db)
    platform_protocols = (
        apps.get_model('assets', 'PlatformProtocol')._base_manager.using(db)
        .filter(name='clickhouse', setting__has_key='http_port').order_by('pk')
    )

    for platform_protocol in platform_protocols.iterator(chunk_size=1000):
        setting = dict(platform_protocol.setting)
        raw_port = setting.pop('http_port')
        try:
            port = int(str(raw_port))
        except (TypeError, ValueError):
            port = 0

        if 1 <= port <= 65535 and port != 8123:
            # No rows are needed for default ports. Preserve explicit per-asset overrides.
            asset_ids = (
                assets.filter(platform_id=platform_protocol.platform_id, protocols__name='clickhouse')
                .exclude(protocols__name='clickhouse_http').values_list('pk', flat=True).distinct()
            )
            batch = []
            for asset_id in asset_ids.iterator(chunk_size=1000):
                batch.append(protocols.model(asset_id=asset_id, name='clickhouse_http', port=port))
                if len(batch) == 1000:
                    protocols.bulk_create(batch)
                    batch = []
            if batch:
                protocols.bulk_create(batch)

        platform_protocol.setting = setting
        platform_protocol.save(using=db, update_fields=['setting'])


class Migration(migrations.Migration):
    dependencies = [('assets', '0034_builtin_device_platform_types')]
    operations = [
        # Keep the asset values on downgrade; they can no longer be represented
        # by a single platform-wide setting.
        migrations.RunPython(move_clickhouse_http_ports, migrations.RunPython.noop),
    ]
