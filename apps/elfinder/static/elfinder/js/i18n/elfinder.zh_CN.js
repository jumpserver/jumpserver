/**
 * 简体中文 translation
 * @author 翻译者 deerchao <deerchao@gmail.com>
 * @author Andy Hu <andyhu7@yahoo.com.hk>
 * @author Max Wen<max.wen@qq.com>
 * @author Kejun Chang <changkejun@hotmail.com>
 * @version 2017-02-03
 */
/**
 * elFinder translation template
 * use this file to create new translation
 * submit new translation via https://github.com/Studio-42/elFinder/issues
 * or make a pull request
 */

/**
 * 简体中文 translation
 * @author Translator Name <translator@email.tld>
 * @version 201x-xx-xx
 */
(function(root, factory) {
	if (typeof define === 'function' && define.amd) {
		define(['elfinder'], factory);
	} else if (typeof exports !== 'undefined') {
		module.exports = factory(require('elfinder'));
	} else {
		factory(root.elFinder);
	}
}(this, function(elFinder) {
	elFinder.prototype.i18.zh_CN = {
		translator : '翻译者 deerchao &lt;deerchao@gmail.com&gt;, Andy Hu &lt;andyhu7@yahoo.com.hk&gt;, Max Wen&lt;max.wen@qq.com&gt;, Kejun Chang &lt;changkejun@hotmail.com&gt;',
		language   : '简体中文',
		direction  : 'ltr',
		dateFormat : 'Y-m-d H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : '错误',
			'errUnknown'           : '未知的错误.',
			'errUnknownCmd'        : '未知的命令.',
			'errJqui'              : '无效的 jQuery UI 配置. 必须包含 Selectable, draggable 以及 droppable 组件.',
			'errNode'              : 'elFinder 需要能创建 DOM 元素.',
			'errURL'               : '无效的 elFinder 配置! URL 选项未配置.',
			'errAccess'            : '访问被拒绝.',
			'errConnect'           : '不能连接到后端.',
			'errAbort'             : '连接中止.',
			'errTimeout'           : '连接超时.',
			'errNotFound'          : '未找到后端.',
			'errResponse'          : '无效的后端响应.',
			'errConf'              : '无效的后端配置.',
			'errJSON'              : 'PHP JSON 模块未安装.',
			'errNoVolumes'         : '无可读的卷.',
			'errCmdParams'         : '无效的参数, 命令: "$1".',
			'errDataNotJSON'       : '响应不符合 JSON 格式.',
			'errDataEmpty'         : '响应为空.',
			'errCmdReq'            : '后端请求需要命令名称.',
			'errOpen'              : '无法打开 "$1".',
			'errNotFolder'         : '对象不是文件夹.',
			'errNotFile'           : '对象不是文件.',
			'errRead'              : '无法读取 "$1".',
			'errWrite'             : '无法写入 "$1".',
			'errPerm'              : '无权限.',
			'errLocked'            : '"$1" 被锁定,不能重命名, 移动或删除.',
			'errExists'            : '文件 "$1" 已经存在了.',
			'errInvName'           : '无效的文件名.',
			'errFolderNotFound'    : '未找到文件夹.',
			'errFileNotFound'      : '未找到文件.',
			'errTrgFolderNotFound' : '未找到目标文件夹 "$1".',
			'errPopup'             : '浏览器拦截了弹出窗口. 请在选项中允许弹出窗口.',
			'errMkdir'             : '不能创建文件夹 "$1".',
			'errMkfile'            : '不能创建文件 "$1".',
			'errRename'            : '不能重命名 "$1".',
			'errCopyFrom'          : '不允许从卷 "$1" 复制.',
			'errCopyTo'            : '不允许向卷 "$1" 复制.',
			'errMkOutLink'         : '无法创建链接到卷根以外的链接.', // from v2.1 added 03.10.2015
			'errUpload'            : '上传出错.',  // old name - errUploadCommon
			'errUploadFile'        : '无法上传 "$1".', // old name - errUpload
			'errUploadNoFiles'     : '未找到要上传的文件.',
			'errUploadTotalSize'   : '数据超过了允许的最大大小.', // old name - errMaxSize
			'errUploadFileSize'    : '文件超过了允许的最大大小.', //  old name - errFileMaxSize
			'errUploadMime'        : '不允许的文件类型.',
			'errUploadTransfer'    : '"$1" 传输错误.',
			'errUploadTemp'        : '无法为上传文件创建临时文件.', // from v2.1 added 26.09.2015
			'errNotReplace'        : '对象 "$1" 已经在此位置存在, 不能被其他对象替换.', // new
			'errReplace'           : '无法替换 "$1".',
			'errSave'              : '无法保存 "$1".',
			'errCopy'              : '无法复制 "$1".',
			'errMove'              : '无法移动 "$1".',
			'errCopyInItself'      : '不能移动 "$1" 到原有位置.',
			'errRm'                : '无法删除 "$1".',
			'errRmSrc'             : '不能删除源文件.',
			'errExtract'           : '无法从 "$1" 提取文件.',
			'errArchive'           : '无法创建压缩包.',
			'errArcType'           : '不支持的压缩格式.',
			'errNoArchive'         : '文件不是压缩包, 或者不支持该压缩格式.',
			'errCmdNoSupport'      : '后端不支持该命令.',
			'errReplByChild'       : '文件夹 “$1” 不能被它所包含的项目替换.',
			'errArcSymlinks'       : '出于安全上的考虑，不允许解压包含符号链接的压缩包.', // edited 24.06.2012
			'errArcMaxSize'        : '压缩包文件超过最大允许文件大小范围.',
			'errResize'            : '无法重新调整大小 "$1".',
			'errResizeDegree'      : '无效的旋转角度.',  // added 7.3.2013
			'errResizeRotate'      : '无法旋转图片.',  // added 7.3.2013
			'errResizeSize'        : '无效的图片尺寸.',  // added 7.3.2013
			'errResizeNoChange'    : '图片尺寸未改变.',  // added 7.3.2013
			'errUsupportType'      : '不被支持的文件格式.',
			'errNotUTF8Content'    : '文件 "$1" 不是 UTF-8 格式, 不能编辑.',  // added 9.11.2011
			'errNetMount'          : '无法装载 "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : '不支持该协议.',     // added 17.04.2012
			'errNetMountFailed'    : '装载失败.',         // added 17.04.2012
			'errNetMountHostReq'   : '需要指定主机.', // added 18.04.2012
			'errSessionExpires'    : '您的会话由于长时间未活动已过期.',
			'errCreatingTempDir'   : '无法创建临时目录: "$1"',
			'errFtpDownloadFile'   : '无法从FTP下载: "$1" 文件',
			'errFtpUploadFile'     : '无法将文件: "$1" 上传至FTP',
			'errFtpMkdir'          : '无法在FTP上创建远程目录: "$1"',
			'errArchiveExec'       : '归档文件时出错: "$1"',
			'errExtractExec'       : '解压文件时出错: "$1"',
			'errNetUnMount'        : '无法卸载', // from v2.1 added 30.04.2012
			'errConvUTF8'          : '未转换至UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : '如果您需要上传目录, 请尝试使用Google Chrome.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : '搜索 "$1" 超时. 仅显示部分搜索结果.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : '必需重新授权.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : '可选择项目的最大数量为 $1.', // from v2.1.17 added 17.10.2016

			/******************************* commands names ********************************/
			'cmdarchive'   : '创建压缩包',
			'cmdback'      : '后退',
			'cmdcopy'      : '复制',
			'cmdcut'       : '剪切',
			'cmddownload'  : '下载',
			'cmdduplicate' : '创建复本',
			'cmdedit'      : '编辑文件',
			'cmdextract'   : '从压缩包提取文件',
			'cmdforward'   : '前进',
			'cmdgetfile'   : '选择文件',
			'cmdhelp'      : '关于本软件',
			'cmdhome'      : '首页',
			'cmdinfo'      : '查看信息',
			'cmdmkdir'     : '新建文件夹',
			'cmdmkdirin'   : '至新文件夹', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : '新建文本文件',
			'cmdopen'      : '打开',
			'cmdpaste'     : '粘贴',
			'cmdquicklook' : '预览',
			'cmdreload'    : '刷新',
			'cmdrename'    : '重命名',
			'cmdrm'        : '删除',
			'cmdsearch'    : '查找文件',
			'cmdup'        : '转到上一级文件夹',
			'cmdupload'    : '上传文件',
			'cmdview'      : '查看',
			'cmdresize'    : '重新调整大小',
			'cmdsort'      : '排序',
			'cmdnetmount'  : '装载网络卷', // added 18.04.2012
			'cmdnetunmount': '卸载', // from v2.1 added 30.04.2012
			'cmdplaces'    : '添加到收藏夹', // added 28.12.2014
			'cmdchmod'     : '改变模式', // from v2.1 added 20.6.2015
			'cmdopendir'   : '打开文件夹', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : '设置列宽', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': '全屏显示', // from v2.1.15 added 03.08.2016
			'cmdmove'      : '移动', // from v2.1.15 added 21.08.2016

			/*********************************** buttons ***********************************/
			'btnClose'  : '关闭',
			'btnSave'   : '保存',
			'btnRm'     : '删除',
			'btnApply'  : '应用',
			'btnCancel' : '取消',
			'btnNo'     : '否',
			'btnYes'    : '是',
			'btnMount'  : '装载',  // added 18.04.2012
			'btnApprove': '至 $1 并确认', // from v2.1 added 26.04.2012
			'btnUnmount': '卸载', // from v2.1 added 30.04.2012
			'btnConv'   : '转换', // from v2.1 added 08.04.2014
			'btnCwd'    : '这里',      // from v2.1 added 22.5.2015
			'btnVolume' : '卷',    // from v2.1 added 22.5.2015
			'btnAll'    : '全部',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME类型', // from v2.1 added 22.5.2015
			'btnFileName':'文件名',  // from v2.1 added 22.5.2015
			'btnSaveClose': '保存并关闭', // from v2.1 added 12.6.2015
			'btnBackup' : '备份', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : '打开文件夹',
			'ntffile'     : '打开文件',
			'ntfreload'   : '刷新文件夹内容',
			'ntfmkdir'    : '创建文件夹',
			'ntfmkfile'   : '创建文件',
			'ntfrm'       : '删除文件',
			'ntfcopy'     : '复制文件',
			'ntfmove'     : '移动文件',
			'ntfprepare'  : '准备复制文件',
			'ntfrename'   : '重命名文件',
			'ntfupload'   : '上传文件',
			'ntfdownload' : '下载文件',
			'ntfsave'     : '保存文件',
			'ntfarchive'  : '创建压缩包',
			'ntfextract'  : '从压缩包提取文件',
			'ntfsearch'   : '搜索文件',
			'ntfresize'   : '正在更改尺寸',
			'ntfsmth'     : '正在忙 >_<',
			'ntfloadimg'  : '正在加载图片',
			'ntfnetmount' : '正在装载网络卷', // added 18.04.2012
			'ntfnetunmount': '卸载网络卷', // from v2.1 added 30.04.2012
			'ntfdim'      : '获取图像尺寸', // added 20.05.2013
			'ntfreaddir'  : '正在读取文件夹信息', // from v2.1 added 01.07.2013
			'ntfurl'      : '正在获取链接地址', // from v2.1 added 11.03.2014
			'ntfchmod'    : '正在改变文件模式', // from v2.1 added 20.6.2015
			'ntfpreupload': '正在验证上传文件名', // from v2.1 added 31.11.2015
			'ntfzipdl'    : '正在创建一个下载文件', // from v2.1.7 added 23.1.2016
			'ntfparents'  : '正在取得路径信息', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': '正在处理上传文件', // from v2.1.17 added 2.11.2016

			/************************************ dates **********************************/
			'dateUnknown' : '未知',
			'Today'       : '今天',
			'Yesterday'   : '昨天',
			'msJan'       : '一月',
			'msFeb'       : '二月',
			'msMar'       : '三月',
			'msApr'       : '四月',
			'msMay'       : '五月',
			'msJun'       : '六月',
			'msJul'       : '七月',
			'msAug'       : '八月',
			'msSep'       : '九月',
			'msOct'       : '十月',
			'msNov'       : '十一月',
			'msDec'       : '十二月',
			'January'     : '一月',
			'February'    : '二月',
			'March'       : '三月',
			'April'       : '四月',
			'May'         : '五月',
			'June'        : '六月',
			'July'        : '七月',
			'August'      : '八月',
			'September'   : '九月',
			'October'     : '十月',
			'November'    : '十一月',
			'December'    : '十二月',
			'Sunday'      : '星期日',
			'Monday'      : '星期一',
			'Tuesday'     : '星期二',
			'Wednesday'   : '星期三',
			'Thursday'    : '星期四',
			'Friday'      : '星期五',
			'Saturday'    : '星期六',
			'Sun'         : '周日',
			'Mon'         : '周一',
			'Tue'         : '周二',
			'Wed'         : '周三',
			'Thu'         : '周四',
			'Fri'         : '周五',
			'Sat'         : '周六',

			/******************************** sort variants ********************************/
			'sortname'          : '按名称',
			'sortkind'          : '按类型',
			'sortsize'          : '按大小',
			'sortdate'          : '按日期',
			'sortFoldersFirst'  : '文件夹优先',
			'sortperm'          : '按权限排序', // from v2.1.13 added 13.06.2016
			'sortmode'          : '按属性排序',       // from v2.1.13 added 13.06.2016
			'sortowner'         : '按所有者排序',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : '按组排序',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : '同时刷新树状目录',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : '新文件.txt', // added 10.11.2015
			'untitled folder'   : '新文件夹',   // added 10.11.2015
			'Archive'           : '新压缩包',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : '请确认',
			'confirmRm'       : '确定要删除文件吗?<br/>该操作不可撤销!',
			'confirmRepl'     : '用新的文件替换原有文件?',
			'confirmConvUTF8' : '文件不是UTF-8格式.<br/>转换为UTF-8吗？<br/>通过在转换后保存,内容变为UTF-8.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : '无法检测到此文件的字符编码.需要暂时转换此文件为UTF-8编码以进行编辑.<br/>请选择此文件的字符编码.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : '文件已被编辑.<br/>如果不保存直接关闭,将丢失编辑内容.', // from v2.1 added 15.7.2015
			'apllyAll'        : '全部应用',
			'name'            : '名称',
			'size'            : '大小',
			'perms'           : '权限',
			'modify'          : '修改于',
			'kind'            : '类别',
			'read'            : '读取',
			'write'           : '写入',
			'noaccess'        : '无权限',
			'and'             : '和',
			'unknown'         : '未知',
			'selectall'       : '选择所有文件',
			'selectfiles'     : '选择文件',
			'selectffile'     : '选择第一个文件',
			'selectlfile'     : '选择最后一个文件',
			'viewlist'        : '列表视图',
			'viewicons'       : '图标视图',
			'places'          : '位置',
			'calc'            : '计算',
			'path'            : '路径',
			'aliasfor'        : '别名',
			'locked'          : '锁定',
			'dim'             : '尺寸',
			'files'           : '文件',
			'folders'         : '文件夹',
			'items'           : '项目',
			'yes'             : '是',
			'no'              : '否',
			'link'            : '链接',
			'searcresult'     : '搜索结果',
			'selected'        : '选中的项目',
			'about'           : '关于',
			'shortcuts'       : '快捷键',
			'help'            : '帮助',
			'webfm'           : '网络文件管理器',
			'ver'             : '版本',
			'protocolver'     : '协议版本',
			'homepage'        : '项目主页',
			'docs'            : '文档',
			'github'          : '复刻我们的Github',
			'twitter'         : '关注我们的推特',
			'facebook'        : '加入我们的脸书',
			'team'            : '团队',
			'chiefdev'        : '首席开发',
			'developer'       : '开发',
			'contributor'     : '贡献',
			'maintainer'      : '维护',
			'translator'      : '翻译',
			'icons'           : '图标',
			'dontforget'      : '别忘了带上你擦汗的毛巾',
			'shortcutsof'     : '快捷键已禁用',
			'dropFiles'       : '把文件拖到这里',
			'or'              : '或者',
			'selectForUpload' : '选择要上传的文件',
			'moveFiles'       : '移动文件',
			'copyFiles'       : '复制文件',
			'rmFromPlaces'    : '从位置中删除',
			'aspectRatio'     : '保持比例',
			'scale'           : '高宽比',
			'width'           : '宽',
			'height'          : '高',
			'resize'          : '重新调整大小',
			'crop'            : '裁切',
			'rotate'          : '旋转',
			'rotate-cw'       : '顺时针旋转90度',
			'rotate-ccw'      : '逆时针旋转90度',
			'degree'          : '度',
			'netMountDialogTitle' : '装载网络目录', // added 18.04.2012
			'protocol'            : '协议', // added 18.04.2012
			'host'                : '主机', // added 18.04.2012
			'port'                : '端口', // added 18.04.2012
			'user'                : '用户', // added 18.04.2012
			'pass'                : '密码', // added 18.04.2012
			'confirmUnmount'      : '确实要卸载 $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': '从浏览器中拖放或粘贴文件', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : '拖放文件，粘贴网址或剪贴板图像', // from v2.1 added 07.04.2014
			'encoding'        : '编码', // from v2.1 added 19.12.2014
			'locale'          : '语言环境',   // from v2.1 added 19.12.2014
			'searchTarget'    : '目标: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : '按输入MIME类型搜索', // from v2.1 added 22.5.2015
			'owner'           : '所有者', // from v2.1 added 20.6.2015
			'group'           : '组', // from v2.1 added 20.6.2015
			'other'           : '其他', // from v2.1 added 20.6.2015
			'execute'         : '执行', // from v2.1 added 20.6.2015
			'perm'            : '许可', // from v2.1 added 20.6.2015
			'mode'            : '属性', // from v2.1 added 20.6.2015
			'emptyFolder'     : '文件夹是空的', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : '文件夹是空的\\A 拖放可追加项目', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : '文件夹是空的\\A 长按可添加项目', // from v2.1.6 added 30.12.2015
			'quality'         : '品质', // from v2.1.6 added 5.1.2016
			'autoSync'        : '自动同步',  // from v2.1.6 added 10.1.2016
			'moveUp'          : '向上移动',  // from v2.1.6 added 18.1.2016
			'getLink'         : '获取URL链接', // from v2.1.7 added 9.2.2016
			'selectedItems'   : '已选择项目 ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : '目录ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : '允许离线操作', // from v2.1.10 added 3.25.2016
			'reAuth'          : '重新验证', // from v2.1.10 added 3.25.2016
			'nowLoading'      : '正在加载...', // from v2.1.12 added 4.26.2016
			'openMulti'       : '打开多个文件', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': '您正在尝试打开$1文件.您确定要在浏览器中打开吗?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : '搜索目标中没有匹配结果', // from v2.1.12 added 5.16.2016
			'editingFile'     : '正在编辑文件.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : '已选择 $1 个项目.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : '剪贴板里有 $1 个项目.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : '增量搜索仅来自当前视图.', // from v2.1.13 added 6.30.2016
			'reinstate'       : '恢复', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 完成', // from v2.1.15 added 21.8.2016
			'contextmenu'     : '上下文菜单', // from v2.1.15 added 9.9.2016
			'pageTurning'     : '翻页', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : '根目录', // from v2.1.16 added 16.9.2016
			'reset'           : '重置', // from v2.1.16 added 1.10.2016
			'bgcolor'         : '背景色', // from v2.1.16 added 1.10.2016
			'colorPicker'     : '颜色选择器', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px 网格', // from v2.1.16 added 4.10.2016
			'enabled'         : '活性', // from v2.1.16 added 4.10.2016
			'disabled'        : '非活性', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : '当前视图下没有匹配结果', // from v2.1.16 added 5.10.2016
			'textLabel'       : '文本标签', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '剩余 $1 分钟', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : '使用所选编码重新打开', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : '使用所选编码保存', // from v2.1.19 added 2.12.2016
			'selectFolder'    : '选择目录', // from v2.1.20 added 13.12.2016

			/********************************** mimetypes **********************************/
			'kindUnknown'     : '未知',
			'kindRoot'        : '根目录', // from v2.1.16 added 16.10.2016
			'kindFolder'      : '文件夹',
			'kindAlias'       : '别名',
			'kindAliasBroken' : '错误的别名',
			// applications
			'kindApp'         : '程序',
			'kindPostscript'  : 'Postscript 文档',
			'kindMsOffice'    : 'Microsoft Office 文档',
			'kindMsWord'      : 'Microsoft Word 文档',
			'kindMsExcel'     : 'Microsoft Excel 文档',
			'kindMsPP'        : 'Microsoft Powerpoint 演示',
			'kindOO'          : 'Open Office 文档',
			'kindAppFlash'    : 'Flash 程序',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent 文件',
			'kind7z'          : '7z 压缩包',
			'kindTAR'         : 'TAR 压缩包',
			'kindGZIP'        : 'GZIP 压缩包',
			'kindBZIP'        : 'BZIP 压缩包',
			'kindXZ'          : 'XZ 压缩包',
			'kindZIP'         : 'ZIP 压缩包',
			'kindRAR'         : 'RAR 压缩包',
			'kindJAR'         : 'Java JAR 文件',
			'kindTTF'         : 'True Type 字体',
			'kindOTF'         : 'Open Type 字体',
			'kindRPM'         : 'RPM 包',
			// texts
			'kindText'        : '文本文件',
			'kindTextPlain'   : '纯文本',
			'kindPHP'         : 'PHP 源代码',
			'kindCSS'         : '层叠样式表(CSS)',
			'kindHTML'        : 'HTML 文档',
			'kindJS'          : 'Javascript 源代码',
			'kindRTF'         : '富文本格式(RTF)',
			'kindC'           : 'C 源代码',
			'kindCHeader'     : 'C 头文件',
			'kindCPP'         : 'C++ 源代码',
			'kindCPPHeader'   : 'C++ 头文件',
			'kindShell'       : 'Unix 外壳脚本',
			'kindPython'      : 'Python 源代码',
			'kindJava'        : 'Java 源代码',
			'kindRuby'        : 'Ruby 源代码',
			'kindPerl'        : 'Perl 源代码',
			'kindSQL'         : 'SQL 脚本',
			'kindXML'         : 'XML 文档',
			'kindAWK'         : 'AWK 源代码',
			'kindCSV'         : '逗号分隔值文件(CSV)',
			'kindDOCBOOK'     : 'Docbook XML 文档',
			'kindMarkdown'    : 'Markdown 文本', // added 20.7.2015
			// images
			'kindImage'       : '图片',
			'kindBMP'         : 'BMP 图片',
			'kindJPEG'        : 'JPEG 图片',
			'kindGIF'         : 'GIF 图片',
			'kindPNG'         : 'PNG 图片',
			'kindTIFF'        : 'TIFF 图片',
			'kindTGA'         : 'TGA 图片',
			'kindPSD'         : 'Adobe Photoshop 图片',
			'kindXBITMAP'     : 'X bitmap 图片',
			'kindPXM'         : 'Pixelmator 图片',
			// media
			'kindAudio'       : '音频',
			'kindAudioMPEG'   : 'MPEG 音频',
			'kindAudioMPEG4'  : 'MPEG-4 音频',
			'kindAudioMIDI'   : 'MIDI 音频',
			'kindAudioOGG'    : 'Ogg Vorbis 音频',
			'kindAudioWAV'    : 'WAV 音频',
			'AudioPlaylist'   : 'MP3 播放列表',
			'kindVideo'       : '视频',
			'kindVideoDV'     : 'DV 视频',
			'kindVideoMPEG'   : 'MPEG 视频',
			'kindVideoMPEG4'  : 'MPEG-4 视频',
			'kindVideoAVI'    : 'AVI 视频',
			'kindVideoMOV'    : 'Quick Time 视频',
			'kindVideoWM'     : 'Windows Media 视频',
			'kindVideoFlash'  : 'Flash 视频',
			'kindVideoMKV'    : 'Matroska 视频',
			'kindVideoOGG'    : 'Ogg 视频'
		}
	};
}));
