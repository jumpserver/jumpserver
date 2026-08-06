#!/usr/bin/env python3

import fcntl
import hashlib
import os
import shutil
import signal
import subprocess
import sys


OPTIONS_WITH_VALUE = {
    '-B', '-b', '-c', '-D', '-E', '-e', '-F', '-I', '-i', '-J', '-L',
    '-l', '-m', '-O', '-o', '-P', '-p', '-Q', '-R', '-S', '-W', '-w',
}


def split_destination(destination):
    destination = str(destination or '')
    if '@' in destination:
        destination = destination.rsplit('@', 1)[1]
    if destination.startswith('['):
        host, __, remainder = destination[1:].partition(']')
        return host, remainder.lstrip(':')
    host, separator, path = destination.partition(':')
    return host, path if separator else ''


def parse_option(option, value, endpoint):
    option = option.lower()
    if option == '-p':
        endpoint['port'] = value
        return
    if option != '-o' or '=' not in value:
        return
    name, option_value = value.split('=', 1)
    if name.lower() == 'port':
        endpoint['port'] = option_value
    elif name.lower() in ('hostname', 'host'):
        endpoint['host'] = option_value


def get_endpoint(client, arguments):
    endpoint = {'host': '', 'port': '22'}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == '--':
            index += 1
            if index < len(arguments):
                endpoint['host'], __ = split_destination(arguments[index])
            break
        if argument in OPTIONS_WITH_VALUE:
            value = arguments[index + 1] if index + 1 < len(arguments) else ''
            parse_option(argument, value, endpoint)
            index += 2
            continue
        if argument.startswith('-o') and '=' in argument[2:]:
            parse_option('-o', argument[2:], endpoint)
            index += 1
            continue
        if argument.startswith('-p') and len(argument) > 2:
            parse_option('-p', argument[2:], endpoint)
            index += 1
            continue
        if argument.startswith('-'):
            index += 1
            continue

        host, remote_path = split_destination(argument)
        if client == 'scp':
            if remote_path:
                endpoint['host'] = host
                break
        else:
            endpoint['host'] = host
            break
        index += 1

    host = endpoint['host'].strip().lower() or 'unknown'
    port = endpoint['port'].strip() or '22'
    return host, port


def find_real_client(client):
    candidates = (f'/usr/bin/{client}', f'/bin/{client}')
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    executable = shutil.which(client)
    if executable:
        return executable
    raise FileNotFoundError(f'Unable to find the real {client} executable')


def run():
    client = os.path.basename(sys.argv[0]).lower()
    if client not in ('ssh', 'scp', 'sftp'):
        client = 'ssh'

    host, port = get_endpoint(client, sys.argv[1:])
    lock_key = hashlib.sha256(f'{host}:{port}'.encode()).hexdigest()
    lock_path = f'/tmp/jumpserver-ansible-ssh-{lock_key}.lock'
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    child = None
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        child = subprocess.Popen(
            [find_real_client(client), *sys.argv[1:]],
            close_fds=False,
        )

        def forward_signal(signum, __):
            if child.poll() is None:
                child.send_signal(signum)

        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, forward_signal)
        return child.wait()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


if __name__ == '__main__':
    raise SystemExit(run())
