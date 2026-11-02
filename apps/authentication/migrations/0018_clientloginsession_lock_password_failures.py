from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0017_clientloginsession_device_info')]
    operations = [migrations.AddField(
        model_name='clientloginsession', name='lock_password_failures',
        field=models.PositiveSmallIntegerField(default=0),
    )]
