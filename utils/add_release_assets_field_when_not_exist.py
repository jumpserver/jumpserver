import os
import sys
import django

from django.db import connection


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'apps'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')
django.setup()

mysql_statement = """
ALTER TABLE xpack_syncinstancetask
ADD COLUMN release_assets TINYINT(1) NOT NULL;
"""

pgsql_statement = """
ALTER TABLE xpack_syncinstancetask
ADD COLUMN release_assets BOOLEAN NOT NULL DEFAULT FALSE;
"""

table_name = 'xpack_syncinstancetask'
with connection.cursor() as cursor:
    table_description = connection.introspection.get_table_description(cursor, table_name)
    existing_columns = [column.name for column in table_description]

if 'release_assets' not in existing_columns:
    with connection.cursor() as cursor:
        if connection.vendor == 'postgresql':
            cursor.execute(pgsql_statement)
        else:
            cursor.execute(mysql_statement)

print("Column added successfully.")
