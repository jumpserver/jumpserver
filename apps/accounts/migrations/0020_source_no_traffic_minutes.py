import django.core.validators
from django.db import migrations, models
from django.db.models.functions import Ceil


MINUTES_PER_DAY = 24 * 60


def convert_to_minutes(apps, schema_editor):
    credential = apps.get_model('accounts', 'ApplicationCredential')
    credential.objects.using(schema_editor.connection.alias).update(
        source_no_traffic_minutes=models.F('source_no_traffic_minutes') * MINUTES_PER_DAY,
    )


def convert_to_days(apps, schema_editor):
    credential = apps.get_model('accounts', 'ApplicationCredential')
    credential.objects.using(schema_editor.connection.alias).update(
        source_no_traffic_minutes=Ceil(models.F('source_no_traffic_minutes') / float(MINUTES_PER_DAY)),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0019_personal_credential_authentication_version'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationcredential',
            old_name='source_no_traffic_days',
            new_name='source_no_traffic_minutes',
        ),
        migrations.AlterField(
            model_name='applicationcredential',
            name='source_no_traffic_minutes',
            field=models.PositiveIntegerField(
                default=7 * MINUTES_PER_DAY,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(3650 * MINUTES_PER_DAY),
                ],
                verbose_name='Source account no-secret-fetch duration (minutes)',
            ),
        ),
        migrations.RunPython(convert_to_minutes, convert_to_days),
    ]
