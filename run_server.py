#!/usr/bin/env python
# coding: utf-8

import time
import datetime
import json
import os
import sys
import os.path
import threading
import re
import functools
from django.core.signals import request_started, request_finished

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.gen
import tornado.httpclient
from tornado.websocket import WebSocketClosedError

from tornado.options import define, options
from pyinotify import WatchManager, ProcessEvent, IN_DELETE, IN_CREATE, IN_MODIFY, AsyncNotifier
import select

from connect import Tty, User, Asset, PermRole, logger, get_object, gen_resource
from connect import TtyLog, Log, Session, user_have_perm, get_group_user_perm, MyRunner, ExecLog

try:
    import simplejson as json
except ImportError:
    import json

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
from jumpserver.settings import IP, PORT

define("port", default=PORT, help="run on the given port", type=int)
define("host", default=IP, help="run port on given host", type=str)
from jlog.views import TermLogRecorder


def django_request_support(func):
    @functools.wraps(func)
    def _deco(*args, **kwargs):
        request_started.send_robust(func)
        response = func(*args, **kwargs)
        request_finished.send_robust(func)
        return response

    return _deco


def require_auth(role='user'):
    def _deco(func):
        def _deco2(request, *args, **kwargs):
            if request.get_cookie('sessionid'):
                session_key = request.get_cookie('sessionid')
            else:
                session_key = request.get_argument('sessionid', '')

            logger.debug('Websocket: session_key: %s' % session_key)
            if session_key:
                session = get_object(Session, session_key=session_key)
                logger.debug('Websocket: session: %s' % session)
                if session and datetime.datetime.now() < session.expire_date:
                    user_id = session.get_decoded().get('_auth_user_id')
                    request.user_id = user_id
                    user = get_object(User, id=user_id)
                    if user:
                        logger.debug('Websocket: user [ %s ] request websocket' % user.username)
                        request.user = user
                        if role == 'admin':
                            if user.role in ['SU', 'GA']:
                                return func(request, *args, **kwargs)
                            logger.debug('Websocket: user [ %s ] is not admin.' % user.username)
                        else:
                            return func(request, *args, **kwargs)
                else:
                    logger.debug('Websocket: session expired: %s' % session_key)
            try:
                request.close()
            except AttributeError:
                pass
            logger.warning('Websocket: Request auth failed.')

        return _deco2

    return _deco


class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            super(MyThread, self).run()
        except WebSocketClosedError:
            pass


class EventHandler(ProcessEvent):
    def __init__(self, client=None):
        self.client = client

    def process_IN_MODIFY(self, event):
        self.client.write_message(f.read().decode('utf-8', 'replace'))


def file_monitor(path='.', client=None):
    wm = WatchManager()
    mask = IN_DELETE | IN_CREATE | IN_MODIFY
    notifier = AsyncNotifier(wm, EventHandler(client))
    wm.add_watch(path, mask, auto_add=True, rec=True)
    if not os.path.isfile(path):
        logger.debug("File %s does not exist." % path)
        sys.exit(3)
    else:
        logger.debug("Now starting monitor file %s." % path)
        global f
        f = open(path, 'r')
        st_size = os.stat(path)[6]
        f.seek(st_size)

    while True:
        try:
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()
        except KeyboardInterrupt:
            print "keyboard Interrupt."
            notifier.stop()
            break


