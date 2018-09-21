/**
 * Español internacional translation
 * @author Julián Torres <julian.torres@pabernosmatao.com>
 * @author Luis Faura <luis@luisfaura.es>
 * @author Adrià Vilanova <me@avm99963.tk>
 * @author Wilman Marín Duran <fuclo05@hotmail.com>
 * @version 2018-04-10
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
	elFinder.prototype.i18.es = {
		translator : 'Julián Torres &lt;julian.torres@pabernosmatao.com&gt;, Luis Faura &lt;luis@luisfaura.es&gt;, Adrià Vilanova &lt;me@avm99963.tk&gt;, Wilman Marín Duran &lt;fuclo05@hotmail.com&gt;',
		language   : 'Español internacional',
		direction  : 'ltr',
		dateFormat : 'M d, Y h:i A', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 h:i A', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Error',
			'errUnknown'           : 'Error desconocido.',
			'errUnknownCmd'        : 'Comando desconocido.',
			'errJqui'              : 'Configuración no válida de jQuery UI. Deben estar incluidos los componentes selectable, draggable y droppable.',
			'errNode'              : 'elFinder necesita crear elementos DOM.',
			'errURL'               : '¡Configuración no válida de elFinder! La opción URL no está configurada.',
			'errAccess'            : 'Acceso denegado.',
			'errConnect'           : 'No se ha podido conectar con el backend.',
			'errAbort'             : 'Conexión cancelada.',
			'errTimeout'           : 'Conexión cancelada por timeout.',
			'errNotFound'          : 'Backend no encontrado.',
			'errResponse'          : 'Respuesta no válida del backend.',
			'errConf'              : 'Configuración no válida del backend .',
			'errJSON'              : 'El módulo PHP JSON no está instalado.',
			'errNoVolumes'         : 'No hay disponibles volúmenes legibles.',
			'errCmdParams'         : 'Parámetros no válidos para el comando "$1".',
			'errDataNotJSON'       : 'los datos no están en formato JSON.',
			'errDataEmpty'         : 'No hay datos.',
			'errCmdReq'            : 'La petición del backend necesita un nombre de comando.',
			'errOpen'              : 'No se puede abrir "$1".',
			'errNotFolder'         : 'El objeto no es una carpeta.',
			'errNotFile'           : 'El objeto no es un archivo.',
			'errRead'              : 'No se puede leer "$1".',
			'errWrite'             : 'No se puede escribir en "$1".',
			'errPerm'              : 'Permiso denegado.',
			'errLocked'            : '"$1" está bloqueado y no puede ser renombrado, movido o borrado.',
			'errExists'            : 'Ya existe un archivo llamado "$1".',
			'errInvName'           : 'Nombre de archivo no válido.',
			'errInvDirname'        : 'Nombre de carpeta inválido.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'Carpeta no encontrada.',
			'errFileNotFound'      : 'Archivo no encontrado.',
			'errTrgFolderNotFound' : 'Carpeta de destino "$1" no encontrada.',
			'errPopup'             : 'El navegador impide abrir nuevas ventanas. Puede activarlo en las opciones del navegador.',
			'errMkdir'             : 'No se puede crear la carpeta "$1".',
			'errMkfile'            : 'No se puede crear el archivo "$1".',
			'errRename'            : 'No se puede renombrar "$1".',
			'errCopyFrom'          : 'No se permite copiar archivos desde el volumen "$1".',
			'errCopyTo'            : 'No se permite copiar archivos al volumen "$1".',
			'errMkOutLink'         : 'No se ha podido crear el enlace fuera del volumen raíz.', // from v2.1 added 03.10.2015
			'errUpload'            : 'Error en el envío.',  // old name - errUploadCommon
			'errUploadFile'        : 'No se ha podido cargar "$1".', // old name - errUpload
			'errUploadNoFiles'     : 'No hay archivos para subir.',
			'errUploadTotalSize'   : 'El tamaño de los datos excede el máximo permitido.', // old name - errMaxSize
			'errUploadFileSize'    : 'El tamaño del archivo excede el máximo permitido.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Tipo de archivo no permitido.',
			'errUploadTransfer'    : 'Error al transferir "$1".',
			'errUploadTemp'        : 'No se ha podido crear el archivo temporal para la subida.', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'El objeto "$1" ya existe y no puede ser reemplazado por otro con otro tipo.', // new
			'errReplace'           : 'No se puede reemplazar "$1".',
			'errSave'              : 'No se puede guardar "$1".',
			'errCopy'              : 'No se puede copiar "$1".',
			'errMove'              : 'No se puede mover "$1".',
			'errCopyInItself'      : 'No se puede copiar "$1" en si mismo.',
			'errRm'                : 'No se puede borrar "$1".',
			'errTrash'             : 'No se puede enviar a la papelera.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'No se puede(n) borrar los archivo(s).',
			'errExtract'           : 'No se puede extraer archivos desde "$1".',
			'errArchive'           : 'No se puede crear el archivo.',
			'errArcType'           : 'Tipo de archivo no soportado.',
			'errNoArchive'         : 'El archivo no es de tipo archivo o es de un tipo no soportado.',
			'errCmdNoSupport'      : 'El backend no soporta este comando.',
			'errReplByChild'       : 'La carpeta “$1” no puede ser reemplazada por un elemento contenido en ella.',
			'errArcSymlinks'       : 'Por razones de seguridad no se pueden descomprimir archivos que contengan enlaces simbólicos.', // edited 24.06.2012
			'errArcMaxSize'        : 'El tamaño del archivo excede el máximo permitido.',
			'errResize'            : 'Error al redimensionar "$1".',
			'errResizeDegree'      : 'Grado de rotación inválido.',  // added 7.3.2013
			'errResizeRotate'      : 'Error al rotar la imagen.',  // added 7.3.2013
			'errResizeSize'        : 'Tamaño de imagen inválido.',  // added 7.3.2013
			'errResizeNoChange'    : 'No se puede cambiar el tamaño de la imagen.',  // added 7.3.2013
			'errUsupportType'      : 'Tipo de archivo no soportado.',
			'errNotUTF8Content'    : 'El archivo "$1" no está en formato UTF-8 y no puede ser editado.',  // added 9.11.2011
			'errNetMount'          : 'Fallo al montar "$1".', // added 17.04.2012
			'errNetMountNoDriver'  : 'Protocolo no soportado.',     // added 17.04.2012
			'errNetMountFailed'    : 'Fallo al montar.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Dominio requerido.', // added 18.04.2012
			'errSessionExpires'    : 'La sesión ha expirado por inactividad',
			'errCreatingTempDir'   : 'No se ha podido crear al directorio temporal: "$1"',
			'errFtpDownloadFile'   : 'No se ha podido descargar el archivo desde FTP: "$1"',
			'errFtpUploadFile'     : 'No se ha podido cargar el archivo a FTP: "$1"',
			'errFtpMkdir'          : 'No se ha podido crear el directorio remoto en FTP: "$1"',
			'errArchiveExec'       : 'Se ha producido un error durante el archivo: "$1"',
			'errExtractExec'       : 'Se ha producido un error durante la extracción de archivos: "$1"',
			'errNetUnMount'        : 'Imposible montar', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'No es convertible a UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Prueba con un navegador moderno, si quieres subir la carpeta completa.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Se agotó el tiempo de espera buscando "$1". Los resultados de búsqueda son parciales.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Se requiere autorizar de nuevo.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Número máximo de elementos seleccionables es $1.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'No se puede restaurar desde la papelera. No se puede identificar el destino de restauración.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Editor no encontrado para este tipo de archivo.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Error ocurrido en el lado del servidor.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'No es posible vaciar la carpeta "$1".', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Crear archivo',
			'cmdback'      : 'Atrás',
			'cmdcopy'      : 'Copiar',
			'cmdcut'       : 'Cortar',
			'cmddownload'  : 'Descargar',
			'cmdduplicate' : 'Duplicar',
			'cmdedit'      : 'Editar archivo',
			'cmdextract'   : 'Extraer elementos del archivo',
			'cmdforward'   : 'Adelante',
			'cmdgetfile'   : 'Seleccionar archivos',
			'cmdhelp'      : 'Acerca de este software',
			'cmdhome'      : 'Inicio',
			'cmdinfo'      : 'Obtener información',
			'cmdmkdir'     : 'Nueva carpeta',
			'cmdmkdirin'   : 'En una nueva carpeta', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Nueva archivo',
			'cmdopen'      : 'Abrir',
			'cmdpaste'     : 'Pegar',
			'cmdquicklook' : 'Previsualizar',
			'cmdreload'    : 'Recargar',
			'cmdrename'    : 'Cambiar nombre',
			'cmdrm'        : 'Eliminar',
			'cmdtrash'     : 'Enviar a la papelera', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'Restaurar', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'Buscar archivos',
			'cmdup'        : 'Ir a la carpeta raíz',
			'cmdupload'    : 'Subir archivos',
			'cmdview'      : 'Ver',
			'cmdresize'    : 'Redimensionar y rotar',
			'cmdsort'      : 'Ordenar',
			'cmdnetmount'  : 'Montar volumen en red', // added 18.04.2012
			'cmdnetunmount': 'Desmontar', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'A Lugares', // added 28.12.2014
			'cmdchmod'     : 'Cambiar modo', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Abrir una carpeta', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Restablecer ancho de columna', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Pantalla completa', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Mover', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Vaciar la carpeta', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Deshacer', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Rehacer', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Preferencias', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Seleccionar todo', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Seleccionar ninguno', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Invertir selección', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Abrir en nueva ventana', // from v2.1.38 added 3.4.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Cerrar',
			'btnSave'   : 'Guardar',
			'btnRm'     : 'Eliminar',
			'btnApply'  : 'Aplicar',
			'btnCancel' : 'Cancelar',
			'btnNo'     : 'No',
			'btnYes'    : 'Sí',
			'btnMount'  : 'Montar',  // added 18.04.2012
			'btnApprove': 'Ir a $1 y aprobar', // from v2.1 added 26.04.2012
			'btnUnmount': 'Desmontar', // from v2.1 added 30.04.2012
			'btnConv'   : 'Convertir', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Aquí',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Volumen',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Todos',       // from v2.1 added 22.5.2015
			'btnMime'   : 'Tipo MIME', // from v2.1 added 22.5.2015
			'btnFileName':'Nombre de archivo',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Guardar y cerrar', // from v2.1 added 12.6.2015
			'btnBackup' : 'Copia de seguridad', // fromv2.1 added 28.11.2015
			'btnRename'    : 'Renombrar',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Renombrar(Todo)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Ant ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Sig ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Guardar como', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'Abrir carpeta',
			'ntffile'     : 'Abrir archivo',
			'ntfreload'   : 'Actualizar contenido de la carpeta',
			'ntfmkdir'    : 'Creando directorio',
			'ntfmkfile'   : 'Creando archivos',
			'ntfrm'       : 'Eliminando archivos',
			'ntfcopy'     : 'Copiar archivos',
			'ntfmove'     : 'Mover archivos',
			'ntfprepare'  : 'Preparar copia de archivos',
			'ntfrename'   : 'Renombrar archivos',
			'ntfupload'   : 'Subiendo archivos',
			'ntfdownload' : 'Descargando archivos',
			'ntfsave'     : 'Guardar archivos',
			'ntfarchive'  : 'Creando archivo',
			'ntfextract'  : 'Extrayendo elementos del archivo',
			'ntfsearch'   : 'Buscando archivos',
			'ntfresize'   : 'Redimensionando imágenes',
			'ntfsmth'     : 'Haciendo algo',
			'ntfloadimg'  : 'Cargando imagen',
			'ntfnetmount' : 'Montando volumen en red', // added 18.04.2012
			'ntfnetunmount': 'Desmontando volumen en red', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Adquiriendo tamaño de imagen', // added 20.05.2013
			'ntfreaddir'  : 'Leyendo información de la carpeta', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Obteniendo URL del enlace', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Cambiando el modo de archivo', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verificando nombre del archivo subido', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Creando un archivo para descargar', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Obteniendo información de la ruta', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Procesando el archivo cargado', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Enviando a la papelera', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Restaurando desde la papelera', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Comprobando carpeta de destino', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Deshaciendo operación previa', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Rehaciendo previo deshacer', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Papelera', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'desconocida',
			'Today'       : 'Hoy',
			'Yesterday'   : 'Ayer',
			'msJan'       : 'Ene',
			'msFeb'       : 'Feb',
			'msMar'       : 'Mar',
			'msApr'       : 'Abr',
			'msMay'       : 'May',
			'msJun'       : 'Jun',
			'msJul'       : 'Jul',
			'msAug'       : 'Ago',
			'msSep'       : 'Sep',
			'msOct'       : 'Oct',
			'msNov'       : 'Nov',
			'msDec'       : 'Dic',
			'January'     : 'Enero',
			'February'    : 'Febrero',
			'March'       : 'Marzo',
			'April'       : 'Abril',
			'May'         : 'Mayo',
			'June'        : 'Junio',
			'July'        : 'Julio',
			'August'      : 'Agosto',
			'September'   : 'Septiembre',
			'October'     : 'Octubre',
			'November'    : 'Noviembre',
			'December'    : 'Diciembre',
			'Sunday'      : 'Domingo',
			'Monday'      : 'Lunes',
			'Tuesday'     : 'Martes',
			'Wednesday'   : 'Miércoles',
			'Thursday'    : 'Jueves',
			'Friday'      : 'Viernes',
			'Saturday'    : 'Sábado',
			'Sun'         : 'Dom',
			'Mon'         : 'Lun',
			'Tue'         : 'Mar',
			'Wed'         : 'Mie',
			'Thu'         : 'Jue',
			'Fri'         : 'Vie',
			'Sat'         : 'Sab',

			/******************************** sort variants ********************************/
			'sortname'          : 'por nombre',
			'sortkind'          : 'por tipo',
			'sortsize'          : 'por tamaño',
			'sortdate'          : 'por fecha',
			'sortFoldersFirst'  : 'Las carpetas primero',
			'sortperm'          : 'por permiso', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'por modo',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'por propietario',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'por grupo',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'También árbol de directorios',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NuevoArchivo.txt', // added 10.11.2015
			'untitled folder'   : 'NuevaCarpeta',   // added 10.11.2015
			'Archive'           : 'NuevoArchivo',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Se necesita confirmación',
			'confirmRm'       : '¿Está seguro de querer eliminar archivos?<br/>¡Esto no se puede deshacer!',
			'confirmRepl'     : '¿Reemplazar el antiguo archivo con el nuevo?',
			'confirmRest'     : '¿Reemplazar elemento existente con el elemento en la papelera?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'No está en UTF-8<br/>Convertir a UTF-8?<br/>Los contenidos se guardarán en UTF-8 tras la conversión.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Codificación de caracteres de este archivo no pudo ser detectada. Es necesario convertir temporalmente a UTF-8 para editarlo. <br/> Por favor, seleccione la codificación de caracteres de este archivo.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Ha sido modificado.<br/>Perderás los cambios si no los guardas.', // from v2.1 added 15.7.2015
			'confirmTrash'    : '¿Estás seguro que quieres mover los elementos a la papelera?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'Aplicar a todo',
			'name'            : 'Nombre',
			'size'            : 'Tamaño',
			'perms'           : 'Permisos',
			'modify'          : 'Modificado',
			'kind'            : 'Tipo',
			'read'            : 'lectura',
			'write'           : 'escritura',
			'noaccess'        : 'sin acceso',
			'and'             : 'y',
			'unknown'         : 'desconocido',
			'selectall'       : 'Seleccionar todos los archivos',
			'selectfiles'     : 'Seleccionar archivo(s)',
			'selectffile'     : 'Seleccionar primer archivo',
			'selectlfile'     : 'Seleccionar último archivo',
			'viewlist'        : 'ver como lista',
			'viewicons'       : 'Ver como iconos',
			'places'          : 'Lugares',
			'calc'            : 'Calcular',
			'path'            : 'Ruta',
			'aliasfor'        : 'Alias para',
			'locked'          : 'Bloqueado',
			'dim'             : 'Dimensiones',
			'files'           : 'Archivos',
			'folders'         : 'Carpetas',
			'items'           : 'Elementos',
			'yes'             : 'sí',
			'no'              : 'no',
			'link'            : 'Enlace',
			'searcresult'     : 'Resultados de la búsqueda',
			'selected'        : 'elementos seleccionados',
			'about'           : 'Acerca',
			'shortcuts'       : 'Accesos directos',
			'help'            : 'Ayuda',
			'webfm'           : 'Administrador de archivos web',
			'ver'             : 'Versión',
			'protocolver'     : 'versión del protocolo',
			'homepage'        : 'Inicio',
			'docs'            : 'Documentación',
			'github'          : 'Bifúrcanos en Github',
			'twitter'         : 'Síguenos en Twitter',
			'facebook'        : 'Únete a nosotros en Facebook',
			'team'            : 'Equipo',
			'chiefdev'        : 'desarrollador jefe',
			'developer'       : 'desarrollador',
			'contributor'     : 'contribuyente',
			'maintainer'      : 'mantenedor',
			'translator'      : 'traductor',
			'icons'           : 'Iconos',
			'dontforget'      : 'y no olvide traer su toalla',
			'shortcutsof'     : 'Accesos directos desactivados',
			'dropFiles'       : 'Arrastre archivos aquí',
			'or'              : 'o',
			'selectForUpload' : 'Seleccione archivos para subir',
			'moveFiles'       : 'Mover archivos',
			'copyFiles'       : 'Copiar archivos',
			'restoreFiles'    : 'Restaurar elementos', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Eliminar en sus ubicaciones',
			'aspectRatio'     : 'Relación de aspecto',
			'scale'           : 'Escala',
			'width'           : 'Ancho',
			'height'          : 'Alto',
			'resize'          : 'Redimensionar',
			'crop'            : 'Recortar',
			'rotate'          : 'Rotar',
			'rotate-cw'       : 'Rotar 90 grados en sentido horario',
			'rotate-ccw'      : 'Rotar 90 grados en sentido anti-horario',
			'degree'          : '°',
			'netMountDialogTitle' : 'Montar volumen en red', // added 18.04.2012
			'protocol'            : 'Protocolo', // added 18.04.2012
			'host'                : 'Dominio', // added 18.04.2012
			'port'                : 'Puerto', // added 18.04.2012
			'user'                : 'Usuario', // added 18.04.2012
			'pass'                : 'Contraseña', // added 18.04.2012
			'confirmUnmount'      : '¿Desmontar $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Arrastra o pega archivos del navegador', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Arrastra o pega enlaces URL aquí', // from v2.1 added 07.04.2014
			'encoding'        : 'Codificando', // from v2.1 added 19.12.2014
			'locale'          : 'Local',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Destino: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Buscar entrada por tipo MIME', // from v2.1 added 22.5.2015
			'owner'           : 'Propietario', // from v2.1 added 20.6.2015
			'group'           : 'Grupo', // from v2.1 added 20.6.2015
			'other'           : 'Otro', // from v2.1 added 20.6.2015
			'execute'         : 'Ejecutar', // from v2.1 added 20.6.2015
			'perm'            : 'Permiso', // from v2.1 added 20.6.2015
			'mode'            : 'Modo', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'La carpeta está vacía', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'La carpeta está vacía\\A Arrastrar para añadir elementos', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'La carpeta está vacía\\A Presiona durante un rato para añadir elementos', // from v2.1.6 added 30.12.2015
			'quality'         : 'Calidad', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Sincronización automática',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Mover arriba',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Obtener enlace', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Elementos seleccionados ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'ID carpeta', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Permitir acceso sin conexión', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Para volver a autenticarse', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Cargando ahora...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Abrir múltiples archivos', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'Estás tratando de abrir los $1 archivos. ¿Estás seguro que quieres abrir en el navegador?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'No se encontraron resultados en el objetivo de búsqueda.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Está editando un archivo.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'Has seleccionado $1 elementos.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Posees $1 elementos en el portapapeles.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'La búsqueda incremental solo se realiza desde la vista actual.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Reinstanciar', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 completo', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Menú contextual', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Cambio de página', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Raíces del volumen', // from v2.1.16 added 16.9.2016
			'reset'           : 'Reiniciar', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Color de fondo', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Selector de color', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px Cuadricula', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Habilitado', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Deshabilitado', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Los resultados de la búsqueda están vacíos en la vista actual. \\ APulse [Intro] para expandir el objetivo de búsqueda.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'La primera letra de los resultados de búsqueda está vacía en la vista actual.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Etiqueta de texto', // from v2.1.17 added 13.10.2016
			'minsLeft'        : 'Falta $1 minuto(s)', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Abrir nuevamente con la codificación seleccionada', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Guardar con la codificación seleccionada', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Seleccionar carpeta', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'Primera letra de búsqueda', // from v2.1.23 added 24.3.2017
			'presets'         : 'Preestablecidos', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'Son demasiados elementos, por lo que no puede enviarse a la papelera.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Área de texto', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Vaciar la carpeta "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'No hay elementos en la carpeta "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preferencia', // from v2.1.26 added 28.6.2017
			'language'        : 'Lenguaje', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Inicializa la configuración guardada en este navegador', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Configuración de la barra de herramientas', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '...falta $1 caracteres.',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Suma', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Tamaño de archivo aproximado', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Centrado en el elemento de diálogo con \'mouseover\'',  // from v2.1.30 added 2.11.2017
			'select'          : 'Seleccionar', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Acción cuando selecciona un archivo', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Abrir con el editor utilizado la última vez', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Invertir selección', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : '¿Estás seguro que quieres renombrar $1 elementos seleccionados como $2?<br/>¡Esto no puede ser deshecho!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Cambiar el nombre del lote', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Número', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Añadir prefijo', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Añadir sufijo', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Cambiar extensión', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Configuración de columnas (Vista de lista)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Todos los cambios se reflejarán inmediatamente en el archivo.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Cualquier cambio no se reflejará hasta que no se desmonte este volumen.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'Los siguientes volúmenes montados en este volumen también se desmontaron. ¿Estás seguro de desmontarlo?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Información de la selección', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algoritmos para mostrar el hash de archivos', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'Elementos de información (Panel de información de selección)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Presiona de nuevo para salir.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Barra de herramienta', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Espacio de trabajo', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Diálogo', // from v2.1.38 added 4.4.2018
			'all'             : 'Todo', // from v2.1.38 added 4.4.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Desconocido',
			'kindRoot'        : 'Raíces del volumen', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Carpeta',
			'kindSelects'     : 'Selecciones', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Alias roto',
			// applications
			'kindApp'         : 'Aplicación',
			'kindPostscript'  : 'Documento Postscript',
			'kindMsOffice'    : 'Documento Microsoft Office',
			'kindMsWord'      : 'Documento Microsoft Word',
			'kindMsExcel'     : 'Documento Microsoft Excel',
			'kindMsPP'        : 'Presentación Microsoft Powerpoint',
			'kindOO'          : 'Documento Open Office',
			'kindAppFlash'    : 'Aplicación Flash',
			'kindPDF'         : 'Documento PDF',
			'kindTorrent'     : 'Archivo Bittorrent',
			'kind7z'          : 'Archivo 7z',
			'kindTAR'         : 'Archivo TAR',
			'kindGZIP'        : 'Archivo GZIP',
			'kindBZIP'        : 'Archivo BZIP',
			'kindXZ'          : 'Archivo XZ',
			'kindZIP'         : 'Archivo ZIP',
			'kindRAR'         : 'Archivo RAR',
			'kindJAR'         : 'Archivo Java JAR',
			'kindTTF'         : 'Fuente True Type',
			'kindOTF'         : 'Fuente Open Type',
			'kindRPM'         : 'Paquete RPM',
			// texts
			'kindText'        : 'Documento de texto',
			'kindTextPlain'   : 'Texto plano',
			'kindPHP'         : 'Código PHP',
			'kindCSS'         : 'Hoja de estilos CSS',
			'kindHTML'        : 'Documento HTML',
			'kindJS'          : 'Código Javascript',
			'kindRTF'         : 'Documento RTF',
			'kindC'           : 'Código C',
			'kindCHeader'     : 'Código C cabeceras',
			'kindCPP'         : 'Código C++',
			'kindCPPHeader'   : 'Código C++ cabeceras',
			'kindShell'       : 'Script de terminal de Unix',
			'kindPython'      : 'Código Python',
			'kindJava'        : 'Código Java',
			'kindRuby'        : 'Código Ruby',
			'kindPerl'        : 'Código Perl',
			'kindSQL'         : 'Código QL',
			'kindXML'         : 'Documento XML',
			'kindAWK'         : 'Código AWK',
			'kindCSV'         : 'Documento CSV (valores separados por comas)',
			'kindDOCBOOK'     : 'Documento Docbook XML',
			'kindMarkdown'    : 'Texto Markdown', // added 20.7.2015
			// images
			'kindImage'       : 'Imagen',
			'kindBMP'         : 'Imagen BMP',
			'kindJPEG'        : 'Imagen JPEG',
			'kindGIF'         : 'Imagen GIF',
			'kindPNG'         : 'Imagen PNG',
			'kindTIFF'        : 'Imagen TIFF',
			'kindTGA'         : 'Imagen TGA',
			'kindPSD'         : 'Imagen Adobe Photoshop',
			'kindXBITMAP'     : 'Imagen X bitmap',
			'kindPXM'         : 'Imagen Pixelmator',
			// media
			'kindAudio'       : 'Archivo de audio',
			'kindAudioMPEG'   : 'Audio MPEG',
			'kindAudioMPEG4'  : 'Audio MPEG-4',
			'kindAudioMIDI'   : 'Audio MIDI',
			'kindAudioOGG'    : 'Audio Ogg Vorbis',
			'kindAudioWAV'    : 'Audio WAV',
			'AudioPlaylist'   : 'Lista de reproducción MP3',
			'kindVideo'       : 'Archivo de vídeo',
			'kindVideoDV'     : 'Película DV',
			'kindVideoMPEG'   : 'Película MPEG',
			'kindVideoMPEG4'  : 'Película MPEG-4',
			'kindVideoAVI'    : 'Película AVI',
			'kindVideoMOV'    : 'Película Quick Time',
			'kindVideoWM'     : 'Película Windows Media',
			'kindVideoFlash'  : 'Película Flash',
			'kindVideoMKV'    : 'Película Matroska MKV',
			'kindVideoOGG'    : 'Película Ogg'
		}
	};
}));
