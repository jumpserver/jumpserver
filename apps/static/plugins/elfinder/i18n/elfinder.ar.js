/**
 * العربية translation
 * @author Tawfek Daghistani <tawfekov@gmail.com>
 * @author Atef Ben Ali <atef.bettaib@gmail.com>
 * @version 2017-08-28
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
	elFinder.prototype.i18.ar = {
		translator : 'Tawfek Daghistani &lt;tawfekov@gmail.com&gt;, Atef Ben Ali &lt;atef.bettaib@gmail.com&gt;',
		language   : 'العربية',
		direction  : 'rtl',
		dateFormat : 'M d, Y h:i A', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 h:i A', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'خطأ',
			'errUnknown'           : 'خطأ غير معروف .',
			'errUnknownCmd'        : 'أمر غير معروف .',
			'errJqui'              : 'إعدادات jQuery UI غير كاملة الرجاء التأكد من وجود كل من selectable, draggable and droppable',
			'errNode'              : '. موجود DOM إلى عنصر  elFinder تحتاج  ',
			'errURL'               : 'إعدادات خاطئة , عليك وضع الرابط ضمن الإعدادات',
			'errAccess'            : 'وصول مرفوض .',
			'errConnect'           : 'غير قادر على الاتصال بالخادم الخلفي  (backend)',
			'errAbort'             : 'تم فصل الإتصال',
			'errTimeout'           : 'مهلة الإتصال قد انتهت.',
			'errNotFound'          : 'الخادوم الخلفي غير موجود .',
			'errResponse'          : 'رد غير مقبول من الخادوم الخلفي',
			'errConf'              : 'خطأ في الإعدادات الخاصة بالخادوم الخلفي ',
			'errJSON'              : 'الميزة PHP JSON module غير موجودة ',
			'errNoVolumes'         : 'لا يمكن القراءة من الوسائط الموجودة ',
			'errCmdParams'         : 'البيانات المرسلة للأمر غير مقبولة "$1".',
			'errDataNotJSON'       : 'المعلومات المرسلة ليست من نوع JSON ',
			'errDataEmpty'         : 'لا يوجد معلومات مرسلة',
			'errCmdReq'            : 'الخادوم الخلفي يطلب وجود اسم الأمر ',
			'errOpen'              : 'غير قادر على فتح  "$1".',
			'errNotFolder'         : 'العنصر المختار ليس مجلد',
			'errNotFile'           : 'العنصر المختار ليس ملف',
			'errRead'              : 'غير قادر على القراءة "$1".',
			'errWrite'             : 'غير قادر على الكتابة "$1".',
			'errPerm'              : 'وصول مرفوض ',
			'errLocked'            : ' محمي ولا يمكن التعديل أو النقل أو إعادة التسمية"$1"',
			'errExists'            : ' موجود مسبقاً "$1"',
			'errInvName'           : 'الاسم مرفوض',
			'errInvDirname'        : 'اسم مجلد غير صالح',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'المجلد غير موجود',
			'errFileNotFound'      : 'الملف غير موجود',
			'errTrgFolderNotFound' : 'الملف الهدف  "$1" غير موجود ',
			'errPopup'             : 'يمنع المتصفح من إنشاء نافذة منبثقة، الرجاء تعديل الخيارات الخاصة من إعدادات المتصفح',
			'errMkdir'             : ' غير قادر على إنشاء مجلد جديد "$1".',
			'errMkfile'            : ' غير قادر على إنشاء ملف جديد"$1".',
			'errRename'            : 'غير قادر على إعادة تسمية الـ  "$1".',
			'errCopyFrom'          : 'نسخ الملفات من الوسط المحدد "$1" غير مسموح.',
			'errCopyTo'            : 'نسخ الملفات إلى الوسط المحدد "$1" غير مسموح .',
			'errMkOutLink'         : 'لا يمكن إنشاء رابط خارج مساحة الملف الجذر.', // from v2.1 added 03.10.2015
			'errUpload'            : 'خطأ أثناء عملية الرفع.',  // old name - errUploadCommon
			'errUploadFile'        : 'غير قادر على رفع "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'لم يتم رفع أي ملف .',
			'errUploadTotalSize'   : 'حجم البيانات أكبر من الحجم المسموح به.', // old name - errMaxSize
			'errUploadFileSize'    : 'حجم الملف أكبر من الحجم المسموح به.', //  old name - errFileMaxSize
			'errUploadMime'        : ' نوع ملف غير مسموح به.',
			'errUploadTransfer'    : '"$1" خطأ أثناء عملية النقل.',
			'errUploadTemp'        : 'لا يمكن إنشاء ملف وقتي للرفع.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'الكائن "$1" موجود في هذا المكان ولا يمكن استبداله بكائن من نوع آخر.', // new
			'errReplace'           : 'لا يمكن استبدال "$1".',
			'errSave'              : 'غير قادر على الحفظ في "$1".',
			'errCopy'              : 'غير قادر على النسخ إلى "$1".',
			'errMove'              : 'غير قادر على النقل إلى "$1".',
			'errCopyInItself'      : 'غير قادر على نسخ الملف "$1" ضمن الملف نفسه.',
			'errRm'                : 'غير قادر على الحذف "$1".',
			'errTrash'             : 'لا يمكن النقل إلى سلة المهملات', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'لا يمكن فسخ الملف(ـات) المصدري(ـة).',
			'errExtract'           : 'غير قادر على استخراج الملفات من "$1".',
			'errArchive'           : 'غير قادر على إنشاء ملف مضغوط.',
			'errArcType'           : 'نوع الملف المضغوط غير مدعومة.',
			'errNoArchive'         : 'هذا الملف ليس ملف مضغوط أو ذو صيغة غير مدعومة.',
			'errCmdNoSupport'      : 'الخادوم الخلفي لا يدعم هذا الأمر ',
			'errReplByChild'       : 'لا يمكن استبدال الملف "$1" بعنصر محتوِ فيه.',
			'errArcSymlinks'       : 'For security reason denied to unpack archives contains symlinks.', // edited 24.06.2012
			'errArcMaxSize'        : 'الملفات المضغوطة تجاوزت السعة المسموح بها.',
			'errResize'            : 'Unable to resize "$1".',
			'errResizeDegree'      : 'Invalid rotate degree.',  // added 7.3.2013
			'errResizeRotate'      : 'Unable to rotate image.',  // added 7.3.2013
			'errResizeSize'        : 'Invalid image size.',  // added 7.3.2013
			'errResizeNoChange'    : 'Image size not changed.',  // added 7.3.2013
			'errUsupportType'      : 'نوع ملف غير مدعوم.',
			'errNotUTF8Content'    : 'File "$1" is not in UTF-8 and cannot be edited.',  // added 9.11.2011
			'errNetMount'          : 'Unable to mount "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Unsupported protocol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Mount failed.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Host required.', // added 18.04.2012
			'errSessionExpires'    : 'Your session has expired due to inactivity.',
			'errCreatingTempDir'   : 'Unable to create temporary directory: "$1"',
			'errFtpDownloadFile'   : 'Unable to download file from FTP: "$1"',
			'errFtpUploadFile'     : 'Unable to upload file to FTP: "$1"',
			'errFtpMkdir'          : 'Unable to create remote directory on FTP: "$1"',
			'errArchiveExec'       : 'Error while archiving files: "$1"',
			'errExtractExec'       : 'Error while extracting files: "$1"',
			'errNetUnMount'        : 'Unable to unmount.', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Not convertible to UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Try the modern browser, If you\'d like to upload the folder.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Timed out while searching "$1". Search result is partial.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Re-authorization is required.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Max number of selectable items is $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Unable to restore from the trash. Can\'t identify the restore destination.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Editor not found to this file type.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Error occurred on the server side.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Unable to empty folder "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'أنشئ مجلد مضغوط',
			'cmdback'      : 'الخلف',
			'cmdcopy'      : 'نسخ',
			'cmdcut'       : 'قص',
			'cmddownload'  : 'تحميل',
			'cmdduplicate' : 'تكرار',
			'cmdedit'      : 'تعديل الملف',
			'cmdextract'   : 'استخراج الملفات',
			'cmdforward'   : 'الأمام',
			'cmdgetfile'   : 'اختيار الملفات',
			'cmdhelp'      : 'عن هذا المشروع',
			'cmdhome'      : 'المجلد الرئيس',
			'cmdinfo'      : 'معلومات ',
			'cmdmkdir'     : 'مجلد جديد',
			'cmdmkdirin'   : 'داخل ملف جديد', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'ملف جديد',
			'cmdopen'      : 'فتح',
			'cmdpaste'     : 'لصق',
			'cmdquicklook' : 'معاينة',
			'cmdreload'    : 'إعادة تحميل',
			'cmdrename'    : 'إعادة تسمية',
			'cmdrm'        : 'حذف',
			'cmdtrash'     : 'داخل سلة المهملات', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Restore', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'بحث عن ملفات',
			'cmdup'        : 'تغيير المسار إلى مستوى أعلى',
			'cmdupload'    : 'رفع ملفات',
			'cmdview'      : 'عرض',
			'cmdresize'    : 'Resize & Rotate',
			'cmdsort'      : 'فرز',
			'cmdnetmount'  : 'Mount network volume', // added 18.04.2012
			'cmdnetunmount': 'Unmount', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'To Places', // added 28.12.2014
			'cmdchmod'     : 'Change mode', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'فتح ملف', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Reset column width', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'ملء الشاشة', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Move', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'تفريغ الملف', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'تراجع', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'إعاجة', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Preferences', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Select all', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Select none', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Invert selection', // from v2.1.28 added 15.08.2017

			/*********************************** buttons ***********************************/
			'btnClose'  : 'إغلاق',
			'btnSave'   : 'حفظ',
			'btnRm'     : 'إزالة',
			'btnApply'  : 'تطبيق',
			'btnCancel' : 'إلغاء',
			'btnNo'     : 'لا',
			'btnYes'    : 'نعم',
			'btnMount'  : 'Mount',  // added 18.04.2012
			'btnApprove': 'Goto $1 & approve', // from v2.1 added 26.04.2012
			'btnUnmount': 'Unmount', // from v2.1 added 30.04.2012
			'btnConv'   : 'Convert', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Here',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'All',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName':'Filename',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Save & Close', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015
			'btnRename'    : 'إعادة تسمية',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'إعادة تسمية (الجميع)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Prev ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Next ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'حفظ إلى', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'فتح مجلد',
			'ntffile'     : 'فتح ملف',
			'ntfreload'   : 'إعادة عرض محتويات المجلد ',
			'ntfmkdir'    : 'ينشئ المجلدات',
			'ntfmkfile'   : 'ينشئ الملفات',
			'ntfrm'       : 'حذف الملفات',
			'ntfcopy'     : 'نسخ الملفات',
			'ntfmove'     : 'نقل الملفات',
			'ntfprepare'  : 'تحضير لنسخ الملفات',
			'ntfrename'   : 'إعادة تسمية الملفات',
			'ntfupload'   : 'رفع الملفات',
			'ntfdownload' : 'تحميل الملفات',
			'ntfsave'     : 'حفظ الملفات',
			'ntfarchive'  : 'ينشئ ملف مضغوط',
			'ntfextract'  : 'استخراج ملفات من الملف المضغوط ',
			'ntfsearch'   : 'يبحث عن ملفات',
			'ntfresize'   : 'Resizing images',
			'ntfsmth'     : 'يفعل شيئا',
			'ntfloadimg'  : 'تحميل الصورة',
			'ntfnetmount' : 'Mounting network volume', // added 18.04.2012
			'ntfnetunmount': 'Unmounting network volume', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Acquiring image dimension', // added 20.05.2013
			'ntfreaddir'  : 'قراءة معلومات الملف', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Getting URL of link', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Changing file mode', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verifying upload file name', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Creating a file for download', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Getting path infomation', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Processing the uploaded file', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Doing throw in the trash', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Doing restore from tha trash', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Checking destination folder', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Undoing previous operation', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Redoing previous undone', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Trash', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'غير معلوم',
			'Today'       : 'اليوم',
			'Yesterday'   : 'البارحة',
			'msJan'       : 'كانون الثاني',
			'msFeb'       : 'شباط',
			'msMar'       : 'آذار',
			'msApr'       : 'نيسان',
			'msMay'       : 'أيار',
			'msJun'       : 'حزيران',
			'msJul'       : 'تموز',
			'msAug'       : 'آب',
			'msSep'       : 'أيلول',
			'msOct'       : 'تشرين الأول',
			'msNov'       : 'تشرين الثاني',
			'msDec'       : 'كانون الأول ',
			'January'     : 'January',
			'February'    : 'February',
			'March'       : 'March',
			'April'       : 'April',
			'May'         : 'May',
			'June'        : 'June',
			'July'        : 'July',
			'August'      : 'August',
			'September'   : 'September',
			'October'     : 'October',
			'November'    : 'November',
			'December'    : 'December',
			'Sunday'      : 'الأحد',
			'Monday'      : 'الاثنين',
			'Tuesday'     : 'الثلاثاء',
			'Wednesday'   : 'الإربعاء',
			'Thursday'    : 'الخميس',
			'Friday'      : 'الجمعة',
			'Saturday'    : 'السبت',
			'Sun'         : 'الأحد',
			'Mon'         : 'الاثنين',
			'Tue'         : 'الثلاثاء',
			'Wed'         : 'الإربعاء',
			'Thu'         : 'الخميس',
			'Fri'         : 'الجمعة',
			'Sat'         : 'السبت',

			/******************************** sort variants ********************************/
			'sortname'          : 'بالاسم',
			'sortkind'          : 'بالنوع',
			'sortsize'          : 'بالحجم',
			'sortdate'          : 'بالتاريخ',
			'sortFoldersFirst'  : 'الملفات أولا',
			'sortperm'          : 'بالصلاحيات', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'by mode',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'by owner',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'بالمجموعة',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Also Treeview',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'ملف_جديد.txt', // added 10.11.2015
			'untitled folder'   : 'مجلد_جديد',   // added 10.11.2015
			'Archive'           : 'ملف_مضغوط',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'يرجى التأكيد',
			'confirmRm'       : 'هل أنت متأكد من أنك تريد الحذف؟ لا يمكن التراجع عن هذه العملية ',
			'confirmRepl'     : 'استبدال الملف القديم بملف جديد؟',
			'confirmRest'     : 'استبدال العنصر بالعنصر من سلة المهملات؟', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Not in UTF-8<br/>Convert to UTF-8?<br/>Contents become UTF-8 by saving after conversion.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Character encoding of this file couldn\'t be detected. It need to temporarily convert to UTF-8 for editting.<br/>Please select character encoding of this file.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'It has been modified.<br/>Losing work if you do not save changes.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Are you sure you want to move items to trash bin?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'تطبيق على الكل',
			'name'            : 'الاسم',
			'size'            : 'الحجم',
			'perms'           : 'الصلاحيات',
			'modify'          : 'آخر تعديل',
			'kind'            : 'نوع الملف',
			'read'            : 'قراءة',
			'write'           : 'كتابة',
			'noaccess'        : 'وصول ممنوع',
			'and'             : 'و',
			'unknown'         : 'غير معروف',
			'selectall'       : 'تحديد كل الملفات',
			'selectfiles'     : 'تحديد ملفات',
			'selectffile'     : 'تحديد الملف الأول',
			'selectlfile'     : 'تحديد الملف الأخير',
			'viewlist'        : 'عرض قائمة',
			'viewicons'       : 'عرض أيْقونات',
			'places'          : 'المواقع',
			'calc'            : 'حساب',
			'path'            : 'مسار',
			'aliasfor'        : 'Alias for',
			'locked'          : 'مقفول',
			'dim'             : 'الأبعاد',
			'files'           : 'ملفات',
			'folders'         : 'مجلدات',
			'items'           : 'عناصر',
			'yes'             : 'نعم',
			'no'              : 'لا',
			'link'            : 'رابط',
			'searcresult'     : 'نتائج البحث',
			'selected'        : 'العناصر المحددة',
			'about'           : 'عن البرنامج',
			'shortcuts'       : 'الاختصارات',
			'help'            : 'مساعدة',
			'webfm'           : 'مدير ملفات الويب',
			'ver'             : 'رقم الإصدار',
			'protocolver'     : 'إصدار البرتوكول',
			'homepage'        : 'الصفحة الرئيسة',
			'docs'            : 'التوثيق',
			'github'          : 'شاركنا بتطوير المشروع على Github',
			'twitter'         : 'تابعنا على تويتر',
			'facebook'        : 'انضم إلينا على الفيس بوك',
			'team'            : 'الفريق',
			'chiefdev'        : 'رئيس المبرمجين',
			'developer'       : 'مبرمج',
			'contributor'     : 'مساعم',
			'maintainer'      : 'مشارك',
			'translator'      : 'مترجم',
			'icons'           : 'أيقونات',
			'dontforget'      : 'and don\'t forget to take your towel',
			'shortcutsof'     : 'الاختصارات غير مفعلة',
			'dropFiles'       : 'لصق الملفات هنا',
			'or'              : 'أو',
			'selectForUpload' : 'اختر الملفات التي تريد رفعها',
			'moveFiles'       : 'قص الملفات',
			'copyFiles'       : 'نسخ الملفات',
			'restoreFiles'    : 'Restore items', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Remove from places',
			'aspectRatio'     : 'Aspect ratio',
			'scale'           : 'Scale',
			'width'           : 'عرض',
			'height'          : 'طول',
			'resize'          : 'Resize',
			'crop'            : 'Crop',
			'rotate'          : 'Rotate',
			'rotate-cw'       : 'Rotate 90 degrees CW',
			'rotate-ccw'      : 'Rotate 90 degrees CCW',
			'degree'          : '°',
			'netMountDialogTitle' : 'Mount network volume', // added 18.04.2012
			'protocol'            : 'Protocol', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'مستخدم', // added 18.04.2012
			'pass'                : 'كلمة العبور', // added 18.04.2012
			'confirmUnmount'      : 'Are you unmount $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Drop or Paste files from browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Drop files, Paste URLs or images(clipboard) here', // from v2.1 added 07.04.2014
			'encoding'        : 'Encoding', // from v2.1 added 19.12.2014
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Target: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Search by input MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Owner', // from v2.1 added 20.6.2015
			'group'           : 'Group', // from v2.1 added 20.6.2015
			'other'           : 'Other', // from v2.1 added 20.6.2015
			'execute'         : 'Execute', // from v2.1 added 20.6.2015
			'perm'            : 'Permission', // from v2.1 added 20.6.2015
			'mode'            : 'Mode', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Folder is empty', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Folder is empty\\A Drop to add items', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Folder is empty\\A Long tap to add items', // from v2.1.6 added 30.12.2015
			'quality'         : 'Quality', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Auto sync',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Move up',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Get URL link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Selected items ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Folder ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Allow offline access', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'To re-authenticate', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Now loading...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Open multiple files', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'You are trying to open the $1 files. Are you sure you want to open in browser?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Search results is empty in search target.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'It is editing a file.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'You have selected $1 items.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'You have $1 items in the clipboard.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Incremental search is only from the current view.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Reinstate', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 complete', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Context menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Page turning', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Volume roots', // from v2.1.16 added 16.9.2016
			'reset'           : 'Reset', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Background color', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Color picker', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px Grid', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Enabled', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Disabled', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Search results is empty in current view.\\APress [Enter] to expand search target.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'First letter search results is empty in current view.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Text label', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 mins left', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Reopen with selected encoding', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Save with the selected encoding', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Select folder', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'First letter search', // from v2.1.23 added 24.3.2017
			'presets'         : 'Presets', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'It\'s too many items so it can\'t into trash.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'TextArea', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Empty the folder "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'There are no items in a folder "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preference', // from v2.1.26 added 28.6.2017
			'language'        : 'Language setting', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Initialize the settings saved in this browser', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Toolbar setting', // from v2.1.27 added 2.8.2017

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'غير معروف',
			'kindRoot'        : 'Volume Root', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'مجلد',
			'kindAlias'       : 'اختصار',
			'kindAliasBroken' : 'اختصار غير صالح',
			// applications
			'kindApp'         : 'برنامج',
			'kindPostscript'  : 'Postscript ملف',
			'kindMsOffice'    : 'Microsoft Office ملف',
			'kindMsWord'      : 'Microsoft Word ملف',
			'kindMsExcel'     : 'Microsoft Excel ملف',
			'kindMsPP'        : 'Microsoft Powerpoint عرض تقديمي ',
			'kindOO'          : 'Open Office ملف',
			'kindAppFlash'    : 'تطبيق فلاش',
			'kindPDF'         : 'ملف (PDF)',
			'kindTorrent'     : 'Bittorrent ملف',
			'kind7z'          : '7z ملف',
			'kindTAR'         : 'TAR ملف',
			'kindGZIP'        : 'GZIP ملف',
			'kindBZIP'        : 'BZIP ملف',
			'kindXZ'          : 'XZ ملف',
			'kindZIP'         : 'ZIP ملف',
			'kindRAR'         : 'RAR ملف',
			'kindJAR'         : 'Java JAR ملف',
			'kindTTF'         : 'True Type خط ',
			'kindOTF'         : 'Open Type خط ',
			'kindRPM'         : 'RPM ملف تنصيب',
			// texts
			'kindText'        : 'Text ملف',
			'kindTextPlain'   : 'مستند نصي',
			'kindPHP'         : 'PHP ملف نصي برمجي لـ',
			'kindCSS'         : 'Cascading style sheet',
			'kindHTML'        : 'HTML ملف',
			'kindJS'          : 'Javascript ملف نصي برمجي لـ',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C ملف نصي برمجي لـ',
			'kindCHeader'     : 'C header ملف نصي برمجي لـ',
			'kindCPP'         : 'C++ ملف نصي برمجي لـ',
			'kindCPPHeader'   : 'C++ header ملف نصي برمجي لـ',
			'kindShell'       : 'Unix shell script',
			'kindPython'      : 'Python ملف نصي برمجي لـ',
			'kindJava'        : 'Java ملف نصي برمجي لـ',
			'kindRuby'        : 'Ruby ملف نصي برمجي لـ',
			'kindPerl'        : 'Perl script',
			'kindSQL'         : 'SQL ملف نصي برمجي لـ',
			'kindXML'         : 'XML ملف',
			'kindAWK'         : 'AWK ملف نصي برمجي لـ',
			'kindCSV'         : 'ملف CSV',
			'kindDOCBOOK'     : 'Docbook XML ملف',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'صورة',
			'kindBMP'         : 'BMP صورة',
			'kindJPEG'        : 'JPEG صورة',
			'kindGIF'         : 'GIF صورة',
			'kindPNG'         : 'PNG صورة',
			'kindTIFF'        : 'TIFF صورة',
			'kindTGA'         : 'TGA صورة',
			'kindPSD'         : 'Adobe Photoshop صورة',
			'kindXBITMAP'     : 'X bitmap صورة',
			'kindPXM'         : 'Pixelmator صورة',
			// media
			'kindAudio'       : 'ملف صوتي',
			'kindAudioMPEG'   : 'MPEG ملف صوتي',
			'kindAudioMPEG4'  : 'MPEG-4 ملف صوتي',
			'kindAudioMIDI'   : 'MIDI ملف صوتي',
			'kindAudioOGG'    : 'Ogg Vorbis ملف صوتي',
			'kindAudioWAV'    : 'WAV ملف صوتي',
			'AudioPlaylist'   : 'MP3 قائمة تشغيل',
			'kindVideo'       : 'ملف فيديو',
			'kindVideoDV'     : 'DV ملف فيديو',
			'kindVideoMPEG'   : 'MPEG ملف فيديو',
			'kindVideoMPEG4'  : 'MPEG-4 ملف فيديو',
			'kindVideoAVI'    : 'AVI ملف فيديو',
			'kindVideoMOV'    : 'Quick Time ملف فيديو',
			'kindVideoWM'     : 'Windows Media ملف فيديو',
			'kindVideoFlash'  : 'Flash ملف فيديو',
			'kindVideoMKV'    : 'Matroska ملف فيديو',
			'kindVideoOGG'    : 'Ogg ملف فيديو'
		}
	};
}));
