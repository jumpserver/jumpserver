/**
 * hr translation
 * @version 2016-04-18
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
	elFinder.prototype.i18.hr = {
		translator : '',
		language   : 'Croatian',
		direction  : 'ltr',
		dateFormat : 'd.m.Y. H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Greška',
			'errUnknown'           : 'Nepoznata greška.',
			'errUnknownCmd'        : 'Nepoznata naredba.',
			'errJqui'              : 'Kriva jQuery UI konfiguracija. Selectable, draggable, i droppable komponente moraju biti uključene.',
			'errNode'              : 'elFinder zahtjeva DOM element da bi bio stvoren.',
			'errURL'               : 'Krivo konfiguriran elFinder. Opcija URL nije postavljena.',
			'errAccess'            : 'Zabranjen pristup.',
			'errConnect'           : 'Nije moguće spajanje na server.',
			'errAbort'             : 'Prekinuta veza.',
			'errTimeout'           : 'Veza je istekla.',
			'errNotFound'          : 'Server nije pronađen.',
			'errResponse'          : 'Krivi odgovor servera.',
			'errConf'              : 'Krivo konfiguriran server',
			'errJSON'              : 'Nije instaliran PHP JSON modul.',
			'errNoVolumes'         : 'Disk nije dostupan.',
			'errCmdParams'         : 'Krivi parametri za naredbu "$1".',
			'errDataNotJSON'       : 'Podaci nisu tipa JSON.',
			'errDataEmpty'         : 'Nema podataka.',
			'errCmdReq'            : 'Backend request requires command name.',
			'errOpen'              : 'Ne mogu otvoriti "$1".',
			'errNotFolder'         : 'Objekt nije mapa.',
			'errNotFile'           : 'Objekt nije dokument.',
			'errRead'              : 'Ne mogu pročitati "$1".',
			'errWrite'             : 'Ne mogu pisati u "$1".',
			'errPerm'              : 'Pristup zabranjen',
			'errLocked'            : '"$1" je zaključan i ne može biti preimenovan, premješten ili obrisan.',
			'errExists'            : 'Dokument s imenom "$1" već postoji.',
			'errInvName'           : 'Krivo ime dokumenta',
			'errFolderNotFound'    : 'Mapa nije pronađena',
			'errFileNotFound'      : 'Dokument nije pronađen',
			'errTrgFolderNotFound' : 'Mapa "$1" nije pronađena',
			'errPopup'             : 'Browser prevented opening popup window. To open file enable it in browser options.',
			'errMkdir'             : 'Ne mogu napraviti mapu "$1".',
			'errMkfile'            : 'Ne mogu napraviti dokument "$1".',
			'errRename'            : 'Ne mogu preimenovati "$1".',
			'errCopyFrom'          : 'Kopiranje s diska "$1" nije dozvoljeno.',
			'errCopyTo'            : 'Kopiranje na disk "$1" nije dozvoljeno.',
			'errMkOutLink'         : 'Unable to create a link to outside the volume root.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Greška pri prebacivanju dokumenta na server.',  // old name - errUploadCommon
			'errUploadFile'        : 'Ne mogu prebaciti "$1" na server', // old name - errUpload
			'errUploadNoFiles'     : 'Nema dokumenata za prebacivanje na server',
			'errUploadTotalSize'   : 'Dokumenti prelaze maksimalnu dopuštenu veličinu.', // old name - errMaxSize
			'errUploadFileSize'    : 'Dokument je prevelik.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Ovaj tip dokumenta nije dopušten.',
			'errUploadTransfer'    : '"$1" greška pri prebacivanju',
			'errUploadTemp'        : 'Ne mogu napraviti privremeni dokument za prijenos na server', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Object "$1" already exists at this location and can not be replaced by object with another type.', // new
			'errReplace'           : 'Ne mogu zamijeniti "$1".',
			'errSave'              : 'Ne mogu spremiti "$1".',
			'errCopy'              : 'Ne mogu kopirati "$1".',
			'errMove'              : 'Ne mogu premjestiti "$1".',
			'errCopyInItself'      : 'Ne mogu kopirati "$1" na isto mjesto.',
			'errRm'                : 'Ne mogu ukloniti "$1".',
			'errRmSrc'             : 'Ne mogu ukloniti izvorni kod.',
			'errExtract'           : 'Unable to extract files from "$1".',
			'errArchive'           : 'Unable to create archive.',
			'errArcType'           : 'Unsupported archive type.',
			'errNoArchive'         : 'File is not archive or has unsupported archive type.',
			'errCmdNoSupport'      : 'Backend does not support this command.',
			'errReplByChild'       : 'The folder "$1" can\'t be replaced by an item it contains.',
			'errArcSymlinks'       : 'For security reason denied to unpack archives contains symlinks or files with not allowed names.', // edited 24.06.2012
			'errArcMaxSize'        : 'Archive files exceeds maximum allowed size.',
			'errResize'            : 'Unable to resize "$1".',
			'errResizeDegree'      : 'Invalid rotate degree.',  // added 7.3.2013
			'errResizeRotate'      : 'Unable to rotate image.',  // added 7.3.2013
			'errResizeSize'        : 'Invalid image size.',  // added 7.3.2013
			'errResizeNoChange'    : 'Image size not changed.',  // added 7.3.2013
			'errUsupportType'      : 'Unsupported file type.',
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
			'errNetUnMount'        : 'Unable to unmount', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Not convertible to UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Try Google Chrome, If you\'d like to upload the folder.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Timed out while searching "$1". Search result is partial.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Re-authorization is required.', // from v2.1.10 added 3.24.2016

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Arhiviraj',
			'cmdback'      : 'Nazad',
			'cmdcopy'      : 'Kopiraj',
			'cmdcut'       : 'Izreži',
			'cmddownload'  : 'Preuzmi',
			'cmdduplicate' : 'Dupliciraj',
			'cmdedit'      : 'Uredi dokument',
			'cmdextract'   : 'Raspakiraj arhivu',
			'cmdforward'   : 'Naprijed',
			'cmdgetfile'   : 'Odaberi dokumente',
			'cmdhelp'      : 'O programu',
			'cmdhome'      : 'Početak',
			'cmdinfo'      : 'Info',
			'cmdmkdir'     : 'Nova mapa',
			'cmdmkdirin'   : 'U novu mapu', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nova файл',
			'cmdopen'      : 'Otvori',
			'cmdpaste'     : 'Zalijepi',
			'cmdquicklook' : 'Pregled',
			'cmdreload'    : 'Ponovo učitaj',
			'cmdrename'    : 'Preimenuj',
			'cmdrm'        : 'Obriši',
			'cmdsearch'    : 'Pronađi',
			'cmdup'        : 'Roditeljska mapa',
			'cmdupload'    : 'Prebaci dokumente na server',
			'cmdview'      : 'Pregledaj',
			'cmdresize'    : 'Promjeni veličinu i rotiraj',
			'cmdsort'      : 'Sortiraj',
			'cmdnetmount'  : 'Spoji se na mrežni disk', // added 18.04.2012
			'cmdnetunmount': 'Odspoji disk', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'To Places', // added 28.12.2014
			'cmdchmod'     : 'Change mode', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Otvori mapu', // from v2.1 added 13.1.2016

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Zatvori',
			'btnSave'   : 'Spremi',
			'btnRm'     : 'Ukloni',
			'btnApply'  : 'Primjeni',
			'btnCancel' : 'Odustani',
			'btnNo'     : 'Ne',
			'btnYes'    : 'Da',
			'btnMount'  : 'Mount',  // added 18.04.2012
			'btnApprove': 'Goto $1 & approve', // from v2.1 added 26.04.2012
			'btnUnmount': 'Unmount', // from v2.1 added 30.04.2012
			'btnConv'   : 'Convert', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Here',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'All',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName':'Filename',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Spremi i zatvori', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Otvori mapu',
			'ntffile'     : 'Otvori dokument',
			'ntfreload'   : 'Ponovo učitaj sadržaj mape',
			'ntfmkdir'    : 'Radim mapu',
			'ntfmkfile'   : 'Radim dokumente',
			'ntfrm'       : 'Brišem dokumente',
			'ntfcopy'     : 'Kopiram dokumente',
			'ntfmove'     : 'Mičem dokumente',
			'ntfprepare'  : 'Priprema za kopiranje dokumenata',
			'ntfrename'   : 'Preimenuj dokumente',
			'ntfupload'   : 'Pohranjujem dokumente na server',
			'ntfdownload' : 'Preuzimam dokumente',
			'ntfsave'     : 'Spremi dokumente',
			'ntfarchive'  : 'Radim arhivu',
			'ntfextract'  : 'Extracting files from archive',
			'ntfsearch'   : 'Tražim dokumente',
			'ntfresize'   : 'Resizing images',
			'ntfsmth'     : 'Doing something',
			'ntfloadimg'  : 'Učitavam sliku',
			'ntfnetmount' : 'Mounting network volume', // added 18.04.2012
			'ntfnetunmount': 'Unmounting network volume', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Acquiring image dimension', // added 20.05.2013
			'ntfreaddir'  : 'Reading folder infomation', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Getting URL of link', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Changing file mode', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verifying upload file name', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Creating a file for download', // from v2.1.7 added 23.1.2016

			/************************************ dates **********************************/
			'dateUnknown' : 'nepoznato',
			'Today'       : 'Danas',
			'Yesterday'   : 'Jučer',
			'msJan'       : 'Sij',
			'msFeb'       : 'Vel',
			'msMar'       : 'Ožu',
			'msApr'       : 'Tra',
			'msMay'       : 'Svi',
			'msJun'       : 'Lip',
			'msJul'       : 'Srp',
			'msAug'       : 'Kol',
			'msSep'       : 'Ruj',
			'msOct'       : 'Lis',
			'msNov'       : 'Stu',
			'msDec'       : 'Pro',
			'January'     : 'Siječanj',
			'February'    : 'Veljača',
			'March'       : 'Ožujak',
			'April'       : 'Travanj',
			'May'         : 'Svibanj',
			'June'        : 'Lipanj',
			'July'        : 'Srpanj',
			'August'      : 'Kolovoz',
			'September'   : 'Rujan',
			'October'     : 'Listopad',
			'November'    : 'Studeni',
			'December'    : 'Prosinac',
			'Sunday'      : 'Nedjelja',
			'Monday'      : 'Ponedjeljak',
			'Tuesday'     : 'Utorak',
			'Wednesday'   : 'Srijeda',
			'Thursday'    : 'Četvrtak',
			'Friday'      : 'Petak',
			'Saturday'    : 'Subota',
			'Sun'         : 'Ned',
			'Mon'         : 'Pon',
			'Tue'         : 'Uto',
			'Wed'         : 'Sri',
			'Thu'         : 'Čet',
			'Fri'         : 'Pet',
			'Sat'         : 'Sub',

			/******************************** sort variants ********************************/
			'sortname'          : 'po imenu',
			'sortkind'          : 'po tipu',
			'sortsize'          : 'po veličini',
			'sortdate'          : 'po datumu',
			'sortFoldersFirst'  : 'Prvo mape',

			/********************************** new items **********************************/
			'untitled file.txt' : 'NoviDokument.txt', // added 10.11.2015
			'untitled folder'   : 'NovaMapa',   // added 10.11.2015
			'Archive'           : 'NovaArhiva',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Potvrda',
			'confirmRm'       : 'Jeste li sigurni?',
			'confirmRepl'     : 'Zamijeni stare dokumente novima?',
			'confirmConvUTF8' : 'Not in UTF-8<br/>Convert to UTF-8?<br/>Contents become UTF-8 by saving after conversion.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'It has been modified.<br/>Losing work if you do not save changes.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Primjeni na sve ',
			'name'            : 'Ime',
			'size'            : 'Veličina',
			'perms'           : 'Dozvole',
			'modify'          : 'Modificiran',
			'kind'            : 'Tip',
			'read'            : 'čitanje',
			'write'           : 'pisanje',
			'noaccess'        : 'bez pristupa',
			'and'             : 'i',
			'unknown'         : 'nepoznato',
			'selectall'       : 'Odaberi sve',
			'selectfiles'     : 'Odaberi dokument(e)',
			'selectffile'     : 'Odaberi prvi dokument',
			'selectlfile'     : 'Odaberi zadnji dokument',
			'viewlist'        : 'Lista',
			'viewicons'       : 'Ikone',
			'places'          : 'Mjesta',
			'calc'            : 'Računaj',
			'path'            : 'Put',
			'aliasfor'        : 'Drugo ime za',
			'locked'          : 'Zaključano',
			'dim'             : 'Dimenzije',
			'files'           : 'Dokumenti',
			'folders'         : 'Mape',
			'items'           : 'Items',
			'yes'             : 'da',
			'no'              : 'ne',
			'link'            : 'poveznica',
			'searcresult'     : 'Rezultati pretrage',
			'selected'        : 'selected items',
			'about'           : 'Info',
			'shortcuts'       : 'Prečaci',
			'help'            : 'Pomoć',
			'webfm'           : 'Web file manager',
			'ver'             : 'Verzija',
			'protocolver'     : 'protocol version',
			'homepage'        : 'Project home',
			'docs'            : 'Dokumentacija',
			'github'          : 'Fork us on Github',
			'twitter'         : 'Follow us on twitter',
			'facebook'        : 'Join us on facebook',
			'team'            : 'Tim',
			'chiefdev'        : 'glavni developer',
			'developer'       : 'developer',
			'contributor'     : 'contributor',
			'maintainer'      : 'maintainer',
			'translator'      : 'translator',
			'icons'           : 'Ikone',
			'dontforget'      : 'and don\'t forget to take your towel',
			'shortcutsof'     : 'Prečaci isključeni',
			'dropFiles'       : 'Ovdje ispusti dokumente',
			'or'              : 'ili',
			'selectForUpload' : 'Odaberi dokumente koje prebacuješ na server',
			'moveFiles'       : 'Premjesti dokumente',
			'copyFiles'       : 'Kopiraj dokumente',
			'rmFromPlaces'    : 'Remove from places',
			'aspectRatio'     : 'Aspect ratio',
			'scale'           : 'Skaliraj',
			'width'           : 'Širina',
			'height'          : 'Visina',
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
			'user'                : 'User', // added 18.04.2012
			'pass'                : 'Password', // added 18.04.2012
			'confirmUnmount'      : 'Are you unmount $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Drop or Paste files from browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Drop or Paste files and URLs here', // from v2.1 added 07.04.2014
			'encoding'        : 'Encoding', // from v2.1 added 19.12.2014
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Target: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Search by input MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Vlasnik', // from v2.1 added 20.6.2015
			'group'           : 'Grupa', // from v2.1 added 20.6.2015
			'other'           : 'Other', // from v2.1 added 20.6.2015
			'execute'         : 'Izvrši', // from v2.1 added 20.6.2015
			'perm'            : 'Dozvole', // from v2.1 added 20.6.2015
			'mode'            : 'Mode', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Mapa je prazna', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Mapa je prazna\\A Dovuci dokumente koje želiš dodati', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Mapa je prazna\\A Pritisni dugo za dodavanje dokumenata', // from v2.1.6 added 30.12.2015
			'quality'         : 'Kvaliteta', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Auto sync',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Gore',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Get URL link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Selected items ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Folder ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Allow offline access', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'To re-authenticate', // from v2.1.10 added 3.25.2016

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Unknown',
			'kindFolder'      : 'Mapa',
			'kindAlias'       : 'Drugo ime',
			'kindAliasBroken' : 'Broken alias',
			// applications
			'kindApp'         : 'Aplikacija',
			'kindPostscript'  : 'Postscript document',
			'kindMsOffice'    : 'Microsoft Office dokument',
			'kindMsWord'      : 'Microsoft Word dokument',
			'kindMsExcel'     : 'Microsoft Excel dokument',
			'kindMsPP'        : 'Microsoft Powerpoint prezentacija',
			'kindOO'          : 'Open Office dokument',
			'kindAppFlash'    : 'Flash aplikacija',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent dokument',
			'kind7z'          : '7z arhiva',
			'kindTAR'         : 'TAR arhiva',
			'kindGZIP'        : 'GZIP arhiva',
			'kindBZIP'        : 'BZIP arhiva',
			'kindXZ'          : 'XZ arhiva',
			'kindZIP'         : 'ZIP arhiva',
			'kindRAR'         : 'RAR arhiva',
			'kindJAR'         : 'Java JAR dokument',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM paket',
			// texts
			'kindText'        : 'Tekst arhiva',
			'kindTextPlain'   : 'Obični tekst',
			'kindPHP'         : 'PHP source',
			'kindCSS'         : 'Cascading style sheet',
			'kindHTML'        : 'HTML document',
			'kindJS'          : 'Javascript source',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C source',
			'kindCHeader'     : 'C header source',
			'kindCPP'         : 'C++ source',
			'kindCPPHeader'   : 'C++ header source',
			'kindShell'       : 'Unix shell script',
			'kindPython'      : 'Python source',
			'kindJava'        : 'Java source',
			'kindRuby'        : 'Ruby source',
			'kindPerl'        : 'Perl skripta',
			'kindSQL'         : 'SQL source',
			'kindXML'         : 'XML dokument',
			'kindAWK'         : 'AWK source',
			'kindCSV'         : 'vrijednosti razdvojene zarezom',
			'kindDOCBOOK'     : 'Docbook XML dokument',
			'kindMarkdown'    : 'Markdown tekst', // added 20.7.2015
			// images
			'kindImage'       : 'slika',
			'kindBMP'         : 'BMP slika',
			'kindJPEG'        : 'JPEG slika',
			'kindGIF'         : 'GIF slika',
			'kindPNG'         : 'PNG slika',
			'kindTIFF'        : 'TIFF slika',
			'kindTGA'         : 'TGA slika',
			'kindPSD'         : 'Adobe Photoshop slika',
			'kindXBITMAP'     : 'X bitmap slika',
			'kindPXM'         : 'Pixelmator slika',
			// media
			'kindAudio'       : 'Audio',
			'kindAudioMPEG'   : 'MPEG audio',
			'kindAudioMPEG4'  : 'MPEG-4 audio',
			'kindAudioMIDI'   : 'MIDI audio',
			'kindAudioOGG'    : 'Ogg Vorbis audio',
			'kindAudioWAV'    : 'WAV audio',
			'AudioPlaylist'   : 'MP3 lista',
			'kindVideo'       : 'Video ',
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

