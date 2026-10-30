from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('authentication', '0012_connection_token_ticket')]

    operations = [
        migrations.AddField(
            model_name='clientloginsession', name='is_locked',
            field=models.BooleanField(default=False),
        ),
    ]
