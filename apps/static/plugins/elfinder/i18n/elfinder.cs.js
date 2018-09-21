/**
 * Czech translation
 * @author Jay Gridley <gridley.jay@hotmail.com>
 * @author RobiNN <kelcakrobo@gmail.com>
 * @version 2018-05-05
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
	elFinder.prototype.i18.cs = {
		translator : 'Jay Gridley &lt;gridley.jay@hotmail.com&gt;, RobiNN &lt;kelcakrobo@gmail.com&gt;',
		language   : 'Čeština',
		direction  : 'ltr',
		dateFormat : 'd. m. Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Chyba',
			'errUnknown'           : 'Neznámá chyba.',
			'errUnknownCmd'        : 'Neznámý příkaz.',
			'errJqui'              : 'Nedostačující konfigurace jQuery UI. Musí být zahrnuty komponenty Selectable, Draggable a Droppable.',
			'errNode'              : 'elFinder vyžaduje vytvořený DOM Elementu.',
			'errURL'               : 'Chybná konfigurace elFinderu! Není nastavena hodnota URL.',
			'errAccess'            : 'Přístup zamítnut.',
			'errConnect'           : 'Nepodařilo se připojit k backendu.',
			'errAbort'             : 'Připojení zrušeno.',
			'errTimeout'           : 'Vypšel limit pro připojení.',
			'errNotFound'          : 'Backend nenalezen.',
			'errResponse'          : 'Nesprávná odpověď backendu.',
			'errConf'              : 'Nepsrávná konfigurace backendu.',
			'errJSON'              : 'PHP modul JSON není nainstalován.',
			'errNoVolumes'         : 'Není dostupný čitelný oddíl.',
			'errCmdParams'         : 'Nesprávné parametry příkazu "$1".',
			'errDataNotJSON'       : 'Data nejsou ve formátu JSON.',
			'errDataEmpty'         : 'Data jsou prázdná.',
			'errCmdReq'            : 'Dotaz backendu vyžaduje název příkazu.',
			'errOpen'              : 'Chyba při otevírání "$1".',
			'errNotFolder'         : 'Objekt není složka.',
			'errNotFile'           : 'Objekt není soubor.',
			'errRead'              : 'Chyba při čtení "$1".',
			'errWrite'             : 'Chyba při zápisu do "$1".',
			'errPerm'              : 'Přístup odepřen.',
			'errLocked'            : '"$1" je uzamčený a nemůže být přejmenován, přesunut nebo smazán.',
			'errExists'            : 'Soubor s názvem "$1" již existuje.',
			'errInvName'           : 'Nesprávný název souboru.',
			'errInvDirname'        : 'Neplatný název adresáře.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Složka nenalezena.',
			'errFileNotFound'      : 'Soubor nenalezen.',
			'errTrgFolderNotFound' : 'Cílová složka "$1" nenalezena.',
			'errPopup'             : 'Prohlížeč zabránil otevření vyskakovacího okna. K otevření souboru, povolte vyskakovací okno v prohlížeči.',
			'errMkdir'             : 'Nepodařilo se vytvořit složku "$1".',
			'errMkfile'            : 'Nepodařilo se vytvořit soubor "$1".',
			'errRename'            : 'Nepodařilo se přejmenovat "$1".',
			'errCopyFrom'          : 'Kopírování souborů z oddílu "$1" není povoleno.',
			'errCopyTo'            : 'Kopírování souborů do oddílu "$1" není povoleno.',
			'errMkOutLink'         : 'Nelze vytvořit odkaz mimo kořenového svazku.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Chyba nahrávání.',  // old name - errUploadCommon
			'errUploadFile'        : 'Nepodařilo se nahrát "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Nejsou vybrány žádné soubory k nahrání.',
			'errUploadTotalSize'   : 'Překročena maximální povolená velikost dat.', // old name - errMaxSize
			'errUploadFileSize'    : 'Překročena maximální povolená velikost souboru.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Nepovolený typ souboru.',
			'errUploadTransfer'    : '"$1" chyba přenosu.',
			'errUploadTemp'        : 'Nelze vytvořit dočasný soubor pro upload.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Objekt "$1" v tomto umístění již existuje a nelze jej nahradit s jiným typem objektu.', // new
			'errReplace'           : 'Nelze nahradit "$1".',
			'errSave'              : '"$1" nelze uložit.',
			'errCopy'              : '"$1" nelze zkopírovat.',
			'errMove'              : '"$1" nelze přemístit.',
			'errCopyInItself'      : '"$1" nelze zkopírovat do sebe sama.',
			'errRm'                : '"$1" nelze odstranit.',
			'errTrash'             : 'Nelze se dostat do koše.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Nelze odstranit zdrojový soubor(y).',
			'errExtract'           : 'Nelze extrahovat soubory z "$1".',
			'errArchive'           : 'Nelze vytvořit archív.',
			'errArcType'           : 'Nepodporovaný typ archívu.',
			'errNoArchive'         : 'Soubor není archív nebo má nepodporovaný formát.',
			'errCmdNoSupport'      : 'Backend tento příkaz nepodporuje.',
			'errReplByChild'       : 'Složka "$1" nemůže být nahrazena souborem, který sama obsahuje.',
			'errArcSymlinks'       : 'Z bezpečnostních důvodů je zakázáno rozbalit archívy obsahující symlinky.', // edited 24.06.2012
			'errArcMaxSize'        : 'Soubory archívu překračují maximální povolenou velikost.',
			'errResize'            : 'Nepodařilo se změnit velikost obrázku "$1".',
			'errResizeDegree'      : 'Neplatný stupeň rotace.',  // added 7.3.2013
			'errResizeRotate'      : 'Nelze otočit obrázek.',  // added 7.3.2013
			'errResizeSize'        : 'Neplatná velikost obrázku.',  // added 7.3.2013
			'errResizeNoChange'    : 'Velikost obrazu se nezmění.',  // added 7.3.2013
			'errUsupportType'      : 'Nepodporovaný typ souboru.',
			'errNotUTF8Content'    : 'Soubor "$1" nemá ani obsah kódovaný v UTF-8 a nelze změnit.',  // added 9.11.2011
			'errNetMount'          : 'Není možné se připojit "$ 1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Nepodporovaný protokol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Připojení se nezdařilo.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Hostitel se vyžaduje.', // added 18.04.2012
			'errSessionExpires'    : 'Relace byla ukončena z důvodu nečinnosti.',
			'errCreatingTempDir'   : 'Nelze vytvořit dočasný adresář: "$1"',
			'errFtpDownloadFile'   : 'Nelze stáhnout soubor z FTP: "$1"',
			'errFtpUploadFile'     : 'Nelze nahrát soubor na FTP: "$1"',
			'errFtpMkdir'          : 'Nepodařilo se vytvořit vzdálený adresář na FTP: "$1"',
			'errArchiveExec'       : 'Při archivaci do souboru došlo k chybě: "$1"',
			'errExtractExec'       : 'Chyba při extrahování souboru: "$1"',
			'errNetUnMount'        : 'Nepodařilo se odpojit', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Nelze převést na UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Chcete-li nahrát složku, zkuste moderní prohlížeč.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Vypršení časového limitu při hledání "$1". Je částečně výsledkem hledání.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Opětovné povolení je nutné.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Maximální počet volitelných předmětů je $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Nelze obnovit z koše. Nelze identifikovat cíl obnovení.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Editor tohoto typu souboru nebyl nalezen.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Došlo k chybě na straně serveru.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Nelze vyprázdnit složku "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Vytvořit archív',
			'cmdback'      : 'Zpět',
			'cmdcopy'      : 'Kopírovat',
			'cmdcut'       : 'Vyjmout',
			'cmddownload'  : 'Stáhnout',
			'cmdduplicate' : 'Duplikovat',
			'cmdedit'      : 'Upravit soubor',
			'cmdextract'   : 'Rozbalit archív',
			'cmdforward'   : 'Vpřed',
			'cmdgetfile'   : 'Vybrat soubory',
			'cmdhelp'      : 'O softwaru',
			'cmdhome'      : 'Domů',
			'cmdinfo'      : 'Zobrazit informace',
			'cmdmkdir'     : 'Nová složka',
			'cmdmkdirin'   : 'Do nové složky', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nový soubor',
			'cmdopen'      : 'Otevřít',
			'cmdpaste'     : 'Vložit',
			'cmdquicklook' : 'Náhled',
			'cmdreload'    : 'Obnovit',
			'cmdrename'    : 'Přejmenovat',
			'cmdrm'        : 'Smazat',
			'cmdtrash'     : 'Do koše', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Obnovit', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Najít soubory',
			'cmdup'        : 'Přejít do nadřazené složky',
			'cmdupload'    : 'Nahrát soubor(y)',
			'cmdview'      : 'Zobrazit',
			'cmdresize'    : 'Změnit velikost',
			'cmdsort'      : 'Seřadit',
			'cmdnetmount'  : 'Připojit síťovou jednotku', // added 18.04.2012
			'cmdnetunmount': 'Odpojit', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Umístění', // added 28.12.2014
			'cmdchmod'     : 'Změnit režim', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Otevření složky', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Obnovení šířku sloupce', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Celá obrazovka', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Posouvat', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Vyprázdnit složku', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Krok zpět', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Udělat to znovu', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Preference', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Vyberat vše', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Nic nevyberať', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Invertovat výběr', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Otevři v novém okně', // from v2.1.38 added 3.4.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Zavřít',
			'btnSave'   : 'Uložit',
			'btnRm'     : 'Odstranit',
			'btnApply'  : 'Použít',
			'btnCancel' : 'Zrušit',
			'btnNo'     : 'Ne',
			'btnYes'    : 'Ano',
			'btnMount'  : 'Připojit',  // added 18.04.2012
			'btnApprove': 'Přejít do části 1 $ & schválit', // from v2.1 added 26.04.2012
			'btnUnmount': 'Odpojit', // from v2.1 added 30.04.2012
			'btnConv'   : 'Převést', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Tu',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Médium',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Všechno',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME typ', // from v2.1 added 22.5.2015
			'btnFileName':'Název souboru',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Uložit & zavřít', // from v2.1 added 12.6.2015
			'btnBackup' : 'Zálohovat', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Přejmenovat',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Přejmenovat vše', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Předch ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Další ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Uložit jako', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Otevírání složky',
			'ntffile'     : 'Otevírání souboru',
			'ntfreload'   : 'Obnovování obsahu složky',
			'ntfmkdir'    : 'Vytváření složky',
			'ntfmkfile'   : 'Vytváření souborů',
			'ntfrm'       : 'Vymazání položek',
			'ntfcopy'     : 'Kopírování položek',
			'ntfmove'     : 'Přemístění položek',
			'ntfprepare'  : 'Kontrola existujících položek',
			'ntfrename'   : 'Přejmenovávání souborů',
			'ntfupload'   : 'Nahrávání souborů',
			'ntfdownload' : 'Stahování souborů',
			'ntfsave'     : 'Ukládání souborů',
			'ntfarchive'  : 'Vytváření archívu',
			'ntfextract'  : 'Rozbalování souborů z archívu',
			'ntfsearch'   : 'Vyhledávání souborů',
			'ntfresize'   : 'Změna velikosti obrázků',
			'ntfsmth'     : 'Čekejte prosím...',
			'ntfloadimg'  : 'Načítání obrázků',
			'ntfnetmount' : 'Připojení síťového média', // added 18.04.2012
			'ntfnetunmount': 'Odpojení síťového média', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Získejte rozměr obrazu', // added 20.05.2013
			'ntfreaddir'  : 'Přečtěte si informace o složce', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Získejte adresu URL odkazu', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Změna souboru', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Zkontrolujte název nahravaného souboru', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Vytvořit soubor ke stažení', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Získání informací o cestě', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Zpracování nahraného souboru', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Hodit do koše', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Obnova z koše', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Kontrola cílové složky', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Zrušit  předchozí operaci', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Obnovit předchozí zrušení', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Koš', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'neznámý',
			'Today'       : 'Dnes',
			'Yesterday'   : 'Včera',
			'msJan'       : 'Led',
			'msFeb'       : 'Úno',
			'msMar'       : 'Bře',
			'msApr'       : 'Dub',
			'msMay'       : 'Kvě',
			'msJun'       : 'Čer',
			'msJul'       : 'Čec',
			'msAug'       : 'Srp',
			'msSep'       : 'Zář',
			'msOct'       : 'Říj',
			'msNov'       : 'Lis',
			'msDec'       : 'Pro',
			'January'     : 'Leden',
			'February'    : 'Únor',
			'March'       : 'Březen',
			'April'       : 'Duben',
			'May'         : 'Květen',
			'June'        : 'Červen',
			'July'        : 'Červenec',
			'August'      : 'Srpen',
			'September'   : 'Září',
			'October'     : 'Říjen',
			'November'    : 'Listopad',
			'December'    : 'Prosinec',
			'Sunday'      : 'Neděle',
			'Monday'      : 'Pondělí',
			'Tuesday'     : 'Úterý',
			'Wednesday'   : 'Středa',
			'Thursday'    : 'Čtvrtek',
			'Friday'      : 'Pátek',
			'Saturday'    : 'Sobota',
			'Sun'         : 'Ne',
			'Mon'         : 'Po',
			'Tue'         : 'Út',
			'Wed'         : 'St',
			'Thu'         : 'Čt',
			'Fri'         : 'Pá',
			'Sat'         : 'So',

			/******************************** sort variants ********************************/
			'sortname'          : 'dle jména',
			'sortkind'          : 'dle typu',
			'sortsize'          : 'dle velikosti',
			'sortdate'          : 'dle data',
			'sortFoldersFirst'  : 'Napřed složky',
			'sortperm'          : 'dle povolení', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'dle módu',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'dle majitele',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'dle skupiny',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Také stromové zobrazení',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'Nový textový soubor.txt', // added 10.11.2015
			'untitled folder'   : 'Nová složka',   // added 10.11.2015
			'Archive'           : 'Nový archiv',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Požadováno potvrzení',
			'confirmRm'       : 'Opravdu chcete odstranit tyto soubory?<br/>Operace nelze vrátit!',
			'confirmRepl'     : 'Nahradit staré soubory novými?',
			'confirmRest'     : 'Nahradit stávající položku položkou z koše?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Není v UTF-8, převést do UTF-8?<br/>Obsah po převodu se stává UTF-8.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Kódování tohoto souboru nemoholo rozpoznán. Pro úpravy je třeba dočasně převést do kódování UTF-8.<br/>Prosím, vyberte kódování znaků souboru.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Byl změněn.<br/>Pokud obsahuje neuložené změny, dojde ke ztrátě práce.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Opravdu chcete položky přesunout do koše?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Pro všechny',
			'name'            : 'Název',
			'size'            : 'Velikost',
			'perms'           : 'Práva',
			'modify'          : 'Upravený',
			'kind'            : 'Typ',
			'read'            : 'čtení',
			'write'           : 'zápis',
			'noaccess'        : 'přístup odepřen',
			'and'             : 'a',
			'unknown'         : 'neznámý',
			'selectall'       : 'Vybrat všechny položky',
			'selectfiles'     : 'Vybrat položku(y)',
			'selectffile'     : 'Vybrat první položku',
			'selectlfile'     : 'Vybrat poslední položku',
			'viewlist'        : 'Seznam',
			'viewicons'       : 'Ikony',
			'places'          : 'Místa',
			'calc'            : 'Vypočítat',
			'path'            : 'Cesta',
			'aliasfor'        : 'Zástupce pro',
			'locked'          : 'Uzamčený',
			'dim'             : 'Rozměry',
			'files'           : 'Soubory',
			'folders'         : 'Složky',
			'items'           : 'Položky',
			'yes'             : 'ano',
			'no'              : 'ne',
			'link'            : 'Odkaz',
			'searcresult'     : 'Výsledky hledání',
			'selected'        : 'vybrané položky',
			'about'           : 'O softwaru',
			'shortcuts'       : 'Zkratky',
			'help'            : 'Nápověda',
			'webfm'           : 'Webový správce souborů',
			'ver'             : 'Verze',
			'protocolver'     : 'verze protokolu',
			'homepage'        : 'Domovská stránka projektu',
			'docs'            : 'Dokumentace',
			'github'          : 'Najdete nás na Gitgube',
			'twitter'         : 'Následujte nás na Twitteri',
			'facebook'        : 'Připojte se k nám na Facebooku',
			'team'            : 'Tým',
			'chiefdev'        : 'séf vývojářů',
			'developer'       : 'vývojár',
			'contributor'     : 'spolupracovník',
			'maintainer'      : 'údržba',
			'translator'      : 'překlad',
			'icons'           : 'Ikony',
			'dontforget'      : 'a nezapomeňte si vzít plavky',
			'shortcutsof'     : 'Zkratky nejsou povoleny',
			'dropFiles'       : 'Sem přetáhněte soubory',
			'or'              : 'nebo',
			'selectForUpload' : 'Vyberte soubory',
			'moveFiles'       : 'Přesunout sobory',
			'copyFiles'       : 'Zkopírovat soubory',
			'restoreFiles'    : 'Obnovit položky', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Odstranit z míst',
			'aspectRatio'     : 'Poměr stran',
			'scale'           : 'Měřítko',
			'width'           : 'Šířka',
			'height'          : 'Výška',
			'resize'          : 'Změnit vel.',
			'crop'            : 'Ořezat',
			'rotate'          : 'Otočit',
			'rotate-cw'       : 'Otočit o +90 stupňů',
			'rotate-ccw'      : 'Otočit o -90 stupňů',
			'degree'          : ' stupňů',
			'netMountDialogTitle' : 'Připojení síťového média', // added 18.04.2012
			'protocol'            : 'Protokol', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'Uživatel', // added 18.04.2012
			'pass'                : 'Heslo', // added 18.04.2012
			'confirmUnmount'      : 'Chcete odpojit $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Přemístěte nebo přesuňte soubory z prohlížeče', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Zde přemístěte nebo přesuňte soubory a adresy URL', // from v2.1 added 07.04.2014
			'encoding'        : 'Kódování', // from v2.1 added 19.12.2014
			'locale'          : 'Lokalizce',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Cíl: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Vyhledávání podle vstupního MIME typu', // from v2.1 added 22.5.2015
			'owner'           : 'Majitel', // from v2.1 added 20.6.2015
			'group'           : 'Skupina', // from v2.1 added 20.6.2015
			'other'           : 'Ostatní', // from v2.1 added 20.6.2015
			'execute'         : 'Spustit', // from v2.1 added 20.6.2015
			'perm'            : 'Povolení', // from v2.1 added 20.6.2015
			'mode'            : 'Režim', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Složka je prázdná', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Složka je prázdná, přesunout nebo zkontrolovat položky', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Složka je prázdná, dlouhim kliknutím přidáte položky', // from v2.1.6 added 30.12.2015
			'quality'         : 'Kvalita', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Automatická synchronizace',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Přesunout nahoru',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Získat URL odkaz', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Vybrané položky ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID složky', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Povolit přístup offline', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Znovu ověřit', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Načítání...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Otevření více souborů', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Pokoušíte se otevřít soubor $1. Chcete jej otevřít v prohlížeči?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Výsledky hledání jsou prázdné', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Upravujete soubor.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Vybrali jste $1 položky.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Máte $1 položky v schránce.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Inkrementální hledání je pouze z aktuálního zobrazení.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Obnovit', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 kompletní', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Kontextové menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Otáčení stránky', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Kořeny média', // from v2.1.16 added 16.9.2016
			'reset'           : 'Reset', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Barva pozadí', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Výběr barvy', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px mřížka', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Povoleno', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Zakázáno', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Výsledky hledání jsou prázdné v aktuálním zobrazení.\\Stisknutím tlačítka [Enter] rozšíříte vyhledávání cíle.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Výsledky vyhledávání prvního listu jsou v aktuálním zobrazení prázdné.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Nápis textu', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 minut zůstává', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Otevřít pomocí zvoleného kódování', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Uložit s vybraným kódováním', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Vyberte složku', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Hledání prvního listu', // from v2.1.23 added 24.3.2017
			'presets'         : 'Předvolby', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Je to příliš mnoho položek, takže se nemohou dostat do koše.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Textarea', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Vyprázdnit složku "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'Ve složce "$1" nejsou žádné položky.', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preference', // from v2.1.26 added 28.6.2017
			'language'        : 'Nastavte jazyk', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Inicializujte nastavení uložená v tomto prohlížeči', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Nastavení panelu nástrojů', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '...$1 znaků zbývá.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Součet', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Hrubá velikost souboru', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Zaměření na prvek dialogu s mouseover',  // from v2.1.30 added 2.11.2017
			'select'          : 'Vybrat', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Akce při vybraném souboru', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Otevřít pomocí naposledy použitého editoru', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Obrátit výběr položek', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Opravdu chcete přejmenovat $1 vybraných položek, jako například $2<br/>Není to možné vrátit zpět!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Batch přejmenování', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Číslo', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Přidat předponu', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Přidat příponu', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Změnit příponu', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Nastavení sloupců (Zobrazení seznamu)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Všechny změny se okamžitě projeví v archivu.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Jakékoliv změny se nebudou odrážet, dokud nebude tento svazek odpojen.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'Následující svazky namontované na tomto svazku jsou také odpojeny. Opravdu ji odpojíte?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Informace o výběru', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algoritmy pro zobrazení hashování souborů', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Informační položky (panel s informacemi o výběru)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Dalším stisknutím opustíte.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Panel nástrojů', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Pracovní prostor', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Dialog', // from v2.1.38 added 4.4.2018
			'all'             : 'Všechno', // from v2.1.38 added 4.4.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Neznámý',
			'kindRoot'        : 'Kořen média', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Složka',
			'kindSelects'     : 'Výběry', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Zlomený alias',
			// applications
			'kindApp'         : 'Aplikace',
			'kindPostscript'  : 'Dokument Postscriptu',
			'kindMsOffice'    : 'Dokument Microsoft Office',
			'kindMsWord'      : 'Dokument Microsoft Word',
			'kindMsExcel'     : 'Dokument Microsoft Excel',
			'kindMsPP'        : 'Prezentace Microsoft Powerpoint',
			'kindOO'          : 'Otevřít dokument Office',
			'kindAppFlash'    : 'Flash aplikace',
			'kindPDF'         : 'PDF',
			'kindTorrent'     : 'Soubor BitTorrent',
			'kind7z'          : 'Archív 7z',
			'kindTAR'         : 'Archív TAR',
			'kindGZIP'        : 'Archív GZIP',
			'kindBZIP'        : 'Archív BZIP',
			'kindXZ'          : 'Archív XZ',
			'kindZIP'         : 'Archív ZIP',
			'kindRAR'         : 'Archív RAR',
			'kindJAR'         : 'Soubor Java JAR',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM balíček',
			// texts
			'kindText'        : 'Textový dokument',
			'kindTextPlain'   : 'Čistý text',
			'kindPHP'         : 'PHP zdrojový kód',
			'kindCSS'         : 'Kaskádové styly',
			'kindHTML'        : 'HTML dokument',
			'kindJS'          : 'Javascript zdrojový kód',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C zdrojový kód',
			'kindCHeader'     : 'C hlavička',
			'kindCPP'         : 'C++ zdrojový kód',
			'kindCPPHeader'   : 'C++ hlavička',
			'kindShell'       : 'Unix shell skript',
			'kindPython'      : 'Python zdrojový kód',
			'kindJava'        : 'Java zdrojový kód',
			'kindRuby'        : 'Ruby zdrojový kód',
			'kindPerl'        : 'Perl skript',
			'kindSQL'         : 'SQL zdrojový kód',
			'kindXML'         : 'Dokument XML',
			'kindAWK'         : 'AWK zdrojový kód',
			'kindCSV'         : 'CSV',
			'kindDOCBOOK'     : 'Docbook XML dokument',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'Obrázek',
			'kindBMP'         : 'Obrázek BMP',
			'kindJPEG'        : 'Obrázek JPEG',
			'kindGIF'         : 'Obrázek GIF',
			'kindPNG'         : 'Obrázek PNG',
			'kindTIFF'        : 'Obrázek TIFF',
			'kindTGA'         : 'Obrázek TGA',
			'kindPSD'         : 'Obrázek Adobe Photoshop',
			'kindXBITMAP'     : 'Obrázek X bitmapa',
			'kindPXM'         : 'Obrázek Pixelmator',
			// media
			'kindAudio'       : 'Audio sobory',
			'kindAudioMPEG'   : 'MPEG audio',
			'kindAudioMPEG4'  : 'MPEG-4 audio',
			'kindAudioMIDI'   : 'MIDI audio',
			'kindAudioOGG'    : 'Ogg Vorbis audio',
			'kindAudioWAV'    : 'WAV audio',
			'AudioPlaylist'   : 'MP3 playlist',
			'kindVideo'       : 'Video sobory',
			'kindVideoDV'     : 'DV video',
			'kindVideoMPEG'   : 'MPEG video',
			'kindVideoMPEG4'  : 'MPEG-4 video',
			'kindVideoAVI'    : 'AVI video',
			'kindVideoMOV'    : 'Quick Time video',
			'kindVideoWM'     : 'Windows Media video',
			'kindVideoFlash'  : 'Flash video',
			'kindVideoMKV'    : 'Matroska video',
			'kindVideoOGG'    : 'Ogg video'
		}
	};
}));

