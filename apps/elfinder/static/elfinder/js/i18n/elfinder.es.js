/**
 * Español internacional translation
 * @author Julián Torres <julian.torres@pabernosmatao.com>
 * @author Luis Faura <luis@luisfaura.es>
 * @author Adrià Vilanova <me@avm99963.tk>
 * @version 2016-03-19
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
		translator : 'Julián Torres &lt;julian.torres@pabernosmatao.com&gt;, Luis Faura &lt;luis@luisfaura.es&gt;',
		language   : 'Español internacional',
		direction  : 'ltr',
		dateFormat : 'M d, Y h:i A', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 h:i A', // will produce smth like: Today 12:25 PM
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
			'errDataNotJSON'       : 'los datos no estan en formato JSON.',
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
			'errUpload'            : 'Error en el envio.',  // old name - errUploadCommon
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
			'errRmSrc'             : 'No se puede(n) borrar los archivo(s).',
			'errExtract'           : 'No se puede extraer archivos desde "$1".',
			'errArchive'           : 'No se puede crear el archivo.',
			'errArcType'           : 'Tipo de archivo no soportado.',
			'errNoArchive'         : 'El archivo no es de tipo archivo o es de un tipo no soportado.',
			'errCmdNoSupport'      : 'El backend no soporta este comando.',
			'errReplByChild'       : 'La carpeta “$1” no puede ser reemplazada por un elemento contenido en ella.',
			'errArcSymlinks'       : 'Por razones de seguridad no se pueden descomprimir archivos que contengan enlaces simbólicos.', // edited 24.06.2012
			'errArcMaxSize'        : 'El tamaño del archivo excede el máximo permitido.',
			'errResize'            : 'Error al redimendionar "$1".',
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
			'errArchiveExec'       : 'Se ha producido un error durante la archivación: "$1"',
			'errExtractExec'       : 'Se ha producido un error durante la extracción de archivos: "$1"',
			'errNetUnMount'        : 'Imposible montar', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'No es convertible a UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Prueba con Google Chrome si quieres subir la carpeta entera.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Se agotó el tiempo de espera buscando "$1". Los resultados de búsqueda son parciales.', // from v2.1 added 12.1.2016

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
			'cmdmkfile'    : 'Nuevo archivo de texto',
			'cmdopen'      : 'Abrir',
			'cmdpaste'     : 'Pegar',
			'cmdquicklook' : 'Previsualizar',
			'cmdreload'    : 'Recargar',
			'cmdrename'    : 'Cambiar nombre',
			'cmdrm'        : 'Eliminar',
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

			/********************************** new items **********************************/
			'untitled file.txt' : 'NuevoArchivo.txt', // added 10.11.2015
			'untitled folder'   : 'NuevaCarpeta',   // added 10.11.2015
			'Archive'           : 'NuevoArchivo',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Se necesita confirmación',
			'confirmRm'       : '¿Está seguro de querer eliminar archivos?<br/>¡Esto no se puede deshacer!',
			'confirmRepl'     : '¿Reemplazar el antiguo archivo con el nuevo?',
			'confirmConvUTF8' : 'No está en UTF-8<br/>Convertir a UTF-8?<br/>Los contenidos se guardarán en UTF-8 tras la conversión.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Ha sido modificado.<br/>Perderás los cambios si no los guardas.', // from v2.1 added 15.7.2015
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
			'rmFromPlaces'    : 'Eliminar en sus ubicaciones',
			'aspectRatio'     : 'Relación de aspecto',
			'scale'           : 'Escala',
			'width'           : 'Ancho',
			'height'          : 'Alto',
			'resize'          : 'Redimensionar',
			'crop'            : 'Recortar',
			'rotate'          : 'Rotar',
			'rotate-cw'       : 'Rotar 90 grados en sentido horario',
			'rotate-ccw'      : 'Rotar 90 grados en sentido antihorario',
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
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
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

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Desconocido',
			'kindFolder'      : 'Carpeta',
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
			'kindVideo'       : 'Archivo de video',
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

