from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('terminal', '0017_applethost_tinker_version')]

    # Command tables can be large. Leave historical rows NULL; do not backfill or add an index.
    operations = [
        migrations.AddField(
            model_name='command',
            name='source',
            field=models.CharField(
                choices=[('unknown', 'Unknown'), ('manual', 'Manual execution'), ('ai', 'AI Assistant')],
                blank=True, null=True, max_length=16, verbose_name='Source',
            ),
        ),
    ]
