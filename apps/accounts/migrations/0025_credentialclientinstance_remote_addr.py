from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def backfill_remote_addr(apps, schema_editor):
    Client = apps.get_model('accounts', 'CredentialClientInstance')
    Audit = apps.get_model('accounts', 'ApplicationAudit')
    alias = schema_editor.connection.alias
    latest = Audit.objects.using(alias).filter(
        org_id=OuterRef('org_id'), service_id=OuterRef('application_id'),
        instance_id=OuterRef('instance_id'), source__iexact=OuterRef('type'),
        result='success', remote_addr__isnull=False,
    ).order_by('-date_created', '-id').values('remote_addr')[:1]
    Client.objects.using(alias).filter(remote_addr__isnull=True).update(remote_addr=Subquery(latest))


class Migration(migrations.Migration):
    dependencies = [('accounts', '0024_credentialclientinstance_application_status')]

    operations = [
        migrations.AddField(
            model_name='credentialclientinstance', name='remote_addr',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='IP'),
        ),
        migrations.RunPython(backfill_remote_addr, migrations.RunPython.noop),
    ]
