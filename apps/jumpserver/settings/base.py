import os
import platform
import re

from redis.sentinel import SentinelManagedSSLConnection

if platform.system() == 'Darwin' and platform.machine() == 'arm64':
    import pymysql

    # pymysql.version_info = (1, 4, 2, "final", 0)
    pymysql.install_as_MySQLdb()

from django.urls import reverse_lazy

from .. import const
from ..const import CONFIG


def exist_or_default(path, default):
    if not os.path.exists(path):
        path = default
    return path


def parse_sentinels_host(sentinels_host):
    service_name, sentinels = None, None
    try:
        service_name, hosts = sentinels_host.split('/', 1)
        sentinels = [tuple(h.split(':', 1)) for h in hosts.split(',')]
    except Exception:
        pass
    return service_name, sentinels


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
VERSION = const.VERSION
BASE_DIR = const.BASE_DIR
PROJECT_DIR = const.PROJECT_DIR
APPS_DIR = os.path.join(PROJECT_DIR, 'apps')
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
SHARE_DIR = os.path.join(DATA_DIR, 'share')
ANSIBLE_DIR = os.path.join(SHARE_DIR, 'ansible')
CERTS_DIR = os.path.join(DATA_DIR, 'certs')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = CONFIG.SECRET_KEY

# SECURITY WARNING: keep the token secret, remove it if all koko, lion ok
BOOTSTRAP_TOKEN = CONFIG.BOOTSTRAP_TOKEN

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = CONFIG.DEBUG
# SECURITY WARNING: If you run with debug turned on, more debug msg with be log
DEBUG_DEV = CONFIG.DEBUG_DEV
# SECURITY WARNING: If you run ansible task with debug turned on, more debug msg with be log
DEBUG_ANSIBLE = CONFIG.DEBUG_ANSIBLE

# Absolute url for some case, for example email link
SITE_URL = CONFIG.SITE_URL

# Absolute url for downloading applet
APPLET_DOWNLOAD_HOST = CONFIG.APPLET_DOWNLOAD_HOST

# https://docs.djangoproject.com/en/4.1/ref/settings/
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# LOG LEVEL
LOG_LEVEL = CONFIG.LOG_LEVEL
DOMAINS = CONFIG.DOMAINS or 'localhost'
for name in ['SERVER_NAME', 'CORE_HOST']:
    env = os.environ.get(name)
    if not env:
        continue
    DOMAINS += ',{}'.format(env.replace(" ", ","))
if CONFIG.SITE_URL:
    DOMAINS += ',{}'.format(CONFIG.SITE_URL)

ALLOWED_DOMAINS = DOMAINS.split(',') if DOMAINS else ['localhost:8080']
ALLOWED_DOMAINS = [host.strip() for host in ALLOWED_DOMAINS]
ALLOWED_DOMAINS = [host.replace('http://', '').replace('https://', '') for host in ALLOWED_DOMAINS if host]
ALLOWED_DOMAINS = [host.split('/')[0] for host in ALLOWED_DOMAINS if host]
ALLOWED_DOMAINS = [re.sub(':80$|:443$', '', host) for host in ALLOWED_DOMAINS]

DEBUG_HOSTS = ('127.0.0.1', 'localhost', 'core')
DEBUG_PORT = ['8080', '80', ]
if DEBUG:
    DEBUG_PORT.extend(['4200', '9528'])
DEBUG_HOST_PORTS = ['{}:{}'.format(host, port) for host in DEBUG_HOSTS for port in DEBUG_PORT]
ALLOWED_DOMAINS.extend(DEBUG_HOST_PORTS)

print("ALLOWED_HOSTS: ", )
for host in ALLOWED_DOMAINS:
    print('  - ' + host.lstrip('.'))

ALLOWED_HOSTS = ['*']

# https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS = []
for host_port in ALLOWED_DOMAINS:
    origin = host_port.strip('.')
    if origin.startswith('http'):
        CSRF_TRUSTED_ORIGINS.append(origin)
        continue
    is_local_origin = origin.split(':')[0] in DEBUG_HOSTS
    for schema in ['https', 'http']:
        if is_local_origin and schema == 'https':
            continue
        CSRF_TRUSTED_ORIGINS.append('{}://*.{}'.format(schema, origin))

