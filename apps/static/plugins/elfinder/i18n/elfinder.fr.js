/**
 * française translation
 * @author Régis Guyomarch <regisg@gmail.com>
 * @author Benoit Delachaux <benorde33@gmail.com>
 * @author Jonathan Grunder <jonathan.grunder@gmail.com>
 * @version 2019-06-11
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
	elFinder.prototype.i18.fr = {
		translator : 'Régis Guyomarch &lt;regisg@gmail.com&gt;, Benoit Delachaux &lt;benorde33@gmail.com&gt;, Jonathan Grunder &lt;jonathan.grunder@gmail.com&gt;',
		language   : 'française',
		direction  : 'ltr',
		dateFormat : 'd/M/Y H:i', // will show like: 11/Jun/2019 19:33
		fancyDateFormat : '$1 H:i', // will show like: Aujourd'hui 19:33
		nonameDateFormat : 'ymd-His', // noname upload will show like: 190611-193346
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Erreur',
			'errUnknown'           : 'Erreur inconnue.',
			'errUnknownCmd'        : 'Commande inconnue.',
			'errJqui'              : 'Mauvaise configuration de jQuery UI. Les composants Selectable, draggable et droppable doivent être inclus.',
			'errNode'              : 'elFinder requiert que l\'élément DOM ait été créé.',
			'errURL'               : 'Mauvaise configuration d\'elFinder ! L\'option URL n\'a pas été définie.',
			'errAccess'            : 'Accès refusé.',
			'errConnect'           : 'Impossible de se connecter au backend.',
			'errAbort'             : 'Connexion interrompue.',
			'errTimeout'           : 'Délai de connexion dépassé.',
			'errNotFound'          : 'Backend non trouvé.',
			'errResponse'          : 'Mauvaise réponse du backend.',
			'errConf'              : 'Mauvaise configuration du backend.',
			'errJSON'              : 'Le module PHP JSON n\'est pas installé.',
			'errNoVolumes'         : 'Aucun volume lisible.',
			'errCmdParams'         : 'Mauvais paramétrage de la commande "$1".',
			'errDataNotJSON'       : 'Les données ne sont pas au format JSON.',
			'errDataEmpty'         : 'Données inexistantes.',
			'errCmdReq'            : 'La requête au Backend doit comporter le nom de la commande.',
			'errOpen'              : 'Impossible d\'ouvrir "$1".',
			'errNotFolder'         : 'Cet objet n\'est pas un dossier.',
			'errNotFile'           : 'Cet objet n\'est pas un fichier.',
			'errRead'              : 'Impossible de lire "$1".',
			'errWrite'             : 'Impossible d\'écrire dans "$1".',
			'errPerm'              : 'Permission refusée.',
			'errLocked'            : '"$1" est verrouillé et ne peut être déplacé ou supprimé.',
			'errExists'            : 'Un élément nommé "$1" existe déjà.',
			'errInvName'           : 'Nom de fichier incorrect.',
			'errInvDirname'        : 'Nom de dossier incorrect.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Dossier non trouvé.',
			'errFileNotFound'      : 'Fichier non trouvé.',
			'errTrgFolderNotFound' : 'Dossier destination "$1" non trouvé.',
			'errPopup'             : 'Le navigateur web a empêché l\'ouverture d\'une fenêtre "popup". Pour ouvrir le fichier, modifiez les options du navigateur web.',
			'errMkdir'             : 'Impossible de créer le dossier "$1".',
			'errMkfile'            : 'Impossible de créer le fichier "$1".',
			'errRename'            : 'Impossible de renommer "$1".',
			'errCopyFrom'          : 'Interdiction de copier des fichiers depuis le volume "$1".',
			'errCopyTo'            : 'Interdiction de copier des fichiers vers le volume "$1".',
			'errMkOutLink'         : 'Impossible de créer un lien en dehors du volume principal.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Erreur lors de l\'envoi du fichier.',  // old name - errUploadCommon
			'errUploadFile'        : 'Impossible d\'envoyer "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'Aucun fichier à envoyer.',
			'errUploadTotalSize'   : 'Les données dépassent la taille maximale allouée.', // old name - errMaxSize
			'errUploadFileSize'    : 'Le fichier dépasse la taille maximale allouée.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Type de fichier non autorisé.',
			'errUploadTransfer'    : '"$1" erreur transfert.',
			'errUploadTemp'        : 'Impossible de créer un fichier temporaire pour transférer les fichiers.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'L\'objet "$1" existe déjà à cet endroit et ne peut être remplacé par un objet d\'un type différent.', // new
			'errReplace'           : 'Impossible de remplacer "$1".',
			'errSave'              : 'Impossible de sauvegarder "$1".',
			'errCopy'              : 'Impossible de copier "$1".',
			'errMove'              : 'Impossible de déplacer "$1".',
			'errCopyInItself'      : 'Impossible de copier "$1" sur lui-même.',
			'errRm'                : 'Impossible de supprimer "$1".',
			'errTrash'             : 'Impossible de déplacer dans la corbeille', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Impossible de supprimer le(s) fichier(s) source(s).',
			'errExtract'           : 'Imbossible d\'extraire les fichiers à partir de "$1".',
			'errArchive'           : 'Impossible de créer l\'archive.',
			'errArcType'           : 'Type d\'archive non supporté.',
			'errNoArchive'         : 'Le fichier n\'est pas une archive, ou c\'est un type d\'archive non supporté.',
			'errCmdNoSupport'      : 'Le Backend ne prend pas en charge cette commande.',
			'errReplByChild'       : 'Le dossier “$1” ne peut pas être remplacé par un élément qu\'il contient.',
			'errArcSymlinks'       : 'Par mesure de sécurité, il est défendu d\'extraire une archive contenant des liens symboliques ou des noms de fichier non autorisés.', // edited 24.06.2012
			'errArcMaxSize'        : 'Les fichiers de l\'archive excèdent la taille maximale autorisée.',
			'errResize'            : 'Impossible de redimensionner "$1".',
			'errResizeDegree'      : 'Degré de rotation invalide.',  // added 7.3.2013
			'errResizeRotate'      : 'L\'image ne peut pas être tournée.',  // added 7.3.2013
			'errResizeSize'        : 'Dimension de l\'image non-valide.',  // added 7.3.2013
			'errResizeNoChange'    : 'L\'image n\'est pas redimensionnable.',  // added 7.3.2013
			'errUsupportType'      : 'Type de fichier non supporté.',
			'errNotUTF8Content'    : 'Le fichier "$1" n\'est pas en UTF-8, il ne peut être édité.',  // added 9.11.2011
			'errNetMount'          : 'Impossible de monter "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Protocole non supporté.',     // added 17.04.2012
			'errNetMountFailed'    : 'Echec du montage.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Hôte requis.', // added 18.04.2012
			'errSessionExpires'    : 'Votre session a expiré en raison de son inactivité.',
			'errCreatingTempDir'   : 'Impossible de créer le répertoire temporaire : "$1"',
			'errFtpDownloadFile'   : 'Impossible de télécharger le file depuis l\'accès FTP : "$1"',
			'errFtpUploadFile'     : 'Impossible d\'envoyer le fichier vers l\'accès FTP : "$1"',
			'errFtpMkdir'          : 'Impossible de créer un répertoire distant sur l\'accès FTP :"$1"',
			'errArchiveExec'       : 'Erreur lors de l\'archivage des fichiers : "$1"',
			'errExtractExec'       : 'Erreur lors de l\'extraction des fichiers : "$1"',
			'errNetUnMount'        : 'Impossible de démonter.', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Conversion en UTF-8 impossible', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Essayez Google Chrome, si voulez envoyer le dossier.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Délai d’attente dépassé pour la recherche "$1". Le résultat de la recherche est partiel.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Réauthorisation requise.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Le nombre maximal d\'éléments pouvant être sélectionnés est $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Impossible de restaurer la corbeille. La destination de la restauration n\'a pu être identifiée.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Aucun éditeur n\'a été trouvé pour ce type de fichier.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Une erreur est survenue du côté serveur.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Impossible de vider le dossier "$1".', // from v2.1.25 added 22.6.2017
			'moreErrors'           : 'There are $1 more errors.', // from v2.1.44 added 9.12.2018

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Créer une archive',
			'cmdback'      : 'Précédent',
			'cmdcopy'      : 'Copier',
			'cmdcut'       : 'Couper',
			'cmddownload'  : 'Télécharger',
			'cmdduplicate' : 'Dupliquer',
			'cmdedit'      : 'Éditer le fichier',
			'cmdextract'   : 'Extraire les fichiers de l\'archive',
			'cmdforward'   : 'Suivant',
			'cmdgetfile'   : 'Sélectionner les fichiers',
			'cmdhelp'      : 'À propos de ce logiciel',
			'cmdhome'      : 'Accueil',
			'cmdinfo'      : 'Informations',
			'cmdmkdir'     : 'Nouveau dossier',
			'cmdmkdirin'   : 'Dans un nouveau dossier', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nouveau fichier',
			'cmdopen'      : 'Ouvrir',
			'cmdpaste'     : 'Coller',
			'cmdquicklook' : 'Prévisualiser',
			'cmdreload'    : 'Actualiser',
			'cmdrename'    : 'Renommer',
			'cmdrm'        : 'Supprimer',
			'cmdtrash'     : 'À la corbeille', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Restaurer', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Trouver les fichiers',
			'cmdup'        : 'Remonter au dossier parent',
			'cmdupload'    : 'Envoyer les fichiers',
			'cmdview'      : 'Vue',
			'cmdresize'    : 'Redimensionner l\'image',
			'cmdsort'      : 'Trier',
			'cmdnetmount'  : 'Monter un volume réseau', // added 18.04.2012
			'cmdnetunmount': 'Démonter', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Vers Favoris', // added 28.12.2014
			'cmdchmod'     : 'Changer de mode', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Ouvrir un dossier', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Réinitialiser largeur colone', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Plein écran', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Déplacer', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Vider le dossier', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Annuler', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Refaire', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Préférences', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Tout sélectionner', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Tout désélectionner', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Inverser la sélection', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Ouvrir dans une nouvelle fenêtre', // from v2.1.38 added 3.4.2018
			'cmdhide'      : 'Hide (Preference)', // from v2.1.41 added 24.7.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Fermer',
			'btnSave'   : 'Sauvegarder',
			'btnRm'     : 'Supprimer',
			'btnApply'  : 'Confirmer',
			'btnCancel' : 'Annuler',
			'btnNo'     : 'Non',
			'btnYes'    : 'Oui',
			'btnMount'  : 'Monter',  // added 18.04.2012
			'btnApprove': 'Aller à $1 & approuver', // from v2.1 added 26.04.2012
			'btnUnmount': 'Démonter', // from v2.1 added 30.04.2012
			'btnConv'   : 'Convertir', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Ici',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volume',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Tous',       // from v2.1 added 22.5.2015
			'btnMime'   : 'Type MIME', // from v2.1 added 22.5.2015
			'btnFileName':'Nom du fichier',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Enregistrer & Ferme', // from v2.1 added 12.6.2015
			'btnBackup' : 'Sauvegarde', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Renommer',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Renommer (tous)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Préc. ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Suiv. ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Sauvegarder sous', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Ouvrir le dossier',
			'ntffile'     : 'Ouvrir le fichier',
			'ntfreload'   : 'Actualiser le contenu du dossier',
			'ntfmkdir'    : 'Création du dossier',
			'ntfmkfile'   : 'Création des fichiers',
			'ntfrm'       : 'Supprimer les éléments',
			'ntfcopy'     : 'Copier les éléments',
			'ntfmove'     : 'Déplacer les éléments',
			'ntfprepare'  : 'Préparation de la copie des éléments',
			'ntfrename'   : 'Renommer les fichiers',
			'ntfupload'   : 'Envoi des fichiers',
			'ntfdownload' : 'Téléchargement des fichiers',
			'ntfsave'     : 'Sauvegarder les fichiers',
			'ntfarchive'  : 'Création de l\'archive',
			'ntfextract'  : 'Extraction des fichiers de l\'archive',
			'ntfsearch'   : 'Recherche des fichiers',
			'ntfresize'   : 'Redimensionner les images',
			'ntfsmth'     : 'Fait quelque chose',
			'ntfloadimg'  : 'Chargement de l\'image',
			'ntfnetmount' : 'Monte le volume réseau', // added 18.04.2012
			'ntfnetunmount': 'Démonte le volume réseau', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Calcule la dimension de l\'image', // added 20.05.2013
			'ntfreaddir'  : 'Lecture des informations du dossier', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Récupération de l’URL du lien', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Changement de mode', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Vérification du nom du fichier envoyé', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Création d’un fichier pour le téléchargement', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Traitement de l\'information du chemin', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Traitement du fichier envoyé', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Mettre à la corbeille', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Restaurer depuis la corbeille', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Validation du dossier de destination', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Annuler l\'opération précédente', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Refaire l\'opération annulée', // from v2.1.27 added 31.07.2017
			'ntfchkcontent' : 'Checking contents', // from v2.1.41 added 3.8.2018

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Corbeille', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'Inconnue',
			'Today'       : 'Aujourd\'hui',
			'Yesterday'   : 'Hier',
			'msJan'       : 'Jan',
			'msFeb'       : 'Fév',
			'msMar'       : 'Mar',
			'msApr'       : 'Avr',
			'msMay'       : 'Mai',
			'msJun'       : 'Jun',
			'msJul'       : 'Jul',
			'msAug'       : 'Aoû',
			'msSep'       : 'Sep',
			'msOct'       : 'Oct',
			'msNov'       : 'Nov',
			'msDec'       : 'Déc',
			'January'     : 'Janvier',
			'February'    : 'Février',
			'March'       : 'Mars',
			'April'       : 'Avril',
			'May'         : 'Mai',
			'June'        : 'Juin',
			'July'        : 'Huillet',
			'August'      : 'Août',
			'September'   : 'Septembre',
			'October'     : 'Octobre',
			'November'    : 'Novembre',
			'December'    : 'Décembre',
			'Sunday'      : 'Dimanche',
			'Monday'      : 'Lundi',
			'Tuesday'     : 'Mardi',
			'Wednesday'   : 'Mercredi',
			'Thursday'    : 'Jeudi',
			'Friday'      : 'Vendredi',
			'Saturday'    : 'Samedi',
			'Sun'         : 'Dim',
			'Mon'         : 'Lun',
			'Tue'         : 'Mar',
			'Wed'         : 'Mer',
			'Thu'         : 'Jeu',
			'Fri'         : 'Ven',
			'Sat'         : 'Sam',

			/******************************** sort variants ********************************/
			'sortname'          : 'par nom',
			'sortkind'          : 'par type',
			'sortsize'          : 'par taille',
			'sortdate'          : 'par date',
			'sortFoldersFirst'  : 'Dossiers en premier',
			'sortperm'          : 'par permission', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'par mode',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'par propriétaire',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'par groupe',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Egalement arborescence',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NouveauFichier.txt', // added 10.11.2015
			'untitled folder'   : 'NouveauDossier',   // added 10.11.2015
			'Archive'           : 'NouvelleArchive',  // from v2.1 added 10.11.2015
			'untitled file'     : 'NewFile.$1',  // from v2.1.41 added 6.8.2018
			'extentionfile'     : '$1: File',    // from v2.1.41 added 6.8.2018
			'extentiontype'     : '$1: $2',      // from v2.1.43 added 17.10.2018

			/********************************** messages **********************************/
			'confirmReq'      : 'Confirmation requise',
			'confirmRm'       : 'Êtes-vous certain de vouloir supprimer les éléments ?<br/>Cela ne peut être annulé !',
			'confirmRepl'     : 'Supprimer l\'ancien fichier par le nouveau ?',
			'confirmRest'     : 'Remplacer l\'élément existant par l\'élément de la corbeille ?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'L\'encodage n\'est pas UTf-8<br/>Convertir en UTF-8 ?<br/>Les contenus deviendront UTF-8 en sauvegardant après la conversion.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Impossible de détecter l\'encodage de ce fichier. Pour être modifié, il doit être temporairement convertit en UTF-8.<br/>Veuillez s\'il vous plaît sélectionner un encodage pour ce fichier.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Ce fichier a été modifié.<br/>Les données seront perdues si les changements ne sont pas sauvegardés.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Êtes-vous certain de vouloir déplacer les éléments vers la corbeille?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Appliquer à tous',
			'name'            : 'Nom',
			'size'            : 'Taille',
			'perms'           : 'Permissions',
			'modify'          : 'Modifié',
			'kind'            : 'Type',
			'read'            : 'Lecture',
			'write'           : 'Écriture',
			'noaccess'        : 'Pas d\'accès',
			'and'             : 'et',
			'unknown'         : 'inconnu',
			'selectall'       : 'Sélectionner tous les éléments',
			'selectfiles'     : 'Sélectionner le(s) élément(s)',
			'selectffile'     : 'Sélectionner le premier élément',
			'selectlfile'     : 'Sélectionner le dernier élément',
			'viewlist'        : 'Vue par liste',
			'viewicons'       : 'Vue par icônes',
			'viewSmall'       : 'Petites icônes', // from v2.1.39 added 22.5.2018
			'viewMedium'      : 'Moyennes icônes', // from v2.1.39 added 22.5.2018
			'viewLarge'       : 'Grandes icônes', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'  : 'Très grandes icônes', // from v2.1.39 added 22.5.2018
			'places'          : 'Favoris',
			'calc'            : 'Calculer',
			'path'            : 'Chemin',
			'aliasfor'        : 'Raccourcis pour',
			'locked'          : 'Verrouiller',
			'dim'             : 'Dimensions',
			'files'           : 'Fichiers',
			'folders'         : 'Dossiers',
			'items'           : 'Éléments',
			'yes'             : 'oui',
			'no'              : 'non',
			'link'            : 'Lien',
			'searcresult'     : 'Résultats de la recherche',
			'selected'        : 'Éléments sélectionnés',
			'about'           : 'À propos',
			'shortcuts'       : 'Raccourcis',
			'help'            : 'Aide',
			'webfm'           : 'Gestionnaire de fichier Web',
			'ver'             : 'Version',
			'protocolver'     : 'Version du protocole',
			'homepage'        : 'Page du projet',
			'docs'            : 'Documentation',
			'github'          : 'Forkez-nous sur Github',
			'twitter'         : 'Suivez nous sur twitter',
			'facebook'        : 'Joignez-nous facebook',
			'team'            : 'Équipe',
			'chiefdev'        : 'Développeur en chef',
			'developer'       : 'Développeur',
			'contributor'     : 'Contributeur',
			'maintainer'      : 'Mainteneur',
			'translator'      : 'Traducteur',
			'icons'           : 'Icônes',
			'dontforget'      : 'et n\'oubliez pas votre serviette',
			'shortcutsof'     : 'Raccourcis désactivés',
			'dropFiles'       : 'Déposez les fichiers ici',
			'or'              : 'ou',
			'selectForUpload' : 'Sélectionner les fichiers à envoyer',
			'moveFiles'       : 'Déplacer les éléments',
			'copyFiles'       : 'Copier les éléments',
			'restoreFiles'    : 'Restaurer les éléments', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Retirer des favoris',
			'aspectRatio'     : 'Ratio d’affichage',
			'scale'           : 'Mise à l\'échelle',
			'width'           : 'Largeur',
			'height'          : 'Hauteur',
			'resize'          : 'Redimensionner',
			'crop'            : 'Recadrer',
			'rotate'          : 'Rotation',
			'rotate-cw'       : 'Rotation de 90 degrés horaire',
			'rotate-ccw'      : 'Rotation de 90 degrés antihoraire',
			'degree'          : '°',
			'netMountDialogTitle' : 'Monter un volume réseau', // added 18.04.2012
			'protocol'            : 'Protocole', // added 18.04.2012
			'host'                : 'Hôte', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'Utilisateur', // added 18.04.2012
			'pass'                : 'Mot de passe', // added 18.04.2012
			'confirmUnmount'      : 'Démonter $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Glissez-déposez depuis le navigateur de fichier', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Glissez-déposez les fichiers ici', // from v2.1 added 07.04.2014
			'encoding'        : 'Encodage', // from v2.1 added 19.12.2014
			'locale'          : 'Encodage régional',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Destination: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Recherche par type MIME', // from v2.1 added 22.5.2015
			'owner'           : 'Propriétaire', // from v2.1 added 20.6.2015
			'group'           : 'Groupe', // from v2.1 added 20.6.2015
			'other'           : 'Autre', // from v2.1 added 20.6.2015
			'execute'         : 'Exécuter', // from v2.1 added 20.6.2015
			'perm'            : 'Permission', // from v2.1 added 20.6.2015
			'mode'            : 'Mode', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Le dossier est vide', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Le dossier est vide.\\ Glissez-déposez pour ajouter des éléments.', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Le dossier est vide.\\ Appuyez longuement pour ajouter des éléments.', // from v2.1.6 added 30.12.2015
			'quality'         : 'Qualité', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Synchronisation automatique',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Déplacer vers le haut',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Obtenir le lien d’URL', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Éléments sélectionnés ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID du dossier', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Permettre l\'accès hors-ligne', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Pour se réauthentifier', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'En cours de chargement...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Ouvrir multiples fichiers', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Vous allez ouvrir $1 fichiers. Êtes-vous sûr de vouloir les ouvrir dans le navigateur ?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Aucun résultat trouvé avec les paramètres de recherche.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Modification d\'un fichier.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Vous avez sélectionné $1 éléments.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Vous avez $1 éléments dans le presse-papier.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Recherche incrémentale disponible uniquement pour la vue active.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Rétablir', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 complété', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Menu contextuel', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Tourner la page', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Volumes principaux', // from v2.1.16 added 16.9.2016
			'reset'           : 'Réinitialiser', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Couleur de fond', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Sélecteur de couleur', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : 'Grille 8px', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Actif', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Inactif', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Aucun résultat trouvé.\\AAppuyez sur [Entrée] pour développer la cible de recherche.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Aucun résultat trouvé pour la recherche par première lettre.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Label texte', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 mins restantes', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Réouvrir avec l\'encodage sélectionné', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Sauvegarder avec l\'encodage sélectionné', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Choisir le dossier', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Recherche par première lettre', // from v2.1.23 added 24.3.2017
			'presets'         : 'Présélections', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Impossible de mettre autant d\'éléments à la corbeille.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Zone de texte', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Vider le dossier "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'Il n\'y a pas d\'élément dans le dossier "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Préférence', // from v2.1.26 added 28.6.2017
			'language'        : 'Configuration de langue', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Initialisation des configurations sauvegardées dans ce navigateur', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Paramètres de la barre d\'outils', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... $1 caractères restants.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Somme', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Taille de fichier brute', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Focus on the element of dialog with mouseover',  // from v2.1.30 added 2.11.2017
			'select'          : 'Sélectionner', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Action lors de la sélection d\'un fichier', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Ouvrir avec le dernier éditeur utilisé', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Inverser la sélection', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Êtes-vous sûr de vouloir renommer les éléments sélectionnés $1 en $2 ?<br/>L\'action est définitive !', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Renommer le Batch', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Nombre', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Ajouter un préfixe', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Ajouter un suffixe', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Modifier l\'extention', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Paramètres des colonnes (List view)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Les changements seront immédiatement appliqués à l\'archive.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Aucun changement ne sera appliqué tant que ce volume n\'a pas été démonté.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'Le(s) volume(s) suivant(s) montés sur ce volume seront également démontés. Êtes-vous sûr de vouloir le démonter ?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Informations sur la sélection', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algorithme de hachage de fichier', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Info Items (Selection Info Panel)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Appuyez à nouveau pour quitter.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Barre d\'outils', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Espace de travail', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Dialogue', // from v2.1.38 added 4.4.2018
			'all'             : 'Tout', // from v2.1.38 added 4.4.2018
			'iconSize'        : 'Icon Size (Icons view)', // from v2.1.39 added 7.5.2018
			'editorMaximized' : 'Open the maximized editor window', // from v2.1.40 added 30.6.2018
			'editorConvNoApi' : 'Because conversion by API is not currently available, please convert on the website.', //from v2.1.40 added 8.7.2018
			'editorConvNeedUpload' : 'After conversion, you must be upload with the item URL or a downloaded file to save the converted file.', //from v2.1.40 added 8.7.2018
			'convertOn'       : 'Convert on the site of $1', // from v2.1.40 added 10.7.2018
			'integrations'    : 'Integrations', // from v2.1.40 added 11.7.2018
			'integrationWith' : 'This elFinder has the following external services integrated. Please check the terms of use, privacy policy, etc. before using it.', // from v2.1.40 added 11.7.2018
			'showHidden'      : 'Show hidden items', // from v2.1.41 added 24.7.2018
			'hideHidden'      : 'Hide hidden items', // from v2.1.41 added 24.7.2018
			'toggleHidden'    : 'Show/Hide hidden items', // from v2.1.41 added 24.7.2018
			'makefileTypes'   : 'File types to enable with "New file"', // from v2.1.41 added 7.8.2018
			'typeOfTextfile'  : 'Type of the Text file', // from v2.1.41 added 7.8.2018
			'add'             : 'Add', // from v2.1.41 added 7.8.2018
			'theme'           : 'Theme', // from v2.1.43 added 19.10.2018
			'default'         : 'Default', // from v2.1.43 added 19.10.2018
			'description'     : 'Description', // from v2.1.43 added 19.10.2018
			'website'         : 'Website', // from v2.1.43 added 19.10.2018
			'author'          : 'Author', // from v2.1.43 added 19.10.2018
			'email'           : 'Email', // from v2.1.43 added 19.10.2018
			'license'         : 'License', // from v2.1.43 added 19.10.2018
			'exportToSave'    : 'This item can\'t be saved. To avoid losing the edits you need to export to your PC.', // from v2.1.44 added 1.12.2018
			'dblclickToSelect': 'Double click on the file to select it.', // from v2.1.47 added 22.1.2019
			'useFullscreen'   : 'Use fullscreen mode', // from v2.1.47 added 19.2.2019

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Inconnu',
			'kindRoot'        : 'Volume principal', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Dossier',
			'kindSelects'     : 'Sélections', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Raccourci',
			'kindAliasBroken' : 'Raccourci cassé',
			// applications
			'kindApp'         : 'Application',
			'kindPostscript'  : 'Document Postscript',
			'kindMsOffice'    : 'Document Microsoft Office',
			'kindMsWord'      : 'Document Microsoft Word',
			'kindMsExcel'     : 'Document Microsoft Excel',
			'kindMsPP'        : 'Présentation Microsoft PowerPoint',
			'kindOO'          : 'Document OpenOffice',
			'kindAppFlash'    : 'Application Flash',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Fichier BitTorrent',
			'kind7z'          : 'Archive 7z',
			'kindTAR'         : 'Archive TAR',
			'kindGZIP'        : 'Archive GZIP',
			'kindBZIP'        : 'Archive BZIP',
			'kindXZ'          : 'Archive XZ',
			'kindZIP'         : 'Archive ZIP',
			'kindRAR'         : 'Archive RAR',
			'kindJAR'         : 'Fichier Java JAR',
			'kindTTF'         : 'Police True Type',
			'kindOTF'         : 'Police Open Type',
			'kindRPM'         : 'Package RPM',
			// texts
			'kindText'        : 'Document Text',
			'kindTextPlain'   : 'Texte non formaté',
			'kindPHP'         : 'Source PHP',
			'kindCSS'         : 'Feuille de style en cascade',
			'kindHTML'        : 'Document HTML',
			'kindJS'          : 'Source JavaScript',
			'kindRTF'         : 'Format de texte enrichi (Rich Text Format)',
			'kindC'           : 'Source C',
			'kindCHeader'     : 'Source header C',
			'kindCPP'         : 'Source C++',
			'kindCPPHeader'   : 'Source header C++',
			'kindShell'       : 'Shell script Unix',
			'kindPython'      : 'Source Python',
			'kindJava'        : 'Source Java',
			'kindRuby'        : 'Source Ruby',
			'kindPerl'        : 'Script Perl',
			'kindSQL'         : 'Source SQL',
			'kindXML'         : 'Document XML',
			'kindAWK'         : 'Source AWK',
			'kindCSV'         : 'CSV',
			'kindDOCBOOK'     : 'Document Docbook XML',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'Image',
			'kindBMP'         : 'Image BMP',
			'kindJPEG'        : 'Image JPEG',
			'kindGIF'         : 'Image GIF',
			'kindPNG'         : 'Image PNG',
			'kindTIFF'        : 'Image TIFF',
			'kindTGA'         : 'Image TGA',
			'kindPSD'         : 'Image Adobe Photoshop',
			'kindXBITMAP'     : 'Image X bitmap',
			'kindPXM'         : 'Image Pixelmator',
			// media
			'kindAudio'       : 'Son',
			'kindAudioMPEG'   : 'Son MPEG',
			'kindAudioMPEG4'  : 'Son MPEG-4',
			'kindAudioMIDI'   : 'Son MIDI',
			'kindAudioOGG'    : 'Son Ogg Vorbis',
			'kindAudioWAV'    : 'Son WAV',
			'AudioPlaylist'   : 'Liste de lecture audio',
			'kindVideo'       : 'Vidéo',
			'kindVideoDV'     : 'Vidéo DV',
			'kindVideoMPEG'   : 'Vidéo MPEG',
			'kindVideoMPEG4'  : 'Vidéo MPEG-4',
			'kindVideoAVI'    : 'Vidéo AVI',
			'kindVideoMOV'    : 'Vidéo Quick Time',
			'kindVideoWM'     : 'Vidéo Windows Media',
			'kindVideoFlash'  : 'Vidéo Flash',
			'kindVideoMKV'    : 'Vidéo Matroska',
			'kindVideoOGG'    : 'Vidéo Ogg'
		}
	};
}));
