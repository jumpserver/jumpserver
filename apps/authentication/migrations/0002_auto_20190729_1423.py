# Generated by Django 4.1.13 on 2024-05-09 03:16

import common.db.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('assets', '0002_auto_20180105_1807'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tickets', '0001_initial'),
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ssotoken',
            name='user',
            field=models.ForeignKey(db_constraint=False, on_delete=common.db.models.CASCADE_SIGNAL_SKIP, to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='privatetoken',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='auth_token', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='passkey',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='connectiontoken',
            name='asset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='connection_tokens', to='assets.asset', verbose_name='Asset'),
        ),
        migrations.AddField(
            model_name='connectiontoken',
            name='from_ticket',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='connection_token', to='tickets.applyloginassetticket', verbose_name='From ticket'),
        ),
        migrations.AddField(
            model_name='connectiontoken',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='connection_tokens', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='accesskey',
            name='user',
            field=models.ForeignKey(on_delete=common.db.models.CASCADE_SIGNAL_SKIP, related_name='access_keys', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.CreateModel(
            name='SuperConnectionToken',
            fields=[
            ],
            options={
                'verbose_name': 'Super connection token',
                'permissions': [('view_superconnectiontokensecret', 'Can view super connection token secret')],
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('authentication.connectiontoken',),
        ),
    ]
