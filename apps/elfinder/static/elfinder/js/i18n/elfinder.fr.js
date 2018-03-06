/**
 * française translation
 * @author Régis Guyomarch <regisg@gmail.com>
 * @author Benoit Delachaux <benorde33@gmail.com>
 * @version 2017-07-13
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
		translator : 'Régis Guyomarch &lt;regisg@gmail.com&gt;, Benoit Delachaux &lt;benorde33@gmail.com&gt;',
		language   : 'française',
		direction  : 'ltr',
		dateFormat : 'd M, Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Erreur',
			'errUnknown'           : 'Erreur inconnue.',
			'errUnknownCmd'        : 'Commande inconnue.',
			'errJqui'              : 'Mauvaise configuration de jQuery UI. Les composants Selectable, draggable et droppable doivent être inclus.',
			'errNode'              : 'elFinder requiert que l\'élément DOM ait été créé.',
			'errURL'               : 'Mauvaise configuration d\'elFinder ! L\'option URL na pas été définie.',
			'errAccess'            : 'Accès refusé.',
			'errConnect'           : 'Impossible de se connecter au backend.',
			'errAbort'             : 'Connexion interrompue.',
			'errTimeout'           : 'Délai de connexion dépassé.',
			'errNotFound'          : 'Backend non trouvé.',
			'errResponse'          : 'Mauvaise réponse du backend.',
			'errConf'              : 'Mauvaise configuration du backend.',
			'errJSON'              : 'Le module PHP JSON n\'est pas installé.',
			'errNoVolumes'         : 'Aucun volume lisible.',
			'errCmdParams'         : 'Mauvais Paramétrage de la commande "$1".',
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
			'errExists'            : 'Un fichier nommé "$1" existe déjà.',
			'errInvName'           : 'Nom de fichier incorrect.',
			'errInvDirname'        : 'Nom de dossier incorrect.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Dossier non trouvé.',
			'errFileNotFound'      : 'Fichier non trouvé.',
			'errTrgFolderNotFound' : 'Dossier destination "$1" non trouvé.',
			'errPopup'             : 'Le navigateur web a empêché l\'ouverture d\'une fenêtre "popup". Pour ouvrir le fichier, modifiez les options du navigateur web.',
			'errMkdir'             : 'Impossible de créer le dossier "$1".',
			'errMkfile'            : 'impossible de créer le fichier "$1".',
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
			'errTrash'             : 'Unable into trash.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'Impossible de supprimer le(s) fichier(s) source(s).',
			'errExtract'           : 'Imbossible d\'extraire les fichiers à partir de "$1".',
			'errArchive'           : 'Impossible de créer l\'archive.',
			'errArcType'           : 'Type d\'archive non supporté.',
			'errNoArchive'         : 'Le fichier n\'est pas une archive, ou c\'est un type d\'archive non supporté.',
			'errCmdNoSupport'      : 'Le Backend ne prend pas en charge cette commande.',
			'errReplByChild'       : 'Le dossier “$1” ne peut pas être remplacé par un élément qu\'il contient.',
			'errArcSymlinks'       : 'Par mesure de sécurité, il est défendu d\'extraire une archive contenant des liens symboliques.', // edited 24.06.2012
			'errArcMaxSize'        : 'Les fichiers de l\'archive excèdent la taille maximale autorisée.',
			'errResize'            : 'Impossible de redimensionner "$1".',
			'errResizeDegree'      : 'Degré de rotation invalide.',  // added 7.3.2013
			'errResizeRotate'      : 'L\'image ne peut pas être tournée.',  // added 7.3.2013
			'errResizeSize'        : 'Dimension de l\'image non-valide.',  // added 7.3.2013
			'errResizeNoChange'    : 'L\'image n\'est pas redimensionnable.',  // added 7.3.2013
			'errUsupportType'      : 'Type de fichier non supporté.',
			'errNotUTF8Content'    : 'Le fichier "$1" n\'est pas en UTF-8, il ne peut être édité.',  // added 9.11.2011
			'errNetMount'          : 'Impossible de monter "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Protocol non supporté.',     // added 17.04.2012
			'errNetMountFailed'    : 'Echec du montage.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Hôte requis.', // added 18.04.2012
			'errSessionExpires'    : 'Votre session a expiré en raison de son inactivité',
			'errCreatingTempDir'   : 'Impossible de créer le répertoire temporaire : "$1"',
			'errFtpDownloadFile'   : 'Impossible de télécharger le file depuis l\'accès FTP : "$1"',
			'errFtpUploadFile'     : 'Impossible d\'envoyer le fichier vers l\'accès FTP : "$1"',
			'errFtpMkdir'          : 'Impossible de créer un répertoire distant sur l\'accès FTP :"$1"',
			'errArchiveExec'       : 'Erreur lors de l\'archivage des fichiers : "$1"',
			'errExtractExec'       : 'Erreur lors de l\'extraction des fichiers : "$1"',
			'errNetUnMount'        : 'Impossible de démonter', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Conversion en UTF-8 impossible', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Essayez Google Chrome, si voulez envoyer le dossier.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Délai d’attente dépassé pour la recherche "$1". Le résultat de la recherche est partiel.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Réauthorisation requise.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Le nombre maximal de fichiers pouvant être sélectionné est $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Impossible de restorer la corbeille. La destination de la restoration n\'a pu être identifiée.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Aucun éditeur n\'a été trouvé pour ce type de fichier.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Un erreur est survenue du côté serveur.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'Impossible de vider le dossier "$1".', // from v2.1.25 added 22.6.2017

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
			'cmdmkfile'    : 'Nouveau fichier texte',
			'cmdopen'      : 'Ouvrir',
			'cmdpaste'     : 'Coller',
			'cmdquicklook' : 'Prévisualiser',
			'cmdreload'    : 'Actualiser',
			'cmdrename'    : 'Renommer',
			'cmdrm'        : 'Supprimer',
			'cmdtrash'     : 'À la corbeille', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Restorer', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Trouver les fichiers',
			'cmdup'        : 'Remonter au dossier parent',
			'cmdupload'    : 'Envoyer les fichiers',
			'cmdview'      : 'Vue',
			'cmdresize'    : 'Redimensionner l\'image',
			'cmdsort'      : 'Trier',
			'cmdnetmount'  : 'Monter un volume réseau', // added 18.04.2012
			'cmdnetunmount': 'Démonter', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Vers Places', // added 28.12.2014
			'cmdchmod'     : 'Changer de mode', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Ouvrir un dossier', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Réinitialiser largeur colone', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Plein écran', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Déplacer', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Vider le dossier', // from v2.1.25 added 22.06.2017

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
			'ntfrm'       : 'Supprimer les fichiers',
			'ntfcopy'     : 'Copier les fichiers',
			'ntfmove'     : 'Déplacer les fichiers',
			'ntfprepare'  : 'Préparation de la copie des fichiers',
			'ntfrename'   : 'Renommer les fichier',
			'ntfupload'   : 'Envoyer les fichiers',
			'ntfdownload' : 'Télécharger les fichiers',
			'ntfsave'     : 'Sauvegarde des fichiers',
			'ntfarchive'  : 'Création de l\'archive',
			'ntfextract'  : 'Extraction des fichiers de l\'archive',
			'ntfsearch'   : 'Recherche des fichiers',
			'ntfresize'   : 'Re-tailler les images',
			'ntfsmth'     : 'Fait quelque chose',
			'ntfloadimg'  : 'Chargement de l\' image',
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
			'ntftrash'    : 'Doing throw in the trash', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Doing restore from tha trash', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Validation du dossier de destination', // from v2.1.24 added 3.5.2017

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
			'sortowner'         : 'by owner',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'par groupe',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Also Treeview',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NewFile.txt', // added 10.11.2015
			'untitled folder'   : 'NewFolder',   // added 10.11.2015
			'Archive'           : 'NewArchive',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Confirmation requise',
			'confirmRm'       : 'Êtes-vous certain de vouloir supprimer les fichiers?<br/>Cela ne peut être annulé!',
			'confirmRepl'     : 'Supprimer l\'ancien fichier par le nouveau?',
			'confirmRest'     : 'Remplacer le fichier existant par le fichier dans la corbeille?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'L\'encodage n\'est pas UTf-8<br/>Convertir en UTF-8?<br/>Les contenus deviendront UTF-8 en sauvegardant après la conversion.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Character encoding of this file couldn\'t be detected. It need to temporarily convert to UTF-8 for editting.<br/>Please select character encoding of this file.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Ce fichier a été modifié.<br/>Les données seront perdues si les changements ne sont pas sauvegardés.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Êtes-vous certain de vouloir déplacer les fichiers vers la corbeille?', //from v2.1.24 added 29.4.2017
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
			'selectall'       : 'Sélectionner tous les fichiers',
			'selectfiles'     : 'Sélectionner le(s) fichier(s)',
			'selectffile'     : 'Sélectionner le premier fichier',
			'selectlfile'     : 'Sélectionner le dernier fichier',
			'viewlist'        : 'Vue par liste',
			'viewicons'       : 'Vue par icônes',
			'places'          : 'Places',
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
			'searcresult'     : 'Résultat de la recherche',
			'selected'        : 'Éléments sélectionnés',
			'about'           : 'À propos',
			'shortcuts'       : 'Raccourcis',
			'help'            : 'Aide',
			'webfm'           : 'Gestionnaire de fichier Web',
			'ver'             : 'Version',
			'protocolver'     : 'Version du protocole',
			'homepage'        : 'Page du projet',
			'docs'            : 'Documentation',
			'github'          : 'Forker-nous sur Github',
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
			'moveFiles'       : 'Déplacer les fichiers',
			'copyFiles'       : 'Copier les fichiers',
			'restoreFiles'    : 'Restorer les fichiers', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Retirer de Places',
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
			'emptyFolderLTap' : 'Le dossier est vide.\\ Un appui long pour ajouter des éléments.', // from v2.1.6 added 30.12.2015
			'quality'         : 'Qualité', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Synchronisation automatique',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Déplacer vers le haut',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Obtenir le lien d’URL', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Éléments sélectionnés ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID du dossier', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Permettre l\'accès offline', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Pour se réauthentifier', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'En cours de chargement...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Ouvrir multiples fichiers', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'You are trying to open the $1 files. Are you sure you want to open in browser?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Search results is empty in search target.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'It is editing a file.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Vous avez sélectionné $1 fichier.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Vous avez $1 items dans le clipboard.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'La recherche incrémentale est seulement pour la vue active.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Reinstate', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 complété', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Context menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Page turning', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Volumes principaux', // from v2.1.16 added 16.9.2016
			'reset'           : 'Réinitialiser', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Couleur de fond', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Sélecteur de couleur', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : 'Grille 8px', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Actif', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Inactif', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Search results is empty in current view.\\APress [Enter] to expand search target.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'First letter search results is empty in current view.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Text label', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 mins restants', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Réouvrir avec l\'encodage sélectionné', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Sauvegarder avec l\'encodage sélectionné', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Choisir le dossier', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Recherche par première lettre', // from v2.1.23 added 24.3.2017
			'presets'         : 'Presets', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'It\'s too many items so it can\'t into trash.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'TextArea', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Empty the folder "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'There are no items in a folder "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Préférence', // from v2.1.26 added 28.6.2017
			'language'        : 'Configuration de langue', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Initialisation des configurations sauvegardés dans ce navigateur', // from v2.1.26 added 28.6.2017

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Inconnu',
			'kindRoot'        : 'Volume principal', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Dossier',
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

