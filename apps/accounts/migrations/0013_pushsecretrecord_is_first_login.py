from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0012_account_follow_template')]

    operations = [
        migrations.AddField(
            model_name='pushsecretrecord', name='is_first_login',
            field=models.BooleanField(default=False),
        ),
    ]
