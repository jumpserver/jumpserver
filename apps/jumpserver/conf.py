#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import os
import sys
import types
import errno
import json
import yaml
from importlib import import_module

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)


def import_string(dotted_path):
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (
            module_path, class_name)
        ) from err


class Config(dict):
    """Works exactly like a dict but provides ways to fill it from files
    or special dictionaries.  There are two common patterns to populate the
    config.

    Either you can fill the config from a config file::

        app.config.from_pyfile('yourconfig.cfg')

    Or alternatively you can define the configuration options in the
    module that calls :meth:`from_object` or provide an import path to
    a module that should be loaded.  It is also possible to tell it to
    use the same module and with that provide the configuration values
    just before the call::

        DEBUG = True
        SECRET_KEY = 'development key'
        app.config.from_object(__name__)

    In both cases (loading from any Python file or loading from modules),
    only uppercase keys are added to the config.  This makes it possible to use
    lowercase values in the config file for temporary values that are not added
    to the config or to define the config keys in the same file that implements
    the application.

    Probably the most interesting way to load configurations is from an
    environment variable pointing to a file::

        app.config.from_envvar('YOURAPPLICATION_SETTINGS')

    In this case before launching the application you have to set this
    environment variable to the file you want to use.  On Linux and OS X
    use the export statement::

        export YOURAPPLICATION_SETTINGS='/path/to/config/file'

    On windows use `set` instead.

    :param root_path: path to which files are read relative from.  When the
                      config object is created by the application, this is
                      the application's :attr:`~flask.Flask.root_path`.
    :param defaults: an optional dictionary of default values
    """

    def __init__(self, root_path=None, defaults=None):
        self.defaults = defaults or {}
        self.root_path = root_path
        super().__init__({})

    def from_envvar(self, variable_name, silent=False):
        """Loads a configuration from an environment variable pointing to
        a configuration file.  This is basically just a shortcut with nicer
        error messages for this line of code::

            app.config.from_pyfile(os.environ['YOURAPPLICATION_SETTINGS'])

        :param variable_name: name of the environment variable
        :param silent: set to ``True`` if you want silent failure for missing
                       files.
        :return: bool. ``True`` if able to load config, ``False`` otherwise.
        """
        rv = os.environ.get(variable_name)
        if not rv:
            if silent:
                return False
            raise RuntimeError('The environment variable %r is not set '
                               'and as such configuration could not be '
                               'loaded.  Set this variable and make it '
                               'point to a configuration file' %
                               variable_name)
        return self.from_pyfile(rv, silent=silent)

    def from_pyfile(self, filename, silent=False):
        """Updates the values in the config from a Python file.  This function
        behaves as if the file was imported as module with the
        :meth:`from_object` function.

        :param filename: the filename of the config.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        :param silent: set to ``True`` if you want silent failure for missing
                       files.

        .. versionadded:: 0.7
           `silent` parameter.
        """
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        d = types.ModuleType('config')
        d.__file__ = filename
        try:
            with open(filename, mode='rb') as config_file:
                exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)
        return True

    def from_object(self, obj):
        """Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes. :meth:`from_object`
        loads only the uppercase attributes of the module/class. A ``dict``
        object will not work with :meth:`from_object` because the keys of a
        ``dict`` are not attributes of the ``dict`` class.

        Example of module-based configuration::

            app.config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            app.config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_pyfile` and ideally from a location not within the
        package because the package might be installed system wide.

        See :ref:`config-dev-prod` for an example of class-based configuration
        using :meth:`from_object`.

        :param obj: an import name or object
        """
        if isinstance(obj, str):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_json(self, filename, silent=False):
        """Updates the values in the config from a JSON file. This function
        behaves as if the JSON object was a dictionary and passed to the
        :meth:`from_mapping` function.

        :param filename: the filename of the JSON file.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        :param silent: set to ``True`` if you want silent failure for missing
                       files.

        .. versionadded:: 0.11
        """
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        try:
            with open(filename) as json_file:
                obj = json.loads(json_file.read())
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        return self.from_mapping(obj)

    def from_yaml(self, filename, silent=False):
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        try:
            with open(filename, 'rt', encoding='utf8') as f:
                obj = yaml.safe_load(f)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        if obj:
            return self.from_mapping(obj)
        return True

    def from_mapping(self, *mapping, **kwargs):
        """Updates the config like :meth:`update` ignoring items with non-upper
        keys.

        .. versionadded:: 0.11
        """
        mappings = []
        if len(mapping) == 1:
            if hasattr(mapping[0], 'items'):
                mappings.append(mapping[0].items())
            else:
                mappings.append(mapping[0])
        elif len(mapping) > 1:
            raise TypeError(
                'expected at most 1 positional argument, got %d' % len(mapping)
            )
        mappings.append(kwargs.items())
        for mapping in mappings:
            for (key, value) in mapping:
                if key.isupper():
                    self[key] = value
        return True

    def get_namespace(self, namespace, lowercase=True, trim_namespace=True):
        """Returns a dictionary containing a subset of configuration options
        that match the specified namespace/prefix. Example usage::

            app.config['IMAGE_STORE_TYPE'] = 'fs'
            app.config['IMAGE_STORE_PATH'] = '/var/app/images'
            app.config['IMAGE_STORE_BASE_URL'] = 'http://img.website.com'
            image_store_config = app.config.get_namespace('IMAGE_STORE_')

        The resulting dictionary `image_store_config` would look like::

            {
                'types': 'fs',
                'path': '/var/app/images',
                'base_url': 'http://img.website.com'
            }

        This is often useful when configuration options map directly to
        keyword arguments in functions or class constructors.

        :param namespace: a configuration namespace
        :param lowercase: a flag indicating if the keys of the resulting
                          dictionary should be lowercase
        :param trim_namespace: a flag indicating if the keys of the resulting
                          dictionary should not include the namespace

        .. versionadded:: 0.11
        """
        rv = {}
        for k, v in self.items():
            if not k.startswith(namespace):
                continue
            if trim_namespace:
                key = k[len(namespace):]
            else:
                key = k
            if lowercase:
                key = key.lower()
            rv[key] = v
        return rv

    def convert_type(self, k, v):
        default_value = self.defaults.get(k)
        if default_value is None:
            return v
        tp = type(default_value)
        # 对bool特殊处理
        if tp is bool and isinstance(v, str):
            if v in ("true", "True", "1"):
                return True
            else:
                return False
        if tp in [list, dict] and isinstance(v, str):
            try:
                v = json.loads(v)
                return v
            except json.JSONDecodeError:
                return v

        try:
            v = tp(v)
        except Exception:
            pass
        return v

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))

    def __getitem__(self, item):
        # 先从设置的来
        try:
            value = super().__getitem__(item)
        except KeyError:
            value = None
        if value is not None:
            return value
        # 其次从环境变量来
        value = os.environ.get(item, None)
        if value is not None:
            return self.convert_type(item, value)
        return self.defaults.get(item)

    def __getattr__(self, item):
        return self.__getitem__(item)


