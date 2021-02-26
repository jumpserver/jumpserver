import os

from django.urls import reverse_lazy

from .. import const
from ..const import CONFIG

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
VERSION = const.VERSION
BASE_DIR = const.BASE_DIR
PROJECT_DIR = const.PROJECT_DIR

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = CONFIG.SECRET_KEY

# SECURITY WARNING: keep the token secret, remove it if all coco, guacamole ok
BOOTSTRAP_TOKEN = CONFIG.BOOTSTRAP_TOKEN

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = CONFIG.DEBUG

# Absolute url for some case, for example email link
SITE_URL = CONFIG.SITE_URL

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
    'common.apps.CommonConfig',
    'terminal.apps.TerminalConfig',
    'audits.apps.AuditsConfig',
    'authentication.apps.AuthenticationConfig',  # authentication
    'applications.apps.ApplicationsConfig',
    'tickets.apps.TicketsConfig',
    'acls.apps.AclsConfig',
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
                'jms_oidc_rp.context_processors.oidc',
            ],
        },
    },
]

WSGI_APPLICATION = 'jumpserver.wsgi.application'

LOGIN_REDIRECT_URL = reverse_lazy('index')
LOGIN_URL = reverse_lazy('authentication:login')

SESSION_COOKIE_DOMAIN = CONFIG.SESSION_COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = CONFIG.CSRF_COOKIE_DOMAIN
SESSION_COOKIE_AGE = CONFIG.SESSION_COOKIE_AGE
SESSION_EXPIRE_AT_BROWSER_CLOSE = CONFIG.SESSION_EXPIRE_AT_BROWSER_CLOSE
SESSION_ENGINE = 'redis_sessions.session'
SESSION_REDIS = {
    'host': CONFIG.REDIS_HOST,
    'port': CONFIG.REDIS_PORT,
    'password': CONFIG.REDIS_PASSWORD,
    'db': CONFIG.REDIS_DB_SESSION,
    'prefix': 'auth_session',
    'socket_timeout': 1,
    'retry_on_timeout': False
}

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
if CONFIG.DB_ENGINE.lower() == 'mysql':
    DB_OPTIONS['init_command'] = "SET sql_mode='STRICT_TRANS_TABLES'"
    if os.path.isfile(DB_CA_PATH):
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
CACHES = {
    'default': {
        # 'BACKEND': 'redis_cache.RedisCache',
        'BACKEND': 'redis_lock.django_cache.RedisCache',
        'LOCATION': 'redis://:%(password)s@%(host)s:%(port)s/%(db)s' % {
            'password': CONFIG.REDIS_PASSWORD,
            'host': CONFIG.REDIS_HOST,
            'port': CONFIG.REDIS_PORT,
            'db': CONFIG.REDIS_DB_CACHE,
        },
        'OPTIONS': {
            "REDIS_CLIENT_KWARGS": {"health_check_interval": 30}
        }
    }
}

FORCE_SCRIPT_NAME = CONFIG.FORCE_SCRIPT_NAME
SESSION_COOKIE_SECURE = CONFIG.SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE = CONFIG.CSRF_COOKIE_SECURE
