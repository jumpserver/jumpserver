/**
 * Italiano translation
 * @author Alberto Tocci (alberto.tocci@gmail.com)
 * @author Claudio Nicora (coolsoft.ita@gmail.com)
 * @version 2016-12-12
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
	elFinder.prototype.i18.it = {
		translator : 'Alberto Tocci (alberto.tocci@gmail.com), Claudio Nicora (coolsoft.ita@gmail.com)',
		language   : 'Italiano',
		direction  : 'ltr',
		dateFormat : 'd/m/Y H:i',
		fancyDateFormat : '$1 H:i',
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Errore',
			'errUnknown'           : 'Errore sconosciuto.',
			'errUnknownCmd'        : 'Comando sconosciuto.',
			'errJqui'              : 'Configurazione JQuery UI non valida. Devono essere inclusi i plugin Selectable, Draggable e Droppable.',
			'errNode'              : 'elFinder necessita dell\'elemento DOM per essere inizializzato.',
			'errURL'               : 'Configurazione non valida.Il parametro URL non è settato.',
			'errAccess'            : 'Accesso non consentito.',
			'errConnect'           : 'Impossibile collegarsi al backend.',
			'errAbort'             : 'Connessione annullata.',
			'errTimeout'           : 'Timeout di connessione.',
			'errNotFound'          : 'Backend non trovato.',
			'errResponse'          : 'Risposta non valida dal backend.',
			'errConf'              : 'Configurazione backend non valida.',
			'errJSON'              : 'Modulo PHP JSON non installato.',
			'errNoVolumes'         : 'Non è stato possibile leggere i volumi.',
			'errCmdParams'         : 'Parametri non validi per il comando "$1".',
			'errDataNotJSON'       : 'I dati non sono nel formato JSON.',
			'errDataEmpty'         : 'Stringa vuota.',
			'errCmdReq'            : 'La richiesta al backend richiede il nome del comando.',
			'errOpen'              : 'Impossibile aprire "$1".',
			'errNotFolder'         : 'L\'oggetto non è una cartella..',
			'errNotFile'           : 'L\'oggetto non è un file.',
			'errRead'              : 'Impossibile leggere "$1".',
			'errWrite'             : 'Non è possibile scrivere in "$1".',
			'errPerm'              : 'Permesso negato.',
			'errLocked'            : '"$1" è bloccato e non può essere rinominato, spostato o eliminato.',
			'errExists'            : 'Il file "$1" è già esistente.',
			'errInvName'           : 'Nome file non valido.',
			'errFolderNotFound'    : 'Cartella non trovata.',
			'errFileNotFound'      : 'File non trovato.',
			'errTrgFolderNotFound' : 'La cartella di destinazione"$1" non è stata trovata.',
			'errPopup'             : 'Il tuo Browser non consente di aprire finestre di pop-up. Per aprire il file abilita questa opzione nelle impostazioni del tuo Browser.',
			'errMkdir'             : 'Impossibile creare la cartella "$1".',
			'errMkfile'            : 'Impossibile creare il file "$1".',
			'errRename'            : 'Impossibile rinominare "$1".',
			'errCopyFrom'          : 'Non è possibile copiare file da "$1".',
			'errCopyTo'            : 'Non è possibile copiare file in "$1".',
			'errMkOutLink'         : 'Impossibile creare un link all\'esterno della radice del volume.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Errore di Caricamento.',  // old name - errUploadCommon
			'errUploadFile'        : 'Impossibile Caricare "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Non sono stati specificati file da caricare.',
			'errUploadTotalSize'   : 'La dimensione totale dei file supera il limite massimo consentito.', // old name - errMaxSize
			'errUploadFileSize'    : 'Le dimensioni del file superano il massimo consentito.', //  old name - errFileMaxSize
			'errUploadMime'        : 'FileType non consentito.',
			'errUploadTransfer'    : 'Trasferimento errato del file "$1".',
			'errUploadTemp'        : 'Impossibile creare il file temporaneo per l\'upload.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'L\'oggetto "$1" esiste già in questa cartella e non può essere sostituito con un oggetto di un tipo differente.', // new
			'errReplace'           : 'Impossibile sostituire "$1".',
			'errSave'              : 'Impossibile salvare "$1".',
			'errCopy'              : 'Impossibile copiare "$1".',
			'errMove'              : 'Impossibile spostare "$1".',
			'errCopyInItself'      : 'Sorgente e destinazione risultato essere uguali.',
			'errRm'                : 'Impossibile rimuovere "$1".',
			'errRmSrc'             : 'Impossibile eliminare i file origine.',
			'errExtract'           : 'Impossibile estrarre file da "$1".',
			'errArchive'           : 'Impossibile creare archivio.',
			'errArcType'           : 'Tipo di archivio non supportato.',
			'errNoArchive'         : 'Il file non è un archivio o contiene file non supportati.',
			'errCmdNoSupport'      : 'Il Backend non supporta questo comando.',
			'errReplByChild'       : 'La cartella $1 non può essere sostituita da un oggetto in essa contenuto.',
			'errArcSymlinks'       : 'Per questioni di sicurezza non è possibile estrarre archivi che contengono collegamenti..', // edited 24.06.2012
			'errArcMaxSize'        : 'La dimensione dell\'archivio supera le massime dimensioni consentite.',
			'errResize'            : 'Impossibile ridimensionare "$1".',
			'errResizeDegree'      : 'Angolo di rotazione non valido.',  // added 7.3.2013
			'errResizeRotate'      : 'Impossibile ruotare l\'immagine.',  // added 7.3.2013
			'errResizeSize'        : 'Dimensione dell\'immagine non valida.',  // added 7.3.2013
			'errResizeNoChange'    : 'Dimensione dell\'immagine non modificata.',  // added 7.3.2013
			'errUsupportType'      : 'Tipo di file non supportato.',
			'errNotUTF8Content'    : 'Il file "$1" non è nel formato UTF-8 e non può essere modificato.',  // added 9.11.2011
			'errNetMount'          : 'Impossibile montare "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Protocollo non supportato.',     // added 17.04.2012
			'errNetMountFailed'    : 'Mount fallito.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Necessario host.', // added 18.04.2012
			'errSessionExpires'    : 'La sessione è scaduta a causa di inattività.',
			'errCreatingTempDir'   : 'Impossibile creare la cartella temporanea: "$1"',
			'errFtpDownloadFile'   : 'Impossibile scaricare il file tramite FTP: "$1"',
			'errFtpUploadFile'     : 'Impossibile caricare il file tramite FTP: "$1"',
			'errFtpMkdir'          : 'Impossibile creare la cartella remota tramite FTP: "$1"',
			'errArchiveExec'       : 'Errore durante l\'archiviazione dei file: "$1"',
			'errExtractExec'       : 'Errore durante l\'estrazione dei file: "$1"',
			'errNetUnMount'        : 'Impossibile smontare', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Non convertibile nel formato UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Per uploadare l0intera cartella usare Google Chrome.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Timeout durante la ricerca di "$1". I risultati della ricerca sono parziali.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'E\' necessaria la riautorizzazione.', // from v2.1.10 added 3.24.2016

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Crea archivio',
			'cmdback'      : 'Indietro',
			'cmdcopy'      : 'Copia',
			'cmdcut'       : 'Taglia',
			'cmddownload'  : 'Download',
			'cmdduplicate' : 'Duplica',
			'cmdedit'      : 'Modifica File',
			'cmdextract'   : 'Estrai Archivio',
			'cmdforward'   : 'Avanti',
			'cmdgetfile'   : 'Seleziona File',
			'cmdhelp'      : 'About',
			'cmdhome'      : 'Home',
			'cmdinfo'      : 'Informazioni',
			'cmdmkdir'     : 'Nuova cartella',
			'cmdmkdirin'   : 'In una nuova cartella', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nuovo file di testo',
			'cmdopen'      : 'Apri',
			'cmdpaste'     : 'Incolla',
			'cmdquicklook' : 'Anteprima',
			'cmdreload'    : 'Ricarica',
			'cmdrename'    : 'Rinomina',
			'cmdrm'        : 'Elimina',
			'cmdsearch'    : 'Ricerca file',
			'cmdup'        : 'Vai alla directory padre',
			'cmdupload'    : 'Carica File',
			'cmdview'      : 'Visualizza',
			'cmdresize'    : 'Ridimensiona Immagine',
			'cmdsort'      : 'Ordina',
			'cmdnetmount'  : 'Monta disco di rete', // added 18.04.2012
			'cmdnetunmount': 'Smonta', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'To Places', // added 28.12.2014
			'cmdchmod'     : 'Cambia modalità', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Apri una cartella', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Reimposta dimensione colonne', // from v2.1.13 added 12.06.2016

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Chiudi',
			'btnSave'   : 'Salva',
			'btnRm'     : 'Elimina',
			'btnApply'  : 'Applica',
			'btnCancel' : 'Annulla',
			'btnNo'     : 'No',
			'btnYes'    : 'Si',
			'btnMount'  : 'Monta',  // added 18.04.2012
			'btnApprove': 'Vai a $1 & approva', // from v2.1 added 26.04.2012
			'btnUnmount': 'Smonta', // from v2.1 added 30.04.2012
			'btnConv'   : 'Converti', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Qui',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Disco',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Tutti',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Type', // from v2.1 added 22.5.2015
			'btnFileName':'Nome file',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Salva & Chiudi', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Apri cartella',
			'ntffile'     : 'Apri file',
			'ntfreload'   : 'Ricarica il contenuto della cartella',
			'ntfmkdir'    : 'Creazione delle directory in corso',
			'ntfmkfile'   : 'Creazione dei files in corso',
			'ntfrm'       : 'Eliminazione dei files in corso',
			'ntfcopy'     : 'Copia file in corso',
			'ntfmove'     : 'Spostamento file in corso',
			'ntfprepare'  : 'Preparazione della copia dei file.',
			'ntfrename'   : 'Sto rinominando i file',
			'ntfupload'   : 'Caricamento file in corso',
			'ntfdownload' : 'Downloading file in corso',
			'ntfsave'     : 'Salvataggio file in corso',
			'ntfarchive'  : 'Creazione archivio in corso',
			'ntfextract'  : 'Estrazione file dall\'archivio in corso',
			'ntfsearch'   : 'Ricerca files in corso',
			'ntfresize'   : 'Ridimensionamento immagini',
			'ntfsmth'     : 'Operazione in corso. Attendere...',
			'ntfloadimg'  : 'Caricamento immagine in corso',
			'ntfnetmount' : 'Montaggio disco di rete', // added 18.04.2012
			'ntfnetunmount': 'Smontaggio disco di rete', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Lettura dimensioni immagine', // added 20.05.2013
			'ntfreaddir'  : 'Lettura informazioni cartella', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Lettura URL del collegamento', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Modifica della modalità del file', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verifica del nome del file caricato', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Creazione del file da scaricare', // from v2.1.7 added 23.1.2016

			/************************************ dates **********************************/
			'dateUnknown' : 'sconosciuto',
			'Today'       : 'Oggi',
			'Yesterday'   : 'Ieri',
			'msJan'       : 'Gen',
			'msFeb'       : 'Feb',
			'msMar'       : 'Mar',
			'msApr'       : 'Apr',
			'msMay'       : 'Mag',
			'msJun'       : 'Giu',
			'msJul'       : 'Lug',
			'msAug'       : 'Ago',
			'msSep'       : 'Set',
			'msOct'       : 'Ott',
			'msNov'       : 'Nov',
			'msDec'       : 'Dic',
			'January'     : 'Gennaio',
			'February'    : 'Febbraio',
			'March'       : 'Marzo',
			'April'       : 'Aprile',
			'May'         : 'Maggio',
			'June'        : 'Giugno',
			'July'        : 'Luglio',
			'August'      : 'Agosto',
			'September'   : 'Settembre',
			'October'     : 'Ottobre',
			'November'    : 'Novembre',
			'December'    : 'Dicembre',
			'Sunday'      : 'Domenica',
			'Monday'      : 'Lunedì',
			'Tuesday'     : 'Martedì',
			'Wednesday'   : 'Mercoledì',
			'Thursday'    : 'Giovedì',
			'Friday'      : 'Venerdì',
			'Saturday'    : 'Sabato',
			'Sun'         : 'Dom',
			'Mon'         : 'Lun',
			'Tue'         : 'Mar',
			'Wed'         : 'Mer',
			'Thu'         : 'Gio',
			'Fri'         : 'Ven',
			'Sat'         : 'Sab',

			/******************************** sort variants ********************************/
			'sortname'          : 'per nome',
			'sortkind'          : 'per tipo',
			'sortsize'          : 'per dimensione',
			'sortdate'          : 'per data',
			'sortFoldersFirst'  : 'cartelle in testa',
			'sortperm'          : 'per permessi', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'per modalità',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'per possessore',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'per gruppo',      // from v2.1.13 added 13.06.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NuovoFile.txt', // added 10.11.2015
			'untitled folder'   : 'NuovaCartella',   // added 10.11.2015
			'Archive'           : 'NuovoArchivio',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Conferma richiesta',
			'confirmRm'       : 'Sei sicuro di voler eliminare i file?<br />L\'operazione non è reversibile!',
			'confirmRepl'     : 'Sostituire i file ?',
			'confirmConvUTF8' : 'Non in formato UTF-8<br/>Convertire in UTF-8?<br/>Il contenuto diventerà UTF-8 salvando dopo la conversione.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Il contenuto è stato modificato.<br/>Le modifiche andranno perse se non si salveranno.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Applica a tutti',
			'name'            : 'Nome',
			'size'            : 'Dimensione',
			'perms'           : 'Permessi',
			'modify'          : 'Modificato il',
			'kind'            : 'Tipo',
			'read'            : 'lettura',
			'write'           : 'scrittura',
			'noaccess'        : 'nessun accesso',
			'and'             : 'e',
			'unknown'         : 'sconosciuto',
			'selectall'       : 'Seleziona tutti i file',
			'selectfiles'     : 'Seleziona file',
			'selectffile'     : 'Seleziona il primo file',
			'selectlfile'     : 'Seleziona l\'ultimo file',
			'viewlist'        : 'Visualizza Elenco',
			'viewicons'       : 'Visualizza Icone',
			'places'          : 'Places',
			'calc'            : 'Calcola',
			'path'            : 'Percorso',
			'aliasfor'        : 'Alias per',
			'locked'          : 'Bloccato',
			'dim'             : 'Dimensioni',
			'files'           : 'File',
			'folders'         : 'Cartelle',
			'items'           : 'Oggetti',
			'yes'             : 'si',
			'no'              : 'no',
			'link'            : 'Collegamento',
			'searcresult'     : 'Risultati ricerca',
			'selected'        : 'oggetti selezionati',
			'about'           : 'Informazioni',
			'shortcuts'       : 'Scorciatoie',
			'help'            : 'Aiuto',
			'webfm'           : 'Web file manager',
			'ver'             : 'Versione',
			'protocolver'     : 'versione protocollo',
			'homepage'        : 'Home del progetto',
			'docs'            : 'Documentazione',
			'github'          : 'Seguici su Github',
			'twitter'         : 'Seguici su Twitter',
			'facebook'        : 'Seguici su Facebook',
			'team'            : 'Team',
			'chiefdev'        : 'sviluppatore capo',
			'developer'       : 'sviluppatore',
			'contributor'     : 'collaboratore',
			'maintainer'      : 'manutentore',
			'translator'      : 'traduttore',
			'icons'           : 'Icone',
			'dontforget'      : 'e non dimenticate di portare l\'asciugamano',
			'shortcutsof'     : 'Scorciatoie disabilitate',
			'dropFiles'       : 'Trascina i file qui',
			'or'              : 'o',
			'selectForUpload' : 'Seleziona file da caricare',
			'moveFiles'       : 'Sposta file',
			'copyFiles'       : 'Copia file',
			'rmFromPlaces'    : 'Rimuovi da places',
			'aspectRatio'     : 'Proporzioni',
			'scale'           : 'Scala',
			'width'           : 'Larghezza',
			'height'          : 'Altezza',
			'resize'          : 'Ridimensione',
			'crop'            : 'Ritaglia',
			'rotate'          : 'Ruota',
			'rotate-cw'       : 'Ruota di 90° in senso orario',
			'rotate-ccw'      : 'Ruota di 90° in senso antiorario',
			'degree'          : 'Gradi',
			'netMountDialogTitle' : 'Monta disco di rete', // added 18.04.2012
			'protocol'            : 'Protocollo', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Porta', // added 18.04.2012
			'user'                : 'Utente', // added 18.04.2012
			'pass'                : 'Password', // added 18.04.2012
			'confirmUnmount'      : 'Vuoi smontare $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Rilascia o incolla dal browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Rilascia o incolla files e indirizzi URL qui', // from v2.1 added 07.04.2014
			'encoding'        : 'Codifica', // from v2.1 added 19.12.2014
			'locale'          : 'Lingua',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Destinazione: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Cerca per MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'Possessore', // from v2.1 added 20.6.2015
			'group'           : 'Gruppo', // from v2.1 added 20.6.2015
			'other'           : 'Altri', // from v2.1 added 20.6.2015
			'execute'         : 'Esegui', // from v2.1 added 20.6.2015
			'perm'            : 'Permessi', // from v2.1 added 20.6.2015
			'mode'            : 'Modalità', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'La cartella è vuota', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'La cartella è vuota\\A Trascina e rilascia per aggiungere elementi', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'La cartella è vuota\\A Premi a lungo per aggiungere elementi', // from v2.1.6 added 30.12.2015
			'quality'         : 'Qualità', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Sincr. automatica',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Sposta in alto',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Mostra URL link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Elementi selezionati ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID cartella', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Permetti accesso non in linea', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Per ri-autenticarsi', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Caricamento...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Apri più files', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Stai cercando di aprire $1 files. Sei sicuro di volerli aprire nel browser?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Nessun risultato soddisfa i criteri di ricerca', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Il file è in modifica.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : '$1 elementi sono selezionati.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : '$1 elementi negli appunti.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'La ricerca incrementale è solo dalla vista corrente.', // from v2.1.13 added 6.30.2016

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Sconosciuto',
			'kindFolder'      : 'Cartella',
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Alias guasto',
			// applications
			'kindApp'         : 'Applicazione',
			'kindPostscript'  : 'Documento Postscript',
			'kindMsOffice'    : 'Documento Microsoft Office',
			'kindMsWord'      : 'Documento Microsoft Word',
			'kindMsExcel'     : 'Documento Microsoft Excel',
			'kindMsPP'        : 'Presentazione Microsoft Powerpoint',
			'kindOO'          : 'Documento Open Office',
			'kindAppFlash'    : 'Applicazione Flash',
			'kindPDF'         : 'Documento PDF',
			'kindTorrent'     : 'File Bittorrent',
			'kind7z'          : 'Archivio 7z',
			'kindTAR'         : 'Archivio TAR',
			'kindGZIP'        : 'Archivio GZIP',
			'kindBZIP'        : 'Archivio BZIP',
			'kindXZ'          : 'Archivio XZ',
			'kindZIP'         : 'Archivio ZIP',
			'kindRAR'         : 'Archivio RAR',
			'kindJAR'         : 'File Java JAR',
			'kindTTF'         : 'Font True Type',
			'kindOTF'         : 'Font Open Type',
			'kindRPM'         : 'Pacchetto RPM',
			// texts
			'kindText'        : 'Documento di testo',
			'kindTextPlain'   : 'Testo Semplice',
			'kindPHP'         : 'File PHP',
			'kindCSS'         : 'File CSS (Cascading Style Sheet)',
			'kindHTML'        : 'Documento HTML',
			'kindJS'          : 'File Javascript',
			'kindRTF'         : 'File RTF (Rich Text Format)',
			'kindC'           : 'File C',
			'kindCHeader'     : 'File C (header)',
			'kindCPP'         : 'File C++',
			'kindCPPHeader'   : 'File C++ (header)',
			'kindShell'       : 'Script Unix shell',
			'kindPython'      : 'File Python',
			'kindJava'        : 'File Java',
			'kindRuby'        : 'File Ruby',
			'kindPerl'        : 'File Perl',
			'kindSQL'         : 'File SQL',
			'kindXML'         : 'File XML',
			'kindAWK'         : 'File AWK',
			'kindCSV'         : 'File CSV (Comma separated values)',
			'kindDOCBOOK'     : 'File Docbook XML',
			'kindMarkdown'    : 'Testo markdown', // added 20.7.2015
			// images
			'kindImage'       : 'Immagine',
			'kindBMP'         : 'Immagine BMP',
			'kindJPEG'        : 'Immagine JPEG',
			'kindGIF'         : 'Immagine GIF',
			'kindPNG'         : 'Immagine PNG',
			'kindTIFF'        : 'Immagine TIFF',
			'kindTGA'         : 'Immagine TGA',
			'kindPSD'         : 'Immagine Adobe Photoshop',
			'kindXBITMAP'     : 'Immagine X bitmap',
			'kindPXM'         : 'Immagine Pixelmator',
			// media
			'kindAudio'       : 'File Audio',
			'kindAudioMPEG'   : 'Audio MPEG',
			'kindAudioMPEG4'  : 'Audio MPEG-4',
			'kindAudioMIDI'   : 'Audio MIDI',
			'kindAudioOGG'    : 'Audio Ogg Vorbis',
			'kindAudioWAV'    : 'Audio WAV',
			'AudioPlaylist'   : 'Playlist MP3',
			'kindVideo'       : 'File Video',
			'kindVideoDV'     : 'Filmato DV',
			'kindVideoMPEG'   : 'Filmato MPEG',
			'kindVideoMPEG4'  : 'Filmato MPEG-4',
			'kindVideoAVI'    : 'Filmato AVI',
			'kindVideoMOV'    : 'Filmato Quick Time',
			'kindVideoWM'     : 'Filmato Windows Media',
			'kindVideoFlash'  : 'Filmato Flash',
			'kindVideoMKV'    : 'Filmato Matroska',
			'kindVideoOGG'    : 'Filmato Ogg'
		}
	};
}));
