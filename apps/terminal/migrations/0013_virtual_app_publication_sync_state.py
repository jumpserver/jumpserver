from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('terminal', '0012_app_provider_runtime_connection'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualapppublication',
            name='app_version',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='Published version'),
        ),
        migrations.AddField(
            model_name='virtualapppublication',
            name='image_digest',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Image digest'),
        ),
        migrations.AddField(
            model_name='virtualapppublication',
            name='date_synced',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date synced'),
        ),
    ]
