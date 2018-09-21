/**
 * Bulgarian translation
 * @author Stamo Petkov <stamo.petkov@gmail.com>
 * @author Nikolay Petkov <office@cmstory.com>
 * @version 2018-07-28
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
	elFinder.prototype.i18.bg = {
		translator : 'Stamo Petkov &lt;stamo.petkov@gmail.com&gt;, Nikolay Petkov &lt;office@cmstory.com&gt;',
		language   : 'Bulgarian',
		direction  : 'ltr',
		dateFormat : 'd.m.Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'Ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Грешка',
			'errUnknown'           : 'Непозната грешка.',
			'errUnknownCmd'        : 'Непозната команда.',
			'errJqui'              : 'Грешна конфигурация на jQuery UI. Компонентите selectable, draggable и droppable трябва да са включени.',
			'errNode'              : 'elFinder изисква да бъде създаден DOM елемент.',
			'errURL'               : 'Грешка в настройките на elFinder! не е зададена стойност на URL.',
			'errAccess'            : 'Достъп отказан.',
			'errConnect'           : 'Няма връзка със сървъра.',
			'errAbort'             : 'Връзката е прекъсната.',
			'errTimeout'           : 'Просрочена връзка.',
			'errNotFound'          : 'Сървърът не е намерен.',
			'errResponse'          : 'Грешен отговор от сървъра.',
			'errConf'              : 'Грешни настройки на сървъра.',
			'errJSON'              : 'Не е инсталиран модул на PHP за JSON.',
			'errNoVolumes'         : 'Няма дялове достъпни за четене.',
			'errCmdParams'         : 'Грешни параметри на командата "$1".',
			'errDataNotJSON'       : 'Данните не са JSON.',
			'errDataEmpty'         : 'Липсват данни.',
			'errCmdReq'            : 'Запитването от сървъра изисква име на команда.',
			'errOpen'              : 'Неуспешно отваряне на "$1".',
			'errNotFolder'         : 'Обектът не е папка.',
			'errNotFile'           : 'Обектът не е файл.',
			'errRead'              : 'Неуспешно прочитане на "$1".',
			'errWrite'             : 'Неуспешен запис в "$1".',
			'errPerm'              : 'Разрешение отказано.',
			'errLocked'            : '"$1" е заключен и не може да бъде преименуван, местен или премахван.',
			'errExists'            : 'Вече съществува файл с име "$1"',
			'errInvName'           : 'Грешно име на файл.',
			'errInvDirname'        : 'Невалидно име на папка.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Папката не е открита.',
			'errFileNotFound'      : 'Файлът не е открит.',
			'errTrgFolderNotFound' : 'Целевата папка "$1" не е намерена.',
			'errPopup'             : 'Браузъра блокира отварянето на прозорец. За да отворите файла, разрешете отварянето в настройките на браузъра.',
			'errMkdir'             : 'Неуспешно създаване на папка "$1".',
			'errMkfile'            : 'Неуспешно създаване на файл "$1".',
			'errRename'            : 'Неуспешно преименуване на "$1".',
			'errCopyFrom'          : 'Копирането на файлове от том "$1" не е разрешено.',
			'errCopyTo'            : 'Копирането на файлове в том "$1" не е разрешено.',
			'errMkOutLink'         : 'Неуспех при създаване на връзка извън началото на ресурса.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Грешка при качване.',  // old name - errUploadCommon
			'errUploadFile'        : 'Неуспешно качване на "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Не са намерени файлове за качване.',
			'errUploadTotalSize'   : 'Данните превишават максимално допостумия размер.', // old name - errMaxSize
			'errUploadFileSize'    : 'Файлът превишава максимално допустимия размер.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Непозволен тип на файла.',
			'errUploadTransfer'    : '"$1" грешка при предаване.',
			'errUploadTemp'        : 'Неуспешно създаване на временен файл за качване.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Обект "$1" вече съществува на това място и не може да бъде заменен от обект от друг тип.', // new
			'errReplace'           : 'Не може да се замени "$1".',
			'errSave'              : 'Не може да се запише "$1".',
			'errCopy'              : 'Не може да се копира "$1".',
			'errMove'              : 'Не може да се премести "$1".',
			'errCopyInItself'      : 'Не може да се копира "$1" върху самия него.',
			'errRm'                : 'Не може да се премахне "$1".',
			'errTrash'             : 'Не може да се премести в кошчето', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Не може да се премахне изходния файл(ове).',
			'errExtract'           : 'Не може да се извлекат файловете от "$1".',
			'errArchive'           : 'Не може да се създаде архив.',
			'errArcType'           : 'Неподдържан тип на архива.',
			'errNoArchive'         : 'Файлът не е архив или е от неподдържан тип.',
			'errCmdNoSupport'      : 'Сървъра не поддържа тази команда.',
			'errReplByChild'       : 'Папката “$1” не може да бъде заменена от съдържащ се в нея елемент.',
			'errArcSymlinks'       : 'От съображения за сигурност няма да бъдат разопаковани архиви съдържащи symlinks.', // edited 24.06.2012
			'errArcMaxSize'        : 'Архивните файлове превишават максимално допустимия размер.',
			'errResize'            : 'Не може да се преоразмери "$1".',
			'errResizeDegree'      : 'Невалиден градус за ротация.',  // added 7.3.2013
			'errResizeRotate'      : 'Изображението не е ротирано.',  // added 7.3.2013
			'errResizeSize'        : 'Невалиден размер на изображение.',  // added 7.3.2013
			'errResizeNoChange'    : 'Размерът на изображението не е променен.',  // added 7.3.2013
			'errUsupportType'      : 'Неподдържан тип на файл.',
			'errNotUTF8Content'    : 'Файл "$1" не е в UTF-8 формат и не може да бъде редактиран.',  // added 9.11.2011
			'errNetMount'          : 'Не може да се монтира "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Неподдържан протокол.',     // added 17.04.2012
			'errNetMountFailed'    : 'Монтирането не е успешно.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Хост се изисква.', // added 18.04.2012
			'errSessionExpires'    : 'Сесията ви изтече поради липса на активност.',
			'errCreatingTempDir'   : 'Не може да се създаде временна директория: "$1"',
			'errFtpDownloadFile'   : 'Не може да се изтегли файл от FTP: "$1"',
			'errFtpUploadFile'     : 'Не може да се качи файл на FTP: "$1"',
			'errFtpMkdir'          : 'Не може да се създаде директория на FTP: "$1"',
			'errArchiveExec'       : 'Грешка при архивиране на файлове: "$1"',
			'errExtractExec'       : 'Грешка при разархивиране на файлове: "$1"',
			'errNetUnMount'        : 'Не може да се размонтира', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Не е конвертируем до UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Опитайте Google Chrome, ако искате да качите папка.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Времето изтече при търсенето на "$1". Резултатът от търсенето е частичен.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Необходимо е повторно оторизиране.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Максималният брой избрани файлове е $ 1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Не може да се възстанови от кошчето. Не може да се определи местоположението за възстановяване.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Не е намерен редактор за този тип файл.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Възникна грешка на сървъра.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Папката "$1" не може да се изпразни.', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Създай архив',
			'cmdback'      : 'Назад',
			'cmdcopy'      : 'Копирай',
			'cmdcut'       : 'Изрежи',
			'cmddownload'  : 'Свали',
			'cmdduplicate' : 'Дублирай',
			'cmdedit'      : 'Редактирай файл',
			'cmdextract'   : 'Извлечи файловете от архива',
			'cmdforward'   : 'Напред',
			'cmdgetfile'   : 'Избери файлове',
			'cmdhelp'      : 'За тази програма',
			'cmdhome'      : 'Начало',
			'cmdinfo'      : 'Информация',
			'cmdmkdir'     : 'Нова папка',
			'cmdmkdirin'   : 'В нова папка', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Нов файл',
			'cmdopen'      : 'Отвори',
			'cmdpaste'     : 'Вмъкни',
			'cmdquicklook' : 'Преглед',
			'cmdreload'    : 'Презареди',
			'cmdrename'    : 'Преименувай',
			'cmdrm'        : 'Изтрий',
			'cmdtrash'     : 'В кошчето', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Възстанови', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Намери файлове',
			'cmdup'        : 'Една директория нагоре',
			'cmdupload'    : 'Качи файлове',
			'cmdview'      : 'Виж',
			'cmdresize'    : 'Промени изображение',
			'cmdsort'      : 'Подреди',
			'cmdnetmount'  : 'Монтирай мрежов ресурс', // added 18.04.2012
			'cmdnetunmount': 'Размонтирай', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Към избрани', // added 28.12.2014
			'cmdchmod'     : 'Промяна на вид', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Отвори папка', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Нулирай ширината на колоната', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Цял екран', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Премести', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Изпразни папката', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Отмени', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Преправи', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Настройки', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Избери всичко', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Избери нищо', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Обърни селекцията', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Отвори в нов прозорец', // from v2.1.38 added 3.4.2018
			'cmdhide'      : 'Скрий (лично)', // from v2.1.41 added 24.7.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Затвори',
			'btnSave'   : 'Запиши',
			'btnRm'     : 'Премахни',
			'btnApply'  : 'Приложи',
			'btnCancel' : 'Отказ',
			'btnNo'     : 'Не',
			'btnYes'    : 'Да',
			'btnMount'  : 'Монтирай',  // added 18.04.2012
			'btnApprove': 'Отиди на $1 и одобри', // from v2.1 added 26.04.2012
			'btnUnmount': 'Размонтирай', // from v2.1 added 30.04.2012
			'btnConv'   : 'Конвертирай', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Тук',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Ресурс',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Всички',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME тип', // from v2.1 added 22.5.2015
			'btnFileName':'Име',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Запази и затвори', // from v2.1 added 12.6.2015
			'btnBackup' : 'Архивирай', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Преименувай',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Преименувай(Всички)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Пред ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'След ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Запази като', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Отваряне на папка',
			'ntffile'     : 'Отваряне на файл',
			'ntfreload'   : 'Презареждане съдържанието на папка',
			'ntfmkdir'    : 'Създава се директория',
			'ntfmkfile'   : 'Създава се файл',
			'ntfrm'       : 'Изтриване на файлове',
			'ntfcopy'     : 'Копиране на файлове',
			'ntfmove'     : 'Преместване на файлове',
			'ntfprepare'  : 'Подготовка за копиране на файлове',
			'ntfrename'   : 'Преименуване на файлове',
			'ntfupload'   : 'Качват се файлове',
			'ntfdownload' : 'Свалят се файлове',
			'ntfsave'     : 'Запис на файлове',
			'ntfarchive'  : 'Създава се архив',
			'ntfextract'  : 'Извличат се файловете от архив',
			'ntfsearch'   : 'Търсят се файлове',
			'ntfresize'   : 'Преоразмеряват се изображения',
			'ntfsmth'     : 'Зает съм >_<',
			'ntfloadimg'  : 'Зареждат се изображения',
			'ntfnetmount' : 'Монтира се мрежов ресурс', // added 18.04.2012
			'ntfnetunmount': 'Размонтира се мрежов ресурс', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Извличат се размерите на изображение', // added 20.05.2013
			'ntfreaddir'  : 'Извлича се информация за папка', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Взима се URL от връзка', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Променя се вида на файл', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Проверка на името на файла за качване', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Създаване на файл за изтегляне', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Получава се информация за пътя', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Обработка на качения файл', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Прехвърлят се позиции в кошчето', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Извършва се възстановяване от кошчето', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Проверка на целевата папка', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Отмяна на предишната операция', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Възстановяване на предходните отменени', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Кошче', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'неизвестна',
			'Today'       : 'днес',
			'Yesterday'   : 'вчера',
			'msJan'       : 'яну',
			'msFeb'       : 'фев',
			'msMar'       : 'мар',
			'msApr'       : 'апр',
			'msMay'       : 'май',
			'msJun'       : 'юни',
			'msJul'       : 'юли',
			'msAug'       : 'авг',
			'msSep'       : 'сеп',
			'msOct'       : 'окт',
			'msNov'       : 'ное',
			'msDec'       : 'дек',
			'January'     : 'януари',
			'February'    : 'февруари',
			'March'       : 'март',
			'April'       : 'април',
			'May'         : 'май',
			'June'        : 'юни',
			'July'        : 'юли',
			'August'      : 'август',
			'September'   : 'септември',
			'October'     : 'октомври',
			'November'    : 'ноември',
			'December'    : 'декември',
			'Sunday'      : 'неделя',
			'Monday'      : 'понеделник',
			'Tuesday'     : 'вторник',
			'Wednesday'   : 'сряда',
			'Thursday'    : 'четвъртък',
			'Friday'      : 'петък',
			'Saturday'    : 'събота',
			'Sun'         : 'нед',
			'Mon'         : 'пон',
			'Tue'         : 'вто',
			'Wed'         : 'сря',
			'Thu'         : 'чет',
			'Fri'         : 'пет',
			'Sat'         : 'съб',

			/******************************** sort variants ********************************/
			'sortname'          : 'по име',
			'sortkind'          : 'по вид',
			'sortsize'          : 'по размер',
			'sortdate'          : 'по дата',
			'sortFoldersFirst'  : 'Папките първи',
			'sortperm'          : 'по права', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'по вид',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'по собственик',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'по група',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Също дървовиден изглед',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NewFile.txt', // added 10.11.2015
			'untitled folder'   : 'NewFolder',   // added 10.11.2015
			'Archive'           : 'NewArchive',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Изисква се подтвърждение',
			'confirmRm'       : 'Сигурни ли сте, че желаете да премахнете файловете?<br/>Това действие е необратимо!',
			'confirmRepl'     : 'Да заменя ли стария файл с новия?',
			'confirmRest'     : 'Да се замени ли съществуващата позиция с тази в кошчето?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Не е в UTF-8 формат<br/>Конвертиране до UTF-8?<br/>Съдържанието става в UTF-8 формат при запазване след конверсията.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Кодирането на този файл не може да бъде открито. Необходимо е временно да се преобразува в UTF-8 за редактиране. <br/> Моля, изберете кодиране на този файл.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Има направени промени.<br/>Те ще бъдат загубени, ако не запишете промените.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Наистина ли искате да преместите позиции в кошчето за боклук?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Приложи за всички',
			'name'            : 'Име',
			'size'            : 'Размер',
			'perms'           : 'Права',
			'modify'          : 'Променено',
			'kind'            : 'Вид',
			'read'            : 'четене',
			'write'           : 'запис',
			'noaccess'        : 'без достъп',
			'and'             : 'и',
			'unknown'         : 'непознат',
			'selectall'       : 'Избери всички файлове',
			'selectfiles'     : 'Избери файл(ове)',
			'selectffile'     : 'Избери първият файл',
			'selectlfile'     : 'Избери последният файл',
			'viewlist'        : 'Изглед списък',
			'viewicons'       : 'Изглед икони',
			'viewSmall'       : 'Малки икони', // from v2.1.39 added 22.5.2018
			'viewMedium'      : 'Средни икони', // from v2.1.39 added 22.5.2018
			'viewLarge'       : 'Големи икони', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'  : 'Много големи икони', // from v2.1.39 added 22.5.2018
			'places'          : 'Избрани',
			'calc'            : 'Изчисли',
			'path'            : 'Път',
			'aliasfor'        : 'Връзка към',
			'locked'          : 'Заключен',
			'dim'             : 'Размери',
			'files'           : 'Файлове',
			'folders'         : 'Папки',
			'items'           : 'Позиции',
			'yes'             : 'да',
			'no'              : 'не',
			'link'            : 'Връзка',
			'searcresult'     : 'Резултати от търсенето',
			'selected'        : 'Избрани позиции',
			'about'           : 'За',
			'shortcuts'       : 'Бързи клавиши',
			'help'            : 'Помощ',
			'webfm'           : 'Файлов менажер за Интернет',
			'ver'             : 'Версия',
			'protocolver'     : 'версия на протокола',
			'homepage'        : 'Начало',
			'docs'            : 'Документация',
			'github'          : 'Разклонение в Github',
			'twitter'         : 'Последвайте ни в Twitter',
			'facebook'        : 'Присъединете се към нас във Facebook',
			'team'            : 'Екип',
			'chiefdev'        : 'Главен разработчик',
			'developer'       : 'разработчик',
			'contributor'     : 'сътрудник',
			'maintainer'      : 'поддръжка',
			'translator'      : 'преводач',
			'icons'           : 'Икони',
			'dontforget'      : 'и не забравяйте да си вземете кърпата',
			'shortcutsof'     : 'Преките пътища са изключени',
			'dropFiles'       : 'Пуснете файловете тук',
			'or'              : 'или',
			'selectForUpload' : 'Избери файлове',
			'moveFiles'       : 'Премести файлове',
			'copyFiles'       : 'Копирай файлове',
			'restoreFiles'    : 'Възстанови файлове', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Премахни от избрани',
			'aspectRatio'     : 'Отношение',
			'scale'           : 'Мащаб',
			'width'           : 'Ширина',
			'height'          : 'Височина',
			'resize'          : 'Преоразмери',
			'crop'            : 'Отрежи',
			'rotate'          : 'Ротирай',
			'rotate-cw'       : 'Ротирай 90 градуса CW',
			'rotate-ccw'      : 'Ротирай 90 градуса CCW',
			'degree'          : '°',
			'netMountDialogTitle' : 'Монтиране на мрежов ресурс', // added 18.04.2012
			'protocol'            : 'Протокол', // added 18.04.2012
			'host'                : 'Хост', // added 18.04.2012
			'port'                : 'Порт', // added 18.04.2012
			'user'                : 'Потребител', // added 18.04.2012
			'pass'                : 'Парола', // added 18.04.2012
			'confirmUnmount'      : 'Ще размонтирате $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Пусни или вмъкни файлове от браузера', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Тук поснете файловете, URL адресите или изображенията от клипборда', // from v2.1 added 07.04.2014
			'encoding'        : 'Кодировка', // from v2.1 added 19.12.2014
			'locale'          : 'Локали',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Цел: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Търсене по въведен MIME тип', // from v2.1 added 22.5.2015
			'owner'           : 'Собственик', // from v2.1 added 20.6.2015
			'group'           : 'Група', // from v2.1 added 20.6.2015
			'other'           : 'Други', // from v2.1 added 20.6.2015
			'execute'         : 'Изпълнява', // from v2.1 added 20.6.2015
			'perm'            : 'Разрешение', // from v2.1 added 20.6.2015
			'mode'            : 'Вид', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Папката е празна', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Папката е празна\\A Влачи и пусни за да добавите файлове', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Папката е празна\\A Докоснете дълго за да добавите позиции', // from v2.1.6 added 30.12.2015
			'quality'         : 'Качество', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Автоматично синхронизиране',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Премести нагоре',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Вземи URL връзка', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Избрани позиции ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Папка ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Позволи офлайн достъп', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'За повторно удостоверяване', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Сега се зарежда...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Отваряне на няколко файла', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Опитвате се да отворите $1 файла. Наистина ли искате да ги отворите в браузъра?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Няма резултат от търсенето.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Редактира се файл.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Вие сте избрали $1 позиции.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Имате $1 позиции в клипборда.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Инкременталното търсене е само от текущия изглед.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Възстановяване', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 завършени', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Контекстно меню', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Завъртане на страницата', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Начала на ресурси', // from v2.1.16 added 16.9.2016
			'reset'           : 'Нулиране', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Цвят на фона', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Средство за избиране на цвят', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px мрежа', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Активно', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Неактивно', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Няма резултат от търсенето в текущия изглед.\\AНатиснете [Enter] за да разширите целта на търсене.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Резултатите от търсенето на първата буква са празни в текущия изглед.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Текстов етикет', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 мин остават', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Отваряне отново с избрано кодиране', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Запазете с избраното кодиране', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Избери папка', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Търсене по първа буква', // from v2.1.23 added 24.3.2017
			'presets'         : 'Мостри', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Прекалено много позиции, не може да премести в кошчето.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Текстово поле', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Изпразнете папка "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'В папка "$1" няма позиции.', // from v2.1.25 added 22.6.2017
			'preference'      : 'Настройки', // from v2.1.26 added 28.6.2017
			'language'        : 'Настройка на езика', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Инициализирайте настройките запаметени в този браузър', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Настройки на лентата с инструменти', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... $1 символа остават.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Сумарно', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Груб размер на файла', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Фокусирайте върху елемента в диалоговия прозорец с мишката',  // from v2.1.30 added 2.11.2017
			'select'          : 'Избери', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Действие при избор на файл', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Отворете с редактора, използван за последен път', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Обърнете селекцията', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Наистина ли искате да преименувате $1 избрани позиции като $2? <br/> Това не може да бъде отменено!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Групово преименуване', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Номер', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Добави префикс', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Добави суфикс', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Промени разширение', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Настройки за колони (Изглед в списък)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Всички промени ще се отразят незабавно в архива.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Промените няма да се отразят, докато не размонтирате този диск.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'The following volume(s) mounted on this volume also unmounted. Are you sure to unmount it?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Информация за селекцията', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Алгоритми за показване на файловия хеш', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Info Items (Selection Info Panel)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Натиснете отново, за да излезете.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Лента с инструменти', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Работно пространство', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Диалог', // from v2.1.38 added 4.4.2018
			'all'             : 'Всички', // from v2.1.38 added 4.4.2018
			'iconSize'        : 'Размер на иконите (изглед с икони)', // from v2.1.39 added 7.5.2018
			'editorMaximized' : 'Отваря максимизиран прозорец на редактора', // from v2.1.40 added 30.6.2018
			'editorConvNoApi' : 'Тъй като в момента не е налична API за конверсията, моля, конвертирайте в уебсайта.', //from v2.1.40 added 8.7.2018
			'editorConvNeedUpload' : 'След конверсията трябва да го качите с URL адреса или изтегления файл, за да запазите конвертирания файл.', //from v2.1.40 added 8.7.2018
			'convertOn'       : 'Конвертиране на сайта от $1', // from v2.1.40 added 10.7.2018
			'integrations'    : 'Интеграции', // from v2.1.40 added 11.7.2018
			'integrationWith' : 'Този elFinder има следните интегрирани външни услуги. Моля, проверете условията за ползване, декларацията за поверителност и т.н., преди да ги използвате.', // from v2.1.40 added 11.7.2018
			'showHidden'      : 'Покажи скритите елементи', // from v2.1.41 added 24.7.2018
			'hideHidden'      : 'Скрий скритите елементи', // from v2.1.41 added 24.7.2018
			'toggleHidden'    : 'Покажи/скрий скритите елементи', // from v2.1.41 added 24.7.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Непознат',
			'kindRoot'        : 'Начало на ресурс', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Папка',
			'kindSelects'     : 'Селекции', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Връзка',
			'kindAliasBroken' : 'Счупена връзка',
			// applications
			'kindApp'         : 'Приложение',
			'kindPostscript'  : 'Postscript документ',
			'kindMsOffice'    : 'Microsoft Office документ',
			'kindMsWord'      : 'Microsoft Word документ',
			'kindMsExcel'     : 'Microsoft Excel документ',
			'kindMsPP'        : 'Microsoft Powerpoint презентация',
			'kindOO'          : 'Open Office документ',
			'kindAppFlash'    : 'Flash приложение',
			'kindPDF'         : 'PDF документ',
			'kindTorrent'     : 'Bittorrent файл',
			'kind7z'          : '7z архив',
			'kindTAR'         : 'TAR архив',
			'kindGZIP'        : 'GZIP архив',
			'kindBZIP'        : 'BZIP архив',
			'kindXZ'          : 'XZ архив',
			'kindZIP'         : 'ZIP архив',
			'kindRAR'         : 'RAR архив',
			'kindJAR'         : 'Java JAR файл',
			'kindTTF'         : 'True Type шрифт',
			'kindOTF'         : 'Open Type шрифт',
			'kindRPM'         : 'RPM пакет',
			// texts
			'kindText'        : 'Текстов документ',
			'kindTextPlain'   : 'Чист текст',
			'kindPHP'         : 'PHP изходен код',
			'kindCSS'         : 'CSS таблица със стилове',
			'kindHTML'        : 'HTML документ',
			'kindJS'          : 'Javascript изходен код',
			'kindRTF'         : 'RTF текстови файл',
			'kindC'           : 'C изходен код',
			'kindCHeader'     : 'C header изходен код',
			'kindCPP'         : 'C++ изходен код',
			'kindCPPHeader'   : 'C++ header изходен код',
			'kindShell'       : 'Unix shell изходен код',
			'kindPython'      : 'Python изходен код',
			'kindJava'        : 'Java изходен код',
			'kindRuby'        : 'Ruby изходен код',
			'kindPerl'        : 'Perl изходен код',
			'kindSQL'         : 'SQL изходен код',
			'kindXML'         : 'XML документ',
			'kindAWK'         : 'AWK изходен код',
			'kindCSV'         : 'CSV стойности разделени със запетая',
			'kindDOCBOOK'     : 'Docbook XML документ',
			'kindMarkdown'    : 'Markdown текст', // added 20.7.2015
			// images
			'kindImage'       : 'Изображение',
			'kindBMP'         : 'BMP изображение',
			'kindJPEG'        : 'JPEG изображение',
			'kindGIF'         : 'GIF изображение',
			'kindPNG'         : 'PNG изображение',
			'kindTIFF'        : 'TIFF изображение',
			'kindTGA'         : 'TGA изображение',
			'kindPSD'         : 'Adobe Photoshop изображение',
			'kindXBITMAP'     : 'X bitmap изображение',
			'kindPXM'         : 'Pixelmator изображение',
			// media
			'kindAudio'       : 'Аудио медия',
			'kindAudioMPEG'   : 'MPEG звук',
			'kindAudioMPEG4'  : 'MPEG-4 звук',
			'kindAudioMIDI'   : 'MIDI звук',
			'kindAudioOGG'    : 'Ogg Vorbis звук',
			'kindAudioWAV'    : 'WAV звук',
			'AudioPlaylist'   : 'MP3 списък за изпълнение',
			'kindVideo'       : 'Видео медия',
			'kindVideoDV'     : 'DV филм',
			'kindVideoMPEG'   : 'MPEG филм',
			'kindVideoMPEG4'  : 'MPEG-4 филм',
			'kindVideoAVI'    : 'AVI филм',
			'kindVideoMOV'    : 'Quick Time филм',
			'kindVideoWM'     : 'Windows Media филм',
			'kindVideoFlash'  : 'Flash филм',
			'kindVideoMKV'    : 'Matroska филм',
			'kindVideoOGG'    : 'Ogg филм'
		}
	};
}));
