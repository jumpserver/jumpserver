from django.db import migrations


def migrate_app_provider_hosts(apps, schema_editor):
    app_provider_model = apps.get_model('terminal', 'AppProvider')
    asset_model = apps.get_model('assets', 'Asset')
    protocol_model = apps.get_model('assets', 'Protocol')
    platform_model = apps.get_model('assets', 'Platform')

    platform = platform_model.objects.get(name='VirtualAppHost')
    managed_providers = app_provider_model.objects.exclude(host_id=None)
    host_ids = list(managed_providers.values_list('host_id', flat=True))
    if not host_ids:
        return

    managed_providers.update(runtime_type='docker', connection_mode='ssh')
    asset_model.objects.filter(id__in=host_ids).update(platform_id=platform.id)
    protocol_model.objects.filter(asset_id__in=host_ids).exclude(name='ssh').delete()
    existing_ssh_asset_ids = set(
        protocol_model.objects.filter(asset_id__in=host_ids, name='ssh')
        .values_list('asset_id', flat=True)
    )
    protocol_model.objects.bulk_create([
        protocol_model(asset_id=host_id, name='ssh', port=22)
        for host_id in host_ids
        if host_id not in existing_ssh_asset_ids
    ])


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0024_add_virtual_app_host_platform'),
        ('terminal', '0014_app_provider_deployment'),
    ]

    operations = [
        migrations.RunPython(
            migrate_app_provider_hosts,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
