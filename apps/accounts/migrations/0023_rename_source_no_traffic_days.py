import django.core.validators
from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0022_credentialclientinstance_delivery_scope'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationcredential',
            old_name='standby_no_traffic_days',
            new_name='source_no_traffic_days',
        ),
        migrations.AlterField(
            model_name='applicationcredential',
            name='source_no_traffic_days',
            field=models.PositiveIntegerField(
                default=7,
                validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3650)],
                verbose_name=_('Source account no-secret-fetch duration (days)'),
            ),
        ),
    ]
