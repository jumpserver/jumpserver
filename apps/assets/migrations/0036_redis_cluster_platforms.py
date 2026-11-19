import logging

from django.db import migrations


def add_redis_cluster_platforms(apps, schema_editor):
    db = schema_editor.connection.alias
    platforms = apps.get_model('assets', 'Platform').objects.using(db)
    protocols = apps.get_model('assets', 'PlatformProtocol').objects.using(db)
    automations = apps.get_model('assets', 'PlatformAutomation').objects.using(db)
    for name, auth_username in (('Redis-Cluster', False), ('Redis-Cluster-ACL', True)):
        platform, created = platforms.get_or_create(
            name=name,
            defaults={'category': 'database', 'type': 'redis', 'internal': True},
        )
        if not created:
            # An administrator may already use this name. Never change the
            # routing mode or authentication policy of their existing assets.
            if not platform.internal or platform.type != 'redis':
                logging.getLogger(__name__).warning('Keeping existing platform named %s', name)
            continue
        automations.create(platform=platform, ansible_enabled=False)
        protocols.create(
            platform=platform, name='redis', port=6379, primary=True, public=True,
            setting={'auth_username': auth_username, 'enable_cluster_mode': True},
        )


class Migration(migrations.Migration):
    dependencies = [('assets', '0035_move_clickhouse_http_port_to_assets')]
    operations = [
        # Platforms may already have assets assigned when downgrading.
        migrations.RunPython(add_redis_cluster_platforms, migrations.RunPython.noop),
    ]
