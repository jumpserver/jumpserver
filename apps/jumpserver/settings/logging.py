# -*- coding: utf-8 -*-
#
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from logging.handlers import SysLogHandler

from django.conf import settings

from ..const import PROJECT_DIR, CONFIG

logger = logging.getLogger('jumpserver.logging')

LOG_DIR = os.path.join(PROJECT_DIR, 'data', 'logs')
JUMPSERVER_LOG_FILE = os.path.join(LOG_DIR, 'jumpserver.log')
DRF_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'drf_exception.log')
UNEXPECTED_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'unexpected_exception.log')
GUNICORN_LOG_FILE = os.path.join(LOG_DIR, 'gunicorn.log')
LOG_LEVEL = CONFIG.LOG_LEVEL

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(pathname)s:%(lineno)d  %(message)s'
        },
        'main': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': '%(asctime)s [%(levelname).4s] %(message)s',
        },
        'exception': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': '\n%(asctime)s [%(levelname)s] %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'syslog': {
            'format': 'osm: %(message)s'
        },
        'msg': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'main'
        },
        'file': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'main',
            'filename': JUMPSERVER_LOG_FILE,
        },
        'drf_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'exception',
            'filename': DRF_EXCEPTION_LOG_FILE,
        },
        'unexpected_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'exception',
            'filename': UNEXPECTED_EXCEPTION_LOG_FILE,
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.NullHandler',
            'formatter': 'syslog'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
            'level': LOG_LEVEL,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file', 'syslog'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'jumpserver': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
        'drf_exception': {
            'handlers': ['console', 'drf_exception'],
            'level': LOG_LEVEL,
        },
        'unexpected_exception': {
            'handlers': ['unexpected_exception'],
            'level': LOG_LEVEL,
        },
        'django_auth_ldap': {
            'handlers': ['console', 'file'],
            'level': "INFO",
        },
        'syslog': {
            'handlers': ['syslog'],
            'level': 'INFO'
        },
        'azure': {
            'handlers': ['null'],
            'level': 'ERROR'
        },
        'oauth2_provider': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
    }
}

if CONFIG.DEBUG_DEV:
    LOGGING['loggers']['django.db'] = {
        'handlers': ['console', 'file'],
        'level': 'DEBUG'
    }

SYSLOG_ENABLE = CONFIG.SYSLOG_ENABLE

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR, mode=0o755)


@dataclass(frozen=True)
class SyslogConfig:
    enabled: bool
    host: str
    port: int
    facility: str
    socktype: int

    @classmethod
    def from_test_data(cls, data):
        return cls(
            enabled=True,
            host=str(data['SYSLOG_HOST']).strip(),
            port=data['SYSLOG_PORT'],
            facility=data['SYSLOG_FACILITY'],
            socktype=data['SYSLOG_SOCKTYPE'],
        )

    @classmethod
    def from_settings(cls):
        return cls(
            enabled=bool(getattr(settings, 'SYSLOG_ENABLE', False)),
            host=str(getattr(settings, 'SYSLOG_HOST', '') or '').strip(),
            port=int(getattr(settings, 'SYSLOG_PORT', 514)),
            facility=getattr(settings, 'SYSLOG_FACILITY', 'user'),
            socktype=int(getattr(settings, 'SYSLOG_SOCKTYPE', 2)),
        )


# 'django.server',
SYSLOG_LOGGER_NAMES = ('syslog',)
SYSLOG_TCP_TIMEOUT = 5


