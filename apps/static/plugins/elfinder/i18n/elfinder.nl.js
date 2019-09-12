/**
 * Dutch translation
 * @author Barry vd. Heuvel <barry@fruitcakestudio.nl>
 * @author Patrick Tingen <patrick@tingen.net>
 * @version 2019-04-17
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
		translator       : 'Barry vd. Heuvel &lt;barry@fruitcakestudio.nl&gt;, Patrick Tingen &lt;patrick@tingen.net&gt;',
		language         : 'Nederlands',
		direction        : 'ltr',
		dateFormat       : 'd-m-Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat  : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // noname upload will show like: 120513-172700
		messages         : {

			/********************************** errors **********************************/
			'error'                : 'Fout',
			'errUnknown'           : 'Onbekend fout',
			'errUnknownCmd'        : 'Onbekend commando',
			'errJqui'              : 'Ongeldige jQuery UI configuratie. Selectable, draggable en droppable componenten moeten aanwezig zijn',
			'errNode'              : 'Voor elFinder moet een DOM Element gemaakt worden',
			'errURL'               : 'Ongeldige elFinder configuratie! URL optie is niet ingesteld',
			'errAccess'            : 'Toegang geweigerd',
			'errConnect'           : 'Kan geen verbinding met de backend maken',
			'errAbort'             : 'Verbinding afgebroken',
			'errTimeout'           : 'Verbinding time-out',
			'errNotFound'          : 'Backend niet gevonden',
			'errResponse'          : 'Ongeldige reactie van de backend',
			'errConf'              : 'Ongeldige backend configuratie',
			'errJSON'              : 'PHP JSON module niet geïnstalleerd',
			'errNoVolumes'         : 'Leesbaar volume is niet beschikbaar',
			'errCmdParams'         : 'Ongeldige parameters voor commando "$1"',
			'errDataNotJSON'       : 'Data is niet JSON',
			'errDataEmpty'         : 'Data is leeg',
			'errCmdReq'            : 'Backend verzoek heeft een commando naam nodig',
			'errOpen'              : 'Kan "$1" niet openen',
			'errNotFolder'         : 'Object is geen map',
			'errNotFile'           : 'Object is geen bestand',
			'errRead'              : 'Kan "$1" niet lezen',
			'errWrite'             : 'Kan niet schrijven in "$1"',
			'errPerm'              : 'Toegang geweigerd',
			'errLocked'            : '"$1" is vergrendeld en kan niet hernoemd, verplaats of verwijderd worden',
			'errExists'            : 'Bestand "$1" bestaat al',
			'errInvName'           : 'Ongeldige bestandsnaam',
			'errFolderNotFound'    : 'Map niet gevonden',
			'errFileNotFound'      : 'Bestand niet gevonden',
			'errTrgFolderNotFound' : 'Doelmap "$1" niet gevonden',
			'errPopup'             : 'De browser heeft voorkomen dat de pop-up is geopend. Pas de browser instellingen aan om de popup te kunnen openen',
			'errMkdir'             : 'Kan map "$1" niet aanmaken',
			'errMkfile'            : 'Kan bestand "$1" niet aanmaken',
			'errRename'            : 'Kan "$1" niet hernoemen',
			'errCopyFrom'          : 'Bestanden kopiëren van "$1" is niet toegestaan',
			'errCopyTo'            : 'Bestanden kopiëren naar "$1" is niet toegestaan',
			'errMkOutLink'         : 'Kan geen link maken buiten de hoofdmap', // from v2.1 added 03.10.2015
			'errUpload'            : 'Upload fout',  // old name - errUploadCommon
			'errUploadFile'        : 'Kan "$1" niet uploaden', // old name - errUpload
			'errUploadNoFiles'     : 'Geen bestanden gevonden om te uploaden',
			'errUploadTotalSize'   : 'Data overschrijdt de maximale grootte', // old name - errMaxSize
			'errUploadFileSize'    : 'Bestand overschrijdt de maximale grootte', //  old name - errFileMaxSize
			'errUploadMime'        : 'Bestandstype niet toegestaan',
			'errUploadTransfer'    : '"$1" overdrachtsfout',
			'errUploadTemp'        : 'Kan geen tijdelijk bestand voor de upload maken', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'Object "$1" bestaat al op deze locatie en kan niet vervangen worden door een ander type object', // new
			'errReplace'           : 'Kan "$1" niet vervangen',
			'errSave'              : 'Kan "$1" niet opslaan',
			'errCopy'              : 'Kan "$1" niet kopiëren',
			'errMove'              : 'Kan "$1" niet verplaatsen',
			'errCopyInItself'      : 'Kan "$1" niet in zichzelf kopiëren',
			'errRm'                : 'Kan "$1" niet verwijderen',
			'errRmSrc'             : 'Kan bronbestanden niet verwijderen',
			'errExtract'           : 'Kan de bestanden van "$1" niet uitpakken',
			'errArchive'           : 'Kan het archief niet maken',
			'errArcType'           : 'Archief type is niet ondersteund',
			'errNoArchive'         : 'Bestand is geen archief of geen ondersteund archief type',
			'errCmdNoSupport'      : 'Backend ondersteund dit commando niet',
			'errReplByChild'       : 'De map "$1" kan niet vervangen worden door een item uit die map',
			'errArcSymlinks'       : 'Om veiligheidsredenen kan een bestand met symlinks of bestanden met niet toegestane namen niet worden uitgepakt ', // edited 24.06.2012
			'errArcMaxSize'        : 'Archief overschrijdt de maximale bestandsgrootte',
			'errResize'            : 'Kan het formaat van "$1" niet wijzigen',
			'errResizeDegree'      : 'Ongeldig aantal graden om te draaien',  // added 7.3.2013
			'errResizeRotate'      : 'Afbeelding kan niet gedraaid worden',  // added 7.3.2013
			'errResizeSize'        : 'Ongeldig afbeelding formaat',  // added 7.3.2013
			'errResizeNoChange'    : 'Afbeelding formaat is niet veranderd',  // added 7.3.2013
			'errUsupportType'      : 'Bestandstype wordt niet ondersteund',
			'errNotUTF8Content'    : 'Bestand "$1" is niet in UTF-8 and kan niet aangepast worden',  // added 9.11.2011
			'errNetMount'          : 'Kan "$1" niet mounten', // added 17.04.2012
			'errNetMountNoDriver'  : 'Niet ondersteund protocol',     // added 17.04.2012
			'errNetMountFailed'    : 'Mount mislukt',         // added 17.04.2012
			'errNetMountHostReq'   : 'Host is verplicht', // added 18.04.2012
			'errSessionExpires'    : 'Uw sessie is verlopen vanwege inactiviteit',
			'errCreatingTempDir'   : 'Kan de tijdelijke map niet aanmaken: "$1" ',
			'errFtpDownloadFile'   : 'Kan het bestand niet downloaden vanaf FTP: "$1"',
			'errFtpUploadFile'     : 'Kan het bestand niet uploaden naar FTP: "$1"',
			'errFtpMkdir'          : 'Kan het externe map niet aanmaken op de FTP-server: "$1"',
			'errArchiveExec'       : 'Er is een fout opgetreden bij het archivering van de bestanden: "$1" ',
			'errExtractExec'       : 'Er is een fout opgetreden bij het uitpakken van de bestanden: "$1" ',
			'errNetUnMount'        : 'Kan niet unmounten', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Niet om te zetten naar UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Probeer een moderne browser als je bestanden wil uploaden', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Time-out bij zoeken naar "$1". Zoekresulataat is niet compleet', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Je moet je opnieuw aanmelden', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Max aantal selecteerbare items is $1', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Kan niet herstellen uit prullenbak, weet niet waar het heen moet', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Geen editor voor dit type bestand', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Fout opgetreden op de server', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Kan folder "$1" niet legen', // from v2.1.25 added 22.6.2017
			'moreErrors'           : 'Er zijn nog $1 fouten', // from v2.1.44 added 9.12.2018

			/******************************* commands names ********************************/
			'cmdarchive'           : 'Maak archief',
			'cmdback'              : 'Vorige',
			'cmdcopy'              : 'Kopieer',
			'cmdcut'               : 'Knip',
			'cmddownload'          : 'Download',
			'cmdduplicate'         : 'Dupliceer',
			'cmdedit'              : 'Pas bestand aan',
			'cmdextract'           : 'Bestanden uit archief uitpakken',
			'cmdforward'           : 'Volgende',
			'cmdgetfile'           : 'Kies bestanden',
			'cmdhelp'              : 'Over deze software',
			'cmdhome'              : 'Home',
			'cmdinfo'              : 'Bekijk info',
			'cmdmkdir'             : 'Nieuwe map',
			'cmdmkdirin'           : 'In nieuwe map', // from v2.1.7 added 19.2.2016
			'cmdmkfile'            : 'Nieuw bestand',
			'cmdopen'              : 'Open',
			'cmdpaste'             : 'Plak',
			'cmdquicklook'         : 'Voorbeeld',
			'cmdreload'            : 'Vernieuwen',
			'cmdrename'            : 'Naam wijzigen',
			'cmdrm'                : 'Verwijder',
			'cmdtrash'             : 'Naar prullenbak', //from v2.1.24 added 29.4.2017
			'cmdrestore'           : 'Herstellen', //from v2.1.24 added 3.5.2017
			'cmdsearch'            : 'Zoek bestanden',
			'cmdup'                : 'Ga een map hoger',
			'cmdupload'            : 'Upload bestanden',
			'cmdview'              : 'Bekijk',
			'cmdresize'            : 'Formaat wijzigen',
			'cmdsort'              : 'Sorteren',
			'cmdnetmount'          : 'Mount netwerk volume', // added 18.04.2012
			'cmdnetunmount'        : 'Unmount', // from v2.1 added 30.04.2012
			'cmdplaces'            : 'Naar Plaatsen', // added 28.12.2014
			'cmdchmod'             : 'Wijzig modus', // from v2.1 added 20.6.2015
			'cmdopendir'           : 'Open een map', // from v2.1 added 13.1.2016
			'cmdcolwidth'          : 'Herstel kolombreedtes', // from v2.1.13 added 12.06.2016
			'cmdfullscreen'        : 'Volledig scherm', // from v2.1.15 added 03.08.2016
			'cmdmove'              : 'Verplaatsen', // from v2.1.15 added 21.08.2016
			'cmdempty'             : 'Map leegmaken', // from v2.1.25 added 22.06.2017
			'cmdundo'              : 'Undo', // from v2.1.27 added 31.07.2017
			'cmdredo'              : 'Redo', // from v2.1.27 added 31.07.2017
			'cmdpreference'        : 'Voorkeuren', // from v2.1.27 added 03.08.2017
			'cmdselectall'         : 'Selecteer alles', // from v2.1.28 added 15.08.2017
			'cmdselectnone'        : 'Deselecteer alles', // from v2.1.28 added 15.08.2017
			'cmdselectinvert'      : 'Selectie omkeren', // from v2.1.28 added 15.08.2017
			'cmdopennew'           : 'Open in nieuw venster', // from v2.1.38 added 3.4.2018
			'cmdhide'              : 'Verberg (voorkeur)', // from v2.1.41 added 24.7.2018


			/*********************************** buttons ***********************************/
			'btnClose'             : 'Sluit',
			'btnSave'              : 'Opslaan',
			'btnRm'                : 'Verwijder',
			'btnApply'             : 'Toepassen',
			'btnCancel'            : 'Annuleren',
			'btnNo'                : 'Nee',
			'btnYes'               : 'Ja',
			'btnMount'             : 'Mount',  // added 18.04.2012
			'btnApprove'           : 'Ga naar $1 & keur goed', // from v2.1 added 26.04.2012
			'btnUnmount'           : 'Unmount', // from v2.1 added 30.04.2012
			'btnConv'              : 'Converteer', // from v2.1 added 08.04.2014
			'btnCwd'               : 'Hier',      // from v2.1 added 22.5.2015
			'btnVolume'            : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'               : 'Alles',       // from v2.1 added 22.5.2015
			'btnMime'              : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName'          : 'Bestandsnaam',  // from v2.1 added 22.5.2015
			'btnSaveClose'         : 'Opslaan & Sluiten', // from v2.1 added 12.6.2015
			'btnBackup'            : 'Back-up', // fromv2.1 added 28.11.2015
			'btnRename'            : 'Hernoemen',      // from v2.1.24 added 6.4.2017
			'btnRenameAll'         : 'Hernoem alles', // from v2.1.24 added 6.4.2017
			'btnPrevious'          : 'Vorige ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'              : 'Volgende ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'            : 'Opslaan als', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'              : 'Bezig met openen van map',
			'ntffile'              : 'Bezig met openen bestand',
			'ntfreload'            : 'Herladen map inhoud',
			'ntfmkdir'             : 'Bezig met map maken',
			'ntfmkfile'            : 'Bezig met Bestanden maken',
			'ntfrm'                : 'Verwijderen bestanden',
			'ntfcopy'              : 'Kopieer bestanden',
			'ntfmove'              : 'Verplaats bestanden',
			'ntfprepare'           : 'Voorbereiden kopiëren',
			'ntfrename'            : 'Hernoem bestanden',
			'ntfupload'            : 'Bestanden uploaden actief',
			'ntfdownload'          : 'Bestanden downloaden actief',
			'ntfsave'              : 'Bestanden opslaan',
			'ntfarchive'           : 'Archief aan het maken',
			'ntfextract'           : 'Bestanden uitpakken actief',
			'ntfsearch'            : 'Zoeken naar bestanden',
			'ntfresize'            : 'Formaat wijzigen van afbeeldingen',
			'ntfsmth'              : 'Iets aan het doen',
			'ntfloadimg'           : 'Laden van plaatje',
			'ntfnetmount'          : 'Mounten van netwerk volume', // added 18.04.2012
			'ntfnetunmount'        : 'Unmounten van netwerk volume', // from v2.1 added 30.04.2012
			'ntfdim'               : 'Opvragen afbeeldingen dimensies', // added 20.05.2013
			'ntfreaddir'           : 'Map informatie lezen', // from v2.1 added 01.07.2013
			'ntfurl'               : 'URL van link ophalen', // from v2.1 added 11.03.2014
			'ntfchmod'             : 'Bestandsmodus wijzigen', // from v2.1 added 20.6.2015
			'ntfpreupload'         : 'Upload bestandsnaam verifiëren', // from v2.1 added 31.11.2015
			'ntfzipdl'             : 'Zipbestand aan het maken', // from v2.1.7 added 23.1.2016
			'ntfparents'           : 'Verzamelen padinformatie', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge'        : 'Aan het verwerken', // from v2.1.17 added 2.11.2016
			'ntftrash'             : 'Aan het verwijderen', // from v2.1.24 added 2.5.2017
			'ntfrestore'           : 'Aan het herstellen', // from v2.1.24 added 3.5.2017
			'ntfchkdir'            : 'Controleren doelmap', // from v2.1.24 added 3.5.2017
			'ntfundo'              : 'Vorige bewerking ongedaan maken', // from v2.1.27 added 31.07.2017
			'ntfredo'              : 'Opnieuw doen', // from v2.1.27 added 31.07.2017
			'ntfchkcontent'        : 'Inhoud controleren', // from v2.1.41 added 3.8.2018

			/*********************************** volumes *********************************/
			'volume_Trash'         : 'Prullenbak', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown'          : 'onbekend',
			'Today'                : 'Vandaag',
			'Yesterday'            : 'Gisteren',
			'msJan'                : 'Jan',
			'msFeb'                : 'Feb',
			'msMar'                : 'Mar',
			'msApr'                : 'Apr',
			'msMay'                : 'Mei',
			'msJun'                : 'Jun',
			'msJul'                : 'Jul',
			'msAug'                : 'Aug',
			'msSep'                : 'Sep',
			'msOct'                : 'Okt',
			'msNov'                : 'Nov',
			'msDec'                : 'Dec',
			'January'              : 'Januari',
			'February'             : 'Februari',
			'March'                : 'Maart',
			'April'                : 'April',
			'May'                  : 'Mei',
			'June'                 : 'Juni',
			'July'                 : 'Juli',
			'August'               : 'Augustus',
			'September'            : 'September',
			'October'              : 'Oktober',
			'November'             : 'November',
			'December'             : 'December',
			'Sunday'               : 'Zondag',
			'Monday'               : 'Maandag',
			'Tuesday'              : 'Dinsdag',
			'Wednesday'            : 'Woensdag',
			'Thursday'             : 'Donderdag',
			'Friday'               : 'Vrijdag',
			'Saturday'             : 'Zaterdag',
			'Sun'                  : 'Zo',
			'Mon'                  : 'Ma',
			'Tue'                  : 'Di',
			'Wed'                  : 'Wo',
			'Thu'                  : 'Do',
			'Fri'                  : 'Vr',
			'Sat'                  : 'Za',

			/******************************** sort variants ********************************/
			'sortname'             : 'op naam',
			'sortkind'             : 'op type',
			'sortsize'             : 'op grootte',
			'sortdate'             : 'op datum',
			'sortFoldersFirst'     : 'Mappen eerst',
			'sortperm'             : 'op rechten', // from v2.1.13 added 13.06.2016
			'sortmode'             : 'op mode',       // from v2.1.13 added 13.06.2016
			'sortowner'            : 'op eigenaar',      // from v2.1.13 added 13.06.2016
			'sortgroup'            : 'op groep',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'     : 'Als boom',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt'    : 'NieuwBestand.txt', // added 10.11.2015
			'untitled folder'      : 'NieuweMap',   // added 10.11.2015
			'Archive'              : 'NieuwArchief',  // from v2.1 added 10.11.2015
			'untitled file'        : 'NieuwBestand.$1',  // from v2.1.41 added 6.8.2018
			'extentionfile'        : '$1: Bestand',    // from v2.1.41 added 6.8.2018
			'extentiontype'        : '$1: $2',      // from v2.1.43 added 17.10.2018

			/********************************** messages **********************************/
			'confirmReq'           : 'Bevestiging nodig',
			'confirmRm'            : 'Weet u zeker dat u deze bestanden wil verwijderen?<br/>Deze actie kan niet ongedaan gemaakt worden!',
			'confirmRepl'          : 'Oud bestand vervangen door het nieuwe bestand?',
			'confirmRest'          : 'Replace existing item with the item in trash?', // fromv2.1.24 added 5.5.2017						
			'confirmConvUTF8'      : 'Niet in UTF-8<br/>Converteren naar UTF-8?<br/>De inhoud wordt UTF-8 door op te slaan na de conversie', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Character encoding of this file couldn\'t be detected. It need to temporarily convert to UTF-8 for editting.<br/>Please select character encoding of this file.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'       : 'Het is aangepast.<br/>Wijzigingen gaan verloren als je niet opslaat', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Are you sure you want to move items to trash bin?', //from v2.1.24 added 29.4.2017
			'apllyAll'             : 'Toepassen op alles',
			'name'                 : 'Naam',
			'size'                 : 'Grootte',
			'perms'                : 'Rechten',
			'modify'               : 'Aangepast',
			'kind'                 : 'Type',
			'read'                 : 'lees',
			'write'                : 'schrijf',
			'noaccess'             : 'geen toegang',
			'and'                  : 'en',
			'unknown'              : 'onbekend',
			'selectall'            : 'Selecteer alle bestanden',
			'selectfiles'          : 'Selecteer bestand(en)',
			'selectffile'          : 'Selecteer eerste bestand',
			'selectlfile'          : 'Selecteer laatste bestand',
			'viewlist'             : 'Lijst weergave',
			'viewicons'            : 'Icoon weergave',
			'viewSmall'            : 'Klein', // from v2.1.39 added 22.5.2018
			'viewMedium'           : 'Middelgroot', // from v2.1.39 added 22.5.2018
			'viewLarge'            : 'Groot', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'       : 'Extra groot', // from v2.1.39 added 22.5.2018
			'places'               : 'Plaatsen',
			'calc'                 : 'Bereken',
			'path'                 : 'Pad',
			'aliasfor'             : 'Alias voor',
			'locked'               : 'Vergrendeld',
			'dim'                  : 'Dimensies',
			'files'                : 'Bestanden',
			'folders'              : 'Mappen',
			'items'                : 'Items',
			'yes'                  : 'ja',
			'no'                   : 'nee',
			'link'                 : 'Link',
			'searcresult'          : 'Zoek resultaten',
			'selected'             : 'geselecteerde items',
			'about'                : 'Over',
			'shortcuts'            : 'Snelkoppelingen',
			'help'                 : 'Help',
			'webfm'                : 'Web bestandsmanager',
			'ver'                  : 'Versie',
			'protocolver'          : 'protocol versie',
			'homepage'             : 'Project home',
			'docs'                 : 'Documentatie',
			'github'               : 'Fork ons op Github',
			'twitter'              : 'Volg ons op twitter',
			'facebook'             : 'Wordt lid op facebook',
			'team'                 : 'Team',
			'chiefdev'             : 'Hoofd ontwikkelaar',
			'developer'            : 'ontwikkelaar',
			'contributor'          : 'bijdrager',
			'maintainer'           : 'onderhouder',
			'translator'           : 'vertaler',
			'icons'                : 'Iconen',
			'dontforget'           : 'En vergeet je handdoek niet!',
			'shortcutsof'          : 'Snelkoppelingen uitgeschakeld',
			'dropFiles'            : 'Sleep hier uw bestanden heen',
			'or'                   : 'of',
			'selectForUpload'      : 'Selecteer bestanden om te uploaden',
			'moveFiles'            : 'Verplaats bestanden',
			'copyFiles'            : 'Kopieer bestanden',
			'restoreFiles'         : 'Items herstellen', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'         : 'Verwijder uit Plaatsen',
			'aspectRatio'          : 'Aspect ratio',
			'scale'                : 'Schaal',
			'width'                : 'Breedte',
			'height'               : 'Hoogte',
			'resize'               : 'Verkleinen',
			'crop'                 : 'Bijsnijden',
			'rotate'               : 'Draaien',
			'rotate-cw'            : 'Draai 90 graden rechtsom',
			'rotate-ccw'           : 'Draai 90 graden linksom',
			'degree'               : '°',
			'netMountDialogTitle'  : 'Mount netwerk volume', // added 18.04.2012
			'protocol'             : 'Protocol', // added 18.04.2012
			'host'                 : 'Host', // added 18.04.2012
			'port'                 : 'Poort', // added 18.04.2012
			'user'                 : 'Gebruikersnaams', // added 18.04.2012
			'pass'                 : 'Wachtwoord', // added 18.04.2012
			'confirmUnmount'       : 'Weet u zeker dat u $1 wil unmounten?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser'     : 'Sleep of plak bestanden vanuit de browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'       : 'Sleep of plak bestanden hier', // from v2.1 added 07.04.2014
			'encoding'             : 'Encodering', // from v2.1 added 19.12.2014
			'locale'               : 'Localisatie',   // from v2.1 added 19.12.2014
			'searchTarget'         : 'Doel: $1',                // from v2.1 added 22.5.2015
			'searchMime'           : 'Zoek op invoer MIME Type', // from v2.1 added 22.5.2015
			'owner'                : 'Eigenaar', // from v2.1 added 20.6.2015
			'group'                : 'Groep', // from v2.1 added 20.6.2015
			'other'                : 'Overig', // from v2.1 added 20.6.2015
			'execute'              : 'Uitvoeren', // from v2.1 added 20.6.2015
			'perm'                 : 'Rechten', // from v2.1 added 20.6.2015
			'mode'                 : 'Modus', // from v2.1 added 20.6.2015
			'emptyFolder'          : 'Map is leeg', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop'      : 'Map is leeg\\A Sleep hier naar toe om toe te voegen', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap'      : 'Map is leeg\\A Lang ingedrukt houden om toe te voegen', // from v2.1.6 added 30.12.2015
			'quality'              : 'Kwaliteit', // from v2.1.6 added 5.1.2016
			'autoSync'             : 'Auto sync',  // from v2.1.6 added 10.1.2016
			'moveUp'               : 'Omhoog',  // from v2.1.6 added 18.1.2016
			'getLink'              : 'Geef link', // from v2.1.7 added 9.2.2016
			'selectedItems'        : 'Geselecteerde items ($1)', // from v2.1.7 added 2.19.2016
			'folderId'             : 'Map ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'        : 'Toestaan offline toegang', // from v2.1.10 added 3.25.2016
			'reAuth'               : 'Opnieuw autenticeren', // from v2.1.10 added 3.25.2016
			'nowLoading'           : 'Laden..', // from v2.1.12 added 4.26.2016
			'openMulti'            : 'Open meerdere bestanden', // from v2.1.12 added 5.14.2016
			'openMultiConfirm'     : 'Je probeert het $1 bestanden te openen. Weet je zeker dat je dat in je browser wil doen?', // from v2.1.12 added 5.14.2016
			'emptySearch'          : 'Geen zoekresultaten', // from v2.1.12 added 5.16.2016
			'editingFile'          : 'Bestand wordt bewerkt', // from v2.1.13 added 6.3.2016
			'hasSelected'          : 'Je hebt $1 items geselecteerd', // from v2.1.13 added 6.3.2016
			'hasClipboard'         : 'Je hebt $1 items op het clipboard', // from v2.1.13 added 6.3.2016
			'incSearchOnly'        : 'Verder zoeken kan alleen vanuit huidige view', // from v2.1.13 added 6.30.2016
			'reinstate'            : 'Herstellen', // from v2.1.15 added 3.8.2016
			'complete'             : '$1 compleet', // from v2.1.15 added 21.8.2016
			'contextmenu'          : 'Context menu', // from v2.1.15 added 9.9.2016
			'pageTurning'          : 'Pagina omslaan', // from v2.1.15 added 10.9.2016
			'volumeRoots'          : 'Volume roots', // from v2.1.16 added 16.9.2016
			'reset'                : 'Reset', // from v2.1.16 added 1.10.2016
			'bgcolor'              : 'Achtergrondkleur', // from v2.1.16 added 1.10.2016
			'colorPicker'          : 'Kleurkiezer', // from v2.1.16 added 1.10.2016
			'8pxgrid'              : '8px Grid', // from v2.1.16 added 4.10.2016
			'enabled'              : 'Actief', // from v2.1.16 added 4.10.2016
			'disabled'             : 'Inactief', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'       : 'Zoekresultaten zijn leeg in actuele view\\ADruk [Enter] om zoekgebied uit te breiden', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'       : 'Zoeken op eerste letter is leeg in actuele view', // from v2.1.23 added 24.3.2017
			'textLabel'            : 'Tekstlabel', // from v2.1.17 added 13.10.2016
			'minsLeft'             : '$1 minuten over', // from v2.1.17 added 13.11.2016
			'openAsEncoding'       : 'Opnieuw openen met geselecteerde encoding', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'       : 'Opslaan met geselecteerde encoding', // from v2.1.19 added 2.12.2016
			'selectFolder'         : 'Selecteer map', // from v2.1.20 added 13.12.2016
			'firstLetterSearch'    : 'Zoeken op eerste letter', // from v2.1.23 added 24.3.2017
			'presets'              : 'Voorkeuren', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'       : 'Teveel voor in de prullenbak', // from v2.1.25 added 9.6.2017
			'TextArea'             : 'Tekstgebied', // from v2.1.25 added 14.6.2017
			'folderToEmpty'        : 'Map "$1" legen', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'        : 'Er zijn geen items in map "$1"', // from v2.1.25 added 22.6.2017
			'preference'           : 'Voorkeur', // from v2.1.26 added 28.6.2017
			'language'             : 'Taal', // from v2.1.26 added 28.6.2017
			'clearBrowserData'     : 'Initialiseer instellingen van deze browser', // from v2.1.26 added 28.6.2017
			'toolbarPref'          : 'Toolbar instellingen', // from v2.1.27 added 2.8.2017
			'charsLeft'            : '... $1 tekens over',  // from v2.1.29 added 30.8.2017
			'sum'                  : 'Totaal', // from v2.1.29 added 28.9.2017
			'roughFileSize'        : 'Geschatte bestandsgrootte', // from v2.1.30 added 2.11.2017
			'autoFocusDialog'      : 'Focus op het dialoogelement met mouseover',  // from v2.1.30 added 2.11.2017
			'select'               : 'Selecteren', // from v2.1.30 added 23.11.2017
			'selectAction'         : 'Actie als bestand is geselecteerd', // from v2.1.30 added 23.11.2017
			'useStoredEditor'      : 'Open met laatstgebruikte editor', // from v2.1.30 added 23.11.2017
			'selectinvert'         : 'Selectie omkeren', // from v2.1.30 added 25.11.2017
			'renameMultiple'       : 'Weet je zeker dat je $1 items wil hernoemen naar $2?<br/>Dit kan niet ongedaan worden gemaakt!', // from v2.1.31 added 4.12.2017
			'batchRename'          : 'Batch hernoemen', // from v2.1.31 added 8.12.2017
			'plusNumber'           : '+ Nummer', // from v2.1.31 added 8.12.2017
			'asPrefix'             : 'Voeg prefix toe', // from v2.1.31 added 8.12.2017
			'asSuffix'             : 'Voeg suffix toe', // from v2.1.31 added 8.12.2017
			'changeExtention'      : 'Verander extentie', // from v2.1.31 added 8.12.2017
			'columnPref'           : 'Kolominstelllingen (List view)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate'   : 'Aanpassingen worden direct toegepast op het archief', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'     : 'Aanpassingen worden pas toegepast na re-mount van dit volume', // from v2.1.33 added 2.3.2018
			'unmountChildren'      : 'Deze volume(s) worden ook unmounted. Weet je het zeker?', // from v2.1.33 added 5.3.2018
			'selectionInfo'        : 'Selectie informatie', // from v2.1.33 added 7.3.2018
			'hashChecker'          : 'Algoritmes voor file hash', // from v2.1.33 added 10.3.2018
			'infoItems'            : 'Informatie Items (Selectie Info Panel)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit'     : 'Druk nogmaals om te eindigen', // from v2.1.38 added 1.4.2018
			'toolbar'              : 'Toolbar', // from v2.1.38 added 4.4.2018
			'workspace'            : 'Work Space', // from v2.1.38 added 4.4.2018
			'dialog'               : 'Dialoog', // from v2.1.38 added 4.4.2018
			'all'                  : 'Alles', // from v2.1.38 added 4.4.2018
			'iconSize'             : 'Icoongrootte (Icons view)', // from v2.1.39 added 7.5.2018
			'editorMaximized'      : 'Open de maximale editor', // from v2.1.40 added 30.6.2018
			'editorConvNoApi'      : 'Conversie via API is niet beschikbaar, converteer aub op de website', //from v2.1.40 added 8.7.2018
			'editorConvNeedUpload' : 'After conversion, you must be upload with the item URL or a downloaded file to save the converted file', //from v2.1.40 added 8.7.2018
			'convertOn'            : 'Converteer op de site $1', // from v2.1.40 added 10.7.2018
			'integrations'         : 'Integratie', // from v2.1.40 added 11.7.2018
			'integrationWith'      : 'Deze elFinder heeft de volgende externe services. Controleer de voorwaarden, privacy policy, etc. voor gebruik', // from v2.1.40 added 11.7.2018
			'showHidden'           : 'Toon verborgen items', // from v2.1.41 added 24.7.2018
			'hideHidden'           : 'Verberg verborgen items', // from v2.1.41 added 24.7.2018
			'toggleHidden'         : 'Toon/verberg verborgen items', // from v2.1.41 added 24.7.2018
			'makefileTypes'        : 'File types die aangemaakt mogen worden', // from v2.1.41 added 7.8.2018
			'typeOfTextfile'       : 'Type voor tekstbestand', // from v2.1.41 added 7.8.2018
			'add'                  : 'Toevoegen', // from v2.1.41 added 7.8.2018
			'theme'                : 'Thema', // from v2.1.43 added 19.10.2018
			'default'              : 'Default', // from v2.1.43 added 19.10.2018
			'description'          : 'Beschrijving', // from v2.1.43 added 19.10.2018
			'website'              : 'Website', // from v2.1.43 added 19.10.2018
			'author'               : 'Auteur', // from v2.1.43 added 19.10.2018
			'email'                : 'Email', // from v2.1.43 added 19.10.2018
			'license'              : 'Licensie', // from v2.1.43 added 19.10.2018
			'exportToSave'         : 'Dit item kan niet worden opgeslagen, exporteer naar je pc om wijzingen te bewaren', // from v2.1.44 added 1.12.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'          : 'Onbekend',
			'kindRoot'             : 'Volume Root', // from v2.1.16 added 16.10.2016
			'kindFolder'           : 'Map',
			'kindSelects'          : 'Selecties', // from v2.1.29 added 29.8.2017
			'kindAlias'            : 'Alias',
			'kindAliasBroken'      : 'Verbroken alias',
			
			/********************************** applications **********************************/
			'kindApp'              : 'Applicatie',
			'kindPostscript'       : 'Postscript document',
			'kindMsOffice'         : 'Microsoft Office document',
			'kindMsWord'           : 'Microsoft Word document',
			'kindMsExcel'          : 'Microsoft Excel document',
			'kindMsPP'             : 'Microsoft Powerpoint presentation',
			'kindOO'               : 'Open Office document',
			'kindAppFlash'         : 'Flash applicatie',
			'kindPDF'              : 'Portable Document Format (PDF)',
			'kindTorrent'          : 'Bittorrent bestand',
			'kind7z'               : '7z archief',
			'kindTAR'              : 'TAR archief',
			'kindGZIP'             : 'GZIP archief',
			'kindBZIP'             : 'BZIP archief',
			'kindXZ'               : 'XZ archief',
			'kindZIP'              : 'ZIP archief',
			'kindRAR'              : 'RAR archief',
			'kindJAR'              : 'Java JAR bestand',
			'kindTTF'              : 'True Type font',
			'kindOTF'              : 'Open Type font',
			'kindRPM'              : 'RPM package',
			
			/********************************** texts **********************************/
			'kindText'             : 'Tekst bestand',
			'kindTextPlain'        : 'Tekst',
			'kindPHP'              : 'PHP bronbestand',
			'kindCSS'              : 'Cascading style sheet',
			'kindHTML'             : 'HTML document',
			'kindJS'               : 'Javascript bronbestand',
			'kindRTF'              : 'Rich Text Format',
			'kindC'                : 'C bronbestand',
			'kindCHeader'          : 'C header bronbestand',
			'kindCPP'              : 'C++ bronbestand',
			'kindCPPHeader'        : 'C++ header bronbestand',
			'kindShell'            : 'Unix shell script',
			'kindPython'           : 'Python bronbestand',
			'kindJava'             : 'Java bronbestand',
			'kindRuby'             : 'Ruby bronbestand',
			'kindPerl'             : 'Perl bronbestand',
			'kindSQL'              : 'SQL bronbestand',
			'kindXML'              : 'XML document',
			'kindAWK'              : 'AWK bronbestand',
			'kindCSV'              : 'Komma gescheiden waardes',
			'kindDOCBOOK'          : 'Docbook XML document',
			'kindMarkdown'         : 'Markdown tekst', // added 20.7.2015
			
			/********************************** images **********************************/
			
			//               
			'kindImage'            : 'Afbeelding',
			'kindBMP'              : 'BMP afbeelding',
			'kindJPEG'             : 'JPEG afbeelding',
			'kindGIF'              : 'GIF afbeelding',
			'kindPNG'              : 'PNG afbeelding',
			'kindTIFF'             : 'TIFF afbeelding',
			'kindTGA'              : 'TGA afbeelding',
			'kindPSD'              : 'Adobe Photoshop afbeelding',
			'kindXBITMAP'          : 'X bitmap afbeelding',
			'kindPXM'              : 'Pixelmator afbeelding',
			
			/********************************** media **********************************/
			'kindAudio'            : 'Audio media',
			'kindAudioMPEG'        : 'MPEG audio',
			'kindAudioMPEG4'       : 'MPEG-4 audio',
			'kindAudioMIDI'        : 'MIDI audio',
			'kindAudioOGG'         : 'Ogg Vorbis audio',
			'kindAudioWAV'         : 'WAV audio',
			'AudioPlaylist'        : 'MP3 playlist',
			'kindVideo'            : 'Video media',
			'kindVideoDV'          : 'DV video',
			'kindVideoMPEG'        : 'MPEG video',
			'kindVideoMPEG4'       : 'MPEG-4 video',
			'kindVideoAVI'         : 'AVI video',
			'kindVideoMOV'         : 'Quick Time video',
			'kindVideoWM'          : 'Windows Media video',
			'kindVideoFlash'       : 'Flash video',
			'kindVideoMKV'         : 'Matroska video',
			'kindVideoOGG'         : 'Ogg video'
		}
	};
}));

