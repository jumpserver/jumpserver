from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0016_clientloginsession_is_locked')]

    operations = [
        migrations.AddField(
            model_name='clientloginsession', name='ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='clientloginsession', name='user_agent',
            field=models.CharField(blank=True, default='', max_length=254),
        ),
    ]
