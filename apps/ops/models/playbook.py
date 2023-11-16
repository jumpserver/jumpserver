import os.path
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from private_storage.fields import PrivateFileField

from ops.const import CreateMethods
from ops.exception import PlaybookNoValidEntry
from orgs.mixins.models import JMSOrgBaseModel

dangerous_keywords = (
    'hosts:localhost',
    'hosts:127.0.0.1',
    'hosts:::1',
    'delegate_to:localhost',
    'delegate_to:127.0.0.1',
    'delegate_to:::1',
    'local_action',
    'connection:local',
    'ansible_connection'
)


class Playbook(JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'), null=True)
    path = PrivateFileField(upload_to='playbooks/')
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    comment = models.CharField(max_length=1024, default='', verbose_name=_('Comment'), null=True, blank=True)
    create_method = models.CharField(max_length=128, choices=CreateMethods.choices, default=CreateMethods.blank,
                                     verbose_name=_('CreateMethod'))
    vcs_url = models.CharField(max_length=1024, default='', verbose_name=_('VCS URL'), null=True, blank=True)

    def __str__(self):
        return self.name

    def check_dangerous_keywords(self):
        result = []
        for root, dirs, files in os.walk(self.work_dir):
            for f in files:
                try:
                    if str(f).endswith('.yml') or str(f).endswith('.yaml'):
                        lines = self.search_keywords(os.path.join(root, f))
                        if len(lines) > 0:
                            for line in lines:
                                result.append({'file': f, 'line': line[0], 'keyword': line[1]})
                # 遇到无法读取的文件，跳过
                except UnicodeEncodeError:
                    continue

        return result

    @staticmethod
    def search_keywords(file):
        result = []
        with open(file, 'r') as f:
            for line_num, line in enumerate(f):
                for keyword in dangerous_keywords:
                    clear_line = line.replace(' ', '') \
                        .replace('\n', '') \
                        .replace('\r', '') \
                        .replace('\t', '') \
                        .replace('\'', '') \
                        .replace('\"', '') \
                        .replace('\v', '')
                    if keyword in clear_line:
                        result.append((line_num, keyword))
            return result

    @property
    def entry(self):
        work_dir = self.work_dir
        valid_entry = ('main.yml', 'main.yaml', 'main')
        for f in os.listdir(work_dir):
            if f in valid_entry:
                return os.path.join(work_dir, f)
        raise PlaybookNoValidEntry

    @property
    def work_dir(self):
        work_dir = os.path.join(settings.DATA_DIR, "ops", "playbook", self.id.__str__())
        return work_dir

    class Meta:
        unique_together = [('name', 'org_id', 'creator')]
        ordering = ['date_created']
