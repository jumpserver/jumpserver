# coding:utf-8
from __future__ import unicode_literals, absolute_import

from django.db import models
import logging
from django.utils.translation import ugettext_lazy as _

from common.utils import encrypt, decrypt

logger = logging.getLogger(__name__)


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    bandwidth = models.CharField(max_length=32, blank=True, verbose_name=_('Bandwidth'))
    contact = models.CharField(max_length=16, blank=True, verbose_name=_('Contact'))
    phone = models.CharField(max_length=32, blank=True, verbose_name=_('Phone'))
    address = models.CharField(max_length=128, blank=True, verbose_name=_("Address"))
    network = models.TextField(blank=True, verbose_name=_('Network'))
    date_created = models.DateTimeField(auto_now=True, null=True, verbose_name=_('Date added'))
    operator = models.CharField(max_length=32, blank=True, verbose_name=_('Operator'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'idc'

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            idc = cls(name=forgery_py.name.full_name(),
                      bandwidth='200M',
                      contact=forgery_py.name.full_name(),
                      phone=forgery_py.address.phone(),
                      address=forgery_py.address.city() + forgery_py.address.street_address(),
                      network="192.168.1.10/24\n192.168.1.20",
                      operator=choice(['北京联通', '北京电信', 'BGP全网通']),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                idc.save()
                logger.debug('Generate fake asset group: %s' % idc.name)
            except IntegrityError:
                print('Error continue')
                continue


class AssetExtend(models.Model):
    key = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('KEY'))
    value = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('VALUE'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_("Created by"))
    date_created = models.DateTimeField(auto_now=True, null=True, blank=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return '%(key)s: %(value)s' % {'key': self.key, 'value': self.value}

    @classmethod
    def initial(cls):
        for k, v in (
                (_('status'), _('In use')),
                (_('status'), _('Out of use')),
                (_('type'), _('Server')),
                (_('type'), _('VM')),
                (_('type'), _('Switch')),
                (_('type'), _('Router')),
                (_('type'), _('Firewall')),
                (_('type'), _('Storage')),
                (_('env'), _('Production')),
                (_('env'), _('Development')),
                (_('env'), _('Testing')),
                ):
            cls.objects.create(key=k, value=v, created_by='System')

    class Meta:
        db_table = 'asset_extend'


class AdminUser(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, verbose_name=_('Password'))
    _private_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH private key'))
    _public_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    as_default = models.BooleanField(default=False, verbose_name=_('As default'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now=True, null=True)
    created_by = models.CharField(max_length=32, null=True, verbose_name=_('Created by'))

    def __unicode__(self):
        return self.name

    @property
    def password(self):
        return decrypt(self._password)

    @password.setter
    def password(self, password_raw):
        self._password = encrypt(password_raw)

    @property
    def private_key(self):
        return decrypt(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = encrypt(private_key_raw)

    @property
    def public_key(self):
        return decrypt(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = encrypt(public_key_raw)

    class Meta:
        db_table = 'admin_user'

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue


class SystemUser(models.Model):
    PROTOCOL_CHOICES = (
        ('ssh', 'ssh'),
    )
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, verbose_name=_('Password'))
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    _private_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH private key'))
    _public_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    as_default = models.BooleanField(default=False, verbose_name=_('As default'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    auto_update = models.BooleanField(default=True, verbose_name=_('Auto update pass/key'))
    sudo = models.TextField(max_length=4096, default='/user/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    home = models.CharField(max_length=64, blank=True, verbose_name=_('Home'))
    uid = models.IntegerField(null=True, blank=True, verbose_name=_('Uid'))
    date_created = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    @property
    def password(self):
        return decrypt(self._password)

    @password.setter
    def password(self, password_raw):
        self._password = encrypt(password_raw)

    @property
    def private_key(self):
        return decrypt(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = encrypt(private_key_raw)

    @property
    def public_key(self):
        return decrypt(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = encrypt(public_key_raw)

    def get_assets_inherit_from_asset_groups(self):
        assets = set()
        asset_groups = self.asset_groups.all()
        for asset_group in asset_groups:
            for asset in asset_group.assets.all():
                setattr(asset, 'is_inherit_from_asset_groups', True)
                setattr(asset, 'inherit_from_asset_groups',
                        getattr(asset, b'inherit_from_asset_groups', set()).add(asset_group))
                assets.add(asset)
        return assets

    def get_assets(self):
        assets = set(self.assets.all()) | self.get_assets_inherit_from_asset_groups()
        return list(assets)

    class Meta:
        db_table = 'system_user'

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue


class AssetGroup(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    system_users = models.ManyToManyField(SystemUser, related_name='asset_groups', blank=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now=True, null=True, verbose_name=_('Date added'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'asset_group'

    @classmethod
    def initial(cls):
        asset_group = cls(name=_('Default'), commont=_('Default asset group'))
        asset_group.save()

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            group = cls(name=forgery_py.name.full_name(),
                        comment=forgery_py.lorem_ipsum.sentence(),
                        created_by='Fake')
            try:
                group.save()
                logger.debug('Generate fake asset group: %s' % group.name)
            except IntegrityError:
                print('Error continue')
                continue


class Asset(models.Model):
    ip = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('IP'))
    other_ip = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Other IP'))
    remote_card_ip = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Remote card IP'))
    hostname = models.CharField(max_length=128, unique=True, null=True, blank=True, verbose_name=_('Hostname'))
    port = models.IntegerField(null=True, blank=True, verbose_name=_('Port'))
    groups = models.ManyToManyField(AssetGroup, related_name='assets', verbose_name=_('Asset groups'))
    username = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Admin user'))
    password = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Admin password"))
    admin_user = models.ForeignKey(AdminUser, null=True, related_name='assets',
                                   on_delete=models.SET_NULL, verbose_name=_("Admin user"))
    system_users = models.ManyToManyField(SystemUser, blank=True, related_name='assets', verbose_name=_("System User"))
    idc = models.ForeignKey(IDC, null=True, related_name='assets', on_delete=models.SET_NULL, verbose_name=_('IDC'))
    mac_address = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Mac address"))
    brand = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Brand'))
    cpu = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('CPU'))
    memory = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Memory'))
    disk = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk'))
    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    cabinet_no = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Cabinet number'))
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=_('Cabinet position'))
    number = models.CharField(max_length=32, null=True, blank=True, unique=True, verbose_name=_('Asset number'))
    status = models.ManyToManyField(AssetExtend, related_name="asset_status_extend", verbose_name=_('Asset status'))
    type = models.ManyToManyField(AssetExtend, related_name="asset_type_extend", verbose_name=_('Asset type'))
    env = models.ManyToManyField(AssetExtend,  related_name="asset_env_extend", verbose_name=_('Asset environment'))
    sn = models.CharField(max_length=128, null=True, blank=True, unique=True, verbose_name=_('Serial number'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    date_created = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name=_('Date added'))
    comment = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return '%(ip)s:%(port)s' % {'ip': self.ip, 'port': self.port}

    def initial(self):
        pass

    class Meta:
        db_table = 'asset'
        index_together = ('ip', 'port')

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            asset = cls(ip='%s.%s.%s.%s' % tuple([forgery_py.forgery.basic.text(length=3, digits=True)
                                                  for i in range(0, 4)]),
                        admin_user=choice(AdminUser.objects.all()),
                        idc=choice(IDC.objects.all()),
                        port=22,
                        created_by='Fake')
            try:
                asset.save()
                asset.system_users = [choice(SystemUser.objects.all()) for i in range(3)]
                asset.groups = [choice(AssetGroup.objects.all()) for i in range(3)]
                logger.debug('Generate fake asset : %s' % asset.ip)
            except IntegrityError:
                print('Error continue')
                continue


class Label(models.Model):
    key = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('KEY'))
    value = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('VALUE'))
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Asset'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_("Created by"))
    date_created = models.DateTimeField(auto_now=True, null=True)
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'label'


def generate_fake():
    for cls in (AssetGroup, IDC, AdminUser, SystemUser, Asset):
        cls.generate_fake()
