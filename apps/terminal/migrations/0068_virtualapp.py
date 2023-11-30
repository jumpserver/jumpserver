# Generated by Django 4.1.10 on 2023-11-30 11:04

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('terminal', '0067_alter_replaystorage_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='VirtualApp',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.SlugField(max_length=128, unique=True, verbose_name='Name')),
                ('display_name', models.CharField(max_length=128, verbose_name='Display name')),
                ('version', models.CharField(max_length=16, verbose_name='Version')),
                ('author', models.CharField(max_length=128, verbose_name='Author')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is active')),
                ('protocols', models.JSONField(default=list, verbose_name='Protocol')),
                ('image_name', models.CharField(max_length=128, verbose_name='Image name')),
                ('image_protocol', models.CharField(default='vnc', max_length=16, verbose_name='Image protocol')),
                ('image_port', models.IntegerField(default=5900, verbose_name='Image port')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('tags', models.JSONField(default=list, verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Virtual app',
            },
        ),
        migrations.CreateModel(
            name='VirtualAppPublication',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('status', models.CharField(default='pending', max_length=16, verbose_name='Status')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='publications', to='terminal.virtualapp', verbose_name='Virtual App')),
            ],
            options={
                'verbose_name': 'Virtual app publication',
            },
        ),
        migrations.AlterField(
            model_name='terminal',
            name='type',
            field=models.CharField(choices=[('koko', 'KoKo'), ('guacamole', 'Guacamole'), ('omnidb', 'OmniDB'), ('xrdp', 'Xrdp'), ('lion', 'Lion'), ('core', 'Core'), ('celery', 'Celery'), ('magnus', 'Magnus'), ('razor', 'Razor'), ('tinker', 'Tinker'), ('video_worker', 'Video Worker'), ('chen', 'Chen'), ('kael', 'Kael'), ('panda', 'Panda')], default='koko', max_length=64, verbose_name='type'),
        ),
        migrations.CreateModel(
            name='VirtualHost',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, unique=True, verbose_name='Name')),
                ('hostname', models.CharField(max_length=128, verbose_name='Hostname')),
                ('apps', models.ManyToManyField(through='terminal.VirtualAppPublication', to='terminal.virtualapp', verbose_name='VirtualApp')),
                ('terminal', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='virtual_host', to='terminal.terminal', verbose_name='Terminal')),
            ],
            options={
                'ordering': ('-date_created',),
            },
        ),
        migrations.AddField(
            model_name='virtualapppublication',
            name='vhost',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='publications', to='terminal.virtualhost', verbose_name='Virtual Host'),
        ),
        migrations.AddField(
            model_name='virtualapp',
            name='hosts',
            field=models.ManyToManyField(through='terminal.VirtualAppPublication', to='terminal.virtualhost', verbose_name='Hosts'),
        ),
        migrations.AlterUniqueTogether(
            name='virtualapppublication',
            unique_together={('vhost', 'app')},
        ),
    ]
