# coding: utf-8

import time
import datetime
import json
import os
import sys
import os.path
import threading
import datetime
import urllib

import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.gen
import tornado.httpclient
from tornado.websocket import WebSocketClosedError

from tornado.options import define, options
from pyinotify import WatchManager, Notifier, ProcessEvent, IN_DELETE, IN_CREATE, IN_MODIFY, AsyncNotifier
import select

from connect import Tty, User, Asset, PermRole, logger, get_object
from connect import TtyLog, Log, Session, user_have_perm

try:
    import simplejson as json
except ImportError:
    import json


define("port", default=3000, help="run on the given port", type=int)
define("host", default='0.0.0.0', help="run port on", type=str)


def require_auth(role='user'):
    def _deco(func):
        def _deco(request, *args, **kwargs):
            if request.get_cookie('sessionid'):
                session_key = request.get_cookie('sessionid')
            else:
                session_key = request.get_secure_cookie('sessionid')

            logger.debug('Websocket: session_key: ' + session_key)

            if session_key:
                session = get_object(Session, session_key=session_key)
                if session and datetime.datetime.now() > session.expire_date:
                    user_id = session.get_decoded().get('_auth_user_id')
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
            request.close()
            logger.warning('Websocket: Request auth failed.')
        # asset_id = int(request.get_argument('id', 9999))
        # print asset_id
        # asset = Asset.objects.filter(id=asset_id)
        # if asset:
        #     asset = asset[0]
        #     request.asset = asset
        # else:
        #     request.close()
        #
        # if user:
        #     user = user[0]
        #     request.user = user
        #
        # else:
        #     print("No session user.")
        #     request.close()
        return _deco
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

    def process_IN_CREATE(self, event):
        print "Create file:%s." % os.path.join(event.path, event.name)

    def process_IN_DELETE(self, event):
        print "Delete file:%s." % os.path.join(event.path, event.name)

    def process_IN_MODIFY(self, event):
        print "Modify file:%s." % os.path.join(event.path, event.name)
        self.client.write_message(f.read())


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


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/monitor', MonitorHandler),
            (r'/terminal', WebTerminalHandler),
            (r'/kill', WebTerminalKillHandler),
        ]

        setting = {
            'cookie_secret': 'DFksdfsasdfkasdfFKwlwfsdfsa1204mx',
            'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
            'static_path': os.path.join(os.path.dirname(__file__), 'static'),
            'debug': True,
        }

        tornado.web.Application.__init__(self, handlers, **setting)


class MonitorHandler(tornado.websocket.WebSocketHandler):
    clients = []
    threads = []

    def __init__(self, *args, **kwargs):
        self.file_path = None
        super(self.__class__, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

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
        self.login_type = 'web'
        self.ws = None
        self.data = ''
        self.input_mode = False


class WebTerminalKillHandler(tornado.web.RequestHandler):
    @require_auth('admin')
    def get(self):
        ws_id = self.get_argument('id')
        Log.objects.filter(id=ws_id).update(is_finished=True)
        for ws in WebTerminalHandler.clients:
            print ws.id
            if ws.id == int(ws_id):
                print "killed"
                ws.log.save()
                ws.close()
        print len(WebTerminalHandler.clients)


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
        super(WebTerminalHandler, self).__init__(*args, **kwargs)

    def check_origin(self, origin):
        return True

    @require_auth
    def open(self):
        role_name = self.get_argument('role', 'sb')
        asset_id = self.get_argument('id', 9999)
        asset = get_object(Asset, id=asset_id)
        if asset:
            roles = user_have_perm(self.user, asset)
            login_role = ''
            for role in roles:
                if role.name == role_name:
                    login_role = role
                    break
            if not login_role:
                logger.warning('Websocket: Not that Role %s for Host: %s User: %s ' % (role_name, asset.name,
                                                                                       self.user.username))
                self.close()
                return
        logger.debug('Websocket: request web terminal Host: %s User: %s Role: %s' % ())
        # Todo: 判断
        self.term = WebTty(self.user, self.asset, login_role)
        self.term.get_connection()
        self.term.channel = self.term.ssh.invoke_shell(term='xterm')
        WebTerminalHandler.tasks.append(MyThread(target=self.forward_outbound))
        WebTerminalHandler.clients.append(self)

        for t in WebTerminalHandler.tasks:
            if t.is_alive():
                continue
            t.setDaemon(True)
            t.start()

    def on_message(self, message):
        data = json.loads(message)
        if not data:
            return
        if data.get('data'):
            self.term.input_mode = True
            if str(data['data']) in ['\r', '\n', '\r\n']:
                if self.term.vim_flag:
                    match = self.term.ps1_pattern.search(self.term.vim_data)
                    if match:
                        self.term.vim_flag = False
                        vim_data = self.term.deal_command(self.term.vim_data)[0:200]
                        if len(data) > 0:
                            TtyLog(log=self.log, datetime=datetime.datetime.now(), cmd=vim_data).save()

                TtyLog(log=self.log, datetime=datetime.datetime.now(),
                       cmd=self.term.deal_command(self.term.data)[0:200]).save()
                self.term.vim_data = ''
                self.term.data = ''
                self.term.input_mode = False
            self.term.channel.send(data['data'])

    def on_close(self):
        print 'On_close'
        if self in WebTerminalHandler.clients:
            WebTerminalHandler.clients.remove(self)
        try:
            self.log_file_f.write('End time is %s' % datetime.datetime.now())
            self.log.is_finished = True
            self.log.end_time = datetime.datetime.now()
            self.log.save()
            self.close()
        except AttributeError:
            pass

    def forward_outbound(self):
        self.log_file_f, self.log_time_f, self.log = self.term.get_log()
        self.id = self.log.id
        try:
            data = ''
            pre_timestamp = time.time()
            while True:
                r, w, e = select.select([self.term.channel, sys.stdin], [], [])
                if self.term.channel in r:
                    recv = self.term.channel.recv(1024)
                    if not len(recv):
                        return
                    data += recv
                    if self.term.vim_flag:
                        self.term.vim_data += recv
                    try:
                        self.write_message(json.dumps({'data': data}))
                        now_timestamp = time.time()
                        self.log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(data)))
                        self.log_file_f.write(data)
                        pre_timestamp = now_timestamp
                        self.log_file_f.flush()
                        self.log_time_f.flush()
                        if self.term.input_mode and not self.term.is_output(data):
                            self.term.data += data
                        data = ''
                    except UnicodeDecodeError:
                        pass
        finally:
            self.close()

if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.bind(options.port, options.host)
    # server.listen(options.port)
    server.start(num_processes=1)
    print "Run server on %s:%s" % (options.host, options.port)
    tornado.ioloop.IOLoop.instance().start()
