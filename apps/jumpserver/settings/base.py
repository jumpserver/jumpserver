import os
import platform

if platform.system() == 'Darwin' and platform.machine() == 'arm64':
    import pymysql

    pymysql.version_info = (1, 4, 2, "final", 0)
    pymysql.install_as_MySQLdb()

from django.urls import reverse_lazy

from .. import const
from ..const import CONFIG


def exist_or_default(path, default):
    if not os.path.exists(path):
        path = default
    return path


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
VERSION = const.VERSION
BASE_DIR = const.BASE_DIR
PROJECT_DIR = const.PROJECT_DIR
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
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

# Absolute url for some case, for example email link
SITE_URL = CONFIG.SITE_URL

# https://docs.djangoproject.com/en/4.1/ref/settings/
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# LOG LEVEL
LOG_LEVEL = CONFIG.LOG_LEVEL

ALLOWED_HOSTS = ['*']

# Max post update field num
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Application definition

INSTALLED_APPS = [
    'orgs.apps.OrgsConfig',
    'users.apps.UsersConfig',
    'assets.apps.AssetsConfig',
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
    'common.apps.CommonConfig',
    'jms_oidc_rp',
    'rest_framework',
    'rest_framework_swagger',
    'drf_yasg',
    'django_cas_ng',
    'channels',
    'django_filters',
    'bootstrap3',
    'captcha',
    'django_celery_beat',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.forms',
    'simple_history',  # 这个要放到最后，别特么瞎改顺序
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jumpserver.middleware.TimezoneMiddleware',
    'jumpserver.middleware.DemoMiddleware',
    'jumpserver.middleware.RequestMiddleware',
    'jumpserver.middleware.RefererCheckMiddleware',
    'orgs.middleware.OrgMiddleware',
    'authentication.backends.oidc.middleware.OIDCRefreshIDTokenMiddleware',
    'authentication.backends.cas.middleware.CASMiddleware',
    'authentication.middleware.MFAMiddleware',
    'authentication.middleware.ThirdPartyLoginMiddleware',
    'authentication.middleware.SessionCookieMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

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
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# 自定义的配置，SESSION_EXPIRE_AT_BROWSER_CLOSE 始终为 True, 下面这个来控制是否强制关闭后过期 cookie
SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE = CONFIG.SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE
SESSION_SAVE_EVERY_REQUEST = CONFIG.SESSION_SAVE_EVERY_REQUEST
SESSION_ENGINE = "django.contrib.sessions.backends.{}".format(CONFIG.SESSION_ENGINE)

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

DB_CA_PATH = os.path.join(PROJECT_DIR, 'data', 'certs', 'db_ca.pem')
DB_USE_SSL = False
if CONFIG.DB_ENGINE.lower() == 'mysql':
    DB_OPTIONS['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"
    if os.path.isfile(DB_CA_PATH):
        DB_OPTIONS['ssl'] = {'ca': DB_CA_PATH}
        DB_USE_SSL = True

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

# Media files (File, ImageField) will be save these

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(PROJECT_DIR, 'data', 'media').replace('\\', '/') + '/'

# Use django-bootstrap-form to format template, input max width arg
# BOOTSTRAP_COLUMN_COUNT = 11

# Init data or generate fake data source for development
FIXTURE_DIRS = [os.path.join(BASE_DIR, 'fixtures'), ]

# Email config
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

# Cache use redis
REDIS_SSL_KEY = exist_or_default(os.path.join(CERTS_DIR, 'redis_client.key'), None)
REDIS_SSL_CERT = exist_or_default(os.path.join(CERTS_DIR, 'redis_client.crt'), None)
REDIS_SSL_CA = exist_or_default(os.path.join(CERTS_DIR, 'redis_ca.pem'), None)
REDIS_SSL_CA = exist_or_default(os.path.join(CERTS_DIR, 'redis_ca.crt'), REDIS_SSL_CA)
REDIS_SSL_REQUIRED = 'none'
REDIS_USE_SSL = CONFIG.REDIS_USE_SSL

REDIS_LOCATION_NO_DB = '%(protocol)s://:%(password)s@%(host)s:%(port)s/{}' % {
    'protocol': 'rediss' if REDIS_USE_SSL else 'redis',
    'password': CONFIG.REDIS_PASSWORD,
    'host': CONFIG.REDIS_HOST,
    'port': CONFIG.REDIS_PORT,
}

REDIS_CACHE_DEFAULT = {
    'BACKEND': 'redis_lock.django_cache.RedisCache',
    'LOCATION': REDIS_LOCATION_NO_DB.format(CONFIG.REDIS_DB_CACHE),
    'OPTIONS': {
        "REDIS_CLIENT_KWARGS": {"health_check_interval": 30},
        "CONNECTION_POOL_KWARGS": {
            'ssl_cert_reqs': REDIS_SSL_REQUIRED,
            "ssl_keyfile": REDIS_SSL_KEY,
            "ssl_certfile": REDIS_SSL_CERT,
            "ssl_ca_certs": REDIS_SSL_CA
        } if REDIS_USE_SSL else {}
    }
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

