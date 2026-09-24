import common.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('acls', '0004_clipboardacl'),
    ]

    operations = [
        migrations.AddField(
            model_name='connectmethodacl',
            name='assets',
            field=common.db.fields.JSONManyToManyField(
                blank=True, default=dict, to='assets.Asset', verbose_name='Assets'
            ),
        ),
    ]
