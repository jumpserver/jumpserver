/**
 * Faroese translation
 * @author Marius Hammer <marius@vrg.fo>
 * @version 2015-12-03
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
	elFinder.prototype.i18.fo = {
		translator : 'Marius Hammer &lt;marius@vrg.fo&gt;',
		language   : 'Faroese',
		direction  : 'ltr',
		dateFormat : 'd.m.Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Villa íkomin',
			'errUnknown'           : 'Ókend villa.',
			'errUnknownCmd'        : 'Ókend boð.',
			'errJqui'              : 'Ógildig jQuery UI konfiguratión. Vælbærar, sum kunnu hálast runt og kunnu sleppast skulu takast við.',
			'errNode'              : 'elFinder krevur DOM Element stovna.',
			'errURL'               : 'Ugyldig elFinder konfiguration! URL stilling er ikki ásett.',
			'errAccess'            : 'Atgongd nokta.',
			'errConnect'           : 'Far ikki samband við backend.',
			'errAbort'             : 'Sambandi avbrotið.',
			'errTimeout'           : 'Sambandi broti av.',
			'errNotFound'          : 'Backend ikki funnið.',
			'errResponse'          : 'Ógildugt backend svar.',
			'errConf'              : 'Ógildugt backend konfiguratión.',
			'errJSON'              : 'PHP JSON modulið er ikki innstallera.',
			'errNoVolumes'         : 'Lesiligar mappur er ikki atkomulig.',
			'errCmdParams'         : 'Ógildigar stillingar fyri kommando "$1".',
			'errDataNotJSON'       : 'Dáta er ikki JSON.',
			'errDataEmpty'         : 'Dáta er tømt.',
			'errCmdReq'            : 'Backend krevur eitt kommando navn.',
			'errOpen'              : 'Kundi ikki opna "$1".',
			'errNotFolder'         : 'Luturin er ikki ein mappa.',
			'errNotFile'           : 'Luturin er ikki ein fíla.',
			'errRead'              : 'Kundi ikki lesa til "$1".',
			'errWrite'             : 'Kundi ikki skriva til "$1".',
			'errPerm'              : 'Atgongd nokta.',
			'errLocked'            : '"$1" er løst og kann ikki umdoybast, flytast ella strikast.',
			'errExists'            : 'Tað finst longu ein fíla við navn "$1".',
			'errInvName'           : 'Ógildugt fíla navn.',
			'errFolderNotFound'    : 'Mappa ikki funnin.',
			'errFileNotFound'      : 'Fíla ikki funnin.',
			'errTrgFolderNotFound' : 'Mappan "$1" bleiv ikke funnin.',
			'errPopup'             : 'Kagin forðaði í at opna eitt popup-vindeyga. Fyri at opna fíluna, aktivera popup-vindeygu í tínum kaga stillingum.',
			'errMkdir'             : '\'Kundi ikki stovna mappu "$1".',
			'errMkfile'            : 'Kundi ikki stovna mappu "$1".',
			'errRename'            : 'Kundi ikki umdoyba "$1".',
			'errCopyFrom'          : 'Kopiering av fílum frá mappuni "$1" er ikke loyvt.',
			'errCopyTo'            : 'Kopiering av fílum til mappuna "$1" er ikke loyvt.',
			'errMkOutLink'         : 'Ikki ført fyri at stovna leinkju til uttanfyri \'volume\' rót.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Innlegginar feilur.',  // old name - errUploadCommon
			'errUploadFile'        : 'Kundi ikki leggja "$1" inn.', // old name - errUpload
			'errUploadNoFiles'     : 'Ongar fílar funnir at leggja inn.',
			'errUploadTotalSize'   : 'Dátain er størri enn mest loyvda støddin.', // old name - errMaxSize
			'errUploadFileSize'    : 'Fíla er størri enn mest loyvda støddin.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Fílu slag ikki góðkent.',
			'errUploadTransfer'    : '"$1" innleggingar feilur.',
			'errUploadTemp'        : 'Ikki ført fyri at gera fyribils fílu fyri innlegging.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Lutur "$1" finst longu á hesum stað og can ikki skiftast út av lutið av øðrum slag.', // new
			'errReplace'           : 'Ikki ført fyri at erstattae "$1".',
			'errSave'              : 'Kundi ikki goyma "$1".',
			'errCopy'              : 'Kundi ikki kopiera "$1".',
			'errMove'              : 'Kundi ikki flyta "$1".',
			'errCopyInItself'      : 'Kundi ikki kopiera "$1" inn í seg sjálva.',
			'errRm'                : 'Kundi ikki strika "$1".',
			'errRmSrc'             : 'Ikki ført fyri at strika keldu fíla(r).',
			'errExtract'           : 'Kundi ikki útpakka fílar frá "$1".',
			'errArchive'           : 'Kundi ikki stovna arkiv.',
			'errArcType'           : 'Arkiv slagið er ikki stuðla.',
			'errNoArchive'         : 'Fílan er ikki eitt arkiv ella er ikki eitt stuðla arkiva slag.',
			'errCmdNoSupport'      : 'Backend stuðlar ikki hesi boð.',
			'errReplByChild'       : 'appan "$1" kann ikki erstattast av einari vøru, hon inniheldur.',
			'errArcSymlinks'       : 'Av trygdarávum grundum, noktaði skipanin at pakka út arkivir ið innihalda symlinks ella fílur við nøvn ið ikki eru loyvd.', // edited 24.06.2012
			'errArcMaxSize'        : 'Arkiv fílar fylla meir enn mest loyvda støddin.',
			'errResize'            : 'Kundi ikki broyta støddina á "$1".',
			'errResizeDegree'      : 'Ógildugt roterings stig.',  // added 7.3.2013
			'errResizeRotate'      : 'Ikki ført fyri at rotera mynd.',  // added 7.3.2013
			'errResizeSize'        : 'Ógildug myndastødd.',  // added 7.3.2013
			'errResizeNoChange'    : 'Mynda stødd ikki broytt.',  // added 7.3.2013
			'errUsupportType'      : 'Ikki stuðla fíla slag.',
			'errNotUTF8Content'    : 'Fílan "$1" er ikki í UTF-8 og kann ikki vera rættað.',  // added 9.11.2011
			'errNetMount'          : 'Kundi ikki "mounta" "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Ikki stuðla protokol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Mount miseydnaðist.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Host kravt.', // added 18.04.2012
			'errSessionExpires'    : 'Tín seta er útgingin vegna óvirkniy.',
			'errCreatingTempDir'   : 'Ikki ført fyri at stovna fyribils fíluskrá: "$1"',
			'errFtpDownloadFile'   : 'Ikki ført fyri at taka fílu niður frá FTP: "$1"',
			'errFtpUploadFile'     : 'Ikki ført fyri at leggja fílu til FTP: "$1"',
			'errFtpMkdir'          : 'Ikki ført fyri at stovna fjar-fílaskrá á FTP: "$1"',
			'errArchiveExec'       : 'Villa íkomin undir arkiveran af fílar: "$1"',
			'errExtractExec'       : 'Villa íkomin undir útpakking af fílum: "$1"',
			'errNetUnMount'        : 'Unable to unmount', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Kann ikki broytast til UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Royn Google Chrome, um tú ynskir at leggja mappu innn.', // from v2.1 added 26.6.2015

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Stovna arkiv',
			'cmdback'      : 'Aftur\'',
			'cmdcopy'      : 'Kopier',
			'cmdcut'       : 'Klipp',
			'cmddownload'  : 'Tak niður',
			'cmdduplicate' : 'Tvífalda',
			'cmdedit'      : 'Rætta fílu',
			'cmdextract'   : 'Pakka út fílar úr arkiv',
			'cmdforward'   : 'Fram',
			'cmdgetfile'   : 'Vel fílar',
			'cmdhelp'      : 'Um hesa software',
			'cmdhome'      : 'Heim',
			'cmdinfo'      : 'Fá upplýsingar',
			'cmdmkdir'     : 'Nýggja mappu',
			'cmdmkfile'    : 'Nýggja tekst fílu',
			'cmdopen'      : 'Opna',
			'cmdpaste'     : 'Set inn',
			'cmdquicklook' : 'Forsýning',
			'cmdreload'    : 'Les inn umaftur',
			'cmdrename'    : 'Umdoyp',
			'cmdrm'        : 'Strika',
			'cmdsearch'    : 'Finn fílar',
			'cmdup'        : 'Eitt stig upp',
			'cmdupload'    : 'Legg fílar inn',
			'cmdview'      : 'Síggj',
			'cmdresize'    : 'Tillaga stødd & Roter',
			'cmdsort'      : 'Raða',
			'cmdnetmount'  : 'Mount network volume', // added 18.04.2012
			'cmdnetunmount': 'Unmount', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Til støð', // added 28.12.2014
			'cmdchmod'     : 'Broytir stíl', // from v2.1 added 20.6.2015

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Lat aftur',
			'btnSave'   : 'Goym',
			'btnRm'     : 'Strika',
			'btnApply'  : 'Brúka',
			'btnCancel' : 'Angra',
			'btnNo'     : 'Nei',
			'btnYes'    : 'Ja',
			'btnMount'  : 'Mount',  // added 18.04.2012
			'btnApprove': 'Goto $1 & approve', // from v2.1 added 26.04.2012
			'btnUnmount': 'Unmount', // from v2.1 added 30.04.2012
			'btnConv'   : 'Konverter', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Her',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Øll',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Slag', // from v2.1 added 22.5.2015
			'btnFileName':'Fílunavn',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Goym & Lat aftur', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Opna mappu',
			'ntffile'     : '\'Opna fílu',
			'ntfreload'   : 'Les innaftur mappu innihald',
			'ntfmkdir'    : 'Stovnar mappu',
			'ntfmkfile'   : 'Stovnar fílur',
			'ntfrm'       : 'Strikar fílur',
			'ntfcopy'     : 'Kopierar fílur',
			'ntfmove'     : 'Flytur fílar',
			'ntfprepare'  : 'Ger klárt at kopiera fílar',
			'ntfrename'   : 'Umdoyp fílar',
			'ntfupload'   : 'Leggur inn fílar',
			'ntfdownload' : 'Tekur fílar niður',
			'ntfsave'     : 'Goymir fílar',
			'ntfarchive'  : 'Stovnar arkiv',
			'ntfextract'  : 'Útpakkar fílar frá arkiv',
			'ntfsearch'   : 'Leitar eftir fílum',
			'ntfresize'   : 'Broytir stødd á fílur',
			'ntfsmth'     : '\'Ger okkurt >_<',
			'ntfloadimg'  : 'Lesur mynd inn',
			'ntfnetmount' : 'Mounting network volume', // added 18.04.2012
			'ntfnetunmount': 'Unmounting network volume', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Tekur mynda vídd', // added 20.05.2013
			'ntfreaddir'  : 'Lesur mappu upplýsingar', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Far URL af leinkju', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Broyti fílu stíl', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Kannar fílunavnið á fílu', // from v2.1 added 31.11.2015

			/************************************ dates **********************************/
			'dateUnknown' : 'ókent',
			'Today'       : 'Í dag',
			'Yesterday'   : 'Í gjár',
			'msJan'       : 'Jan',
			'msFeb'       : 'Feb',
			'msMar'       : 'Mar',
			'msApr'       : 'Apr',
			'msMay'       : 'Mai',
			'msJun'       : 'Jun',
			'msJul'       : 'Jul',
			'msAug'       : 'Aug',
			'msSep'       : 'Sep',
			'msOct'       : 'Okt',
			'msNov'       : 'Nov',
			'msDec'       : 'Des',
			'January'     : 'Januar',
			'February'    : 'Februar',
			'March'       : 'Mars',
			'April'       : 'Apríl',
			'May'         : 'Mai',
			'June'        : 'Juni',
			'July'        : 'Juli',
			'August'      : 'August',
			'September'   : 'September',
			'October'     : 'Oktober',
			'November'    : 'November',
			'December'    : 'Desember',
			'Sunday'      : 'Sunnudag',
			'Monday'      : 'Mánadag',
			'Tuesday'     : 'Týsdag',
			'Wednesday'   : 'Mikudag',
			'Thursday'    : 'Hósdag',
			'Friday'      : 'Fríggjadag',
			'Saturday'    : 'Leygardag',
			'Sun'         : 'Sun',
			'Mon'         : 'Mán',
			'Tue'         : 'Týs',
			'Wed'         : 'Mik',
			'Thu'         : 'Hós',
			'Fri'         : 'Frí',
			'Sat'         : 'Ley',

			/******************************** sort variants ********************************/
			'sortname'          : 'eftir navn',
			'sortkind'          : 'eftir slag',
			'sortsize'          : 'eftir stødd',
			'sortdate'          : 'eftir dato',
			'sortFoldersFirst'  : 'mappur fyrst',

			/********************************** new items **********************************/
			'untitled file.txt' : 'NýggjaFílu.txt', // added 10.11.2015
			'untitled folder'   : 'NýggjaMappu',   // added 10.11.2015
			'Archive'           : 'NýtArkiv',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Váttan kravd',
			'confirmRm'       : 'Ert tú vísur í at tú ynskir at strika fílarnar?<br/>Hetta kann ikki angrast!',
			'confirmRepl'     : 'Erstatta gomlu fílu við nýggja?',
			'confirmConvUTF8' : 'Brúka á øll', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Er blivi rættað.<br/>Missir sínar broytingar um tú ikki goymir.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Brúka til øll',
			'name'            : 'Navn',
			'size'            : 'Stødd',
			'perms'           : 'Rættindi',
			'modify'          : 'Rættað',
			'kind'            : 'Slag',
			'read'            : 'síggja',
			'write'           : 'broyta',
			'noaccess'        : 'onga atgongd',
			'and'             : 'og',
			'unknown'         : 'ókent',
			'selectall'       : 'Vel allar fílur',
			'selectfiles'     : 'Vel fílu(r)',
			'selectffile'     : 'Vel fyrstu fílu',
			'selectlfile'     : 'Vel síðstu fílu',
			'viewlist'        : 'Lista vísing',
			'viewicons'       : 'Ikon vísing',
			'places'          : 'Støð',
			'calc'            : 'Rokna',
			'path'            : 'Stiga',
			'aliasfor'        : 'Hjánavn fyri',
			'locked'          : 'Læst',
			'dim'             : 'Vídd',
			'files'           : 'Fílur',
			'folders'         : 'Mappur',
			'items'           : 'Myndir',
			'yes'             : 'ja',
			'no'              : 'nei',
			'link'            : 'Leinkja',
			'searcresult'     : 'Leiti úrslit',
			'selected'        : 'valdar myndir',
			'about'           : 'Um',
			'shortcuts'       : 'Snarvegir',
			'help'            : 'Hjálp',
			'webfm'           : 'Web fílu umsitan',
			'ver'             : 'Útgáva',
			'protocolver'     : 'protokol versión',
			'homepage'        : 'Verkætlan heim',
			'docs'            : 'Skjalfesting',
			'github'          : 'Mynda okkum á Github',
			'twitter'         : 'Fylg okkum á twitter',
			'facebook'        : 'Fylg okkum á facebook',
			'team'            : 'Lið',
			'chiefdev'        : 'forritaleiðari',
			'developer'       : 'forritari',
			'contributor'     : 'stuðulsveitari',
			'maintainer'      : 'viðlíkahaldari',
			'translator'      : 'umsetari',
			'icons'           : 'Ikonir',
			'dontforget'      : 'and don\'t forget to take your towel',
			'shortcutsof'     : 'Snarvegir sligi frá',
			'dropFiles'       : 'Slepp fílur her',
			'or'              : 'ella',
			'selectForUpload' : 'Vel fílur at leggja inn',
			'moveFiles'       : 'Flyt fílur',
			'copyFiles'       : 'Kopier fílur',
			'rmFromPlaces'    : 'Flyt frá støð',
			'aspectRatio'     : 'Skermformat',
			'scale'           : 'Skalera',
			'width'           : 'Longd',
			'height'          : 'Hædd',
			'resize'          : 'Tilliga stødd',
			'crop'            : 'Sker til',
			'rotate'          : 'Rotera',
			'rotate-cw'       : 'Rotera 90 gradir við urið',
			'rotate-ccw'      : 'otera 90 gradir móti urið',
			'degree'          : '°',
			'netMountDialogTitle' : 'Mount network volume', // added 18.04.2012
			'protocol'            : 'Protokol', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'Brúkari', // added 18.04.2012
			'pass'                : 'Loyniorð', // added 18.04.2012
			'confirmUnmount'      : 'Are you unmount $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Hála ella set innn fílar frá kaga', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Hála ella set inn fílar frá URls her', // from v2.1 added 07.04.2014
			'encoding'        : 'Encoding', // from v2.1 added 19.12.2014
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Target: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Leita við input MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Eigari', // from v2.1 added 20.6.2015
			'group'           : 'Bólkur', // from v2.1 added 20.6.2015
			'other'           : 'Annað', // from v2.1 added 20.6.2015
			'execute'         : 'Útfør', // from v2.1 added 20.6.2015
			'perm'            : 'Rættindi', // from v2.1 added 20.6.2015
			'mode'            : 'Mode', // from v2.1 added 20.6.2015

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Ókent',
			'kindFolder'      : 'Mappa',
			'kindAlias'       : 'Hjánavn',
			'kindAliasBroken' : 'Óvirki hjánavn',
			// applications
			'kindApp'         : 'Applikatión',
			'kindPostscript'  : 'Postscript skjal',
			'kindMsOffice'    : 'Microsoft Office skjal',
			'kindMsWord'      : 'Microsoft Word skjal',
			'kindMsExcel'     : 'Microsoft Excel skjal',
			'kindMsPP'        : 'Microsoft Powerpoint framløga',
			'kindOO'          : 'Open Office skjal',
			'kindAppFlash'    : 'Flash applikatión',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent fíla',
			'kind7z'          : '7z arkiv',
			'kindTAR'         : 'TAR arkiv',
			'kindGZIP'        : 'GZIP arkiv',
			'kindBZIP'        : 'BZIP arkiv',
			'kindXZ'          : 'XZ arkiv',
			'kindZIP'         : 'ZIP arkiv',
			'kindRAR'         : 'RAR arkiv',
			'kindJAR'         : 'Java JAR ffílaile',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM pakki',
			// texts
			'kindText'        : 'Text skjal',
			'kindTextPlain'   : 'Reinur tekstur',
			'kindPHP'         : 'PHP kelda',
			'kindCSS'         : 'Cascading style sheet (CSS)',
			'kindHTML'        : 'HTML skjal',
			'kindJS'          : 'Javascript kelda',
			'kindRTF'         : 'Rich Text Format (RTF)',
			'kindC'           : 'C kelda',
			'kindCHeader'     : 'C header kelda',
			'kindCPP'         : 'C++ kelda',
			'kindCPPHeader'   : 'C++ header kelda',
			'kindShell'       : 'Unix shell script',
			'kindPython'      : 'Python kelda',
			'kindJava'        : 'Java kelda',
			'kindRuby'        : 'Ruby kelda',
			'kindPerl'        : 'Perl script',
			'kindSQL'         : 'SQL kelda',
			'kindXML'         : 'XML skjal',
			'kindAWK'         : 'AWK kelda',
			'kindCSV'         : 'Comma separated values (CSV)',
			'kindDOCBOOK'     : 'Docbook XML skjal',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'Mynd',
			'kindBMP'         : 'BMP mynd',
			'kindJPEG'        : 'JPEG mynd',
			'kindGIF'         : 'GIF mynd',
			'kindPNG'         : 'PNG mynd',
			'kindTIFF'        : 'TIFF mynd',
			'kindTGA'         : 'TGA mynd',
			'kindPSD'         : 'Adobe Photoshop mynd',
			'kindXBITMAP'     : 'X bitmap mynd',
			'kindPXM'         : 'Pixelmator mynd',
			// media
			'kindAudio'       : 'Audio media',
			'kindAudioMPEG'   : 'MPEG ljóðfíla',
			'kindAudioMPEG4'  : 'MPEG-4 ljóðfíla',
			'kindAudioMIDI'   : 'MIDI ljóðfíla',
			'kindAudioOGG'    : 'Ogg Vorbis ljóðfíla',
			'kindAudioWAV'    : 'WAV ljóðfíla',
			'AudioPlaylist'   : 'MP3 playlisti',
			'kindVideo'       : 'Video media',
			'kindVideoDV'     : 'DV filmur',
			'kindVideoMPEG'   : 'MPEG filmur',
			'kindVideoMPEG4'  : 'MPEG-4 filmur',
			'kindVideoAVI'    : 'AVI filmur',
			'kindVideoMOV'    : 'Quick Time filmur',
			'kindVideoWM'     : 'Windows Media filmur',
			'kindVideoFlash'  : 'Flash filmur',
			'kindVideoMKV'    : 'Matroska filmur',
			'kindVideoOGG'    : 'Ogg filmur'
		}
	};
}));

