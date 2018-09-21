/**
 * Dutch translation
 * @author Barry vd. Heuvel <barry@fruitcakestudio.nl>
 * @version 2015-12-01
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
	elFinder.prototype.i18.nl = {
		translator : 'Barry vd. Heuvel &lt;barry@fruitcakestudio.nl&gt;',
		language   : 'Nederlands',
		direction  : 'ltr',
		dateFormat : 'd-m-Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Fout',
			'errUnknown'           : 'Onbekend fout.',
			'errUnknownCmd'        : 'Onbekend commando.',
			'errJqui'              : 'Ongeldige jQuery UI configuratie. Selectable, draggable en droppable componenten moeten aanwezig zijn.',
			'errNode'              : 'Voor elFinder moet een DOM Element gemaakt worden.',
			'errURL'               : 'Ongeldige elFinder configuratie! URL optie is niet ingesteld.',
			'errAccess'            : 'Toegang geweigerd.',
			'errConnect'           : 'Kan geen verbinding met de backend maken.',
			'errAbort'             : 'Verbinding afgebroken.',
			'errTimeout'           : 'Verbinding time-out.',
			'errNotFound'          : 'Backend niet gevonden.',
			'errResponse'          : 'Ongeldige reactie van de backend.',
			'errConf'              : 'Ongeldige backend configuratie.',
			'errJSON'              : 'PHP JSON module niet geïnstalleerd.',
			'errNoVolumes'         : 'Leesbaar volume is niet beschikbaar.',
			'errCmdParams'         : 'Ongeldige parameters voor commando "$1".',
			'errDataNotJSON'       : 'Data is niet JSON.',
			'errDataEmpty'         : 'Data is leeg.',
			'errCmdReq'            : 'Backend verzoek heeft een commando naam nodig.',
			'errOpen'              : 'Kan "$1" niet openen.',
			'errNotFolder'         : 'Object is geen map.',
			'errNotFile'           : 'Object is geen bestand.',
			'errRead'              : 'Kan "$1" niet lezen.',
			'errWrite'             : 'Kan niet schrijven in "$1".',
			'errPerm'              : 'Toegang geweigerd.',
			'errLocked'            : '"$1" is vergrendeld en kan niet hernoemd, verplaats of verwijderd worden.',
			'errExists'            : 'Bestand "$1" bestaat al.',
			'errInvName'           : 'Ongeldige bestandsnaam.',
			'errFolderNotFound'    : 'Map niet gevonden.',
			'errFileNotFound'      : 'Bestand niet gevonden.',
			'errTrgFolderNotFound' : 'Doelmap"$1" niet gevonden.',
			'errPopup'             : 'De browser heeft voorkomen dat de pop-up is geopend. Pas de browser instellingen aan om de popup te kunnen openen.',
			'errMkdir'             : 'Kan map "$1" niet aanmaken.',
			'errMkfile'            : 'Kan bestand "$1" niet aanmaken.',
			'errRename'            : 'Kan "$1" niet hernoemen.',
			'errCopyFrom'          : 'Bestanden kopiëren van "$1" is niet toegestaan.',
			'errCopyTo'            : 'Bestanden kopiëren naar "$1" is niet toegestaan.',
			'errMkOutLink'         : 'Kan geen link maken buiten de hoofdmap.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Upload fout.',  // old name - errUploadCommon
			'errUploadFile'        : 'Kan "$1" niet uploaden.', // old name - errUpload
			'errUploadNoFiles'     : 'Geen bestanden gevonden om te uploaden.',
			'errUploadTotalSize'   : 'Data overschrijdt de maximale grootte.', // old name - errMaxSize
			'errUploadFileSize'    : 'Bestand overschrijdt de maximale grootte.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Bestandstype niet toegestaan.',
			'errUploadTransfer'    : '"$1" overdrachtsfout.',
			'errUploadTemp'        : 'Kan geen tijdelijk bestand voor de upload maken.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Object "$1" bestaat al op deze locatie en kan niet vervangen worden door een ander type object.', // new
			'errReplace'           : 'Kan "$1" niet vervangen.',
			'errSave'              : 'Kan "$1" niet opslaan.',
			'errCopy'              : 'Kan "$1" niet kopiëren.',
			'errMove'              : 'Kan "$1" niet verplaatsen.',
			'errCopyInItself'      : 'Kan "$1" niet in zichzelf kopiëren.',
			'errRm'                : 'Kan "$1" niet verwijderen.',
			'errRmSrc'             : 'Kan bronbestanden niet verwijderen.',
			'errExtract'           : 'Kan de bestanden van "$1" niet uitpakken.',
			'errArchive'           : 'Kan het archief niet maken.',
			'errArcType'           : 'Archief type is niet ondersteund.',
			'errNoArchive'         : 'Bestand is geen archief of geen ondersteund archief type.',
			'errCmdNoSupport'      : 'Backend ondersteund dit commando niet.',
			'errReplByChild'       : 'De map "$1" kan niet vervangen worden door een item uit die map.',
			'errArcSymlinks'       : 'Om veiligheidsredenen kan een bestand met symlinks of bestanden met niet toegestane namen niet worden uitgepakt .', // edited 24.06.2012
			'errArcMaxSize'        : 'Archief overschrijdt de maximale bestandsgrootte.',
			'errResize'            : 'Kan het formaat van "$1" niet wijzigen.',
			'errResizeDegree'      : 'Ongeldig aantal graden om te draaien.',  // added 7.3.2013
			'errResizeRotate'      : 'Afbeelding kan niet gedraaid worden.',  // added 7.3.2013
			'errResizeSize'        : 'Ongeldig afbeelding formaat.',  // added 7.3.2013
			'errResizeNoChange'    : 'Afbeelding formaat is niet veranderd.',  // added 7.3.2013
			'errUsupportType'      : 'Bestandstype wordt niet ondersteund.',
			'errNotUTF8Content'    : 'Bestand "$1" is niet in UTF-8 and kan niet aangepast worden.',  // added 9.11.2011
			'errNetMount'          : 'Kan "$1" niet mounten.', // added 17.04.2012
			'errNetMountNoDriver'  : 'Niet ondersteund protocol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Mount mislukt.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Host is verplicht.', // added 18.04.2012
			'errSessionExpires'    : 'Uw sessie is verlopen vanwege inactiviteit.',
			'errCreatingTempDir'   : 'Kan de tijdelijke map niet aanmaken: "$1" ',
			'errFtpDownloadFile'   : 'Kan het bestand niet downloaden vanaf FTP: "$1"',
			'errFtpUploadFile'     : 'Kan het bestand niet uploaden naar FTP: "$1"',
			'errFtpMkdir'          : 'Kan het externe map niet aanmaken op de FTP-server: "$1"',
			'errArchiveExec'       : 'Er is een fout opgetreden bij het archivering van de bestanden: "$1" ',
			'errExtractExec'       : 'Er is een fout opgetreden bij het uitpakken van de bestanden: "$1" ',
			'errNetUnMount'        : 'Kan niet unmounten', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Kan niet converteren naar UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Probeer Google Chrome, als je de map wil uploaden.', // from v2.1 added 26.6.2015

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Maak archief',
			'cmdback'      : 'Vorige',
			'cmdcopy'      : 'Kopieer',
			'cmdcut'       : 'Knip',
			'cmddownload'  : 'Download',
			'cmdduplicate' : 'Dupliceer',
			'cmdedit'      : 'Pas bestand aan',
			'cmdextract'   : 'Bestanden uit archief uitpakken',
			'cmdforward'   : 'Volgende',
			'cmdgetfile'   : 'Kies bestanden',
			'cmdhelp'      : 'Over deze software',
			'cmdhome'      : 'Home',
			'cmdinfo'      : 'Bekijk info',
			'cmdmkdir'     : 'Nieuwe map',
			'cmdmkfile'    : 'Nieuw bestand',
			'cmdopen'      : 'Open',
			'cmdpaste'     : 'Plak',
			'cmdquicklook' : 'Voorbeeld',
			'cmdreload'    : 'Vernieuwen',
			'cmdrename'    : 'Naam wijzigen',
			'cmdrm'        : 'Verwijder',
			'cmdsearch'    : 'Zoek bestanden',
			'cmdup'        : 'Ga een map hoger',
			'cmdupload'    : 'Upload bestanden',
			'cmdview'      : 'Bekijk',
			'cmdresize'    : 'Formaat wijzigen',
			'cmdsort'      : 'Sorteren',
			'cmdnetmount'  : 'Mount netwerk volume', // added 18.04.2012
			'cmdnetunmount': 'Unmount', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Naar Plaatsen', // added 28.12.2014
			'cmdchmod'     : 'Wijzig modus', // from v2.1 added 20.6.2015

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Sluit',
			'btnSave'   : 'Opslaan',
			'btnRm'     : 'Verwijder',
			'btnApply'  : 'Toepassen',
			'btnCancel' : 'Annuleren',
			'btnNo'     : 'Nee',
			'btnYes'    : 'Ja',
			'btnMount'  : 'Mount',  // added 18.04.2012
			'btnApprove': 'Ga naar $1 & keur goed', // from v2.1 added 26.04.2012
			'btnUnmount': 'Unmount', // from v2.1 added 30.04.2012
			'btnConv'   : 'Converteer', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Hier',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Alles',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName':'Bestandsnaam',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Opslaan & Sluiten', // from v2.1 added 12.6.2015
			'btnBackup' : 'Back-up', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Bezig met openen van map',
			'ntffile'     : 'Bezig met openen bestand',
			'ntfreload'   : 'Herladen map inhoud',
			'ntfmkdir'    : 'Bezig met map maken',
			'ntfmkfile'   : 'Bezig met Bestanden maken',
			'ntfrm'       : 'Verwijderen bestanden',
			'ntfcopy'     : 'Kopieer bestanden',
			'ntfmove'     : 'Verplaats bestanden',
			'ntfprepare'  : 'Voorbereiden kopiëren',
			'ntfrename'   : 'Hernoem bestanden',
			'ntfupload'   : 'Bestanden uploaden actief',
			'ntfdownload' : 'Bestanden downloaden actief',
			'ntfsave'     : 'Bestanden opslaan',
			'ntfarchive'  : 'Archief aan het maken',
			'ntfextract'  : 'Bestanden uitpakken actief',
			'ntfsearch'   : 'Zoeken naar bestanden',
			'ntfresize'   : 'Formaat wijzigen van afbeeldingen',
			'ntfsmth'     : 'Iets aan het doen',
			'ntfloadimg'  : 'Laden van plaatje',
			'ntfnetmount' : 'Mounten van netwerk volume', // added 18.04.2012
			'ntfnetunmount': 'Unmounten van netwerk volume', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Opvragen afbeeldingen dimensies', // added 20.05.2013
			'ntfreaddir'  : 'Map informatie lezen', // from v2.1 added 01.07.2013
			'ntfurl'      : 'URL van link ophalen', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Bestandsmodus wijzigen', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Upload bestandsnaam verifiëren', // from v2.1 added 31.11.2015

			/************************************ dates **********************************/
			'dateUnknown' : 'onbekend',
			'Today'       : 'Vandaag',
			'Yesterday'   : 'Gisteren',
			'msJan'       : 'Jan',
			'msFeb'       : 'Feb',
			'msMar'       : 'Mar',
			'msApr'       : 'Apr',
			'msMay'       : 'Mei',
			'msJun'       : 'Jun',
			'msJul'       : 'Jul',
			'msAug'       : 'Aug',
			'msSep'       : 'Sep',
			'msOct'       : 'Okt',
			'msNov'       : 'Nov',
			'msDec'       : 'Dec',
			'January'     : 'Januari',
			'February'    : 'Februari',
			'March'       : 'Maart',
			'April'       : 'April',
			'May'         : 'Mei',
			'June'        : 'Juni',
			'July'        : 'Juli',
			'August'      : 'Augustus',
			'September'   : 'September',
			'October'     : 'Oktober',
			'November'    : 'November',
			'December'    : 'December',
			'Sunday'      : 'Zondag',
			'Monday'      : 'Maandag',
			'Tuesday'     : 'Dinsdag',
			'Wednesday'   : 'Woensdag',
			'Thursday'    : 'Donderdag',
			'Friday'      : 'Vrijdag',
			'Saturday'    : 'Zaterdag',
			'Sun'         : 'Zo',
			'Mon'         : 'Ma',
			'Tue'         : 'Di',
			'Wed'         : 'Wo',
			'Thu'         : 'Do',
			'Fri'         : 'Vr',
			'Sat'         : 'Za',

			/******************************** sort variants ********************************/
			'sortname'          : 'op naam',
			'sortkind'          : 'op type',
			'sortsize'          : 'op grootte',
			'sortdate'          : 'op datum',
			'sortFoldersFirst'  : 'Mappen eerst',

			/********************************** new items **********************************/
			'untitled file.txt' : 'NieuwBestand.txt', // added 10.11.2015
			'untitled folder'   : 'NieuweMap',   // added 10.11.2015
			'Archive'           : 'NieuwArchief',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Bevestiging nodig',
			'confirmRm'       : 'Weet u zeker dat u deze bestanden wil verwijderen?<br/>Deze actie kan niet ongedaan gemaakt worden!',
			'confirmRepl'     : 'Oud bestand vervangen door het nieuwe bestand?',
			'confirmConvUTF8' : 'Niet in UTF-8<br/>Converteren naar UTF-8?<br/>De inhoud wordt UTF-8 door op te slaan na de conversie.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Het is aangepast.<br/>Wijzigingen gaan verloren als je niet opslaat.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Toepassen op alles',
			'name'            : 'Naam',
			'size'            : 'Grootte',
			'perms'           : 'Rechten',
			'modify'          : 'Aangepast',
			'kind'            : 'Type',
			'read'            : 'lees',
			'write'           : 'schrijf',
			'noaccess'        : 'geen toegang',
			'and'             : 'en',
			'unknown'         : 'onbekend',
			'selectall'       : 'Selecteer alle bestanden',
			'selectfiles'     : 'Selecteer bestand(en)',
			'selectffile'     : 'Selecteer eerste bestand',
			'selectlfile'     : 'Selecteer laatste bestand',
			'viewlist'        : 'Lijst weergave',
			'viewicons'       : 'Icoon weergave',
			'places'          : 'Plaatsen',
			'calc'            : 'Bereken',
			'path'            : 'Pad',
			'aliasfor'        : 'Alias voor',
			'locked'          : 'Vergrendeld',
			'dim'             : 'Dimensies',
			'files'           : 'Bestanden',
			'folders'         : 'Mappen',
			'items'           : 'Items',
			'yes'             : 'ja',
			'no'              : 'nee',
			'link'            : 'Link',
			'searcresult'     : 'Zoek resultaten',
			'selected'        : 'geselecteerde items',
			'about'           : 'Over',
			'shortcuts'       : 'Snelkoppelingen',
			'help'            : 'Help',
			'webfm'           : 'Web bestandsmanager',
			'ver'             : 'Versie',
			'protocolver'     : 'protocol versie',
			'homepage'        : 'Project home',
			'docs'            : 'Documentatie',
			'github'          : 'Fork ons op Github',
			'twitter'         : 'Volg ons op twitter',
			'facebook'        : 'Wordt lid op facebook',
			'team'            : 'Team',
			'chiefdev'        : 'Hoofd ontwikkelaar',
			'developer'       : 'ontwikkelaar',
			'contributor'     : 'bijdrager',
			'maintainer'      : 'onderhouder',
			'translator'      : 'vertaler',
			'icons'           : 'Iconen',
			'dontforget'      : 'En vergeet je handdoek niet!',
			'shortcutsof'     : 'Snelkoppelingen uitgeschakeld',
			'dropFiles'       : 'Sleep hier uw bestanden heen',
			'or'              : 'of',
			'selectForUpload' : 'Selecteer bestanden om te uploaden',
			'moveFiles'       : 'Verplaats bestanden',
			'copyFiles'       : 'Kopieer bestanden',
			'rmFromPlaces'    : 'Verwijder uit Plaatsen',
			'aspectRatio'     : 'Aspect ratio',
			'scale'           : 'Schaal',
			'width'           : 'Breedte',
			'height'          : 'Hoogte',
			'resize'          : 'Verkleinen',
			'crop'            : 'Bijsnijden',
			'rotate'          : 'Draaien',
			'rotate-cw'       : 'Draai 90 graden rechtsom',
			'rotate-ccw'      : 'Draai 90 graden linksom',
			'degree'          : '°',
			'netMountDialogTitle' : 'Mount netwerk volume', // added 18.04.2012
			'protocol'            : 'Protocol', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Poort', // added 18.04.2012
			'user'                : 'Gebruikersnaams', // added 18.04.2012
			'pass'                : 'Wachtwoord', // added 18.04.2012
			'confirmUnmount'      : 'Weet u zeker dat u $1 wil unmounten?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Sleep of plak bestanden vanuit de browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Sleep of plak bestanden hier', // from v2.1 added 07.04.2014
			'encoding'        : 'Encodering', // from v2.1 added 19.12.2014
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Doel: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Zoek op invoer MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Eigenaar', // from v2.1 added 20.6.2015
			'group'           : 'Groep', // from v2.1 added 20.6.2015
			'other'           : 'Overig', // from v2.1 added 20.6.2015
			'execute'         : 'Uitvoeren', // from v2.1 added 20.6.2015
			'perm'            : 'Rechten', // from v2.1 added 20.6.2015
			'mode'            : 'Modus', // from v2.1 added 20.6.2015

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Onbekend',
			'kindFolder'      : 'Map',
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Kapot alias',
			// applications
			'kindApp'         : 'Applicatie',
			'kindPostscript'  : 'Postscript document',
			'kindMsOffice'    : 'Microsoft Office document',
			'kindMsWord'      : 'Microsoft Word document',
			'kindMsExcel'     : 'Microsoft Excel document',
			'kindMsPP'        : 'Microsoft Powerpoint presentation',
			'kindOO'          : 'Open Office document',
			'kindAppFlash'    : 'Flash applicatie',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent bestand',
			'kind7z'          : '7z archief',
			'kindTAR'         : 'TAR archief',
			'kindGZIP'        : 'GZIP archief',
			'kindBZIP'        : 'BZIP archief',
			'kindXZ'          : 'XZ archief',
			'kindZIP'         : 'ZIP archief',
			'kindRAR'         : 'RAR archief',
			'kindJAR'         : 'Java JAR bestand',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM package',
			// texts
			'kindText'        : 'Tekst bestand',
			'kindTextPlain'   : 'Tekst',
			'kindPHP'         : 'PHP bronbestand',
			'kindCSS'         : 'Cascading style sheet',
			'kindHTML'        : 'HTML document',
			'kindJS'          : 'Javascript bronbestand',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C bronbestand',
			'kindCHeader'     : 'C header bronbestand',
			'kindCPP'         : 'C++ bronbestand',
			'kindCPPHeader'   : 'C++ header bronbestand',
			'kindShell'       : 'Unix shell script',
			'kindPython'      : 'Python bronbestand',
			'kindJava'        : 'Java bronbestand',
			'kindRuby'        : 'Ruby bronbestand',
			'kindPerl'        : 'Perl bronbestand',
			'kindSQL'         : 'SQL bronbestand',
			'kindXML'         : 'XML document',
			'kindAWK'         : 'AWK bronbestand',
			'kindCSV'         : 'Komma gescheiden waardes',
			'kindDOCBOOK'     : 'Docbook XML document',
			'kindMarkdown'    : 'Markdown tekst', // added 20.7.2015
			// images
			'kindImage'       : 'Afbeelding',
			'kindBMP'         : 'BMP afbeelding',
			'kindJPEG'        : 'JPEG afbeelding',
			'kindGIF'         : 'GIF afbeelding',
			'kindPNG'         : 'PNG afbeelding',
			'kindTIFF'        : 'TIFF afbeelding',
			'kindTGA'         : 'TGA afbeelding',
			'kindPSD'         : 'Adobe Photoshop afbeelding',
			'kindXBITMAP'     : 'X bitmap afbeelding',
			'kindPXM'         : 'Pixelmator afbeelding',
			// media
			'kindAudio'       : 'Audio media',
			'kindAudioMPEG'   : 'MPEG audio',
			'kindAudioMPEG4'  : 'MPEG-4 audio',
			'kindAudioMIDI'   : 'MIDI audio',
			'kindAudioOGG'    : 'Ogg Vorbis audio',
			'kindAudioWAV'    : 'WAV audio',
			'AudioPlaylist'   : 'MP3 playlist',
			'kindVideo'       : 'Video media',
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