class MonitorHandler(tornado.websocket.WebSocketHandler):
    clients = []
    threads = []

    def __init__(self, *args, **kwargs):
        self.file_path = None
        super(self.__class__, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    @django_request_support
    @require_auth('admin')
    def open(self):
        # 获取监控的path
        self.file_path = self.get_argument('file_path', '')
        MonitorHandler.clients.append(self)
        thread = MyThread(target=file_monitor, args=('%s.log' % self.file_path, self))
        MonitorHandler.threads.append(thread)
        self.stream.set_nodelay(True)

        try:
            for t in MonitorHandler.threads:
                if t.is_alive():
                    continue
                t.setDaemon(True)
                t.start()

        except WebSocketClosedError:
            client_index = MonitorHandler.clients.index(self)
            MonitorHandler.threads[client_index].stop()
            MonitorHandler.clients.remove(self)
            MonitorHandler.threads.remove(MonitorHandler.threads[client_index])

        logger.debug("Websocket: Monitor client num: %s, thread num: %s" % (len(MonitorHandler.clients),
                                                                            len(MonitorHandler.threads)))

    def on_message(self, message):
        # 监控日志，发生变动发向客户端
        pass

    def on_close(self):
        # 客户端主动关闭
        # self.close()

        logger.debug("Websocket: Monitor client close request")
        try:
            client_index = MonitorHandler.clients.index(self)
            MonitorHandler.clients.remove(self)
            MonitorHandler.threads.remove(MonitorHandler.threads[client_index])
        except ValueError:
            pass


class WebTty(Tty):
    def __init__(self, *args, **kwargs):
        super(WebTty, self).__init__(*args, **kwargs)
        self.ws = None
        self.data = ''
        self.input_mode = False


class WebTerminalKillHandler(tornado.web.RequestHandler):
    @django_request_support
    @require_auth('admin')
    def get(self):
        ws_id = self.get_argument('id')
        Log.objects.filter(id=ws_id).update(is_finished=True)
        for ws in WebTerminalHandler.clients:
            if ws.id == int(ws_id):
                logger.debug("Kill log id %s" % ws_id)
                ws.log.save()
                ws.close()
        logger.debug('Websocket: web terminal client num: %s' % len(WebTerminalHandler.clients))


class ExecHandler(tornado.websocket.WebSocketHandler):
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.id = 0
        self.user = None
        self.role = None
        self.runner = None
        self.assets = []
        self.perm = {}
        self.remote_ip = ''
        super(ExecHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    @django_request_support
    @require_auth('user')
    def open(self):
        logger.debug('Websocket: Open exec request')
        role_name = self.get_argument('role', 'sb')
        self.remote_ip = self.request.headers.get("X-Real-IP")
        if not self.remote_ip:
            self.remote_ip = self.request.remote_ip
        logger.debug('Web执行命令: 请求系统用户 %s' % role_name)
        self.role = get_object(PermRole, name=role_name)
        self.perm = get_group_user_perm(self.user)
        roles = self.perm.get('role').keys()
        if self.role not in roles:
            self.write_message('No perm that role %s' % role_name)
            self.close()
        self.assets = self.perm.get('role').get(self.role).get('asset')

        res = gen_resource({'user': self.user, 'asset': self.assets, 'role': self.role})
        self.runner = MyRunner(res)
        message = '有权限的主机: ' + ', '.join([asset.hostname for asset in self.assets])
        self.__class__.clients.append(self)
        self.write_message(message)

    def on_message(self, message):
        data = json.loads(message)
        pattern = data.get('pattern', '')
        self.command = data.get('command', '')
        self.asset_name_str = ''
        if pattern and self.command:
            for inv in self.runner.inventory.get_hosts(pattern=pattern):
                self.asset_name_str += '%s ' % inv.name
            self.write_message('匹配主机: ' + self.asset_name_str)
            self.write_message('<span style="color: yellow">Ansible> %s</span>\n\n' % self.command)
            self.__class__.tasks.append(MyThread(target=self.run_cmd, args=(self.command, pattern)))

        for t in self.__class__.tasks:
            if t.is_alive():
                continue
            try:
                t.setDaemon(True)
                t.start()
            except RuntimeError:
                pass

    def run_cmd(self, command, pattern):
        self.runner.run('shell', command, pattern=pattern)
        ExecLog(host=self.asset_name_str, cmd=self.command, user=self.user.username,
                remote_ip=self.remote_ip, result=self.runner.results).save()
        newline_pattern = re.compile(r'\n')
        for k, v in self.runner.results.items():
            for host, output in v.items():
                output = newline_pattern.sub('<br />', output)
                if k == 'ok':
                    header = "<span style='color: green'>[ %s => %s]</span>\n" % (host, 'Ok')
                else:
                    header = "<span style='color: red'>[ %s => %s]</span>\n" % (host, 'failed')
                self.write_message(header)
                self.write_message(output)

        self.write_message('\n~o~ Task finished ~o~\n')

    def on_close(self):
        logger.debug('关闭web_exec请求')


class WebTerminalHandler(tornado.websocket.WebSocketHandler):
    clients = []
    tasks = []

    def __init__(self, *args, **kwargs):
        self.term = None
        self.log_file_f = None
        self.log_time_f = None
        self.log = None
        self.id = 0
        self.user = None
        self.ssh = None
        self.channel = None
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    @django_request_support
    @require_auth('user')
    def open(self):
        logger.debug('Websocket: Open request')
        role_name = self.get_argument('role', 'sb')
        asset_id = self.get_argument('id', 9999)
        asset = get_object(Asset, id=asset_id)
        self.termlog = TermLogRecorder(User.objects.get(id=self.user_id))
        if asset:
            roles = user_have_perm(self.user, asset)
            logger.debug(roles)
            logger.debug('系统用户: %s' % role_name)
            login_role = ''
            for role in roles:
                if role.name == role_name:
                    login_role = role
                    break
            if not login_role:
                logger.warning('Websocket: Not that Role %s for Host: %s User: %s ' % (role_name, asset.hostname,
                                                                                       self.user.username))
                self.close()
                return
        else:
            logger.warning('Websocket: No that Host: %s User: %s ' % (asset_id, self.user.username))
            self.close()
            return
        logger.debug('Websocket: request web terminal Host: %s User: %s Role: %s' % (asset.hostname, self.user.username,
                                                                                     login_role.name))
        self.term = WebTty(self.user, asset, login_role, login_type='web')
        # self.term.remote_ip = self.request.remote_ip
        self.term.remote_ip = self.request.headers.get("X-Real-IP")
        if not self.term.remote_ip:
            self.term.remote_ip = self.request.remote_ip
        self.ssh = self.term.get_connection()
        self.channel = self.ssh.invoke_shell(term='xterm')
        WebTerminalHandler.tasks.append(MyThread(target=self.forward_outbound))
        WebTerminalHandler.clients.append(self)

        for t in WebTerminalHandler.tasks:
            if t.is_alive():
                continue
            try:
                t.setDaemon(True)
                t.start()
            except RuntimeError:
                pass

    def on_message(self, message):
        jsondata = json.loads(message)
        if not jsondata:
            return

        if 'resize' in jsondata.get('data'):
            self.termlog.write(message)
            self.channel.resize_pty(
                width=int(jsondata.get('data').get('resize').get('cols', 100)),
                height=int(jsondata.get('data').get('resize').get('rows', 35))
            )
        elif jsondata.get('data'):
            self.termlog.recoder = True
            self.term.input_mode = True
            if str(jsondata['data']) in ['\r', '\n', '\r\n']:
                match = re.compile(r'\x1b\[\?1049', re.X).findall(self.term.vim_data)
                if match:
                    if self.term.vim_flag or len(match) == 2:
                        self.term.vim_flag = False
                    else:
                        self.term.vim_flag = True
                elif not self.term.vim_flag:
                    result = self.term.deal_command(self.term.data)[0:200]
                    if len(result) > 0:
                        TtyLog(log=self.log, datetime=datetime.datetime.now(), cmd=result).save()
                self.term.vim_data = ''
                self.term.data = ''
                self.term.input_mode = False
            self.channel.send(jsondata['data'])
        else:
            pass

    def on_close(self):
        logger.debug('Websocket: Close request')
        print self.termlog.CMD
        self.termlog.save()
        if self in WebTerminalHandler.clients:
            WebTerminalHandler.clients.remove(self)
        try:
            self.log_file_f.write('End time is %s' % datetime.datetime.now())
            self.log.is_finished = True
            self.log.end_time = datetime.datetime.now()
            self.log.filename = self.termlog.filename
            self.log.save()
            self.log_time_f.close()
            self.ssh.close()
            self.close()
        except AttributeError:
            pass

    def forward_outbound(self):
        self.log_file_f, self.log_time_f, self.log = self.term.get_log()
        self.id = self.log.id
        self.termlog.setid(self.id)
        try:
            data = ''
            pre_timestamp = time.time()
            while True:
                r, w, e = select.select([self.channel], [], [])
                if self.channel in r:
                    recv = self.channel.recv(1024)
                    if not len(recv):
                        return
                    data += recv
                    self.term.vim_data += recv
                    try:
                        self.write_message(data.decode('utf-8', 'replace'))
                        self.termlog.write(data)
                        self.termlog.recoder = False
                        now_timestamp = time.time()
                        self.log_time_f.write('%s %s\n' % (round(now_timestamp - pre_timestamp, 4), len(data)))
                        self.log_file_f.write(data)
                        pre_timestamp = now_timestamp
                        self.log_file_f.flush()
                        self.log_time_f.flush()
                        if self.term.input_mode:
                            self.term.data += data
                        data = ''
                    except UnicodeDecodeError:
                        pass
        except IndexError:
            pass


# class MonitorHandler(WebTerminalHandler):
#     @django_request_support
#     @require_auth('user')
#     def open(self):
#         try:
#             self.returnlog = TermLogRecorder.loglist[self.get_argument('id')]
#             self.returnlog.write_message = self.write_message
#         except:
#             self.write_message('Log is None')
#             self.close()
#
#     def on_message(self, message):
#         pass
#
#     def on_close(self):
#         self.close()


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/monitor', MonitorHandler),
            (r'/terminal', WebTerminalHandler),
            (r'/kill', WebTerminalKillHandler),
            (r'/exec', ExecHandler),
        ]

        setting = {
            'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
            'debug': False,
        }

        tornado.web.Application.__init__(self, handlers, **setting)


def main():
    from django.core.wsgi import get_wsgi_application
    import tornado.wsgi
    wsgi_app = get_wsgi_application()
    container = tornado.wsgi.WSGIContainer(wsgi_app)
    setting = {
        'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
        'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
        'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        'debug': False,
    }
    tornado_app = tornado.web.Application(
        [
            (r'/ws/monitor', MonitorHandler),
            (r'/ws/terminal', WebTerminalHandler),
            (r'/ws/kill', WebTerminalKillHandler),
            (r'/ws/exec', ExecHandler),
            (r"/static/(.*)", tornado.web.StaticFileHandler,
             dict(path=os.path.join(os.path.dirname(__file__), "static"))),
            ('.*', tornado.web.FallbackHandler, dict(fallback=container)),
        ], **setting)

    server = tornado.httpserver.HTTPServer(tornado_app)
    server.listen(options.port, address=IP)

    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    # tornado.options.parse_command_line()
    # app = Application()
    # server = tornado.httpserver.HTTPServer(app)
    # server.bind(options.port, options.host)
    # #server.listen(options.port)
    # server.start(num_processes=5)
    # tornado.ioloop.IOLoop.instance().start()
    print "Run server on %s:%s" % (options.host, options.port)
    main()
