
from django.db import migrations, connection


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    access_key_table_exist = 'users_accesskey' in connection.introspection.table_names()
    private_token_sql_exist = 'users_privatetoken' in connection.introspection.table_names()
    insert_access_key_sql = "INSERT INTO authentication_accesskey(id, secret, user_id) " \
                            "SELECT id, secret, user_id from users_accesskey"
    rename_access_key_sql = "RENAME TABLE users_accesskey TO users_accesskey_bak"
    insert_private_token_sql = "INSERT INTO authentication_privatetoken(`key`, created, user_id) " \
                               "SELECT `key`, created, user_id from users_privatetoken"
    rename_private_token_sql = "RENAME TABLE users_privatetoken TO users_privatetoken_bak"

    operations = []
    if access_key_table_exist:
        operations.append(migrations.RunSQL(insert_access_key_sql))
        operations.append(migrations.RunSQL(rename_access_key_sql))
    if private_token_sql_exist:
        operations.append(migrations.RunSQL(insert_private_token_sql))
        operations.append(migrations.RunSQL(rename_private_token_sql))

