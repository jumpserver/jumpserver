from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('acls', '0007_loginassetacl_controls')]

    # Retain the migration identifier for environments that tested this branch.
    # Preserve activation states; enabled review rules without available
    # reviewers must block connections through the normal runtime checks.
    operations = []
