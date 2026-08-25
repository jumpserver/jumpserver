from django.db import migrations


def enable_internal_http_safe_mode(apps, schema_editor):
    platform_protocol_model = apps.get_model('assets', 'PlatformProtocol')
    protocols = platform_protocol_model.objects.filter(
        platform__internal=True,
        name='http',
    )

    for protocol in protocols:
        setting = {**(protocol.setting or {}), 'safe_mode': True}
        if protocol.setting != setting:
            protocol.setting = setting
            protocol.save(update_fields=['setting'])


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0019_alter_asset_connectivity'),
    ]

    operations = [
        migrations.RunPython(enable_internal_http_safe_mode, migrations.RunPython.noop),
    ]
