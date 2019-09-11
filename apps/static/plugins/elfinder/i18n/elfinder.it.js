/**
 * Italiano translation
 * @author Alberto Tocci (alberto.tocci@gmail.com)
 * @author Claudio Nicora (coolsoft.ita@gmail.com)
 * @author Stefano Galeazzi <stefano.galeazzi@probanet.it>
 * @author Thomas Camaran <camaran@gmail.com>
 * @version 2018-06-08
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
		translator : 'Alberto Tocci (alberto.tocci@gmail.com), Claudio Nicora (coolsoft.ita@gmail.com), Stefano Galeazzi &lt;stefano.galeazzi@probanet.it&gt;, Thomas Camaran &lt;camaran@gmail.com&gt;',
		language   : 'Italiano',
		direction  : 'ltr',
		dateFormat : 'd/m/Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Errore',
			'errUnknown'           : 'Errore sconosciuto.',
			'errUnknownCmd'        : 'Comando sconosciuto.',
			'errJqui'              : 'Configurazione JQuery UI non valida. Devono essere inclusi i plugin Selectable, Draggable e Droppable.',
			'errNode'              : 'elFinder necessita dell\'elemento DOM per essere inizializzato.',
			'errURL'               : 'Configurazione non valida.Il parametro URL non è settato.',
			'errAccess'            : 'Accesso negato.',
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
			'errInvDirname'        : 'Nome cartella non valido.',  // from v2.1.24 added 12.4.2017
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
			'errTrash'             : 'Impossibile cestinare.', // from v2.1.24 added 30.4.2017
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
			'errNetMountHostReq'   : 'Host richiesto.', // added 18.04.2012
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
			'errReauthRequire'     : 'E\' necessaria la riautorizzazione.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Il numero massimo di oggetti selezionabili è $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Impossibile ripristinare dal cestino: destinazione di ripristino non trovata.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Impossibile trovare un editor per questo tipo di file.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Si è verificato un errore lato server.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Impossibile svuotare la cartella "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Crea archivio',
			'cmdback'      : 'Indietro',
			'cmdcopy'      : 'Copia',
			'cmdcut'       : 'Taglia',
			'cmddownload'  : 'Scarica',
			'cmdduplicate' : 'Duplica',
			'cmdedit'      : 'Modifica File',
			'cmdextract'   : 'Estrai Archivio',
			'cmdforward'   : 'Avanti',
			'cmdgetfile'   : 'Seleziona File',
			'cmdhelp'      : 'Informazioni su...',
			'cmdhome'      : 'Home',
			'cmdinfo'      : 'Informazioni',
			'cmdmkdir'     : 'Nuova cartella',
			'cmdmkdirin'   : 'In una nuova cartella', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nuovo file',
			'cmdopen'      : 'Apri',
			'cmdpaste'     : 'Incolla',
			'cmdquicklook' : 'Anteprima',
			'cmdreload'    : 'Ricarica',
			'cmdrename'    : 'Rinomina',
			'cmdrm'        : 'Elimina',
			'cmdtrash'     : 'Nel cestino', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Ripristina', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Ricerca file',
			'cmdup'        : 'Vai alla directory padre',
			'cmdupload'    : 'Carica File',
			'cmdview'      : 'Visualizza',
			'cmdresize'    : 'Ridimensiona Immagine',
			'cmdsort'      : 'Ordina',
			'cmdnetmount'  : 'Monta disco di rete', // added 18.04.2012
			'cmdnetunmount': 'Smonta', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Aggiungi ad Accesso rapido', // added 28.12.2014
			'cmdchmod'     : 'Cambia modalità', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Apri una cartella', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Reimposta dimensione colonne', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Schermo intero', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Sposta', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Svuota la cartella', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Annulla', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Ripeti', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Preferenze', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Seleziona tutto', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Annulla selezione', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Inverti selezione', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Apri in una nuova finestra', // from v2.1.38 added 3.4.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Chiudi',
			'btnSave'   : 'Salva',
			'btnRm'     : 'Elimina',
			'btnApply'  : 'Applica',
			'btnCancel' : 'Annulla',
			'btnNo'     : 'No',
			'btnYes'    : 'Sì',
			'btnMount'  : 'Monta',  // added 18.04.2012
			'btnApprove': 'Vai a $1 & approva', // from v2.1 added 26.04.2012
			'btnUnmount': 'Smonta', // from v2.1 added 30.04.2012
			'btnConv'   : 'Converti', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Qui',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Disco',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Tutti',       // from v2.1 added 22.5.2015
			'btnMime'   : 'Tipo MIME', // from v2.1 added 22.5.2015
			'btnFileName':'Nome file',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Salva & Chiudi', // from v2.1 added 12.6.2015
			'btnBackup' : 'Backup', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Rinomina',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Rinomina (tutto)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Indietro ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Avanti ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Salva come', // from v2.1.25 added 24.5.2017

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
			'ntfparents'  : 'Ottenimento informazioni percorso', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Processazione file caricato', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Spostamento nel cestino', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Ripristino dal cestino', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Controllo cartella destinazione', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Annullamento operazione precedente', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Rifacimento precedente annullamento', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Cestino', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'Sconosciuto',
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
			'sortAlsoTreeview'  : 'Anche vista ad albero',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NuovoFile.txt', // added 10.11.2015
			'untitled folder'   : 'NuovaCartella',   // added 10.11.2015
			'Archive'           : 'NuovoArchivio',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Conferma richiesta',
			'confirmRm'       : 'Sei sicuro di voler eliminare i file?<br />L\'operazione non è reversibile!',
			'confirmRepl'     : 'Sostituire i file ?',
			'confirmRest'     : 'Rimpiazza l\'oggetto esistente con quello nel cestino?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'Non in formato UTF-8<br/>Convertire in UTF-8?<br/>Il contenuto diventerà UTF-8 salvando dopo la conversione.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'La codifica caratteri di questo file non può essere determinata. Sarà temporaneamente convertito in UTF-8 per l\'editting.<br/>Per cortesia, selezionare la codifica caratteri per il file.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Il contenuto è stato modificato.<br/>Le modifiche andranno perse se non si salveranno.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Sei sicuro di voler cestinare gli oggetti?', //from v2.1.24 added 29.4.2017
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
			'viewSmall'       : 'Icone piccole', // from v2.1.39 added 22.5.2018
			'viewMedium'      : 'Icone medie', // from v2.1.39 added 22.5.2018
			'viewLarge'       : 'Icone grandi', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'  : 'Icone molto grandi', // from v2.1.39 added 22.5.2018
			'places'          : 'Accesso rapido',
			'calc'            : 'Calcola',
			'path'            : 'Percorso',
			'aliasfor'        : 'Alias per',
			'locked'          : 'Bloccato',
			'dim'             : 'Dimensioni',
			'files'           : 'File',
			'folders'         : 'Cartelle',
			'items'           : 'Oggetti',
			'yes'             : 'sì',
			'no'              : 'no',
			'link'            : 'Collegamento',
			'searcresult'     : 'Risultati ricerca',
			'selected'        : 'oggetti selezionati',
			'about'           : 'Informazioni',
			'shortcuts'       : 'Scorciatoie',
			'help'            : 'Aiuto',
			'webfm'           : 'Gestore file WEB',
			'ver'             : 'Versione',
			'protocolver'     : 'versione protocollo',
			'homepage'        : 'Home del progetto',
			'docs'            : 'Documentazione',
			'github'          : 'Seguici su Github',
			'twitter'         : 'Seguici su Twitter',
			'facebook'        : 'Seguici su Facebook',
			'team'            : 'Gruppo',
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
			'restoreFiles'    : 'Ripristina oggetti', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Rimuovi da Accesso rapido',
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
			'reinstate'       : 'Reistanzia', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 completato', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Menu contestuale', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Orientamento pagina', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Percorsi base del volume', // from v2.1.16 added 16.9.2016
			'reset'           : 'Resetta', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Colore di sfondo', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Selettore colori', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : 'Griglia di 8px', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Abilitato', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Disabilitato', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Nessun risultato di ricerca nella vista corrente\\APremere [Invio] per espandere l\'oggetto della ricerca.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Nessun risultato di ricerca tramite prima lettera nella vista corrente.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Etichetta di testo', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 minuti rimanenti', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Riapri con la codifica di caratteri selezionata', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Salva con la codifica di caratteri selezionata', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Seleziona cartella', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Cerca tramite la prima lettera', // from v2.1.23 added 24.3.2017
			'presets'         : 'Opzioni predefinite', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Troppi oggetti da spostare nel cestino', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Area di testo', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Svuota la cartella "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'Non ci sono oggetti nella cartella "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preferenze', // from v2.1.26 added 28.6.2017
			'language'        : 'Impostazioni Lingua', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Inizializza le impostazioni salvate nel browser', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Impostazioni ToolBar', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... $1 caratteri rimanenti.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Somma', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Dimensione file approssimativa', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Fuoco sull\'elemento sotto al mouse',  // from v2.1.30 added 2.11.2017
			'select'          : 'Seleziona', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Azione quando un file è selezionato', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Apri con l\'editor usato l\'ultima volta', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Inverti selezione', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Sei sicuro di voler rinominare $1 selezionati come $2?<br/>Questo non può essere annullato!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Batch rename', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Numero', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Aggiungi prefisso', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Aggiungi sufisso', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Cambia estensione', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Impostazioni delle colonne (visualizzazione elenco)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Tutti i cambiamenti saranno immeditamente applicati.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Qualsiasi modifica non sarà visibile fino a quando non si monta questo volume.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'The following volume(s) mounted on this volume also unmounted. Are you sure to unmount it?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Seleziona Info', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algoritmi per visualizzare l\'hash del file', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Informazioni (pannello di informazioni sulla selezione)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Premi di nuovo per uscire.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Toolbar', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Spazio di lavoro', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Dialog', // from v2.1.38 added 4.4.2018
			'all'             : 'Tutti', // from v2.1.38 added 4.4.2018
			'iconSize'        : 'Dimensione icona (Visualizzazione icone)', // form v2.1.39 added 7.5.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Sconosciuto',
			'kindRoot'        : 'Percorso base del volume', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Cartella',
			'kindSelects'     : 'Selezioni', // from v2.1.29 added 29.8.2017
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

