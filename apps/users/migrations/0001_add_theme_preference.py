# Generated migration for adding theme preference to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),  # Adjust this to the latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='theme_preference',
            field=models.CharField(
                max_length=50,
                default='auto',
                choices=[
                    ('auto', 'Auto (System)'),
                    ('light', 'Light Theme'),
                    ('dark', 'Dark Theme'),
                    ('classic_green', 'Classic Green'),
                ],
                help_text='User interface theme preference',
                verbose_name='Theme Preference'
            ),
        ),
    ]
