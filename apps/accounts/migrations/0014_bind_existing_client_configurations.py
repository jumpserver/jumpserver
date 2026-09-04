import django.db.models.deletion
from django.db import migrations, models


def bind_existing_clients(apps, schema_editor):
    Client = apps.get_model('accounts', 'CredentialClientInstance')
    Configuration = apps.get_model('accounts', 'ClientAccessConfiguration')
    State = apps.get_model('accounts', 'CredentialClientStatus')
    for client in Client.objects.using(schema_editor.connection.alias).filter(configuration__isnull=True).iterator():
        configuration, _ = Configuration.objects.get_or_create(
            application_id=client.application_id, name=f'Existing {client.type.upper()}',
            defaults={'org_id': client.org_id, 'type': client.type},
        )
        ids = State.objects.filter(client_id=client.id).values_list('binding__credential_id', flat=True)
        configuration.credentials.add(*ids)
        client.configuration_id = configuration.id
        client.save(update_fields=['configuration'])


def rename_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    for permission in Permission.objects.filter(
        content_type__app_label='accounts', codename__endswith='_credentialpolicy'
    ):
        permission.codename = permission.codename.replace('_credentialpolicy', '_applicationcredential')
        permission.name = permission.name.replace('credential policy', 'application credential')
        permission.save(update_fields=['codename', 'name'])


class Migration(migrations.Migration):
    # Commit the backfill before altering foreign-key constraints on PostgreSQL.
    atomic = False
    dependencies = [('accounts', '0013_application_credential_access')]

    operations = [
        migrations.RunPython(bind_existing_clients, migrations.RunPython.noop, atomic=True),
        migrations.AlterField(
            model_name='credentialclientinstance', name='configuration',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name='instances',
                to='accounts.clientaccessconfiguration', verbose_name='Client access configuration',
            ),
        ),
        migrations.RunPython(rename_permissions, migrations.RunPython.noop, atomic=True),
    ]
