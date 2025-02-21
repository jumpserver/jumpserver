# Generated by Django 4.1.13 on 2024-11-04 06:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0006_baseautomation_start_time"),
        ("accounts", "0005_account_secret_reset"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="accountrisk",
            name="account",
        ),
        migrations.AddField(
            model_name="accountrisk",
            name="asset",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="risks",
                to="assets.asset",
                verbose_name="Asset",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="accountrisk",
            name="username",
            field=models.CharField(default="", max_length=32, verbose_name="Username"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="accountrisk",
            name="risk",
            field=models.CharField(
                choices=[
                    ("zombie", "Long time no login"),
                    ("ghost", "Not managed"),
                    ("long_time_no_change", "Long time no change"),
                    ("weak_password", "Weak password"),
                    ("login_bypass", "Login bypass"),
                    ("group_change", "Group change"),
                    ("account_delete", "Account delete"),
                    ("password_expired", "Password expired"),
                    ("no_admin_account", "No admin account"),
                    ("password_error", "Password error"),
                    ("other", "Other"),
                ],
                max_length=128,
                verbose_name="Risk",
            ),
        ),
    ]
