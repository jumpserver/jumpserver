from django.db import models
from django.utils.translation import gettext_lazy as _


class StrategyChoice(models.TextChoices):
    push = 'push', _('Push')
    verify = 'verify', _('Verify')
    collect = 'collect', _('Collect')
    change_secret = 'change_secret', _('Change password')


class SSHKeyStrategy(models.TextChoices):
    add = 'add', _('Append SSH KEY')
    set = 'set', _('Empty and append SSH KEY')
    set_jms = 'set_jms', _('Replace (Replace only keys pushed by JumpServer) ')


class PasswordStrategy(models.TextChoices):
    custom = 'custom', _('Custom password')
    random_one = 'random_one', _('All assets use the same random password')
    random_all = 'random_all', _('All assets use different random password')


string_punctuation = '!#$%&()*+,-.:;<=>?@[]^_~'
DEFAULT_PASSWORD_LENGTH = 30
DEFAULT_PASSWORD_RULES = {
    'length': DEFAULT_PASSWORD_LENGTH,
    'symbol_set': string_punctuation
}


class CreateMethods(models.TextChoices):
    blank = 'blank', _('Blank')
    vcs = 'vcs', _('VCS')


class Types(models.TextChoices):
    adhoc = 'adhoc', _('Adhoc')
    playbook = 'playbook', _('Playbook')
    upload_file = 'upload_file', _('Upload File')


class RunasPolicies(models.TextChoices):
    privileged_only = 'privileged_only', _('Privileged Only')
    privileged_first = 'privileged_first', _('Privileged First')
    skip = 'skip', _('Skip')


class JobModules(models.TextChoices):
    shell = 'shell', _('Shell')
    winshell = 'win_shell', _('Powershell')
    python = 'python', _('Python')
    mysql = 'mysql', _('MySQL')
    postgresql = 'postgresql', _('PostgreSQL')
    sqlserver = 'sqlserver', _('SQLServer')
    raw = 'raw', _('Raw')


class AdHocModules(models.TextChoices):
    shell = 'shell', _('Shell')
    winshell = 'win_shell', _('Powershell')
    python = 'python', _('Python')
    mysql = 'mysql', _('MySQL')
    mariadb = 'mariadb', _('MariaDB')
    postgresql = 'postgresql', _('PostgreSQL')
    sqlserver = 'sqlserver', _('SQLServer')
    oracle = 'oracle', _('Oracle')
    raw = 'raw', _('Raw')


class JobStatus(models.TextChoices):
    running = 'running', _('Running')
    success = 'success', _('Success')
    timeout = 'timeout', _('Timeout')
    failed = 'failed', _('Failed')


# celery 日志完成之后，写入的魔法字符，作为结束标记
CELERY_LOG_MAGIC_MARK = b'\x00\x00\x00\x00\x00'