class LazySyslogHandler(logging.Handler):
    """Create the network handler only when a syslog record is emitted."""

    retry_interval = 5
    warning_interval = 60

    def __init__(self, config):
        super().__init__(level=logging.INFO)
        self._config = config
        self._delegate = None
        self._pid = os.getpid()
        self._next_retry_at = 0
        self._next_warning_at = 0
        self._state_lock = threading.RLock()
        self.setFormatter(logging.Formatter('osm: %(message)s'))

    def update_config(self, config):
        with self._state_lock:
            if self._config == config:
                return
            self._config = config
            self._reset_retry_state()
            self._close_delegate()

    def emit(self, record):
        self.send(record)

    def send(self, record):
        """Attempt local delivery and return whether the socket accepted it."""
        with self._state_lock:
            self._reset_after_fork()
            if not self._config.enabled or not self._config.host:
                return False

            delegate = self._get_delegate()
            if delegate is None:
                return False

            try:
                delegate.emit(record)
                self._next_warning_at = 0
                return True
            except Exception as e:
                if self._config.socktype == socket.SOCK_STREAM:
                    return self._retry_tcp_delivery(record, e)
                self._mark_delegate_failed(e)
                return False

    def close(self):
        with self._state_lock:
            self._close_delegate()
        super().close()

    def _get_delegate(self):
        if self._delegate is not None:
            return self._delegate
        if time.monotonic() < self._next_retry_at:
            return None
        try:
            self._delegate = self._create_delegate()
            return self._delegate
        except Exception as e:
            self._mark_delegate_failed(e)
            return None

    def _create_delegate(self):
        return create_syslog_handler(self._config, self.formatter, self.level)

    def _retry_tcp_delivery(self, record, error):
        """Reconnect once because TCP peers may close an idle connection."""
        self._close_delegate()
        try:
            self._delegate = self._create_delegate()
            self._delegate.emit(record)
            self._next_warning_at = 0
            logger.info(
                'Syslog TCP delivery recovered: pid=%s host=%s port=%s',
                os.getpid(), self._config.host, self._config.port,
            )
            return True
        except Exception as retry_error:
            logger.debug(
                'Syslog TCP retry failed after delivery error: %s', error,
            )
            self._mark_delegate_failed(retry_error)
            return False

    def _reset_after_fork(self):
        pid = os.getpid()
        if pid == self._pid:
            return
        self._pid = pid
        self._reset_retry_state()
        self._close_delegate()

    def _reset_retry_state(self):
        self._next_retry_at = 0
        self._next_warning_at = 0

    def _mark_delegate_failed(self, error):
        now = time.monotonic()
        self._next_retry_at = now + self.retry_interval
        if now >= self._next_warning_at:
            logger.warning(
                'Syslog delivery failed, retry in %ss: host=%s port=%s '
                'socktype=%s error=%s',
                self.retry_interval, self._config.host, self._config.port,
                self._config.socktype, error,
            )
            self._next_warning_at = now + self.warning_interval
        self._close_delegate()

    def _close_delegate(self):
        if self._delegate is None:
            return
        try:
            self._delegate.close()
        except Exception:
            pass
        finally:
            self._delegate = None


class RetriableSysLogHandler(SysLogHandler):
    """Let the lazy proxy handle delivery errors from SysLogHandler."""

    def handleError(self, record):
        raise


def create_syslog_handler(config, formatter=None, level=logging.INFO):
    handler = RetriableSysLogHandler(
        address=(config.host, config.port),
        facility=config.facility,
        socktype=config.socktype,
        timeout=SYSLOG_TCP_TIMEOUT if config.socktype == socket.SOCK_STREAM else None,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter or logging.Formatter('osm: %(message)s'))
    return handler


def _get_lazy_syslog_handler(logger):
    return next(
        (handler for handler in logger.handlers if isinstance(handler, LazySyslogHandler)),
        None,
    )


def initialize_syslog_handler():
    """Install the lazy proxy after database-backed settings are loaded."""
    config = SyslogConfig.from_settings()
    for logger_name in SYSLOG_LOGGER_NAMES:
        syslog_logger = logging.getLogger(logger_name)
        handler = _get_lazy_syslog_handler(syslog_logger)
        if handler is not None:
            handler.update_config(config)
            continue

        for old_handler in list(syslog_logger.handlers):
            if isinstance(old_handler, (SysLogHandler, logging.NullHandler)):
                syslog_logger.removeHandler(old_handler)
                old_handler.close()

        syslog_logger.addHandler(LazySyslogHandler(config))


def reconfigure_syslog_handler():
    """Refresh the local snapshot without performing network I/O."""
    initialize_syslog_handler()
