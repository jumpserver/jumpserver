from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('acls', '0005_connectmethodacl_assets')]

    operations = [
        migrations.AddField(
            model_name='loginassetacl',
            name='review_duration',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='Review exemption duration (hours)',
                help_text='0 means approval is required for every connection.',
            ),
        ),
    ]
