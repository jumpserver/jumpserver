from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('terminal', '0015_sessionjoinrecord_joiner_display_and_more')]

    operations = [
        migrations.AddField(
            model_name='applethost',
            name='tinker_version',
            field=models.CharField(
                max_length=32, blank=True, default='', editable=False, verbose_name='Tinker version',
            ),
        ),
    ]
