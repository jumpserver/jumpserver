#!/usr/bin/python

import os
import datetime
import shutil
import sys
import django

GUACAMOLE_REPLAYS_DIR = '/tmp/guacamole/record'
UPLOAD_TO = 'local'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
LOCAL_REPLAY_DIR = os.path.join(PROJECT_DIR, 'data', 'media', 'replay')
APPS_DIR = os.path.join(PROJECT_DIR, "apps")


if os.path.exists(APPS_DIR):
    sys.path.insert(0, APPS_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from terminal.models import Session


def find_replays():
    replays = []

    for root, dirs, files in os.walk(GUACAMOLE_REPLAYS_DIR, topdown=True):
        for name in files:
            if name.startswith('20') and name.endswith('.gz'):
                session_id = '-'.join(name.split('-')[3:]).replace(".gz", "")
                file_path = os.path.join(root, name)
                create_ts = os.stat(file_path).st_ctime
                create_date = datetime.datetime.utcfromtimestamp(create_ts)
                replays.append({
                    "id": session_id,
                    "path": file_path,
                    "date": create_date,
                })
    return replays


def upload_to_local(session):
    source_path = session["path"]
    session_id = session["id"]
    target_filename = session_id + ".replay.gz"
    date_created = session["date"].strftime("%Y-%m-%d")
    target_dir = os.path.join(LOCAL_REPLAY_DIR, date_created )
    target_path = os.path.join(target_dir, target_filename)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    print("Move {} => {}".format(source_path, target_path))
    shutil.copy(source_path, target_path)
    shutil.copystat(source_path, target_path)
    os.unlink(source_path)
    Session.objects.filter(id=session_id).update(is_finished=True)


if __name__ == '__main__':
    for s in find_replays():
        upload_to_local(s)
