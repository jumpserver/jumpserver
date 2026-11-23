from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0009_enforce_user_email_uniqueness')]
    operations = [
        migrations.CreateModel(
            name='JDMCNodeBinding',
            fields=[
                ('name', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('user', models.OneToOneField(null=True, on_delete=models.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
