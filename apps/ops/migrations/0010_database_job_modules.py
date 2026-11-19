from django.db import migrations, models


JOB_MODULES = [
    ('shell', 'Shell'), ('win_shell', 'Powershell'), ('python', 'Python'),
    ('mysql', 'MySQL'), ('mariadb', 'MariaDB'), ('postgresql', 'PostgreSQL'),
    ('sqlserver', 'SQLServer'), ('oracle', 'Oracle'), ('dameng', 'Dameng'),
    ('oceanbase', 'OceanBase'), ('db2', 'DB2'), ('clickhouse', 'ClickHouse'),
    ('raw', 'Raw'), ('huawei', 'HUAWEI'),
]


class Migration(migrations.Migration):
    dependencies = [('ops', '0009_celerytaskexecution_lookup_indexes')]

    # Choices affect API/model validation only. No table/asset/account changes.
    operations = [migrations.SeparateDatabaseAndState(state_operations=[
        migrations.AlterField(
            model_name=name, name='module',
            field=models.CharField(max_length=128, choices=JOB_MODULES,
                                   default='shell', null=True, verbose_name='Module'),
        ) for name in ('job', 'historicaljob')
    ] + [migrations.AlterField(
        model_name='adhoc', name='module',
        field=models.CharField(max_length=128, choices=JOB_MODULES[:-1],
                               default='shell', verbose_name='Module'),
    )])]
