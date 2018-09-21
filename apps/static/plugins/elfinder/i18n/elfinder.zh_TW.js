/**
 * Traditional Chinese translation
 * @author Yuwei Chuang <ywchuang.tw@gmail.com>
 * @author Danny Lin <danny0838@gmail.com>
 * @author TCC <john987john987@gmail.com>
 * @version 2017-09-28
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
	elFinder.prototype.i18.zh_TW = {
		translator : 'Yuwei Chuang &lt;ywchuang.tw@gmail.com&gt;, Danny Lin &lt;danny0838@gmail.com&gt;, TCC &lt;john987john987@gmail.com&gt;',
		language   : '正體中文',
		direction  : 'ltr',
		dateFormat : 'Y/m/d H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : '錯誤',
			'errUnknown'           : '未知的錯誤.',
			'errUnknownCmd'        : '未知的指令.',
			'errJqui'              : '無效的 jQuery UI 設定. 必須包含 Selectable, draggable 以及 droppable 元件.',
			'errNode'              : 'elFinder 需要能建立 DOM 元素.',
			'errURL'               : '無效的 elFinder 設定! 尚未設定 URL 選項.',
			'errAccess'            : '拒絕存取.',
			'errConnect'           : '無法連線至後端.',
			'errAbort'             : '連線中斷.',
			'errTimeout'           : '連線逾時.',
			'errNotFound'          : '後端不存在.',
			'errResponse'          : '無效的後端回復.',
			'errConf'              : '無效的後端設定.',
			'errJSON'              : '未安裝 PHP JSON 模組.',
			'errNoVolumes'         : '無可讀取的 volumes.',
			'errCmdParams'         : '無效的參數, 指令: "$1".',
			'errDataNotJSON'       : '資料不是 JSON 格式.',
			'errDataEmpty'         : '沒有資料.',
			'errCmdReq'            : '後端請求需要命令名稱.',
			'errOpen'              : '無法開啟 "$1".',
			'errNotFolder'         : '非資料夾.',
			'errNotFile'           : '非檔案.',
			'errRead'              : '無法讀取 "$1".',
			'errWrite'             : '無法寫入 "$1".',
			'errPerm'              : '無權限.',
			'errLocked'            : '"$1" 被鎖定,不能重新命名, 移動或删除.',
			'errExists'            : '檔案 "$1" 已經存在了.',
			'errInvName'           : '無效的檔案名稱.',
			'errInvDirname'        : '無效的資料夾名稱',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : '未找到資料夾.',
			'errFileNotFound'      : '未找到檔案.',
			'errTrgFolderNotFound' : '未找到目標資料夾 "$1".',
			'errPopup'             : '連覽器攔截了彈跳視窗. 請在瀏覽器選項允許彈跳視窗.',
			'errMkdir'             : '不能建立資料夾 "$1".',
			'errMkfile'            : '不能建立檔案 "$1".',
			'errRename'            : '不能重新命名 "$1".',
			'errCopyFrom'          : '不允許從磁碟 "$1" 複製.',
			'errCopyTo'            : '不允複製到磁碟 "$1".',
			'errMkOutLink'         : '無法建立連結到磁碟根目錄外面.', // from v2.1 added 03.10.2015
			'errUpload'            : '上傳錯誤.',  // old name - errUploadCommon
			'errUploadFile'        : '無法上傳 "$1".', // old name - errUpload
			'errUploadNoFiles'     : '未找到要上傳的檔案.',
			'errUploadTotalSize'   : '資料超過了最大允許大小.', // old name - errMaxSize
			'errUploadFileSize'    : '檔案超過了最大允許大小.', //  old name - errFileMaxSize
			'errUploadMime'        : '不允許的檔案類型.',
			'errUploadTransfer'    : '"$1" 傳輸錯誤.',
			'errUploadTemp'        : '無法建立暫存檔以供上傳.', // from v2.1 added 26.09.2015
			'errNotReplace'        : '"$1" 已經存在此位置, 不能被其他的替换.', // new
			'errReplace'           : '無法替换 "$1".',
			'errSave'              : '無法保存 "$1".',
			'errCopy'              : '無法複製 "$1".',
			'errMove'              : '無法移動 "$1".',
			'errCopyInItself'      : '無法移動 "$1" 到原有位置.',
			'errRm'                : '無法删除 "$1".',
			'errTrash'             : '無法丟入垃圾桶', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : '無法删除來源檔案.',
			'errExtract'           : '無法從 "$1" 解壓縮檔案.',
			'errArchive'           : '無法建立壓縮膽.',
			'errArcType'           : '不支援的壓縮格式.',
			'errNoArchive'         : '檔案不是壓縮檔, 或者不支援該壓缩格式.',
			'errCmdNoSupport'      : '後端不支援該指令.',
			'errReplByChild'       : '資料夾 “$1” 不能被它所包含的檔案(資料夾)替换.',
			'errArcSymlinks'       : '由於安全考量，拒絕解壓縮符號連結或含有不允許檔名的檔案.', // edited 24.06.2012
			'errArcMaxSize'        : '待壓縮檔案的大小超出上限.',
			'errResize'            : '無法重新調整大小 "$1".',
			'errResizeDegree'      : '無效的旋轉角度.',  // added 7.3.2013
			'errResizeRotate'      : '無法旋轉圖片.',  // added 7.3.2013
			'errResizeSize'        : '無效的圖片大小.',  // added 7.3.2013
			'errResizeNoChange'    : '圖片大小未更改.',  // added 7.3.2013
			'errUsupportType'      : '不支援的檔案格式.',
			'errNotUTF8Content'    : '檔案 "$1" 不是 UTF-8 格式, 不能編輯.',  // added 9.11.2011
			'errNetMount'          : '無法掛載 "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : '不支援該通訊協議.',     // added 17.04.2012
			'errNetMountFailed'    : '掛載失敗.',         // added 17.04.2012
			'errNetMountHostReq'   : '需要指定主機位置.', // added 18.04.2012
			'errSessionExpires'    : '由於過久無活動, session 已過期.',
			'errCreatingTempDir'   : '無法建立暫時目錄: "$1"',
			'errFtpDownloadFile'   : '無法從 FTP 下載檔案: "$1"',
			'errFtpUploadFile'     : '無法上傳檔案到 FTP: "$1"',
			'errFtpMkdir'          : '無法在 FTP 建立遠端目錄: "$1"',
			'errArchiveExec'       : '壓縮檔案時發生錯誤: "$1"',
			'errExtractExec'       : '解壓縮檔案時發生錯誤: "$1"',
			'errNetUnMount'        : '無法卸載', // from v2.1 added 30.04.2012
			'errConvUTF8'          : '無法轉換為 UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : '如要上傳這個資料夾, 請嘗試 Google Chrome.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : '搜尋 "$1" 逾時. 只列出部分搜尋結果.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : '需要重新驗證權限.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : '最多可選擇 $1 個物件.', // from v2.1.17 added 17.10.2016
			'errRestore'           : '無法從垃圾桶恢復。 無法識別恢復目的地。', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : '編輯器找不到此文件類型。', // from v2.1.25 added 23.5.2017
			'errServerError'       : '服務器發生錯誤。', // from v2.1.25 added 16.6.2017
			'errEmpty'             : '無法清空"$1"文件夾', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : '建立壓縮檔',
			'cmdback'      : '後退',
			'cmdcopy'      : '複製',
			'cmdcut'       : '剪下',
			'cmddownload'  : '下載',
			'cmdduplicate' : '建立副本',
			'cmdedit'      : '編輯檔案',
			'cmdextract'   : '從壓縮檔解壓縮',
			'cmdforward'   : '前進',
			'cmdgetfile'   : '選擇檔案',
			'cmdhelp'      : '關於本軟體',
			'cmdhome'      : '首頁',
			'cmdinfo'      : '查看關於',
			'cmdmkdir'     : '建立資料夾',
			'cmdmkdirin'   : '移入新資料夾', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : '建立文檔',
			'cmdopen'      : '開啟',
			'cmdpaste'     : '貼上',
			'cmdquicklook' : '預覽',
			'cmdreload'    : '更新',
			'cmdrename'    : '重新命名',
			'cmdrm'        : '删除',
			'cmdtrash'     : '丟到垃圾桶', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : '恢復', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : '搜尋檔案',
			'cmdup'        : '移到上一層資料夾',
			'cmdupload'    : '上傳檔案',
			'cmdview'      : '檢視',
			'cmdresize'    : '調整大小及旋轉',
			'cmdsort'      : '排序',
			'cmdnetmount'  : '掛載網路磁碟', // added 18.04.2012
			'cmdnetunmount': '卸載', // from v2.1 added 30.04.2012
			'cmdplaces'    : '加到"位置"', // added 28.12.2014
			'cmdchmod'     : '更改權限', // from v2.1 added 20.6.2015
			'cmdopendir'   : '開啟資料夾', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : '重設欄寬', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': '全螢幕', // from v2.1.15 added 03.08.2016
			'cmdmove'      : '移動', // from v2.1.15 added 21.08.2016
			'cmdempty'     : '清空資料夾', // from v2.1.25 added 22.06.2017
			'cmdundo'      : '上一步', // from v2.1.27 added 31.07.2017
			'cmdredo'      : '下一步', // from v2.1.27 added 31.07.2017
			'cmdpreference': '優先權', // from v2.1.27 added 03.08.2017
			'cmdselectall' : '全選', // from v2.1.28 added 15.08.2017
			'cmdselectnone': '取消選取', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': '反向選取', // from v2.1.28 added 15.08.2017

			/*********************************** buttons ***********************************/
			'btnClose'  : '關閉',
			'btnSave'   : '儲存',
			'btnRm'     : '删除',
			'btnApply'  : '使用',
			'btnCancel' : '取消',
			'btnNo'     : '否',
			'btnYes'    : '是',
			'btnMount'  : '掛載',  // added 18.04.2012
			'btnApprove': '移到 $1 並批准', // from v2.1 added 26.04.2012
			'btnUnmount': '卸載', // from v2.1 added 30.04.2012
			'btnConv'   : '轉換', // from v2.1 added 08.04.2014
			'btnCwd'    : '這裡',      // from v2.1 added 22.5.2015
			'btnVolume' : '磁碟',    // from v2.1 added 22.5.2015
			'btnAll'    : '全部',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME 類型', // from v2.1 added 22.5.2015
			'btnFileName':'檔名',  // from v2.1 added 22.5.2015
			'btnSaveClose': '儲存並關閉', // from v2.1 added 12.6.2015
			'btnBackup' : '備份', // fromv2.1 added 28.11.2015
			'btnRename'    : '重新命名',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : '重新命名全部', // from v2.1.24 added 6.4.2017
			'btnPrevious' : '上一頁 ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : '下一頁 ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : '另存新檔', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : '開啟資料夾',
			'ntffile'     : '開啟檔案',
			'ntfreload'   : '更新資料夾内容',
			'ntfmkdir'    : '建立資料夾',
			'ntfmkfile'   : '建立檔案',
			'ntfrm'       : '删除檔案',
			'ntfcopy'     : '複製檔案',
			'ntfmove'     : '移動檔案',
			'ntfprepare'  : '準備複製檔案',
			'ntfrename'   : '重新命名檔案',
			'ntfupload'   : '上傳檔案',
			'ntfdownload' : '下載檔案',
			'ntfsave'     : '儲存檔案',
			'ntfarchive'  : '建立壓縮檔',
			'ntfextract'  : '從壓縮檔解壓縮',
			'ntfsearch'   : '搜尋檔案',
			'ntfresize'   : '正在更改圖片大小',
			'ntfsmth'     : '正在忙 >_<',
			'ntfloadimg'  : '正在讀取圖片',
			'ntfnetmount' : '正在掛載網路磁碟', // added 18.04.2012
			'ntfnetunmount': '正在卸載網路磁碟', // from v2.1 added 30.04.2012
			'ntfdim'      : '取得圖片大小', // added 20.05.2013
			'ntfreaddir'  : '正在讀取資料夾資訊', // from v2.1 added 01.07.2013
			'ntfurl'      : '正在取得連結 URL', // from v2.1 added 11.03.2014
			'ntfchmod'    : '更改檔案模式', // from v2.1 added 20.6.2015
			'ntfpreupload': '正在驗證上傳檔案名稱', // from v2.1 added 31.11.2015
			'ntfzipdl'    : '正在建立縮檔以供下載', // from v2.1.7 added 23.1.2016
			'ntfparents'  : '正在取得路徑資訊', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': '正在處理上傳的檔案', // from v2.1.17 added 2.11.2016
			'ntftrash'    : '正在丟到垃圾桶', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : '正從垃圾桶恢復', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : '正在檢查目標資料夾', // from v2.1.24 added 3.5.2017
			'ntfundo'     : '正在撤銷上一步動作', // from v2.1.27 added 31.07.2017
			'ntfredo'     : '正在重做上一步動作', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : '垃圾桶', //from v2.1.24 added 29.4.2017

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
			'sortname'          : '按名稱',
			'sortkind'          : '按類型',
			'sortsize'          : '按大小',
			'sortdate'          : '按日期',
			'sortFoldersFirst'  : '資料夾置前',
			'sortperm'          : '按權限', // from v2.1.13 added 13.06.2016
			'sortmode'          : '按模式',       // from v2.1.13 added 13.06.2016
			'sortowner'         : '按擁有者',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : '按群組',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : '也套用於樹狀圖',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : '新檔案.txt', // added 10.11.2015
			'untitled folder'   : '新資料夾',   // added 10.11.2015
			'Archive'           : '新壓縮檔',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : '請確認',
			'confirmRm'       : '確定要删除檔案嗎?<br/>此操作無法回復!',
			'confirmRepl'     : '用新檔案取代原檔案?',
			'confirmRest'     : '用垃圾桶中的項目替換現有項目？', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : '不是 UTF-8 檔案<br/>轉換為 UTF-8 嗎?<br/>轉換後儲存會把內容變成 UTF-8.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : '無法偵測此檔案的字元編碼, 須暫時轉換為 UTF-8 以供編輯.<br/>請選擇此檔案的字元編碼.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : '此檔案已修改.<br/>若未儲存將遺失目前的工作.', // from v2.1 added 15.7.2015
			'confirmTrash'    : '確定要將項目丟到垃圾桶嗎？', //from v2.1.24 added 29.4.2017
			'apllyAll'        : '全部套用',
			'name'            : '名稱',
			'size'            : '大小',
			'perms'           : '權限',
			'modify'          : '修改於',
			'kind'            : '類別',
			'read'            : '讀取',
			'write'           : '寫入',
			'noaccess'        : '無權限',
			'and'             : '和',
			'unknown'         : '未知',
			'selectall'       : '選擇所有檔案',
			'selectfiles'     : '選擇檔案',
			'selectffile'     : '選擇第一個檔案',
			'selectlfile'     : '選擇最後一個檔案',
			'viewlist'        : '列表檢視',
			'viewicons'       : '圖示檢視',
			'places'          : '位置',
			'calc'            : '計算',
			'path'            : '路徑',
			'aliasfor'        : '别名',
			'locked'          : '鎖定',
			'dim'             : '圖片大小',
			'files'           : '檔案',
			'folders'         : '資料夾',
			'items'           : '項目',
			'yes'             : '是',
			'no'              : '否',
			'link'            : '連結',
			'searcresult'     : '搜尋结果',
			'selected'        : '選取的項目',
			'about'           : '關於',
			'shortcuts'       : '快捷鍵',
			'help'            : '協助',
			'webfm'           : '網路檔案總管',
			'ver'             : '版本',
			'protocolver'     : '協定版本',
			'homepage'        : '首頁',
			'docs'            : '文件',
			'github'          : '在 Github 建立我們的分支',
			'twitter'         : '在 Twitter 追蹤我們',
			'facebook'        : '在 Facebook 加入我們',
			'team'            : '團隊',
			'chiefdev'        : '主要開發者',
			'developer'       : '開發者',
			'contributor'     : '貢獻者',
			'maintainer'      : '維護者',
			'translator'      : '翻譯者',
			'icons'           : '圖示',
			'dontforget'      : '别忘了帶上你擦汗的毛巾',
			'shortcutsof'     : '快捷鍵已停用',
			'dropFiles'       : '把檔案拖到此處',
			'or'              : '或',
			'selectForUpload' : '選擇要上傳的檔案',
			'moveFiles'       : '移動檔案',
			'copyFiles'       : '複製檔案',
			'restoreFiles'    : '恢復項目', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : '從"位置"中删除',
			'aspectRatio'     : '保持比例',
			'scale'           : '寬高比',
			'width'           : '寬',
			'height'          : '高',
			'resize'          : '重新調整大小',
			'crop'            : '裁切',
			'rotate'          : '旋轉',
			'rotate-cw'       : '順時針旋轉90度',
			'rotate-ccw'      : '逆時針旋轉90度',
			'degree'          : '度',
			'netMountDialogTitle' : '掛載網路磁碟', // added 18.04.2012
			'protocol'            : '通訊協定', // added 18.04.2012
			'host'                : '主機', // added 18.04.2012
			'port'                : '連接埠', // added 18.04.2012
			'user'                : '使用者', // added 18.04.2012
			'pass'                : '密碼', // added 18.04.2012
			'confirmUnmount'      : '確定要卸載 $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': '從瀏覽器拖放或貼上檔案', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : '拖放檔案或從剪貼簿貼上 URL 或圖片至此', // from v2.1 added 07.04.2014
			'encoding'        : '編碼', // from v2.1 added 19.12.2014
			'locale'          : '語系',   // from v2.1 added 19.12.2014
			'searchTarget'    : '目標: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : '根據輸入的 MIME 類型搜尋', // from v2.1 added 22.5.2015
			'owner'           : '擁有者', // from v2.1 added 20.6.2015
			'group'           : '群組', // from v2.1 added 20.6.2015
			'other'           : '其他', // from v2.1 added 20.6.2015
			'execute'         : '執行', // from v2.1 added 20.6.2015
			'perm'            : '權限', // from v2.1 added 20.6.2015
			'mode'            : '模式', // from v2.1 added 20.6.2015
			'emptyFolder'     : '資料夾是空的', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : '資料夾是空的\\A 拖曳以增加項目', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : '資料夾是空的\\A 長按以增加項目', // from v2.1.6 added 30.12.2015
			'quality'         : '品質', // from v2.1.6 added 5.1.2016
			'autoSync'        : '自動同步',  // from v2.1.6 added 10.1.2016
			'moveUp'          : '上移',  // from v2.1.6 added 18.1.2016
			'getLink'         : '取得 URL 連結', // from v2.1.7 added 9.2.2016
			'selectedItems'   : '選取的項目 ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : '資料夾 ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : '允許離線存取', // from v2.1.10 added 3.25.2016
			'reAuth'          : '重新驗證權限', // from v2.1.10 added 3.25.2016
			'nowLoading'      : '正在載入...', // from v2.1.12 added 4.26.2016
			'openMulti'       : '開啟多個檔案', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': '確定要在瀏覽器開啟 $1 個檔案嗎?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : '在搜尋目標中的搜尋結果是空的.', // from v2.1.12 added 5.16.2016
			'editingFile'     : '正在編輯檔案.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : '己選取 $1 個項目.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : '剪貼簿裡有 $1 個項目.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : '增量搜尋只來自目前視圖.', // from v2.1.13 added 6.30.2016
			'reinstate'       : '恢復原狀', // from v2.1.15 added 3.8.2016
			'complete'        : '$1完成', // from v2.1.15 added 21.8.2016
			'contextmenu'     : '情境選單', // from v2.1.15 added 9.9.2016
			'pageTurning'     : '正在換頁', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : '磁碟根目錄', // from v2.1.16 added 16.9.2016
			'reset'           : '重設', // from v2.1.16 added 1.10.2016
			'bgcolor'         : '背景頻色', // from v2.1.16 added 1.10.2016
			'colorPicker'     : '顏色選擇器', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px 網格', // from v2.1.16 added 4.10.2016
			'enabled'         : '啟用', // from v2.1.16 added 4.10.2016
			'disabled'        : '停用', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : '目前視圖的搜尋結果是空的.\\A按 [Enter] 擴大搜尋目標.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : '目前視圖中的第一個字母的搜索結果是空的。', // from v2.1.23 added 24.3.2017
			'textLabel'       : '文字標示', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '剩下 $1 分鐘', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : '以選擇的編碼重新開啟', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : '以選擇的編碼儲存', // from v2.1.19 added 2.12.2016
			'selectFolder'    : '選擇資料夾', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': '首字母搜索', // from v2.1.23 added 24.3.2017
			'presets'         : '預置', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : '有太多項目，所以不能丟入垃圾桶。', // from v2.1.25 added 9.6.2017
			'TextArea'        : '文字區域', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : '$1" 資料夾是空的', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : '"$1" 資料夾中沒有任何項目', // from v2.1.25 added 22.6.2017
			'preference'      : '偏好', // from v2.1.26 added 28.6.2017
			'language'        : '語言設置', // from v2.1.26 added 28.6.2017
			'clearBrowserData': '初始化保存在此瀏覽器中的設置', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : '工具欄設置', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... 剩下 $1 個字元',  // from v2.1.29 added 30.8.2017

			/********************************** mimetypes **********************************/
			'kindUnknown'     : '未知',
			'kindRoot'        : '磁碟根目錄', // from v2.1.16 added 16.10.2016
			'kindFolder'      : '資料夾',
			'kindSelects'     : '選擇', // from v2.1.29 added 29.8.2017
			'kindAlias'       : '别名',
			'kindAliasBroken' : '毀損的别名',
			// applications
			'kindApp'         : '應用程式',
			'kindPostscript'  : 'Postscript 文件',
			'kindMsOffice'    : 'Microsoft Office 文件',
			'kindMsWord'      : 'Microsoft Word 文件',
			'kindMsExcel'     : 'Microsoft Excel 文件',
			'kindMsPP'        : 'Microsoft Powerpoint 簡報',
			'kindOO'          : 'Open Office 文件',
			'kindAppFlash'    : 'Flash 應用程式',
			'kindPDF'         : '可攜式文件格式(PDF)',
			'kindTorrent'     : 'Bittorrent 檔案',
			'kind7z'          : '7z 壓縮檔',
			'kindTAR'         : 'TAR 壓縮檔',
			'kindGZIP'        : 'GZIP 壓縮檔',
			'kindBZIP'        : 'BZIP 壓縮檔',
			'kindXZ'          : 'XZ 壓縮檔',
			'kindZIP'         : 'ZIP 壓縮檔',
			'kindRAR'         : 'RAR 壓縮檔',
			'kindJAR'         : 'Java JAR 檔案',
			'kindTTF'         : 'True Type 字體',
			'kindOTF'         : 'Open Type 字體',
			'kindRPM'         : 'RPM 封裝檔',
			// texts
			'kindText'        : '文字檔案',
			'kindTextPlain'   : '純文字',
			'kindPHP'         : 'PHP 原始碼',
			'kindCSS'         : '階層樣式表(CSS)',
			'kindHTML'        : 'HTML 文件',
			'kindJS'          : 'Javascript 原始碼',
			'kindRTF'         : '富文本(RTF)',
			'kindC'           : 'C 原始碼',
			'kindCHeader'     : 'C 標頭原始碼',
			'kindCPP'         : 'C++ 原始碼',
			'kindCPPHeader'   : 'C++ 標頭原始碼',
			'kindShell'       : 'Unix Shell 脚本',
			'kindPython'      : 'Python 原始碼',
			'kindJava'        : 'Java 原始碼',
			'kindRuby'        : 'Ruby 原始碼',
			'kindPerl'        : 'Perl 原始碼',
			'kindSQL'         : 'SQL 原始碼',
			'kindXML'         : 'XML 文件',
			'kindAWK'         : 'AWK 原始碼',
			'kindCSV'         : '逗號分隔值(CSV)',
			'kindDOCBOOK'     : 'Docbook XML 文件',
			'kindMarkdown'    : 'Markdown 文本', // added 20.7.2015
			// images
			'kindImage'       : '圖片',
			'kindBMP'         : 'BMP 圖片',
			'kindJPEG'        : 'JPEG 圖片',
			'kindGIF'         : 'GIF 圖片',
			'kindPNG'         : 'PNG 圖片',
			'kindTIFF'        : 'TIFF 圖片',
			'kindTGA'         : 'TGA 圖片',
			'kindPSD'         : 'Adobe Photoshop 圖片',
			'kindXBITMAP'     : 'X bitmap 圖片',
			'kindPXM'         : 'Pixelmator 圖片',
			// media
			'kindAudio'       : '音訊',
			'kindAudioMPEG'   : 'MPEG 音訊',
			'kindAudioMPEG4'  : 'MPEG-4 音訊',
			'kindAudioMIDI'   : 'MIDI 音訊',
			'kindAudioOGG'    : 'Ogg Vorbis 音訊',
			'kindAudioWAV'    : 'WAV 音訊',
			'AudioPlaylist'   : 'MP3 播放清單',
			'kindVideo'       : '影片',
			'kindVideoDV'     : 'DV 影片',
			'kindVideoMPEG'   : 'MPEG 影片',
			'kindVideoMPEG4'  : 'MPEG-4 影片',
			'kindVideoAVI'    : 'AVI 影片',
			'kindVideoMOV'    : 'Quick Time 影片',
			'kindVideoWM'     : 'Windows Media 影片',
			'kindVideoFlash'  : 'Flash 影片',
			'kindVideoMKV'    : 'Matroska 影片',
			'kindVideoOGG'    : 'Ogg 影片'
		}
	};
}));

