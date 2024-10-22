# Generated by Django 4.1.13 on 2024-10-22 06:36

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0006_baseautomation_start_time"),
        ("accounts", "0005_account_secret_reset"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountCheckAutomation",
            fields=[
                (
                    "baseautomation_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="assets.baseautomation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gather account automation",
            },
            bases=("accounts.accountbaseautomation",),
        ),
        migrations.CreateModel(
            name="AccountRisk",
            fields=[
                (
                    "created_by",
                    models.CharField(
                        blank=True, max_length=128, null=True, verbose_name="Created by"
                    ),
                ),
                (
                    "updated_by",
                    models.CharField(
                        blank=True, max_length=128, null=True, verbose_name="Updated by"
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(
                        auto_now_add=True, null=True, verbose_name="Date created"
                    ),
                ),
                (
                    "date_updated",
                    models.DateTimeField(auto_now=True, verbose_name="Date updated"),
                ),
                (
                    "comment",
                    models.TextField(blank=True, default="", verbose_name="Comment"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "org_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        max_length=36,
                        verbose_name="Organization",
                    ),
                ),
                (
                    "risk",
                    models.CharField(
                        choices=[
                            ("zombie", "Zombie"),
                            ("ghost", "Ghost"),
                            ("weak_password", "Weak password"),
                            ("long_time_no_change", "Long time no change"),
                        ],
                        max_length=128,
                        verbose_name="Risk",
                    ),
                ),
                (
                    "confirmed",
                    models.BooleanField(default=False, verbose_name="Confirmed"),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="risks",
                        to="accounts.account",
                        verbose_name="Account",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
