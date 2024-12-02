"""
-- This script is necessary to add the 'release_assets' column to the 'xpack_syncinstancetask' table.
-- After upgrading to the latest version 3, upgrading to version 4 is not an issue.
--
-- However, if you perform a fresh installation of versions 4.0, 4.1, 4.2, or 4.3,
-- upgrading to version 4.4 or later may cause issues (this script must be executed to add the column).
--
-- Fresh installations of version 4.4 and later versions will not encounter these issues.
"""

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
