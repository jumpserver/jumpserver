from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0008_alter_adhoc_args_alter_historicaljob_args_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adhoc',
            name='module',
            field=models.CharField(
                choices=[
                    ('shell', 'Shell'),
                    ('win_shell', 'Powershell'),
                    ('python', 'Python'),
                    ('mysql', 'MySQL'),
                    ('mariadb', 'MariaDB'),
                    ('postgresql', 'PostgreSQL'),
                    ('sqlserver', 'SQLServer'),
                    ('oracle', 'Oracle'),
                    ('dameng', 'Dameng'),
                    ('raw', 'Raw'),
                ],
                default='shell',
                max_length=128,
                verbose_name='Module',
            ),
        ),
    ]
