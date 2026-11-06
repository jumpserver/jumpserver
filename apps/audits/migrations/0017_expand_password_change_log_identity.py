from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0016_merge_application_credential_calls'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passwordchangelog',
            name='user',
            field=models.CharField(max_length=258, verbose_name='User'),
        ),
        migrations.AlterField(
            model_name='passwordchangelog',
            name='change_by',
            field=models.CharField(max_length=258, verbose_name='Change by'),
        ),
    ]