CORS_ALLOWED_ORIGINS = [o.replace('*.', '') for o in CSRF_TRUSTED_ORIGINS]
CSRF_FAILURE_VIEW = 'jumpserver.views.other.csrf_failure'
# print("CSRF_TRUSTED_ORIGINS: ")
# for origin in CSRF_TRUSTED_ORIGINS:
# print('  - ' + origin)
# Max post update field num
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Application definition

INSTALLED_APPS = [
    'orgs.apps.OrgsConfig',
    'users.apps.UsersConfig',
    'assets.apps.AssetsConfig',
    'accounts.apps.AccountsConfig',
    'perms.apps.PermsConfig',
    'ops.apps.OpsConfig',
    'settings.apps.SettingsConfig',
    'terminal.apps.TerminalConfig',
    'audits.apps.AuditsConfig',
    'authentication.apps.AuthenticationConfig',  # authentication
    'applications.apps.ApplicationsConfig',
    'tickets.apps.TicketsConfig',
    'acls.apps.AclsConfig',
    'notifications.apps.NotificationsConfig',
    'rbac.apps.RBACConfig',
    'labels.apps.LabelsConfig',
    'rest_framework',
    'rest_framework_swagger',
    'drf_yasg',
    'django_cas_ng',
    'channels',
    'django_filters',
    'bootstrap3',
    'captcha',
    'corsheaders',
    'private_storage',
    'django_celery_beat',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.forms',
    'common.apps.CommonConfig',  # 这个放到内置的最后, django ready
    'simple_history',  # 这个要放到最后，别特么瞎改顺序
]

MIDDLEWARE = [
    'jumpserver.middleware.StartMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jumpserver.middleware.TimezoneMiddleware',
    'jumpserver.middleware.DemoMiddleware',
    'jumpserver.middleware.RequestMiddleware',
    'jumpserver.middleware.RefererCheckMiddleware',
    'jumpserver.middleware.SQLCountMiddleware',
    'orgs.middleware.OrgMiddleware',
    'authentication.backends.oidc.middleware.OIDCRefreshIDTokenMiddleware',
    'authentication.backends.cas.middleware.CASMiddleware',
    'authentication.middleware.MFAMiddleware',
    'authentication.middleware.ThirdPartyLoginMiddleware',
    'authentication.middleware.SessionCookieMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'jumpserver.middleware.EndMiddleware',
]

if DEBUG or DEBUG_DEV:
    INSTALLED_APPS.insert(0, 'daphne')

ROOT_URLCONF = 'jumpserver.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.i18n',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'jumpserver.context_processor.jumpserver_processor',
                'orgs.context_processor.org_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'jumpserver.wsgi.application'

LOGIN_REDIRECT_URL = reverse_lazy('index')
LOGIN_URL = reverse_lazy('authentication:login')
LOGOUT_REDIRECT_URL = CONFIG.LOGOUT_REDIRECT_URL

SESSION_COOKIE_DOMAIN = CONFIG.SESSION_COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = CONFIG.SESSION_COOKIE_DOMAIN

# 设置 SESSION_COOKIE_NAME_PREFIX_KEY
# 解决 不同域 session csrf cookie 获取混乱问题
SESSION_COOKIE_NAME_PREFIX_KEY = 'SESSION_COOKIE_NAME_PREFIX'
SESSION_COOKIE_NAME_PREFIX = CONFIG.SESSION_COOKIE_NAME_PREFIX
if SESSION_COOKIE_NAME_PREFIX is not None:
    pass
elif SESSION_COOKIE_DOMAIN is not None:
    SESSION_COOKIE_NAME_PREFIX = SESSION_COOKIE_DOMAIN.split('.')[0]
else:
    SESSION_COOKIE_NAME_PREFIX = 'jms_'
CSRF_COOKIE_NAME = '{}csrftoken'.format(SESSION_COOKIE_NAME_PREFIX)
SESSION_COOKIE_NAME = '{}sessionid'.format(SESSION_COOKIE_NAME_PREFIX)

SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE
SESSION_SAVE_EVERY_REQUEST = CONFIG.SESSION_SAVE_EVERY_REQUEST
SESSION_EXPIRE_AT_BROWSER_CLOSE = CONFIG.SESSION_EXPIRE_AT_BROWSER_CLOSE
SESSION_ENGINE = "common.sessions.{}".format(CONFIG.SESSION_ENGINE)

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DB_OPTIONS = {}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.{}'.format(CONFIG.DB_ENGINE.lower()),
        'NAME': CONFIG.DB_NAME,
        'HOST': CONFIG.DB_HOST,
        'PORT': CONFIG.DB_PORT,
        'USER': CONFIG.DB_USER,
        'PASSWORD': CONFIG.DB_PASSWORD,
        'ATOMIC_REQUESTS': True,
        'OPTIONS': DB_OPTIONS
    }
}

DB_USE_SSL = CONFIG.DB_USE_SSL
if CONFIG.DB_ENGINE.lower() == 'mysql':
    DB_OPTIONS['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"
    if DB_USE_SSL:
        DB_CA_PATH = exist_or_default(os.path.join(CERTS_DIR, 'db_ca.pem'), None)
        DB_OPTIONS['ssl'] = {'ca': DB_CA_PATH}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators
#
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
# LANGUAGE_CODE = 'en'
LANGUAGE_CODE = CONFIG.LANGUAGE_CODE

TIME_ZONE = CONFIG.TIME_ZONE

USE_I18N = True

USE_L10N = True

USE_TZ = True

# I18N translation
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '{}/static/'.format(CONFIG.FORCE_SCRIPT_NAME)
STATIC_ROOT = os.path.join(PROJECT_DIR, "data", "static")
STATIC_DIR = os.path.join(BASE_DIR, "static")

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# Media files (File, ImageField) will be safe these
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'data', 'media').replace('\\', '/') + '/'

PRIVATE_STORAGE_ROOT = MEDIA_ROOT
PRIVATE_STORAGE_AUTH_FUNCTION = 'jumpserver.rewriting.storage.permissions.allow_access'
PRIVATE_STORAGE_INTERNAL_URL = '/private-media/'
PRIVATE_STORAGE_SERVER = 'jumpserver.rewriting.storage.servers.StaticFileServer'

# Use django-bootstrap-form to format template, input max width arg
# BOOTSTRAP_COLUMN_COUNT = 11

# Init data or generate fake data source for development
FIXTURE_DIRS = [os.path.join(BASE_DIR, 'fixtures'), ]

# Email config
EMAIL_PROTOCOL = CONFIG.EMAIL_PROTOCOL
EMAIL_HOST = CONFIG.EMAIL_HOST
EMAIL_PORT = CONFIG.EMAIL_PORT
EMAIL_HOST_USER = CONFIG.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = CONFIG.EMAIL_HOST_PASSWORD
EMAIL_FROM = CONFIG.EMAIL_FROM
EMAIL_RECIPIENT = CONFIG.EMAIL_RECIPIENT
EMAIL_USE_SSL = CONFIG.EMAIL_USE_SSL
EMAIL_USE_TLS = CONFIG.EMAIL_USE_TLS

# Custom User Auth model
AUTH_USER_MODEL = 'users.User'

# File Upload Permissions
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

X_FRAME_OPTIONS = CONFIG.X_FRAME_OPTIONS

# Cache use redis
REDIS_SSL_KEY = exist_or_default(os.path.join(CERTS_DIR, 'redis_client.key'), None)
REDIS_SSL_CERT = exist_or_default(os.path.join(CERTS_DIR, 'redis_client.crt'), None)
REDIS_SSL_CA = exist_or_default(os.path.join(CERTS_DIR, 'redis_ca.pem'), None)
REDIS_SSL_CA = exist_or_default(os.path.join(CERTS_DIR, 'redis_ca.crt'), REDIS_SSL_CA)
REDIS_SSL_REQUIRED = 'none'
REDIS_USE_SSL = CONFIG.REDIS_USE_SSL
REDIS_PROTOCOL = 'rediss' if REDIS_USE_SSL else 'redis'
# Cache use sentinel
REDIS_SENTINEL_HOSTS = CONFIG.REDIS_SENTINEL_HOSTS
REDIS_SENTINEL_SERVICE_NAME, REDIS_SENTINELS = parse_sentinels_host(REDIS_SENTINEL_HOSTS)
REDIS_SENTINEL_PASSWORD = CONFIG.REDIS_SENTINEL_PASSWORD
if CONFIG.REDIS_SENTINEL_SOCKET_TIMEOUT:
    REDIS_SENTINEL_SOCKET_TIMEOUT = float(CONFIG.REDIS_SENTINEL_SOCKET_TIMEOUT)
