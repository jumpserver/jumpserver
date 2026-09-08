import uuid

from django.conf import settings
from django.db import migrations, models

import accounts.models.mixins.vault


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_merge_0009_account_migrations'),
        ('assets', '0025_node_tree_pagination_index'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalAssetCredential',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('username', models.CharField(max_length=128, verbose_name='Username')),
                ('secret_type', models.CharField(choices=[('password', 'Password'), ('ssh_key', 'SSH key'), ('ssh_certificate', 'SSH certificate'), ('access_key', 'Access key'), ('token', 'Token'), ('api_key', 'API key')], default='password', max_length=16, verbose_name='Secret type')),
                ('_secret', accounts.models.mixins.vault.VaultSecretField(blank=True, null=True, verbose_name='Secret')),
                ('protocol', models.CharField(choices=[('ssh', 'SSH'), ('sftp', 'SFTP'), ('rdp', 'RDP'), ('telnet', 'Telnet'), ('vnc', 'VNC'), ('winrm', 'WinRM'), ('mysql', 'MySQL'), ('mariadb', 'MariaDB'), ('oracle', 'Oracle'), ('postgresql', 'PostgreSQL'), ('sqlserver', 'SQLServer'), ('db2', 'DB2'), ('dameng', 'Dameng'), ('clickhouse', 'ClickHouse'), ('redis', 'Redis'), ('mongodb', 'MongoDB'), ('k8s', 'K8s'), ('http', 'HTTP(s)'), ('chatgpt', 'ChatGPT')], default='ssh', max_length=16, verbose_name='Protocol')),
                ('connectivity', models.CharField(choices=[('-', 'Unknown'), ('na', 'N/A'), ('ok', 'OK'), ('err', 'Error'), ('rdp_err', 'RDP error'), ('auth_err', 'Authentication error'), ('password_err', 'Invalid password error'), ('openssh_key_err', 'OpenSSH key error'), ('ntlm_err', 'NTLM credentials rejected error'), ('create_temp_err', 'Create temporary error')], default='-', max_length=16, verbose_name='Connectivity')),
                ('date_verified', models.DateTimeField(null=True, verbose_name='Date verified')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('version', models.PositiveIntegerField(default=1, verbose_name='Version')),
                ('asset', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='personal_credentials', to='assets.asset', verbose_name='Asset')),
                ('owner', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='personal_asset_credentials', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
            ],
            options={
                'verbose_name': 'Personal asset credential',
                'default_permissions': (),
                'indexes': [
                    models.Index(fields=['owner', 'asset', 'is_active'], name='acct_pcred_owner_asset_idx'),
                    models.Index(fields=['org_id', 'owner'], name='acct_pcred_org_owner_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('org_id', 'owner', 'asset', 'username', 'secret_type', 'protocol'), name='acct_personal_cred_uniq'),
                ],
            },
        ),
    ]
