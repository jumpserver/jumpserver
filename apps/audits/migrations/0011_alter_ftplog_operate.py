from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0010_ticketaudit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ftplog',
            name='operate',
            field=models.CharField(
                choices=[
                    ('create', 'Create file'),
                    ('mkdir', 'Mkdir'),
                    ('rmdir', 'Rmdir'),
                    ('delete', 'Delete'),
                    ('upload', 'Upload'),
                    ('rename', 'Rename'),
                    ('symlink', 'Symlink'),
                    ('download', 'Download'),
                    ('rename_dir', 'Rename dir'),
                ],
                max_length=16,
                verbose_name='Operate',
            ),
        ),
    ]
