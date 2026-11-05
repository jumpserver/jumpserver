from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0010_connectiontoken_personal_credential_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='connectiontoken',
            name='date_last_used',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Date last used'),
        ),
    ]