else:
    REDIS_SENTINEL_SOCKET_TIMEOUT = None

# Cache config

REDIS_OPTIONS = {
    "REDIS_CLIENT_KWARGS": {
        "health_check_interval": 30
    },
    "CONNECTION_POOL_KWARGS": {
        'max_connections': 100,
    }
}
if REDIS_USE_SSL:
    REDIS_OPTIONS['CONNECTION_POOL_KWARGS'].update({
        'ssl_cert_reqs': REDIS_SSL_REQUIRED,
        "ssl_keyfile": REDIS_SSL_KEY,
        "ssl_certfile": REDIS_SSL_CERT,
        "ssl_ca_certs": REDIS_SSL_CA
    })

if REDIS_SENTINEL_SERVICE_NAME and REDIS_SENTINELS:
    REDIS_LOCATION_NO_DB = "%(protocol)s://%(service_name)s/{}" % {
        'protocol': REDIS_PROTOCOL, 'service_name': REDIS_SENTINEL_SERVICE_NAME,
    }
    REDIS_OPTIONS.update({
        'CLIENT_CLASS': 'django_redis.client.SentinelClient',
        'SENTINELS': REDIS_SENTINELS, 'PASSWORD': CONFIG.REDIS_PASSWORD,
        'SENTINEL_KWARGS': {
            'ssl': REDIS_USE_SSL,
            'ssl_cert_reqs': REDIS_SSL_REQUIRED,
            "ssl_keyfile": REDIS_SSL_KEY,
            "ssl_certfile": REDIS_SSL_CERT,
            "ssl_ca_certs": REDIS_SSL_CA,
            'password': REDIS_SENTINEL_PASSWORD,
            'socket_timeout': REDIS_SENTINEL_SOCKET_TIMEOUT
        }
    })
    if REDIS_USE_SSL:
        CONNECTION_POOL_KWARGS = REDIS_OPTIONS['CONNECTION_POOL_KWARGS']
        CONNECTION_POOL_KWARGS['connection_class'] = SentinelManagedSSLConnection
        REDIS_OPTIONS['CONNECTION_POOL_KWARGS'] = CONNECTION_POOL_KWARGS
    DJANGO_REDIS_CONNECTION_FACTORY = 'django_redis.pool.SentinelConnectionFactory'
else:
    REDIS_LOCATION_NO_DB = '%(protocol)s://:%(password)s@%(host)s:%(port)s/{}' % {
        'protocol': REDIS_PROTOCOL,
        'password': CONFIG.REDIS_PASSWORD_QUOTE,
        'host': CONFIG.REDIS_HOST,
        'port': CONFIG.REDIS_PORT,
    }

REDIS_CACHE_DEFAULT = {
    'BACKEND': 'redis_lock.django_cache.RedisCache',
    'LOCATION': REDIS_LOCATION_NO_DB.format(CONFIG.REDIS_DB_CACHE),
    'OPTIONS': REDIS_OPTIONS
}
REDIS_CACHE_SESSION = dict(REDIS_CACHE_DEFAULT)
REDIS_CACHE_SESSION['LOCATION'] = REDIS_LOCATION_NO_DB.format(CONFIG.REDIS_DB_SESSION)

CACHES = {
    'default': REDIS_CACHE_DEFAULT,
    'session': REDIS_CACHE_SESSION
}
SESSION_CACHE_ALIAS = "session"

FORCE_SCRIPT_NAME = CONFIG.FORCE_SCRIPT_NAME
SESSION_COOKIE_SECURE = CONFIG.SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE = CONFIG.CSRF_COOKIE_SECURE

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

GMSSL_ENABLED = CONFIG.GMSSL_ENABLED
GM_HASHER = 'common.hashers.PBKDF2SM3PasswordHasher'
if GMSSL_ENABLED:
    PASSWORD_HASHERS.insert(0, GM_HASHER)
else:
    PASSWORD_HASHERS.append(GM_HASHER)

# For Debug toolbar
INTERNAL_IPS = ["127.0.0.1"]
if os.environ.get('DEBUG_TOOLBAR', False):
    INSTALLED_APPS = ['debug_toolbar'] + INSTALLED_APPS
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]
