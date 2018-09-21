/**
 * Slovak translation
 * @author RobiNN <kelcakrobo@gmail.com>
 * @author Jakub Ďuraš <jkblmr@gmail.com>
 * @version 2018-06-09
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
	elFinder.prototype.i18.sk = {
		translator : 'RobiNN &lt;kelcakrobo@gmail.com&gt;, Jakub Ďuraš &lt;jkblmr@gmail.com&gt;',
		language   : 'Slovenčina',
		direction  : 'ltr',
		dateFormat : 'd.m.Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Chyba',
			'errUnknown'           : 'Neznáma chyba.',
			'errUnknownCmd'        : 'Neznámy príkaz.',
			'errJqui'              : 'Nesprávna jQuery UI konfigurácia. Selectable, draggable a droppable musia byť načítané.',
			'errNode'              : 'elFinder vyžaduje vytvorenie DOM elementu.',
			'errURL'               : 'Nesprávna elFinder konfigurácia! URL nie je definovaná.',
			'errAccess'            : 'Prístup zamietnutý.',
			'errConnect'           : 'Nepodarilo sa pripojiť do backendu.',
			'errAbort'             : 'Spojenie bolo prerušené.',
			'errTimeout'           : 'Časový limit vypršal.',
			'errNotFound'          : 'Backend nenájdený.',
			'errResponse'          : 'Nesprávna backend odpoveď.',
			'errConf'              : 'Nesprávna backend konfigurácia.',
			'errJSON'              : 'PHP JSON modul nie je nainštalovaný.',
			'errNoVolumes'         : 'Nie sú dostupné žiadne čitateľné média.',
			'errCmdParams'         : 'Nesprávne parametre pre príkaz "$1".',
			'errDataNotJSON'       : 'Dáta nie sú formátu JSON.',
			'errDataEmpty'         : 'Prázdne dáta.',
			'errCmdReq'            : 'Backend požiadavka požaduje názov príkazu.',
			'errOpen'              : 'Nie je možné otvoriť "$1".',
			'errNotFolder'         : 'Objekt nie je priečinok.',
			'errNotFile'           : 'Objekt nie je súbor.',
			'errRead'              : 'Nie je možné prečítať "$1".',
			'errWrite'             : 'Nie je možné písať do "$1".',
			'errPerm'              : 'Prístup zamietnutý.',
			'errLocked'            : '"$1" je uzamknutý a nemôže byť premenovaný, presunutý alebo odstránený.',
			'errExists'            : 'Položka s názvom "$1" už existuje.',
			'errInvName'           : 'Neplatný názov súboru.',
			'errInvDirname'        : 'Neplatný názov priečinka.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Priečinok nebol nájdený.',
			'errFileNotFound'      : 'Súbor nenájdený.',
			'errTrgFolderNotFound' : 'Cieľový priečinok "$1" sa nenašiel.',
			'errPopup'             : 'Prehliadač zabránil otvoreniu vyskakovacieho okna. Pre otvorenie súboru povoľte vyskakovacie okná.',
			'errMkdir'             : 'Nepodarilo sa vytvoriť priečinok "$1".',
			'errMkfile'            : 'Nepodarilo sa vytvoriť súbor "$1".',
			'errRename'            : 'Nepodarilo sa premenovať "$1".',
			'errCopyFrom'          : 'Kopírovanie súborov z média "$1" nie je povolené.',
			'errCopyTo'            : 'Kopírovanie súborov na médium "$1" nie je povolené.',
			'errMkOutLink'         : 'Nie je možné vytvoriť odkaz mimo koreňového zväzku.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Chyba pri nahrávaní.',  // old name - errUploadCommon
			'errUploadFile'        : 'Nepodarilo sa nahrať "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Neboli nájdené žiadne súbory na nahranie.',
			'errUploadTotalSize'   : 'Dáta prekračujú maximálnu povolenú veľkosť.', // old name - errMaxSize
			'errUploadFileSize'    : 'Súbor prekračuje maximálnu povolenú veľkosť.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Nepovolený typ súboru.',
			'errUploadTransfer'    : 'Problém s nahrávaním "$1".',
			'errUploadTemp'        : 'Nepodarilo sa vytvoriť dočasný súbor na nahranie.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Objekt "$1" na tomto mieste už existuje a nemôže byť nahradený objektom iného typu.', // new
			'errReplace'           : 'Nie je možné nahradiť "$1".',
			'errSave'              : 'Nie je možné uložiť "$1".',
			'errCopy'              : 'Nie je možné kopírovať "$1".',
			'errMove'              : 'Nie je možné preniesť "$1".',
			'errCopyInItself'      : 'Nie je možné kopírovať "$1" do seba.',
			'errRm'                : 'Nie je možné vymazať "$1".',
			'errTrash'             : 'Nie je možné presunúť do koša.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Nie je možné odstrániť zdrojový/é súbor/y.',
			'errExtract'           : 'Nie je možné extrahovať súbory z "$1".',
			'errArchive'           : 'Nie je možné vytvoriť archív.',
			'errArcType'           : 'Nepodporovaný typ archívu.',
			'errNoArchive'         : 'Súbor nie je archív alebo má nepodporovaný typ archívu.',
			'errCmdNoSupport'      : 'Backend nepodporuje tento príkaz.',
			'errReplByChild'       : 'Priečinok "$1" nemôže byť nahradený položkou, ktorú už obsahuje.',
			'errArcSymlinks'       : 'Z bezpečnostných dôvodov bolo zakázané extrahovanie archívov obsahujúcich symlinky, alebo súborov s nepovolenými názvami.', // edited 24.06.2012
			'errArcMaxSize'        : 'Súbory archívu prekračujú maximálnu povolenú veľkosť.',
			'errResize'            : 'Nie je možné zmeniť veľkosť "$1".',
			'errResizeDegree'      : 'Neplatný stupeň otočenia.',  // added 7.3.2013
			'errResizeRotate'      : 'Nie je možné otočiť obrázok.',  // added 7.3.2013
			'errResizeSize'        : 'Neplatná veľkosť obrázka.',  // added 7.3.2013
			'errResizeNoChange'    : 'Veľkosť obrázku sa nezmenila.',  // added 7.3.2013
			'errUsupportType'      : 'Nepodporovaný typ súboru.',
			'errNotUTF8Content'    : 'Súbor "$1" nie je v UTF-8 a nemôže byť upravený.',  // added 9.11.2011
			'errNetMount'          : 'Nie je možné pripojiť "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Nepodporovaný protokol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Pripájanie zlyhalo.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Hosť je požadovaný.', // added 18.04.2012
			'errSessionExpires'    : 'Vaša relácia vypršala kvôli nečinnosti.',
			'errCreatingTempDir'   : 'Nepodarilo sa vytvoriť dočasný adresár: "$1"',
			'errFtpDownloadFile'   : 'Nie je možné stiahnuť súbor z FTP: "$1"',
			'errFtpUploadFile'     : 'Nie je možné nahrať súbor na FTP: "$1"',
			'errFtpMkdir'          : 'Nedá sa vytvoriť vzdialený adresár na FTP: "$1"',
			'errArchiveExec'       : 'Chyba pri archivácii súborov: "$1"',
			'errExtractExec'       : 'Chyba pri extrahovaní súborov: "$1"',
			'errNetUnMount'        : 'Nepodarilo sa odpojiť', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Nie je prevoditeľný na UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Vyskúšajte moderný prehliadač, ak chcete nahrať priečinok.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Vypršal časový limit pri hľadaní "$1". Výsledok vyhľadávania je čiastočný.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Opätovné povolenie je potrebné.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Maximálny počet voliteľných položiek je $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Nepodarilo sa obnoviť z koša. Cieľ obnovenia nie je možné identifikovať.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Editor tohto typu súboru nebol nájdený.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Vyskytla sa chyba na strane servera.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Nepodarilo sa vyprázdniť priečinok "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Vytvoriť archív',
			'cmdback'      : 'Späť',
			'cmdcopy'      : 'Kopírovať',
			'cmdcut'       : 'Vystrihnúť',
			'cmddownload'  : 'Stiahnuť',
			'cmdduplicate' : 'Duplikovať',
			'cmdedit'      : 'Upraviť súbor',
			'cmdextract'   : 'Extrahovať súbory z archívu',
			'cmdforward'   : 'Ďalej',
			'cmdgetfile'   : 'Vybrať súbory',
			'cmdhelp'      : 'O tomto softvéri',
			'cmdhome'      : 'Domov',
			'cmdinfo'      : 'Info',
			'cmdmkdir'     : 'Nový priečinok',
			'cmdmkdirin'   : 'Do novej zložky', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nový súbor',
			'cmdopen'      : 'Otvoriť',
			'cmdpaste'     : 'Vložiť',
			'cmdquicklook' : 'Náhľad',
			'cmdreload'    : 'Obnoviť',
			'cmdrename'    : 'Premenovať',
			'cmdrm'        : 'Vymazať',
			'cmdtrash'     : 'Do koša', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Obnoviť', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Nájsť súbory',
			'cmdup'        : 'Prejsť do nadradeného priečinka',
			'cmdupload'    : 'Nahrať súbory',
			'cmdview'      : 'Pozrieť',
			'cmdresize'    : 'Zmeniť veľkosť obrázku',
			'cmdsort'      : 'Zoradiť',
			'cmdnetmount'  : 'Pripojiť sieťové médium', // added 18.04.2012
			'cmdnetunmount': 'Odpojiť', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Do umiestnení', // added 28.12.2014
			'cmdchmod'     : 'Zmeniť režim', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Otvoriť priečinok', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Resetovať šírku stĺpca', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Celá obrazovka', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Posúvať', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Vyprázdniť priečinok', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Krok späť', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Vykonať znova', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Preferencie', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Vybrať všetko', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Nič nevyberať', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Invertovať výber', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Otvoriť v novom okne', // from v2.1.38 added 3.4.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Zavrieť',
			'btnSave'   : 'Uložiť',
			'btnRm'     : 'Vymazať',
			'btnApply'  : 'Použiť',
			'btnCancel' : 'Zrušiť',
			'btnNo'     : 'Nie',
			'btnYes'    : 'Áno',
			'btnMount'  : 'Pripojiť',  // added 18.04.2012
			'btnApprove': 'Ísť na $1 & schváliť', // from v2.1 added 26.04.2012
			'btnUnmount': 'Odpojiť', // from v2.1 added 30.04.2012
			'btnConv'   : 'Previesť', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Tu',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Médium',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Všetko',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME typ', // from v2.1 added 22.5.2015
			'btnFileName':'Názov súboru',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Uložiť & zavrieť', // from v2.1 added 12.6.2015
			'btnBackup' : 'Zálohovať', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Premenovať',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Premenovať všetko', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Predchádzajúce ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Ďalšie ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Uložiť ako', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Otváranie priečinka',
			'ntffile'     : 'Otváranie súboru',
			'ntfreload'   : 'Znovu-načítanie obsahu priečinka',
			'ntfmkdir'    : 'Vytváranie priečinka',
			'ntfmkfile'   : 'Vytváranie súborov',
			'ntfrm'       : 'Vymazanie položiek',
			'ntfcopy'     : 'Kopírovanie položiek',
			'ntfmove'     : 'Premiestnenie položiek',
			'ntfprepare'  : 'Kontrola existujúcich položiek',
			'ntfrename'   : 'Premenovanie súborov',
			'ntfupload'   : 'Nahrávanie súborov',
			'ntfdownload' : 'Sťahovanie súborov',
			'ntfsave'     : 'Uloženie súborov',
			'ntfarchive'  : 'Vytváranie archívu',
			'ntfextract'  : 'Extrahovanie súborov z archívu',
			'ntfsearch'   : 'Vyhľadávanie súborov',
			'ntfresize'   : 'Zmena veľkosti obrázkov',
			'ntfsmth'     : 'Počkajte prosím...',
			'ntfloadimg'  : 'Načítavanie obrázka',
			'ntfnetmount' : 'Pripájanie sieťového média', // added 18.04.2012
			'ntfnetunmount': 'Odpájanie sieťového média', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Získanie rozmeru obrázka', // added 20.05.2013
			'ntfreaddir'  : 'Čítajú sa informácie o priečinku', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Získanie adresy URL odkazu', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Zmena súboru', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Overenie názvu nahravaného súboru', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Vytvorenie súboru na stiahnutie', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Získanie informácií o ceste', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Spracovanie nahraného súboru', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Vhadzovanie do koša', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Vykonávanie obnovy z koša', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Kontrola cieľového priečinka', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Zrušiť predchádzajúcu operáciu', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Obnovenie predchádzajúceho zrušenia', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Kôš', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'neznámy',
			'Today'       : 'Dnes',
			'Yesterday'   : 'Včera',
			'msJan'       : 'Jan',
			'msFeb'       : 'Feb',
			'msMar'       : 'Mar',
			'msApr'       : 'Apr',
			'msMay'       : 'Maj',
			'msJun'       : 'Jun',
			'msJul'       : 'Júl',
			'msAug'       : 'Aug',
			'msSep'       : 'Sep',
			'msOct'       : 'Okt',
			'msNov'       : 'Nov',
			'msDec'       : 'Dec',
			'January'     : 'Január',
			'February'    : 'Február',
			'March'       : 'Marec',
			'April'       : 'Apríl',
			'May'         : 'Máj',
			'June'        : 'Jún',
			'July'        : 'Júl',
			'August'      : 'August',
			'September'   : 'September',
			'October'     : 'Október',
			'November'    : 'November',
			'December'    : 'December',
			'Sunday'      : 'Nedeľa',
			'Monday'      : 'Pondelok',
			'Tuesday'     : 'Utorok',
			'Wednesday'   : 'Streda',
			'Thursday'    : 'Štvrtok',
			'Friday'      : 'Piatok',
			'Saturday'    : 'Sobota',
			'Sun'         : 'Ned',
			'Mon'         : 'Pon',
			'Tue'         : 'Ut',
			'Wed'         : 'Str',
			'Thu'         : 'Štv',
			'Fri'         : 'Pia',
			'Sat'         : 'Sob',

			/******************************** sort variants ********************************/
			'sortname'          : 'podľa názvu',
			'sortkind'          : 'podľa druhu',
			'sortsize'          : 'podľa veľkosti',
			'sortdate'          : 'podľa dátumu',
			'sortFoldersFirst'  : 'Najskôr priečinky',
			'sortperm'          : 'podľa povolenia', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'podľa módu',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'podľa majiteľa',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'podľa skupiny',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Tiež stromové zobrazenie',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'Nový textový dokument.txt', // added 10.11.2015
			'untitled folder'   : 'Nový priečinok',   // added 10.11.2015
			'Archive'           : 'Nový archív',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Potrebné potvrdenie',
			'confirmRm'       : 'Určite chcete vymazať súbory?<br/>Nie je to možné vrátiť späť!',
			'confirmRepl'     : 'Nahradiť starý súbor za nový? (Ak obsahuje priečinky, bude zlúčené. Ak chcete zálohovať a nahradiť, vyberte možnosť Zálohovať.)',
			'confirmRest'     : 'Nahradiť existujúcu položku s položkou v koši?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Nie je v UTF-8<br/>Previesť na UTF-8?<br/>Obsah bude v UTF-8 po uložení konverzie.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Kódovanie tohto súboru nemohlo byť detekované. Pre úpravu dočasne potrebujete previesť na UTF-8 .<br/>Prosím, vyberte kódovanie znakov tohto súboru.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Bol upravený.<br/>Ak zmeny neuložíte, stratíte vykonanú prácu.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Naozaj chcete presunúť položky do koša?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Použiť na všetky',
			'name'            : 'Názov',
			'size'            : 'Veľkosť',
			'perms'           : 'Povolenia',
			'modify'          : 'Zmenené',
			'kind'            : 'Druh',
			'read'            : 'čítať',
			'write'           : 'zapisovať',
			'noaccess'        : 'bez prístupu',
			'and'             : 'a',
			'unknown'         : 'neznámy',
			'selectall'       : 'Vybrať všetky položky',
			'selectfiles'     : 'Vybrať položku(y)',
			'selectffile'     : 'Vybrať prvú položku',
			'selectlfile'     : 'Vybrať poslednú položku',
			'viewlist'        : 'Zoznam',
			'viewicons'       : 'Ikony',
			'viewSmall'       : 'Malé ikony', // from v2.1.39 added 22.5.2018
			'viewMedium'      : 'Stredné ikony', // from v2.1.39 added 22.5.2018
			'viewLarge'       : 'Veľké ikony', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'  : 'Extra veľké ikony', // from v2.1.39 added 22.5.2018
			'places'          : 'Miesta',
			'calc'            : 'Prepočítavanie',
			'path'            : 'Cesta',
			'aliasfor'        : 'Alias pre',
			'locked'          : 'Uzamknuté',
			'dim'             : 'Rozmery',
			'files'           : 'Súbory',
			'folders'         : 'Priečinky',
			'items'           : 'Položky',
			'yes'             : 'áno',
			'no'              : 'nie',
			'link'            : 'Odkaz',
			'searcresult'     : 'Výsledky hľadania',
			'selected'        : 'zvolené položky',
			'about'           : 'O aplikácii',
			'shortcuts'       : 'Skratky',
			'help'            : 'Pomoc',
			'webfm'           : 'Webový správca súborov',
			'ver'             : 'Verzia',
			'protocolver'     : 'verzia protokolu',
			'homepage'        : 'Domovská stránka',
			'docs'            : 'Dokumentácia',
			'github'          : 'Pozri nás na Githube',
			'twitter'         : 'Nasleduj nás na Twitteri',
			'facebook'        : 'Pripoj sa k nám na Facebooku',
			'team'            : 'Tím',
			'chiefdev'        : 'hlavný vývojár',
			'developer'       : 'vývojár',
			'contributor'     : 'prispievateľ',
			'maintainer'      : 'správca',
			'translator'      : 'prekladateľ',
			'icons'           : 'Ikony',
			'dontforget'      : 'a nezabudnite si plavky',
			'shortcutsof'     : 'Skratky nie sú povolené',
			'dropFiles'       : 'Sem pretiahnite súbory',
			'or'              : 'alebo',
			'selectForUpload' : 'Vyberte súbory',
			'moveFiles'       : 'Premiestniť súbory',
			'copyFiles'       : 'Kopírovať súbory',
			'restoreFiles'    : 'Obnoviť položky', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Odstrániť z umiestnení',
			'aspectRatio'     : 'Pomer zobrazenia',
			'scale'           : 'Mierka',
			'width'           : 'Šírka',
			'height'          : 'Výška',
			'resize'          : 'Zmeniť veľkosť',
			'crop'            : 'Orezať',
			'rotate'          : 'Otočiť',
			'rotate-cw'       : 'Otočiť o 90 stupňov (v smere h.r.)',
			'rotate-ccw'      : 'Otočiť o 90 stupňov (proti smeru)',
			'degree'          : '°',
			'netMountDialogTitle' : 'Pripojiť sieťové médium', // added 18.04.2012
			'protocol'            : 'Protokol', // added 18.04.2012
			'host'                : 'Hosť', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'Užívateľ', // added 18.04.2012
			'pass'                : 'Heslo', // added 18.04.2012
			'confirmUnmount'      : 'Naozaj chcete odpojiť $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Premiestnite alebo presuňte súbory z prehliadača', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Tu premiestnite alebo presuňte súbory a adresy URL', // from v2.1 added 07.04.2014
			'encoding'        : 'Kódovanie', // from v2.1 added 19.12.2014
			'locale'          : 'Lokalizácia',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Cieľ: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Vyhľadávanie podľa vstupného MIME typu', // from v2.1 added 22.5.2015
			'owner'           : 'Majiteľ', // from v2.1 added 20.6.2015
			'group'           : 'Skupina', // from v2.1 added 20.6.2015
			'other'           : 'Ostatné', // from v2.1 added 20.6.2015
			'execute'         : 'Spustiť', // from v2.1 added 20.6.2015
			'perm'            : 'Povolenie', // from v2.1 added 20.6.2015
			'mode'            : 'Režim', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Priečinok je prázdny', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Priečinok je prázdny\\A Premiestnite alebo presuňte položky', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Priečinok je prázdny\\A Dlhým kliknutím pridáte položky', // from v2.1.6 added 30.12.2015
			'quality'         : 'Kvalita', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Automatická synchronizácia',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Posunúť nahor',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Získať URL odkaz', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Vybraté položky ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID priečinka', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Povoliť prístup v offline režime', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Znova overiť', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Práve načítava...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Otvorenie viacerých súborov', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Pokúšate sa otvoriť súbor $1. Naozaj ho chcete otvoriť v prehliadači?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Výsledky vyhľadávania sú prázdne v hľadanom cieli.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Je to úprava súboru.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Vybrali ste $1 položky.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Máte $1 položky v schránke.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Prírastkové hľadanie je iba z aktuálneho zobrazenia.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Obnovovanie', // from v2.1.15 added 3.8.2016
			'complete'        : '$1: kompletné', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Kontextové menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Otáčanie stránky', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Korene média', // from v2.1.16 added 16.9.2016
			'reset'           : 'Resetovať', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Farba pozadia', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Výber farby', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px mriežka', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Povolené', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Zakázané', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Výsledky vyhľadávania sú prázdne v aktuálnom zobrazení. Stlačením tlačidla [Enter] rozšírite vyhľadávanie cieľa.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Výsledky vyhľadávania prvého listu sú v aktuálnom zobrazení prázdne.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Nápis textu', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 minút ostáva', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Otvoriť s vybratým kódovaním', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Uložiť s vybratým kódovaním', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Vyberte priečinok', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Hľadanie prvého listu', // from v2.1.23 added 24.3.2017
			'presets'         : 'Presety', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Je to príliš veľa položiek, takže sa nemôže dostať do koša.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Textarea', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Vyprázdniť priečinok "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'V priečinku "$1" nie sú žiadne položky.', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preferencie', // from v2.1.26 added 28.6.2017
			'language'        : 'Nastavenie jazyka', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Inicializujte nastavenia uložené v tomto prehliadači', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Nastavenie panela s nástrojmi', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '...$1 znakov ostáva.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Súčet', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Hrubá veľkosť súboru', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Zameranie na prvok dialógu s mouseover',  // from v2.1.30 added 2.11.2017
			'select'          : 'Vybrať', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Akcia pri vybranom súbore', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Otvoriť pomocou naposledy použitého editora', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Invertovať výber položiek', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Naozaj chcete premenovať $1 vybraných položiek, ako napríklad $2<br/>Nie je to možné vrátiť späť!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Batch premenovanie', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Číslo', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Pridať predponu', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Pridať príponu', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Zmeniť príponu', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Nastavenia stĺpcov (zoznamové zobrazenie)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Všetky zmeny sa okamžite premietnu do archívu.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Akékoľvek zmeny sa neodzrkadľujú, kým sa toto médium neodinštaluje.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'Nasledujúce médium(a) pripojené v tomto médiu je tiež odpojené. Určite ho odpojiť?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Informácie o výbere', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algoritmy na zobrazenie hashu súborov', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Informačné položky (panel s informáciami o výbere)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Opätovným stlačením opustíte.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Panel nástrojov', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Pracovný priestor', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Dialóg', // from v2.1.38 added 4.4.2018
			'all'             : 'Všetko', // from v2.1.38 added 4.4.2018
			'iconSize'        : 'Veľkosť ikony (zobrazenie ikon)', // form v2.1.39 added 7.5.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Neznámy',
			'kindRoot'        : 'Koreň média', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Priečinok',
			'kindSelects'     : 'Výbery', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Porušený alias',
			// applications
			'kindApp'         : 'Aplikácia',
			'kindPostscript'  : 'Postscript dokument',
			'kindMsOffice'    : 'Microsoft Office dokument',
			'kindMsWord'      : 'Microsoft Word dokument',
			'kindMsExcel'     : 'Microsoft Excel dokument',
			'kindMsPP'        : 'Microsoft Powerpoint prezentácia',
			'kindOO'          : 'Open Office dokument',
			'kindAppFlash'    : 'Flashová aplikácia',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent súbor',
			'kind7z'          : '7z archív',
			'kindTAR'         : 'TAR archív',
			'kindGZIP'        : 'GZIP archív',
			'kindBZIP'        : 'BZIP archív',
			'kindXZ'          : 'XZ archív',
			'kindZIP'         : 'ZIP archív',
			'kindRAR'         : 'RAR archív',
			'kindJAR'         : 'Java JAR súbor',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM balík',
			// texts
			'kindText'        : 'Textový document',
			'kindTextPlain'   : 'Obyčajný text',
			'kindPHP'         : 'PHP zdrojový kód',
			'kindCSS'         : 'Cascading style sheet (CSS)',
			'kindHTML'        : 'HTML dokument',
			'kindJS'          : 'Javascript zdrojový kód',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C zdrojový kód',
			'kindCHeader'     : 'C header zdrojový kód',
			'kindCPP'         : 'C++ zdrojový kód',
			'kindCPPHeader'   : 'C++ header zdrojový kód',
			'kindShell'       : 'Unix shell skript',
			'kindPython'      : 'Python zdrojový kód',
			'kindJava'        : 'Java zdrojový kód',
			'kindRuby'        : 'Ruby zdrojový kód',
			'kindPerl'        : 'Perl zdrojový kód',
			'kindSQL'         : 'SQL zdrojový kód',
			'kindXML'         : 'XML dokument',
			'kindAWK'         : 'AWK zdrojový kód',
			'kindCSV'         : 'Čiarkou oddeľované hodnoty',
			'kindDOCBOOK'     : 'Docbook XML dokument',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'Obrázok',
			'kindBMP'         : 'BMP obrázok',
			'kindJPEG'        : 'JPEG obrázok',
			'kindGIF'         : 'GIF obrázok',
			'kindPNG'         : 'PNG obrázok',
			'kindTIFF'        : 'TIFF obrázok',
			'kindTGA'         : 'TGA obrázok',
			'kindPSD'         : 'Adobe Photoshop obrázok',
			'kindXBITMAP'     : 'X bitmap obrázok',
			'kindPXM'         : 'Pixelmator obrázok',
			// media
			'kindAudio'       : 'Zvukový súbor',
			'kindAudioMPEG'   : 'MPEG zvuk',
			'kindAudioMPEG4'  : 'MPEG-4 zvuk',
			'kindAudioMIDI'   : 'MIDI zvuk',
			'kindAudioOGG'    : 'Ogg Vorbis zvuk',
			'kindAudioWAV'    : 'WAV zvuk',
			'AudioPlaylist'   : 'MP3 playlist',
			'kindVideo'       : 'Video súbor',
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

