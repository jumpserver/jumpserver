from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0021_asset_date_last_login'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='automationexecution',
            index=models.Index(
                fields=['status', 'type'],
                name='assets_ae_status_type_idx',
            ),
        ),
    ]
