# coding: utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf8')

import os
import re
import time
import textwrap
import getpass
import readline
import django
from multiprocessing import Pool

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    django.setup()
from jumpserver.api import BASE_DIR, ServerError, User, UserGroup, Asset, Jtty, get_object
from jumpserver.api import CRYPTOR, logger, is_dir
from jumpserver.api import BisGroup as AssetGroup

login_user = get_object(User, username=getpass.getuser())


def color_print(msg, color='red', exits=False):
    """
    Print colorful string.
    颜色打印
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m'}

    print color_msg.get(color, 'blue') % msg
    if exits:
        time.sleep(2)
        sys.exit()


def verify_connect(user, option):
    """鉴定用户是否有该主机权限 或 匹配到的ip是否唯一"""
    ip_matched = []
    try:
        assets_info = login_user.get_asset_info()
    except ServerError, e:
        color_print(e, 'red')
        return False

    for ip, asset_info in assets_info.items():
        if option in asset_info[1:] and option:
            ip_matched = [asset_info[1]]
            break

        for info in asset_info[1:]:
            if option in info:
                ip_matched.append(ip)

    logger.debug('%s matched input %s: %s' % (login_user.username, option, ip_matched))
    ip_matched = list(set(ip_matched))

    if len(ip_matched) > 1:
        ip_comment = {}
        for ip in ip_matched:
            ip_comment[ip] = assets_info[ip][2]

        for ip in sorted(ip_comment):
            if ip_comment[ip]:
                print '%-15s -- %s' % (ip, ip_comment[ip])
            else:
                print '%-15s' % ip
        print ''
    elif len(ip_matched) < 1:
        color_print('没有该主机，或者您没有该主机的权限 No Permission or No host.', 'red')
    else:
        asset = get_object(Asset, ip=ip_matched[0])
        jtty = Jtty(user, asset)
        jtty.connect()


def print_prompt():
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
    1) Type \033[32mIP or Part IP, Host Alias or Comments \033[0m To Login.
    2) Type \033[32mP/p\033[0m To Print The Servers You Available.
    3) Type \033[32mG/g\033[0m To Print The Server Groups You Available.
    4) Type \033[32mG/g(1-N)\033[0m To Print The Server Group Hosts You Available.
    5) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
    6) Type \033[32mQ/q\033[0m To Quit.
    """
    print textwrap.dedent(msg)


# def remote_exec_cmd(ip, port, username, password, cmd):
#     try:
#         time.sleep(5)
#         ssh = paramiko.SSHClient()
#         ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         ssh.connect(ip, port, username, password, timeout=5)
#         stdin, stdout, stderr = ssh.exec_command("bash -l -c '%s'" % cmd)
#         out = stdout.readlines()
#         err = stderr.readlines()
#         color_print('%s:' % ip, 'blue')
#         for i in out:
#             color_print(" " * 4 + i.strip(), 'green')
#         for j in err:
#             color_print(" " * 4 + j.strip(), 'red')
#         ssh.close()
#     except Exception as e:
#         color_print(ip + ':', 'blue')
#         color_print(str(e), 'red')


# def multi_remote_exec_cmd(hosts, username, cmd):
#     pool = Pool(processes=5)
#     for host in hosts:
#         username, password, ip, port = get_connect_item(username, host)
#         pool.apply_async(remote_exec_cmd, (ip, port, username, password, cmd))
#     pool.close()
#     pool.join()


# def exec_cmd_servers(username):
#     color_print("You can choose in the following IP(s), Use glob or ips split by comma. q/Q to PreLayer.", 'green')
#     user.get_asset_info(printable=True)
#     while True:
#         hosts = []
#         inputs = raw_input('\033[1;32mip(s)>: \033[0m')
#         if inputs in ['q', 'Q']:
#             break
#         get_hosts = login_user.get_asset_info().keys()
#
#         if ',' in inputs:
#             ips_input = inputs.split(',')
#             for host in ips_input:
#                 if host in get_hosts:
#                     hosts.append(host)
#         else:
#             for host in get_hosts:
#                 if fnmatch.fnmatch(host, inputs):
#                     hosts.append(host.strip())
#
#         if len(hosts) == 0:
#             color_print("Check again, Not matched any ip!", 'red')
#             continue
#         else:
#             print "You matched ip: %s" % hosts
#         color_print("Input the Command , The command will be Execute on servers, q/Q to quit.", 'green')
#         while True:
#             cmd = raw_input('\033[1;32mCmd(s): \033[0m')
#             if cmd in ['q', 'Q']:
#                 break
#             exec_log_dir = os.path.join(log_dir, 'exec_cmds')
#             if not os.path.isdir(exec_log_dir):
#                 os.mkdir(exec_log_dir)
#                 os.chmod(exec_log_dir, 0777)
#             filename = "%s/%s.log" % (exec_log_dir, time.strftime('%Y%m%d'))
#             f = open(filename, 'a')
#             f.write("DateTime: %s User: %s Host: %s Cmds: %s\n" %
#                     (time.strftime('%Y/%m/%d %H:%M:%S'), username, hosts, cmd))
#             multi_remote_exec_cmd(hosts, username, cmd)


def main():
    if not login_user:  # 判断用户是否存在
        color_print(u'没有该用户，或许你是以root运行的 No that user.', exits=True)

    print_prompt()
    gid_pattern = re.compile(r'^g\d+$')

    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                print_prompt()
                continue
            except KeyboardInterrupt:
                sys.exit(0)
            if option in ['P', 'p']:
                login_user.get_asset_info(printable=True)
                continue
            elif option in ['G', 'g']:
                login_user.get_asset_group_info(printable=True)
                continue
            elif gid_pattern.match(option):
                gid = option[1:].strip()
                asset_group = get_object(AssetGroup, id=gid)
                if asset_group and asset_group.is_permed(user=login_user):
                    asset_group.get_asset_info(printable=True)
                continue
            elif option in ['E', 'e']:
                # exec_cmd_servers(login_name)
                pass
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                try:
                    verify_connect(login_user, option)
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass

if __name__ == '__main__':
    main()


