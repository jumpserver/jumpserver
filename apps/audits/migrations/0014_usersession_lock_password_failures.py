from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('audits', '0013_usersession_is_locked')]
    operations = [migrations.AddField(
        model_name='usersession', name='lock_password_failures',
        field=models.PositiveSmallIntegerField(default=0),
    )]
