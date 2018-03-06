/**
 * Русский язык translation
 * @author Dmitry "dio" Levashov <dio@std42.ru>
 * @author Andrew Berezovsky <andrew.berezovsky@gmail.com>
 * @author Alex Yashkin <alex@yashkin.by>
 * @version 2017-10-06
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
	elFinder.prototype.i18.ru = {
		translator : 'Dmitry "dio" Levashov &lt;dio@std42.ru&gt;, Andrew Berezovsky &lt;andrew.berezovsky@gmail.com&gt;, Alex Yashkin &lt;alex@yashkin.by&gt;',
		language   : 'Русский язык',
		direction  : 'ltr',
		dateFormat : 'd M Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Ошибка',
			'errUnknown'           : 'Неизвестная ошибка.',
			'errUnknownCmd'        : 'Неизвестная команда.',
			'errJqui'              : 'Отсутствуют необходимые компоненты jQuery UI - selectable, draggable и droppable.',
			'errNode'              : 'Отсутствует DOM элемент для инициализации elFinder.',
			'errURL'               : 'Неверная конфигурация elFinder! Не указан URL.',
			'errAccess'            : 'Доступ запрещен.',
			'errConnect'           : 'Не удалось соединиться с сервером.',
			'errAbort'             : 'Соединение прервано.',
			'errTimeout'           : 'Таймаут соединения.',
			'errNotFound'          : 'Сервер не найден.',
			'errResponse'          : 'Некорректный ответ сервера.',
			'errConf'              : 'Некорректная настройка сервера.',
			'errJSON'              : 'Модуль PHP JSON не установлен.',
			'errNoVolumes'         : 'Отсутствуют корневые директории достуные для чтения.',
			'errCmdParams'         : 'Некорректные параметры команды "$1".',
			'errDataNotJSON'       : 'Данные не в формате JSON.',
			'errDataEmpty'         : 'Данные отсутствуют.',
			'errCmdReq'            : 'Для запроса к серверу необходимо указать имя команды.',
			'errOpen'              : 'Не удалось открыть "$1".',
			'errNotFolder'         : 'Объект не является папкой.',
			'errNotFile'           : 'Объект не является файлом.',
			'errRead'              : 'Ошибка чтения "$1".',
			'errWrite'             : 'Ошибка записи в "$1".',
			'errPerm'              : 'Доступ запрещен.',
			'errLocked'            : '"$1" защищен и не может быть переименован, перемещен или удален.',
			'errExists'            : 'В папке уже существует файл с именем "$1".',
			'errInvName'           : 'Недопустимое имя файла.',
			'errInvDirname'        : 'Недопустимое имя папки.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Папка не найдена.',
			'errFileNotFound'      : 'Файл не найден.',
			'errTrgFolderNotFound' : 'Целевая папка "$1" не найдена.',
			'errPopup'             : 'Браузер заблокировал открытие нового окна. Чтобы открыть файл, измените настройки браузера.',
			'errMkdir'             : 'Ошибка создания папки "$1".',
			'errMkfile'            : 'Ошибка создания файла "$1".',
			'errRename'            : 'Ошибка переименования "$1".',
			'errCopyFrom'          : 'Копирование файлов из директории "$1" запрещено.',
			'errCopyTo'            : 'Копирование файлов в директорию "$1" запрещено.',
			'errMkOutLink'         : 'Невозможно создать ссылку вне корня раздела.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Ошибка загрузки.',  // old name - errUploadCommon
			'errUploadFile'        : 'Невозможно загрузить "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Нет файлов для загрузки.',
			'errUploadTotalSize'   : 'Превышен допустимый размер загружаемых данных.', // old name - errMaxSize
			'errUploadFileSize'    : 'Размер файла превышает допустимый.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Недопустимый тип файла.',
			'errUploadTransfer'    : 'Ошибка передачи файла "$1".',
			'errUploadTemp'        : 'Невозможно создать временный файл для загрузки.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Объект "$1" по этому адресу уже существует и не может быть заменен объектом другого типа.', // new
			'errReplace'           : 'Невозможно заменить "$1".',
			'errSave'              : 'Невозможно сохранить "$1".',
			'errCopy'              : 'Невозможно скопировать "$1".',
			'errMove'              : 'Невозможно переместить "$1".',
			'errCopyInItself'      : 'Невозможно скопировать "$1" в самого себя.',
			'errRm'                : 'Невозможно удалить "$1".',
			'errTrash'             : 'Невозможно переместить в корзину.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Невозможно удалить файлы источника.',
			'errExtract'           : 'Невозможно извлечь фалы из "$1".',
			'errArchive'           : 'Невозможно создать архив.',
			'errArcType'           : 'Неподдерживаемый тип архива.',
			'errNoArchive'         : 'Файл не является архивом или неподдерживаемый тип архива.',
			'errCmdNoSupport'      : 'Сервер не поддерживает эту команду.',
			'errReplByChild'       : 'Невозможно заменить папку "$1" содержащимся в ней объектом.',
			'errArcSymlinks'       : 'По соображениям безопасности запрещена распаковка архивов, содержащих ссылки (symlinks) или файлы с недопустимыми именами.', // edited 24.06.2012
			'errArcMaxSize'        : 'Размер файлов в архиве превышает максимально разрешенный.',
			'errResize'            : 'Не удалось изменить размер "$1".',
			'errResizeDegree'      : 'Некорректный градус поворота.',  // added 7.3.2013
			'errResizeRotate'      : 'Невозможно повернуть изображение.',  // added 7.3.2013
			'errResizeSize'        : 'Некорректный размер изображения.',  // added 7.3.2013
			'errResizeNoChange'    : 'Размер изображения не изменился.',  // added 7.3.2013
			'errUsupportType'      : 'Неподдерживаемый тип файла.',
			'errNotUTF8Content'    : 'Файл "$1" содержит текст в кодировке отличной от UTF-8 и не может быть отредактирован.',  // added 9.11.2011
			'errNetMount'          : 'Невозможно подключить "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Неподдерживаемый протокол.',     // added 17.04.2012
			'errNetMountFailed'    : 'Ошибка монтирования.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Требуется указать хост.', // added 18.04.2012
			'errSessionExpires'    : 'Сессия была завершена так как превышено время отсутствия активности.',
			'errCreatingTempDir'   : 'Невозможно создать временную директорию: "$1"',
			'errFtpDownloadFile'   : 'Невозможно скачать файл с FTP: "$1"',
			'errFtpUploadFile'     : 'Невозможно загрузить файл на FTP: "$1"',
			'errFtpMkdir'          : 'Невозможно создать директорию на FTP: "$1"',
			'errArchiveExec'       : 'Ошибка при выполнении архивации: "$1"',
			'errExtractExec'       : 'Ошибка при выполнении распаковки: "$1"',
			'errNetUnMount'        : 'Невозможно отключить', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Не конвертируется в UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Если вы хотите загружать папки, попробуйте Google Chrome.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Превышено время ожидания при поиске "$1". Результаты поиска частичные.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Требуется повторная авторизация.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Максимальное число выбираемых файлов: $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Невозможно восстановить из корзины. Не удалось определить путь для восстановления.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Не найден редактор для этого типа файлов.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Возникла ошибка на стороне сервера.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Невозможно очистить папку "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Создать архив',
			'cmdback'      : 'Назад',
			'cmdcopy'      : 'Копировать',
			'cmdcut'       : 'Вырезать',
			'cmddownload'  : 'Скачать',
			'cmdduplicate' : 'Сделать копию',
			'cmdedit'      : 'Редактировать файл',
			'cmdextract'   : 'Распаковать архив',
			'cmdforward'   : 'Вперед',
			'cmdgetfile'   : 'Выбрать файлы',
			'cmdhelp'      : 'О программе',
			'cmdhome'      : 'Домой',
			'cmdinfo'      : 'Свойства',
			'cmdmkdir'     : 'Новая папка',
			'cmdmkdirin'   : 'В новую папку', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Новый текстовый файл',
			'cmdopen'      : 'Открыть',
			'cmdpaste'     : 'Вставить',
			'cmdquicklook' : 'Быстрый просмотр',
			'cmdreload'    : 'Обновить',
			'cmdrename'    : 'Переименовать',
			'cmdrm'        : 'Удалить',
			'cmdtrash'     : 'Переместить в корзину', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Восстановить', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Поиск файлов',
			'cmdup'        : 'Наверх',
			'cmdupload'    : 'Загрузить файлы',
			'cmdview'      : 'Вид',
			'cmdresize'    : 'Изменить размер и повернуть',
			'cmdsort'      : 'Сортировать',
			'cmdnetmount'  : 'Подключить сетевой раздел', // added 18.04.2012
			'cmdnetunmount': 'Отключить', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'В избранное', // added 28.12.2014
			'cmdchmod'     : 'Изменить права доступа', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Открыть папку', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Сбросить ширину колонок', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Полный экран', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Переместить', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Очистить папку', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Отменить', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Вернуть', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Предпочтения', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Выделить все', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Снять все выделение', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Инвертировать выделение', // from v2.1.28 added 15.08.2017

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Закрыть',
			'btnSave'   : 'Сохранить',
			'btnRm'     : 'Удалить',
			'btnApply'  : 'Применить',
			'btnCancel' : 'Отмена',
			'btnNo'     : 'Нет',
			'btnYes'    : 'Да',
			'btnMount'  : 'Подключить',  // added 18.04.2012
			'btnApprove': 'Перейти в $1 и применить', // from v2.1 added 26.04.2012
			'btnUnmount': 'Отключить', // from v2.1 added 30.04.2012
			'btnConv'   : 'Конвертировать', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Здесь',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Раздел',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Все',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME тип', // from v2.1 added 22.5.2015
			'btnFileName':'Имя файла',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Сохранить и закрыть', // from v2.1 added 12.6.2015
			'btnBackup' : 'Резервная копия', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Переименовать',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Переименовать (все)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Пред. ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'След. ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Сохранить как', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Открыть папку',
			'ntffile'     : 'Открыть файл',
			'ntfreload'   : 'Обновить текущую папку',
			'ntfmkdir'    : 'Создание папки',
			'ntfmkfile'   : 'Создание файлов',
			'ntfrm'       : 'Удалить файлы',
			'ntfcopy'     : 'Скопировать файлы',
			'ntfmove'     : 'Переместить файлы',
			'ntfprepare'  : 'Подготовка к копированию файлов',
			'ntfrename'   : 'Переименовать файлы',
			'ntfupload'   : 'Загрузка файлов',
			'ntfdownload' : 'Скачивание файлов',
			'ntfsave'     : 'Сохранить файлы',
			'ntfarchive'  : 'Создание архива',
			'ntfextract'  : 'Распаковка архива',
			'ntfsearch'   : 'Поиск файлов',
			'ntfresize'   : 'Изменение размеров изображений',
			'ntfsmth'     : 'Занят важным делом',
			'ntfloadimg'  : 'Загрузка изображения',
			'ntfnetmount' : 'Подключение сетевого диска', // added 18.04.2012
			'ntfnetunmount': 'Отключение сетевого диска', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Получение размеров изображения', // added 20.05.2013
			'ntfreaddir'  : 'Чтение информации о папке', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Получение URL ссылки', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Изменение прав доступа к файлу', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Проверка измени загруженного файла', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Создание файла для скачки', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Получение информации о пути', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Обработка загруженного файла', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Перемещение в корзину', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Восстановление из корзины', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Проверка папки назначения', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Отмена предыдущей операции', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Восстановление предыдущей операции', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Корзина', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'неизвестно',
			'Today'       : 'Сегодня',
			'Yesterday'   : 'Вчера',
			'msJan'       : 'Янв',
			'msFeb'       : 'Фев',
			'msMar'       : 'Мар',
			'msApr'       : 'Апр',
			'msMay'       : 'Май',
			'msJun'       : 'Июн',
			'msJul'       : 'Июл',
			'msAug'       : 'Авг',
			'msSep'       : 'Сен',
			'msOct'       : 'Окт',
			'msNov'       : 'Ноя',
			'msDec'       : 'Дек',
			'January'     : 'Январь',
			'February'    : 'Февраль',
			'March'       : 'Март',
			'April'       : 'Апрель',
			'May'         : 'Май',
			'June'        : 'Июнь',
			'July'        : 'Июль',
			'August'      : 'Август',
			'September'   : 'Сентябрь',
			'October'     : 'Октябрь',
			'November'    : 'Ноябрь',
			'December'    : 'Декабрь',
			'Sunday'      : 'Воскресенье',
			'Monday'      : 'Понедельник',
			'Tuesday'     : 'Вторник',
			'Wednesday'   : 'Среда',
			'Thursday'    : 'Четверг',
			'Friday'      : 'Пятница',
			'Saturday'    : 'Суббота',
			'Sun'         : 'Вск',
			'Mon'         : 'Пнд',
			'Tue'         : 'Втр',
			'Wed'         : 'Срд',
			'Thu'         : 'Чтв',
			'Fri'         : 'Птн',
			'Sat'         : 'Сбт',

			/******************************** sort variants ********************************/
			'sortname'          : 'по имени',
			'sortkind'          : 'по типу',
			'sortsize'          : 'по размеру',
			'sortdate'          : 'по дате',
			'sortFoldersFirst'  : 'Папки в начале',
			'sortperm'          : 'по разрешениям', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'по режиму',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'по владельцу',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'по группе',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Также и дерево каталогов',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'НовыйФайл.txt', // added 10.11.2015
			'untitled folder'   : 'НоваяПапка',   // added 10.11.2015
			'Archive'           : 'НовыйАрхив',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Необходимо подтверждение',
			'confirmRm'       : 'Вы уверены, что хотите удалить файлы?<br>Действие необратимо!',
			'confirmRepl'     : 'Заменить старый файл новым?',
			'confirmRest'     : 'Заменить существующий файл файлом из корзины?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Не UTF-8<br/>Сконвертировать в UTF-8?<br/>Данные станут UTF-8 при сохранении после конвертации.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Невозможно определить кодировку файла. Необходима предварительная конвертация файла в UTF-8 для дальнейшего редактирования.<br/>Выберите кодировку файла.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Произошли изменения.<br/>Если не сохраните изменения, то потеряете их.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Вы уверены, что хотите переместить файлы в корзину?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Применить для всех',
			'name'            : 'Имя',
			'size'            : 'Размер',
			'perms'           : 'Доступ',
			'modify'          : 'Изменен',
			'kind'            : 'Тип',
			'read'            : 'чтение',
			'write'           : 'запись',
			'noaccess'        : 'нет доступа',
			'and'             : 'и',
			'unknown'         : 'неизвестно',
			'selectall'       : 'Выбрать все файлы',
			'selectfiles'     : 'Выбрать файл(ы)',
			'selectffile'     : 'Выбрать первый файл',
			'selectlfile'     : 'Выбрать последний файл',
			'viewlist'        : 'В виде списка',
			'viewicons'       : 'В виде иконок',
			'places'          : 'Избранное',
			'calc'            : 'Вычислить',
			'path'            : 'Путь',
			'aliasfor'        : 'Указывает на',
			'locked'          : 'Защита',
			'dim'             : 'Размеры',
			'files'           : 'Файлы',
			'folders'         : 'Папки',
			'items'           : 'Объекты',
			'yes'             : 'да',
			'no'              : 'нет',
			'link'            : 'Ссылка',
			'searcresult'     : 'Результаты поиска',
			'selected'        : 'выбрано',
			'about'           : 'О программе',
			'shortcuts'       : 'Горячие клавиши',
			'help'            : 'Помощь',
			'webfm'           : 'Файловый менеджер для Web',
			'ver'             : 'Версия',
			'protocolver'     : 'версия протокола',
			'homepage'        : 'Сайт проекта',
			'docs'            : 'Документация',
			'github'          : 'Форкните на Github',
			'twitter'         : 'Следите в twitter',
			'facebook'        : 'Присоединяйтесь на facebook',
			'team'            : 'Команда',
			'chiefdev'        : 'ведущий разработчик',
			'developer'       : 'разработчик',
			'contributor'     : 'участник',
			'maintainer'      : 'сопровождение проекта',
			'translator'      : 'переводчик',
			'icons'           : 'Иконки',
			'dontforget'      : 'и не забудьте взять своё полотенце',
			'shortcutsof'     : 'Горячие клавиши отключены',
			'dropFiles'       : 'Перетащите файлы сюда',
			'or'              : 'или',
			'selectForUpload' : 'Выбрать файлы для загрузки',
			'moveFiles'       : 'Переместить файлы',
			'copyFiles'       : 'Скопировать файлы',
			'restoreFiles'    : 'Восстановить файлы', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Удалить из избранного',
			'aspectRatio'     : 'Соотношение сторон',
			'scale'           : 'Масштаб',
			'width'           : 'Ширина',
			'height'          : 'Высота',
			'resize'          : 'Изменить размер',
			'crop'            : 'Обрезать',
			'rotate'          : 'Повернуть',
			'rotate-cw'       : 'Повернуть на 90 градусов по часовой стрелке',
			'rotate-ccw'      : 'Повернуть на 90 градусов против часовой стрелке',
			'degree'          : '°',
			'netMountDialogTitle' : 'Подключить сетевой диск', // added 18.04.2012
			'protocol'            : 'Протокол', // added 18.04.2012
			'host'                : 'Хост', // added 18.04.2012
			'port'                : 'Порт', // added 18.04.2012
			'user'                : 'Пользователь', // added 18.04.2012
			'pass'                : 'Пароль', // added 18.04.2012
			'confirmUnmount'      : 'Вы хотите отключить $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Перетащите или вставьте файлы из браузера', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Перетащите или вставьте файлы и ссылки сюда', // from v2.1 added 07.04.2014
			'encoding'        : 'Кодировка', // from v2.1 added 19.12.2014
			'locale'          : 'Локаль',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Цель: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Поиск по введенному MIME типу', // from v2.1 added 22.5.2015
			'owner'           : 'Владелец', // from v2.1 added 20.6.2015
			'group'           : 'Группа', // from v2.1 added 20.6.2015
			'other'           : 'Остальные', // from v2.1 added 20.6.2015
			'execute'         : 'Исполнить', // from v2.1 added 20.6.2015
			'perm'            : 'Разрешение', // from v2.1 added 20.6.2015
			'mode'            : 'Режим', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Папка пуста', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Папка пуста\\A Перетащите чтобы добавить', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Папка пуста\\A Долгое нажатие чтобы добавить', // from v2.1.6 added 30.12.2015
			'quality'         : 'Качество', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Авто синхронизация',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Передвинуть вверх',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Получить URL ссылку', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Выбранные объекты ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID папки', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Позволить автономный доступ', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Авторизоваться повторно', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Загружается...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Открыть несколько файлов', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Вы пытаетесь открыть $1 файл(а/ов). Вы уверены, что хотите открыть их в браузере?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Ничего не найдено', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Это редактируемый файл.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Вы выбрали $1 файл(-ов).', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'У вас $1 файл(-ов) в буфере обмена.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Инкрементный поиск возможен только из текущего вида.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Восстановить', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 завершен', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Контекстное меню', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Переключение страницы', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Корни томов', // from v2.1.16 added 16.9.2016
			'reset'           : 'Сбросить', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Фоновый цвет', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Выбор цвета', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px сетка', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Включено', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Отключено', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Ничего не найдено в текущем виде.\\AНажмите [Enter] для развертывания цели поиска.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Поиск по первому символу не дал результатов в текущем виде.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Текстовая метка', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 минут осталось', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Переоткрыть с выбранной кодировкой', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Сохранить с выбранной кодировкой', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Выбрать папку', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Поиск по первому символу', // from v2.1.23 added 24.3.2017
			'presets'         : 'Пресеты', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Слишком много файлов для перемещения в корзину.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Текстовая область', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Очистить папку "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'Нет файлов в паке "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Настройки', // from v2.1.26 added 28.6.2017
			'language'        : 'Язык', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Сбросить настройки для этого браузера', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Настройки панели', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... еще символов: $1.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Общий размер', // from v2.1.29 added 28.9.2017

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Неизвестный',
			'kindRoot'        : 'Корень тома', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Папка',
			'kindSelects'     : 'Выбор', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Ссылка',
			'kindAliasBroken' : 'Битая ссылка',
			// applications
			'kindApp'         : 'Приложение',
			'kindPostscript'  : 'Документ Postscript',
			'kindMsOffice'    : 'Документ Microsoft Office',
			'kindMsWord'      : 'Документ Microsoft Word',
			'kindMsExcel'     : 'Документ Microsoft Excel',
			'kindMsPP'        : 'Презентация Microsoft Powerpoint',
			'kindOO'          : 'Документ Open Office',
			'kindAppFlash'    : 'Приложение Flash',
			'kindPDF'         : 'Документ PDF',
			'kindTorrent'     : 'Файл Bittorrent',
			'kind7z'          : 'Архив 7z',
			'kindTAR'         : 'Архив TAR',
			'kindGZIP'        : 'Архив GZIP',
			'kindBZIP'        : 'Архив BZIP',
			'kindXZ'          : 'Архив XZ',
			'kindZIP'         : 'Архив ZIP',
			'kindRAR'         : 'Архив RAR',
			'kindJAR'         : 'Файл Java JAR',
			'kindTTF'         : 'Шрифт True Type',
			'kindOTF'         : 'Шрифт Open Type',
			'kindRPM'         : 'Пакет RPM',
			// texts
			'kindText'        : 'Текстовый документ',
			'kindTextPlain'   : 'Простой текст',
			'kindPHP'         : 'Исходник PHP',
			'kindCSS'         : 'Таблицы стилей CSS',
			'kindHTML'        : 'Документ HTML',
			'kindJS'          : 'Исходник Javascript',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'Исходник C',
			'kindCHeader'     : 'Заголовочный файл C',
			'kindCPP'         : 'Исходник C++',
			'kindCPPHeader'   : 'Заголовочный файл C++',
			'kindShell'       : 'Скрипт Unix shell',
			'kindPython'      : 'Исходник Python',
			'kindJava'        : 'Исходник Java',
			'kindRuby'        : 'Исходник Ruby',
			'kindPerl'        : 'Исходник Perl',
			'kindSQL'         : 'Исходник SQL',
			'kindXML'         : 'Документ XML',
			'kindAWK'         : 'Исходник AWK',
			'kindCSV'         : 'Текст с разделителями',
			'kindDOCBOOK'     : 'Документ Docbook XML',
			'kindMarkdown'    : 'Текст Markdown', // added 20.7.2015
			// images
			'kindImage'       : 'Изображение',
			'kindBMP'         : 'Изображение BMP',
			'kindJPEG'        : 'Изображение JPEG',
			'kindGIF'         : 'Изображение GIF',
			'kindPNG'         : 'Изображение PNG',
			'kindTIFF'        : 'Изображение TIFF',
			'kindTGA'         : 'Изображение TGA',
			'kindPSD'         : 'Изображение Adobe Photoshop',
			'kindXBITMAP'     : 'Изображение X bitmap',
			'kindPXM'         : 'Изображение Pixelmator',
			// media
			'kindAudio'       : 'Аудио файл',
			'kindAudioMPEG'   : 'Аудио MPEG',
			'kindAudioMPEG4'  : 'Аудио MPEG-4',
			'kindAudioMIDI'   : 'Аудио MIDI',
			'kindAudioOGG'    : 'Аудио Ogg Vorbis',
			'kindAudioWAV'    : 'Аудио WAV',
			'AudioPlaylist'   : 'Плейлист MP3',
			'kindVideo'       : 'Видео файл',
			'kindVideoDV'     : 'Видео DV',
			'kindVideoMPEG'   : 'Видео MPEG',
			'kindVideoMPEG4'  : 'Видео MPEG-4',
			'kindVideoAVI'    : 'Видео AVI',
			'kindVideoMOV'    : 'Видео Quick Time',
			'kindVideoWM'     : 'Видео Windows Media',
			'kindVideoFlash'  : 'Видео Flash',
			'kindVideoMKV'    : 'Видео Matroska',
			'kindVideoOGG'    : 'Видео Ogg'
		}
	};
}));

