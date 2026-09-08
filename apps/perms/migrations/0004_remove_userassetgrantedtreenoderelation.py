from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('perms', '0003_alter_assetpermission_date_expired'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserAssetGrantedTreeNodeRelation',
        ),
    ]
