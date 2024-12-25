# Generated by Django 4.1.13 on 2024-11-26 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_gatheraccountsautomation_check_risk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accountrisk",
            name="risk",
            field=models.CharField(
                choices=[
                    ("long_time_no_login", "Long time no login"),
                    ("new_found", "New found"),
                    ("groups_changed", "Groups change"),
                    ("sudoers_changed", "Sudo changed"),
                    ("authorized_keys_changed", "Authorized keys changed"),
                    ("account_deleted", "Account delete"),
                    ("password_expired", "Password expired"),
                    ("long_time_password", "Long time no change"),
                    ("weak_password", "Weak password"),
                    ("password_error", "Password error"),
                    ("no_admin_account", "No admin account"),
                    ("others", "Others"),
                ],
                max_length=128,
                verbose_name="Risk",
            ),
        ),
    ]