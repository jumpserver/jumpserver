from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0024_remove_windows_rdp_verify_methods'),
    ]

    operations = [
        migrations.AddField(
            model_name='web',
            name='success_selector',
            field=models.CharField(
                blank=True,
                default='',
                max_length=128,
                verbose_name='Success selector',
            ),
        ),
    ]
