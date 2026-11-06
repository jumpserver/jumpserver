from django.db import migrations


class RemoveFieldIfExists(migrations.RemoveField):
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return
        column = model._meta.get_field(self.name).column
        with schema_editor.connection.cursor() as cursor:
            columns = schema_editor.connection.introspection.get_table_description(cursor, model._meta.db_table)
        # Some installations already recorded the briefly empty 0013 migration.
        if any(field.name == column for field in columns):
            super().database_forwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    dependencies = [('audits', '0017_expand_password_change_log_identity')]

    operations = [
        RemoveFieldIfExists(model_name='usersession', name='is_locked'),
        RemoveFieldIfExists(model_name='usersession', name='lock_password_failures'),
    ]
