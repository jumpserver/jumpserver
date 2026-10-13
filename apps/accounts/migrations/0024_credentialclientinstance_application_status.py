from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0023_rename_source_no_traffic_days')]

    operations = [
        migrations.AddField(
            model_name='credentialclientinstance', name='rotation_enabled',
            field=models.BooleanField(default=True, editable=False),
        ),
        migrations.AddField(
            model_name='credentialclientinstance', name='application_status',
            field=models.JSONField(blank=True, default=dict, verbose_name='Application status'),
        ),
        migrations.AddField(
            model_name='credentialclientinstance', name='date_status_reported',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Status reported at'),
        ),
    ]
