from django.db import migrations, models


def preserve_existing_token_versions(apps, schema_editor):
    credential = apps.get_model('accounts', 'PersonalAssetCredential')
    credential.objects.using(schema_editor.connection.alias).update(
        authentication_version=models.F('version'),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0018_connectivity_record'),
    ]

    operations = [
        migrations.AddField(
            model_name='personalassetcredential',
            name='authentication_version',
            field=models.PositiveIntegerField(default=1, editable=False),
        ),
        migrations.RunPython(
            preserve_existing_token_versions, migrations.RunPython.noop,
        ),
    ]
