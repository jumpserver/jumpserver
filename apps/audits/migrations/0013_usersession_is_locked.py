from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('audits', '0012_userloginlog_lookup_indexes')]
    operations = [
        migrations.AddField(
            model_name='usersession', name='is_locked', field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usersession', name='lock_password_failures',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
