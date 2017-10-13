# coding:utf-8
from django.db.models import Q
from django.template import RequestContext
from django.shortcuts import render_to_response, render
from jumpserver.api import *
from jperm.perm_api import user_have_perm
from django.http import HttpResponseNotFound
from jlog.log_api import renderJSON

from jlog.models import Log, ExecLog, FileLog, TermLog
from jumpserver.settings import LOG_DIR
import zipfile
import json
import pyte


@require_role('admin')
def log_list(request, offset):
    """ 显示日志 """
    header_title, path1 = u'审计', u'操作审计'
    date_seven_day = request.GET.get('start', '')
    date_now_str = request.GET.get('end', '')
    username_list = request.GET.getlist('username', [])
    host_list = request.GET.getlist('host', [])
    cmd = request.GET.get('cmd', '')

    if offset == 'online':
        keyword = request.GET.get('keyword', '')
        posts = Log.objects.filter(is_finished=False).order_by('-start_time')
        if keyword:
            posts = posts.filter(Q(user__icontains=keyword) | Q(host__icontains=keyword) |
                                 Q(login_type__icontains=keyword))

    elif offset == 'exec':
        posts = ExecLog.objects.all().order_by('-id')
        keyword = request.GET.get('keyword', '')
        if keyword:
            posts = posts.filter(Q(user__icontains=keyword) | Q(host__icontains=keyword) | Q(cmd__icontains=keyword))
    elif offset == 'file':
        posts = FileLog.objects.all().order_by('-id')
        keyword = request.GET.get('keyword', '')
        if keyword:
            posts = posts.filter(
                Q(user__icontains=keyword) | Q(host__icontains=keyword) | Q(filename__icontains=keyword))
    else:
        posts = Log.objects.filter(is_finished=True).order_by('-start_time')
        username_all = set([log.user for log in Log.objects.all()])
        ip_all = set([log.host for log in Log.objects.all()])

        if date_seven_day and date_now_str:
            datetime_start = datetime.datetime.strptime(date_seven_day + ' 00:00:01', '%m/%d/%Y %H:%M:%S')
            datetime_end = datetime.datetime.strptime(date_now_str + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            posts = posts.filter(start_time__gte=datetime_start).filter(start_time__lte=datetime_end)

        if username_list:
            posts = posts.filter(user__in=username_list)

        if host_list:
            posts = posts.filter(host__in=host_list)

        if cmd:
            log_id_list = set([log.log_id for log in TtyLog.objects.filter(cmd__contains=cmd)])
            posts = posts.filter(id__in=log_id_list)

        if not date_seven_day:
            date_now = datetime.datetime.now()
            date_now_str = date_now.strftime('%m/%d/%Y')
            date_seven_day = (date_now + datetime.timedelta(days=-7)).strftime('%m/%d/%Y')

    contact_list, p, contacts, page_range, current_page, show_first, show_end = pages(posts, request)

    session_id = request.session.session_key
    return render_to_response('jlog/log_%s.html' % offset, locals(), context_instance=RequestContext(request))


@require_role('admin')
def log_detail(request):
    return my_render('jlog/exec_detail.html', locals(), request)


@require_role('admin')
def log_kill(request):
    """ 杀掉connect进程 """
    pid = request.GET.get('id', '')
    log = Log.objects.filter(pid=pid)
    if log:
        log = log[0]
        try:
            os.kill(int(pid), 9)
        except OSError:
            pass
        Log.objects.filter(pid=pid).update(is_finished=1, end_time=datetime.datetime.now())
        return render_to_response('jlog/log_offline.html', locals(), context_instance=RequestContext(request))
    else:
        return HttpResponseNotFound(u'没有此进程!')


@require_role('admin')
def log_history(request):
    """ 命令历史记录 """
    log_id = request.GET.get('id', 0)
    log = Log.objects.filter(id=log_id)
    if log:
        log = log[0]
        tty_logs = log.ttylog_set.all()

        if tty_logs:
            content = ''
            for tty_log in tty_logs:
                content += '%s: %s\n' % (tty_log.datetime.strftime('%Y-%m-%d %H:%M:%S'), tty_log.cmd)
            return HttpResponse(content)

    return HttpResponse('无日志记录!')


# @require_role('admin')
# def log_record(request):
#     log_id = request.GET.get('id', 0)
#     log = Log.objects.filter(id=int(log_id))
#     if log:
#         log = log[0]
#         log_file = log.log_path + '.log'
#         log_time = log.log_path + '.time'
#         if os.path.isfile(log_file) and os.path.isfile(log_time):
#             content = renderTemplate(log_file, log_time)
#             return HttpResponse(content)
#         else:
#             return HttpResponse('无日志记录!')
@require_role('admin')
def log_record(request):
    """
    Author: liuzheng712@gmail.com
    """
    if request.method == "GET":
        return render(request, 'jlog/record.html')
    elif request.method == "POST":
        log_id = request.REQUEST.get('id', None)
        if log_id:
            TermL = TermLogRecorder(request.user)
            log = Log.objects.get(id=int(log_id))
            if len(log.filename) == 0:
                log_file = log.log_path + '.log'
                log_time = log.log_path + '.time'
                if os.path.isfile(log_file) and os.path.isfile(log_time):
                    content = renderJSON(log_file, log_time)
                    return HttpResponse(content)
            else:
                return HttpResponse(TermL.load_full_log(filename=log.filename))
        else:
            return HttpResponse("ERROR")
    else:
        return HttpResponse("ERROR METHOD!")


@require_role('admin')
def log_detail(request, offset):
    log_id = request.GET.get('id')
    if offset == 'exec':
        log = get_object(ExecLog, id=log_id)
        assets_hostname = log.host.split(' ')
        try:
            result = eval(str(log.result))
        except (SyntaxError, NameError):
            result = {}
        return my_render('jlog/exec_detail.html', locals(), request)
    elif offset == 'file':
        log = get_object(FileLog, id=log_id)
        assets_hostname = log.host.split(' ')
        file_list = log.filename.split(' ')
        try:
            result = eval(str(log.result))
        except (SyntaxError, NameError):
            result = {}
        return my_render('jlog/file_detail.html', locals(), request)


class TermLogRecorder(object):
    """
    TermLogRecorder
    ---
    Author: liuzheng <liuzheng712@gmail>
    This class is use for record the terminal output log.
        self.commands is pure commands list, it will have empty item '' because in vi/vim model , I made it log noting.
        self.CMD is the command with timestamp, like this {'1458723794.88': u'ls', '1458723799.82': u'tree'}.
        self.log is the all output with delta time log.
        self.vim_pattern is the regexp for check vi/vim/fg model.
    Usage:
        recorder = TermLogRecorder(user=UserObject) # or recorder = TermLogRecorder(uid=UserID)
        recoder.write(messages)
        recoder.save() # save all log into database
        # The following methods all have `user`,`uid`,args. Same as __init__
        list = recoder.list() # will give a object about this user's all log info
        recoder.load_full_log(filemane) # will get full log
        recoder.load_history(filename) # will only get the command history list
        recoder.share_to(filename,user=UserObject) # or recoder.share_to(filename,uid=UserID). will share this commands to someone
        recoder.unshare_to(filename,user=UserObject) # or recoder.unshare_to(filename,uid=UserID). will unshare this commands to someone
        recoder.setid(id) # registered this term with an id, for monitor
    """
    loglist = dict()

    def __init__(self, user=None, uid=None):
        self.log = {}
        self.id = 0
        if isinstance(user, User):
            self.user = user
        elif uid:
            self.user = User.objects.get(id=uid)
        else:
            self.user = None
        self.recoderStartTime = time.time()
        self.__init_screen_stream()
        self.recoder = False
        self.commands = []
        self._lists = None
        self.file = None
        self.filename = None
        self._data = None
        self.vim_pattern = re.compile(r'\W?vi[m]?\s.* | \W?fg\s.*', re.X)
        self._in_vim = False
        self.CMD = {}

    def __init_screen_stream(self):
        """
        Initializing the virtual screen and the character stream
        """
        self._stream = pyte.ByteStream()
        self._screen = pyte.Screen(100, 35)
        self._stream.attach(self._screen)

    def _command(self):
        for i in self._screen.display:
            if i.strip().__len__() > 0:
                self.commands.append(i.strip())
                if not i.strip() == '':
                    self.CMD[str(time.time())] = self.commands[-1]
        self._screen.reset()

    def setid(self, id):
        self.id = id
        TermLogRecorder.loglist[str(id)] = [self]

    def write(self, msg):
        """
        if self.recoder and (not self._in_vim):
            if self.commands.__len__() == 0:
                self._stream.feed(msg)
            elif not self.vim_pattern.search(self.commands[-1]):
                self._stream.feed(msg)
            else:
                self._in_vim = True
                self._command()
        else:
            if self._in_vim:
                if re.compile(r'\[\?1049', re.X).search(msg.decode('utf-8', 'replace')):
                    self._in_vim = False
                    self.commands.append('')
                self._screen.reset()
            else:
                self._command()
        """
        try:
            self.write_message(msg)
        except:
            pass
        # print "<<<<<<<<<<<<<<<<"
        # print self.commands
        # print self.CMD
        # print ">>>>>>>>>>>>>>>>"
        self.log[str(time.time() - self.recoderStartTime)] = msg.decode('utf-8', 'replace')

    def save(self, path=LOG_DIR):
        date = datetime.datetime.now().strftime('%Y%m%d')
        filename = str(uuid.uuid4())
        self.filename = filename
        filepath = os.path.join(path, 'tty', date, filename + '.zip')
        if not os.path.isdir(os.path.join(path, 'tty', date)):
            mkdir(os.path.join(path, 'tty', date), mode=777)
        while os.path.isfile(filepath):
            filename = str(uuid.uuid4())
            filepath = os.path.join(path, 'tty', date, filename + '.zip')
        password = str(uuid.uuid4())
        try:
            zf = zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED)
            zf.setpassword(password)
            zf.writestr(filename, json.dumps(self.log))
            zf.close()
            record = TermLog.objects.create(logPath=filepath, logPWD=password, filename=filename,
                                            history=json.dumps(self.CMD), timestamp=int(self.recoderStartTime))
            if self.user:
                record.user.add(self.user)
        except:
            record = TermLog.objects.create(logPath='locale', logPWD=password, log=json.dumps(self.log),
                                            filename=filename, history=json.dumps(self.CMD),
                                            timestamp=int(self.recoderStartTime))
            if self.user:
                record.user.add(self.user)
        try:
            del TermLogRecorder.loglist[str(self.id)]
        except KeyError:
            pass

    def list(self, user=None, uid=None):
        tmp = []
        if isinstance(user, User):
            user = user
        elif uid:
            user = User.objects.get(id=uid)
        else:
            user = self.user
        if user:
            self._lists = TermLog.objects.filter(user=user.id)
            for i in self._lists.all():
                tmp.append(
                    {'filename': i.filename, 'locale': i.logPath == 'locale', 'nick': i.nick, 'timestamp': i.timestamp,
                     'date': i.datetimestamp})
        return tmp

    def load_full_log(self, filename, user=None, uid=None):
        if isinstance(user, User):
            user = user
        elif uid:
            user = User.objects.get(id=uid)
        else:
            user = self.user
        if user:
            if self._lists:
                self.file = self._lists.get(filename=filename)
            else:
                self.file = TermLog.objects.get(filename=filename)
            if self.file.logPath == 'locale':
                return self.file.log
            else:
                try:
                    zf = zipfile.ZipFile(self.file.logPath, 'r', zipfile.ZIP_DEFLATED)
                    zf.setpassword(self.file.logPWD)
                    self._data = zf.read(zf.namelist()[0])
                    return self._data
                except KeyError:
                    return 'ERROR: Did not find %s file' % filename
        return 'ERROR User(None)'

    def load_history(self, filename, user=None, uid=None):
        if isinstance(user, User):
            user = user
        elif uid:
            user = User.objects.get(id=uid)
        else:
            user = self.user
        if user:
            if self._lists:
                self.file = self._lists.get(filename=filename)
            else:
                self.file = TermLog.objects.get(filename=filename)
            return self.file.history
        return 'ERROR User(None)'

    def share_to(self, filename, user=None, uid=None):
        if isinstance(user, User):
            user = user
        elif uid:
            user = User.objects.get(id=uid)
        else:
            pass
        if user:
            TermLog.objects.get(filename=filename).user.add(user)
            return True
        return False

    def unshare_to(self, filename, user=None, uid=None):
        if isinstance(user, User):
            user = user
        elif uid:
            user = User.objects.get(id=uid)
        else:
            pass
        if user:
            TermLog.objects.get(filename=filename).user.remove(user)
            return True
        return False
