import common.db.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0007_user_allowed_mfa_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=common.db.fields.EncryptCharField(
                max_length=256, storage_max_length=1536,
                unique=True, verbose_name='Email',
            ),
        ),
    ]
