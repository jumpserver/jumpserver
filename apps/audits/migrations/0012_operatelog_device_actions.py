from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('audits', '0011_alter_storagereclamationlog_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operatelog',
            name='action',
            field=models.CharField(
                choices=[
                    ('view', 'View'),
                    ('update', 'Update'),
                    ('delete', 'Delete'),
                    ('create', 'Create'),
                    ('export', 'Export'),
                    ('download', 'Download'),
                    ('connect', 'Connect'),
                    ('login', 'Login'),
                    ('change_password', 'Change secret'),
                    ('accept', 'Accept'),
                    ('review', 'Review'),
                    ('notice', 'Notifications'),
                    ('reject', 'Reject'),
                    ('approve', 'Approve'),
                    ('close', 'Close'),
                    ('finished', 'Finished'),
                    ('ha_build', 'Build primary/standby HA'),
                    ('ha_detach', 'Detach primary/standby HA'),
                    ('patch_upgrade', 'Patch upgrade'),
                    ('system_upgrade', 'System upgrade'),
                ],
                max_length=16,
                verbose_name='Action',
            ),
        ),
    ]
