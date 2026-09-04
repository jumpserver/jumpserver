from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('assets', '0024_remove_windows_rdp_verify_methods'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='node',
            index=models.Index(
                fields=['org_id', 'parent_key', 'value', 'id'],
                name='assets_node_org_parent_val_idx',
            ),
        ),
    ]
