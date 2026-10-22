from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('terminal', '0017_applethost_tinker_version')]

    # Command tables can be large. Leave historical rows NULL; do not backfill or add an index.
    operations = [
        migrations.AddField(
            model_name='command',
            name='source',
            field=models.SmallIntegerField(
                choices=[(0, 'Manual execution'), (1, 'AI Assistant')],
                blank=True, null=True, verbose_name='Source',
            ),
        ),
    ]
