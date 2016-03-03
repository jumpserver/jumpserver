"""
Django settings for jumpserver project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import ConfigParser
import getpass

config = ConfigParser.ConfigParser()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
config.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
KEY_DIR = os.path.join(BASE_DIR, 'keys')


DB_HOST = config.get('db', 'host')
DB_PORT = config.getint('db', 'port')
DB_USER = config.get('db', 'user')
DB_PASSWORD = config.get('db', 'password')
DB_DATABASE = config.get('db', 'database')
AUTH_USER_MODEL = 'juser.User'
# mail config
MAIL_ENABLE = config.get('mail', 'mail_enable')
EMAIL_HOST = config.get('mail', 'email_host')
EMAIL_PORT = config.get('mail', 'email_port')
EMAIL_HOST_USER = config.get('mail', 'email_host_user')
EMAIL_HOST_PASSWORD = config.get('mail', 'email_host_password')
EMAIL_USE_TLS = config.getboolean('mail', 'email_use_tls')
EMAIL_TIMEOUT = 5

# ======== Log ==========
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys/role_keys')
KEY = config.get('base', 'key')
URL = config.get('base', 'url')
LOG_LEVEL = config.get('base', 'log')
IP = config.get('base', 'ip')
PORT = config.get('base', 'port')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!%=t81uof5rhmtpi&(zr=q^fah#$enny-c@mswz49l42j0o49-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['0.0.0.0/8']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_crontab',
    'bootstrapform',
    'jumpserver',
    'juser',
    'jasset',
    'jperm',
    'jlog',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'jumpserver.urls'

WSGI_APPLICATION = 'jumpserver.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_DATABASE,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'jumpserver.context_processors.name_proc',
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

# STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)
# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

BOOTSTRAP_COLUMN_COUNT = 10

CRONJOBS = [
    ('0 1 * * *', 'jasset.asset_api.asset_ansible_update_all'),
    ('*/10 * * * *', 'jlog.log_api.kill_invalid_connection'),
]
