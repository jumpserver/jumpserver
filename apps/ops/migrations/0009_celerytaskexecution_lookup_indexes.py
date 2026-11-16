from django.db import migrations, models


INDEXES = [
    models.Index(fields=['name', '-date_published', '-id'], name='ops_task_name_recent_idx'),
]


def add_indexes(apps, schema_editor):
    model = apps.get_model('ops', 'CeleryTaskExecution')
    for index in INDEXES:
        if schema_editor.connection.vendor == 'mysql':
            # Task names allow 1024 characters, exceeding InnoDB's composite
            # index key limit. A prefix preserves the full stored name and SQL
            # equality checks while supporting both utf8mb3 and utf8mb4 tables.
            sql = str(index.create_sql(model, schema_editor))
            name_column = schema_editor.quote_name('name')
            sql = sql.replace(name_column, f'{name_column}(191)')
            schema_editor.execute(sql)
        else:
            schema_editor.add_index(model, index)


def remove_indexes(apps, schema_editor):
    model = apps.get_model('ops', 'CeleryTaskExecution')
    for index in reversed(INDEXES):
        schema_editor.remove_index(model, index)


class Migration(migrations.Migration):
    dependencies = [
        ('ops', '0008_alter_adhoc_args_alter_historicaljob_args_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(add_indexes, remove_indexes, atomic=False)],
            state_operations=[
                migrations.AddIndex(model_name='celerytaskexecution', index=index)
                for index in INDEXES
            ],
        ),
    ]
