from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('terminal', '0016_soft_delete_lion')]

    operations = [
        migrations.AddField(
            model_name='applethost',
            name='tinker_version',
            field=models.CharField(
                max_length=32, blank=True, default='', editable=False, verbose_name='Tinker version',
            ),
        ),
    ]
