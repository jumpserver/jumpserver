#!/usr/bin/env python
#
import os
import signal
import sys
import threading
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIR = os.path.join(BASE_DIR, 'apps')

sys.path.insert(0, APPS_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')
os.environ.setdefault('PYTHONOPTIMIZE', '1')
if os.getuid() == 0:
    os.environ.setdefault('C_FORCE_ROOT', '1')

from django.core.cache import cache

scheduler = "django_celery_beat.schedulers:DatabaseScheduler"


class BeatLeaseLost(RuntimeError):
    pass


class BeatLease:
    """Renew the leader lease and stop the scheduler if renewal fails."""

    def __init__(self, lock):
        self.lock = lock
        self.lost = threading.Event()
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._renew, name='beat-lease', daemon=True)

    def check(self):
        if self.lost.is_set():
            raise BeatLeaseLost('Beat leader lease was lost')
        try:
            owned = self.lock.get_owner_id() == self.lock.id
        except Exception as exc:
            self.lost.set()
            raise BeatLeaseLost('Unable to verify Beat leader lease') from exc
        if not owned:
            self.lost.set()
            raise BeatLeaseLost('Beat leader lease was lost')

    def _renew(self):
        while not self.stopping.wait(20):
            try:
                # extend checks the owner token atomically; never reacquire here.
                self.lock.extend(expire=60)
            except Exception:
                if not self.stopping.is_set():
                    self.lost.set()
                    print('Beat lease renewal failed; stopping scheduler', flush=True)
                    os.kill(os.getpid(), signal.SIGTERM)
                return

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopping.set()
        # A broken Redis connection must not prevent process shutdown forever.
        if self.thread.ident is not None:
            self.thread.join(timeout=5)


def leased_database_scheduler(lease):
    # Import only after Celery has initialized Django and its task loader.
    from django_celery_beat.schedulers import DatabaseScheduler

    class LeasedDatabaseScheduler(DatabaseScheduler):
        def tick(self, *args, **kwargs):
            lease.check()
            return super().tick(*args, **kwargs)

        def reserve(self, *args, **kwargs):
            lease.check()
            return super().reserve(*args, **kwargs)

        def apply_async(self, *args, **kwargs):
            lease.check()
            return super().apply_async(*args, **kwargs)

        def sync(self):
            # A former leader must not overwrite the new leader's schedule state.
            try:
                lease.check()
            except BeatLeaseLost:
                return
            return super().sync()

    return LeasedDatabaseScheduler


def run_beat_in_process():
    def stop_during_startup(sig, frame):
        raise SystemExit(0)

    # Celery installs its own graceful sync handlers once the scheduler starts.
    # Until then, terminate lock acquisition / Django initialization cleanly.
    signal.signal(signal.SIGTERM, stop_during_startup)
    signal.signal(signal.SIGINT, stop_during_startup)
    os.chdir(APPS_DIR)
    lock = cache.lock('beat-distribute-start-lock', expire=60, auto_renewal=False)
    # Redis socket timeouts can be shorter than the previous leader's TTL.
    # Poll atomically instead of blocking in BLPOP until that lease expires.
    while not lock.acquire(blocking=False):
        time.sleep(1)
    lease = BeatLease(lock)
    try:
        lease.start()
        from ops.celery import app

        class LeasedBeat(app.Beat):
            def init_loader(self):
                super().init_loader()
                self.scheduler_cls = leased_database_scheduler(lease)

        print('Get beat lock start to run it in process', flush=True)
        LeasedBeat(loglevel='INFO', scheduler=scheduler, max_interval=60).run()
        if lease.lost.is_set():
            raise BeatLeaseLost('Beat stopped after losing its leader lease')
    except SystemExit:
        if lease.lost.is_set():
            raise BeatLeaseLost('Beat stopped after losing its leader lease')
        raise
    finally:
        lease.stop()
        try:
            lock.release()
        except Exception:
            # Token-checked release never removes another leader's lock.
            print('Unable to release Beat lease; it will expire by TTL', flush=True)


def main():
    return run_beat_in_process()


if __name__ == '__main__':
    main()