defaults = {
    'SECRET_KEY': '',
    'BOOTSTRAP_TOKEN': '',
    'DEBUG': True,
    'SITE_URL': 'http://localhost',
    'LOG_LEVEL': 'DEBUG',
    'LOG_DIR': os.path.join(PROJECT_DIR, 'logs'),
    'DB_ENGINE': 'mysql',
    'DB_NAME': 'jumpserver',
    'DB_HOST': '127.0.0.1',
    'DB_PORT': 3306,
    'DB_USER': 'root',
    'DB_PASSWORD': '',
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379,
    'REDIS_PASSWORD': '',
    'REDIS_DB_CELERY': 3,
    'REDIS_DB_CACHE': 4,
    'REDIS_DB_SESSION': 5,
    'CAPTCHA_TEST_MODE': None,
    'TOKEN_EXPIRATION': 3600 * 24,
    'DISPLAY_PER_PAGE': 25,
    'DEFAULT_EXPIRED_YEARS': 70,
    'SESSION_COOKIE_DOMAIN': None,
    'CSRF_COOKIE_DOMAIN': None,
    'SESSION_COOKIE_AGE': 3600 * 24,
    'SESSION_EXPIRE_AT_BROWSER_CLOSE': False,
    'AUTH_OPENID': False,
    'OTP_VALID_WINDOW': 0,
    'OTP_ISSUER_NAME': 'Jumpserver',
    'EMAIL_SUFFIX': 'jumpserver.org',
    'TERMINAL_PASSWORD_AUTH': True,
    'TERMINAL_PUBLIC_KEY_AUTH': True,
    'TERMINAL_HEARTBEAT_INTERVAL': 20,
    'TERMINAL_ASSET_LIST_SORT_BY': 'hostname',
    'TERMINAL_ASSET_LIST_PAGE_SIZE': 'auto',
    'TERMINAL_SESSION_KEEP_DURATION': 9999,
    'TERMINAL_HOST_KEY': '',
    'TERMINAL_TELNET_REGEX': '',
    'TERMINAL_COMMAND_STORAGE': {},
    'SECURITY_MFA_AUTH': False,
    'SECURITY_LOGIN_LIMIT_COUNT': 7,
    'SECURITY_LOGIN_LIMIT_TIME': 30,
    'SECURITY_MAX_IDLE_TIME': 30,
    'SECURITY_PASSWORD_EXPIRATION_TIME': 9999,
    'SECURITY_PASSWORD_MIN_LENGTH': 6,
    'SECURITY_PASSWORD_UPPER_CASE': False,
    'SECURITY_PASSWORD_LOWER_CASE': False,
    'SECURITY_PASSWORD_NUMBER': False,
    'SECURITY_PASSWORD_SPECIAL_CHAR': False,
    'AUTH_RADIUS': False,
    'RADIUS_SERVER': 'localhost',
    'RADIUS_PORT': 1812,
    'RADIUS_SECRET': '',
    'HTTP_BIND_HOST': '0.0.0.0',
    'HTTP_LISTEN_PORT': 8080,
    'LOGIN_LOG_KEEP_DAYS': 90,
    'ASSETS_PERM_CACHE_TIME': 3600,

}


def load_from_object(config):
    try:
        from config import config as c
        config.from_object(c)
        return True
    except ImportError:
        pass
    return False


def load_from_yml(config):
    for i in ['config.yml', 'config.yaml']:
        if not os.path.isfile(os.path.join(config.root_path, i)):
            continue
        loaded = config.from_yaml(i)
        if loaded:
            return True
    return False


def load_user_config():
    sys.path.insert(0, PROJECT_DIR)
    config = Config(PROJECT_DIR, defaults)

    loaded = load_from_object(config)
    if not loaded:
        loaded = load_from_yml(config)
    if not loaded:
        msg = """
    
        Error: No config file found.
    
        You can run `cp config_example.yml config.yml`, and edit it.
        """
        raise ImportError(msg)
    return config
