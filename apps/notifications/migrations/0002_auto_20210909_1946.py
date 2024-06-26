# Generated by Django 4.1.13 on 2024-05-09 03:16

import common.db.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0001_initial'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usermsgsubscription',
            name='user',
            field=models.OneToOneField(on_delete=common.db.models.CASCADE_SIGNAL_SKIP, related_name='user_msg_subscription', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='systemmsgsubscription',
            name='groups',
            field=models.ManyToManyField(related_name='system_msg_subscriptions', to='users.usergroup'),
        ),
        migrations.AddField(
            model_name='systemmsgsubscription',
            name='users',
            field=models.ManyToManyField(related_name='system_msg_subscriptions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='sitemessage',
            name='content',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='notifications.messagecontent'),
        ),
        migrations.AddField(
            model_name='sitemessage',
            name='user',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='messagecontent',
            name='groups',
            field=models.ManyToManyField(to='users.usergroup'),
        ),
        migrations.AddField(
            model_name='messagecontent',
            name='sender',
            field=models.ForeignKey(db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='send_site_message', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='messagecontent',
            name='users',
            field=models.ManyToManyField(related_name='recv_site_messages', through='notifications.SiteMessage', to=settings.AUTH_USER_MODEL),
        ),
    ]
