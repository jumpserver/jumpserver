from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0011_personalassetcredential')]

    operations = [
        migrations.AddField(
            model_name='account',
            name='follow_template',
            field=models.BooleanField(default=False, verbose_name='Follow template'),
        ),
    ]
