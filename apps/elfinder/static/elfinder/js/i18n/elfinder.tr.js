/**
 * Türkçe translation
 * @author I.Taskinoglu & A.Kaya <alikaya@armsyazilim.com>
 * @author Abdullah ELEN <abdullahelen@msn.com>
 * @version 2016-11-12
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
	elFinder.prototype.i18.tr = {
		translator : 'I.Taskinoglu & A.Kaya &lt;alikaya@armsyazilim.com&gt;, Abdullah ELEN &lt;abdullahelen@msn.com&gt;',
		language   : 'Türkçe',
		direction  : 'ltr',
		dateFormat : 'd.m.Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'Hata',
			'errUnknown'           : 'Bilinmeyen hata.',
			'errUnknownCmd'        : 'Bilinmeyen komut.',
			'errJqui'              : 'Geçersiz jQuery UI yapılandırması. Seçilebilir, sürükle ve bırak bileşenlerini içermelidir.',
			'errNode'              : 'elFinder, DOM Element\'ini oluşturması gerekir.',
			'errURL'               : 'Geçersiz elFinder yapılandırması! URL seçeneği ayarlı değil.',
			'errAccess'            : 'Erişim engellendi.',
			'errConnect'           : 'Sunucuya bağlanamıyor.',
			'errAbort'             : 'Bağlantı durduruldu.',
			'errTimeout'           : 'Bağlantı zaman aşımı.',
			'errNotFound'          : 'Sunucu bulunamadı.',
			'errResponse'          : 'Geçersiz sunucu yanıtı.',
			'errConf'              : 'Geçersiz sunucu yapılandırması.',
			'errJSON'              : 'PHP JSON modülü kurulu değil.',
			'errNoVolumes'         : 'Okunabilir birimler mevcut değil.',
			'errCmdParams'         : '"$1" komutu için geçersiz parametre.',
			'errDataNotJSON'       : 'Bu veri JSON formatında değil.',
			'errDataEmpty'         : 'Boş veri.',
			'errCmdReq'            : 'Sunucu isteği için komut adı gerekli.',
			'errOpen'              : '"$1" açılamıyor.',
			'errNotFolder'         : 'Bu nesne bir klasör değil.',
			'errNotFile'           : 'Bu nesne bir dosya değil.',
			'errRead'              : '"$1" okunamıyor.',
			'errWrite'             : '"$1" yazılamıyor.',
			'errPerm'              : 'Yetki engellendi.',
			'errLocked'            : '"$1" kilitli. Bu nedenle taşıma, yeniden adlandırma veya kaldırma yapılamıyor.',
			'errExists'            : '"$1" adında bir dosya zaten var.',
			'errInvName'           : 'Geçersiz dosya ismi.',
			'errFolderNotFound'    : 'Klasör bulunamıyor.',
			'errFileNotFound'      : 'Dosya bulunamadı.',
			'errTrgFolderNotFound' : 'Hedef klasör "$1" bulunamadı.',
			'errPopup'             : 'Tarayıcı popup penceresi açmayı engelledi. Tarayıcı ayarlarından dosya açmayı aktif hale getirin.',
			'errMkdir'             : 'Klasör oluşturulamıyor "$1".',
			'errMkfile'            : '"$1" dosyası oluşturulamıyor.',
			'errRename'            : '"$1" yeniden adlandırma yapılamıyor.',
			'errCopyFrom'          : '"$1" biriminden dosya kopyalamaya izin verilmedi.',
			'errCopyTo'            : '"$1" birimine dosya kopyalamaya izin verilmedi.',
			'errMkOutLink'         : 'Kök birim dışında bir bağlantı oluşturulamıyor', // from v2.1 added 03.10.2015
			'errUpload'            : 'Dosya yükleme hatası.',  // old name - errUploadCommon
			'errUploadFile'        : '"$1" dosya yüklenemedi.', // old name - errUpload
			'errUploadNoFiles'     : 'Yüklenecek dosya bulunamadı.',
			'errUploadTotalSize'   : 'Veri izin verilen boyuttan büyük.', // old name - errMaxSize
			'errUploadFileSize'    : 'Dosya izin verilen boyuttan büyük.', //  old name - errFileMaxSize
			'errUploadMime'        : 'Dosya türüne izin verilmedi.',
			'errUploadTransfer'    : '"$1" transfer hatası.',
			'errUploadTemp'        : 'Yükleme için geçici dosya yapılamıyor.', // from v2.1 added 26.09.2015
			'errNotReplace'        : '"$1" nesnesi bu konumda zaten var ve başka türde nesne ile değiştirilemez.', // new
			'errReplace'           : 'Değişiklik yapılamıyor "$1".',
			'errSave'              : '"$1" kaydedilemiyor.',
			'errCopy'              : '"$1" kopyalanamıyor.',
			'errMove'              : '"$1" taşınamıyor.',
			'errCopyInItself'      : '"$1" kendi içine kopyalanamaz.',
			'errRm'                : '"$1" kaldırılamıyor.',
			'errRmSrc'             : 'Kaynak dosya(lar) kaldırılamıyor.',
			'errExtract'           : '"$1" kaynağından dosyalar çıkartılamıyor.',
			'errArchive'           : 'Arşiv oluşturulamıyor.',
			'errArcType'           : 'Desteklenmeyen arşiv türü.',
			'errNoArchive'         : 'Dosya arşiv değil veya desteklenmeyen arşiv türü.',
			'errCmdNoSupport'      : 'Sunucu bu komutu desteklemiyor.',
			'errReplByChild'       : '“$1” klasörü içerdiği bir öğe tarafından değiştirilemez.',
			'errArcSymlinks'       : 'Sembolik bağlantıları içeren arşivlerin açılması güvenlik nedeniyle reddedildi.', // edited 24.06.2012
			'errArcMaxSize'        : 'Arşiv dosyaları izin verilen maksimum boyutu aştı.',
			'errResize'            : '"$1" yeniden boyutlandırılamıyor.',
			'errResizeDegree'      : 'Geçersiz döndürme derecesi.',  // added 7.3.2013
			'errResizeRotate'      : 'Resim döndürülemiyor.',  // added 7.3.2013
			'errResizeSize'        : 'Geçersiz resim boyutu.',  // added 7.3.2013
			'errResizeNoChange'    : 'Resim boyutu değiştirilemez.',  // added 7.3.2013
			'errUsupportType'      : 'Desteklenmeyen dosya türü.',
			'errNotUTF8Content'    : 'Dosya "$1" UTF-8 olmadığından düzenlenemez.',  // added 9.11.2011
			'errNetMount'          : '"$1" bağlanamadı.', // added 17.04.2012
			'errNetMountNoDriver'  : 'Desteklenmeyen protokol.',     // added 17.04.2012
			'errNetMountFailed'    : 'Bağlama hatası.',         // added 17.04.2012
			'errNetMountHostReq'   : 'Sunucu gerekli.', // added 18.04.2012
			'errSessionExpires'    : 'Uzun süre işlem yapılmadığından oturumunuz sonlandı.',
			'errCreatingTempDir'   : 'Geçici dizin oluşturulamıyor: "$1"',
			'errFtpDownloadFile'   : 'Unable to download file from FTP: "$1"',
			'errFtpUploadFile'     : 'Unable to upload file to FTP: "$1"',
			'errFtpMkdir'          : 'Unable to create remote directory on FTP: "$1"',
			'errArchiveExec'       : 'Error while archiving files: "$1"',
			'errExtractExec'       : 'Error while extracting files: "$1"',
			'errNetUnMount'        : 'Unable to unmount', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'Not convertible to UTF-8', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Try Google Chrome, If you\'d like to upload the folder.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : 'Timed out while searching "$1". Search result is partial.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Re-authorization is required.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Max number of selectable items is $1.', // from v2.1.17 added 17.10.2016

			/******************************* commands names ********************************/
			'cmdarchive'   : 'Arşiv oluştur',
			'cmdback'      : 'Geri',
			'cmdcopy'      : 'Kopyala',
			'cmdcut'       : 'Kes',
			'cmddownload'  : 'İndir',
			'cmdduplicate' : 'Çoğalt',
			'cmdedit'      : 'Dosyayı düzenle',
			'cmdextract'   : 'Arşivden dosyaları çıkart',
			'cmdforward'   : 'İleri',
			'cmdgetfile'   : 'Dosyaları seç',
			'cmdhelp'      : 'Bu yazılım hakkında',
			'cmdhome'      : 'Anasayfa',
			'cmdinfo'      : 'Bilgi göster',
			'cmdmkdir'     : 'Yeni Klasör',
			'cmdmkdirin'   : 'Into new folder', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Yeni metin dosyası',
			'cmdopen'      : 'Aç',
			'cmdpaste'     : 'Yapıştır',
			'cmdquicklook' : 'Ön izleme',
			'cmdreload'    : 'Geri Yükle',
			'cmdrename'    : 'Yeniden Adlandır',
			'cmdrm'        : 'Sil',
			'cmdsearch'    : 'Dosyaları bul',
			'cmdup'        : 'Üst dizine çık',
			'cmdupload'    : 'Dosyaları yükle',
			'cmdview'      : 'Görüntüle',
			'cmdresize'    : 'Resmi yeniden boyutlandır',
			'cmdsort'      : 'Sırala',
			'cmdnetmount'  : 'Bağlı ağ birimi', // added 18.04.2012
			'cmdnetunmount': 'Devredışı bırak', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'Yerlere', // added 28.12.2014
			'cmdchmod'     : 'Mod değiştir', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'Open a folder', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Reset column width', // from v2.1.13 added 12.06.2016
			'cmdmove'      : 'Move', // from v2.1.15 added 21.08.2016

			/*********************************** buttons ***********************************/
			'btnClose'  : 'Kapat',
			'btnSave'   : 'Kaydet',
			'btnRm'     : 'Kaldır',
			'btnApply'  : 'Uygula',
			'btnCancel' : 'İptal',
			'btnNo'     : 'Hayır',
			'btnYes'    : 'Evet',
			'btnMount'  : 'Bağla',  // added 18.04.2012
			'btnApprove': 'Git $1 & onayla', // from v2.1 added 26.04.2012
			'btnUnmount': 'Bağlantıyı kes', // from v2.1 added 30.04.2012
			'btnConv'   : 'Dönüştür', // from v2.1 added 08.04.2014
			'btnCwd'    : 'Buraya',      // from v2.1 added 22.5.2015
			'btnVolume' : 'Birim',    // from v2.1 added 22.5.2015
			'btnAll'    : 'Hepsi',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME Türü', // from v2.1 added 22.5.2015
			'btnFileName':'Dosya adı',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'Kaydet & Kapat', // from v2.1 added 12.6.2015
			'btnBackup' : 'Yedekle', // fromv2.1 added 28.11.2015

			/******************************** notifications ********************************/
			'ntfopen'     : 'Klasör Aç',
			'ntffile'     : 'Dosya Aç',
			'ntfreload'   : 'Klasör içeriğini yeniden yükle',
			'ntfmkdir'    : 'Dizin oluşturuluyor',
			'ntfmkfile'   : 'Dosyaları oluşturma',
			'ntfrm'       : 'Dosyaları sil',
			'ntfcopy'     : 'Dosyaları kopyala',
			'ntfmove'     : 'Dosyaları taşı',
			'ntfprepare'  : 'Dosyaları kopyalamaya hazırla',
			'ntfrename'   : 'Dosyaları yeniden adlandır',
			'ntfupload'   : 'Dosyalar yükleniyor',
			'ntfdownload' : 'Dosyalar indiriliyor',
			'ntfsave'     : 'Dosyalar kaydediliyor',
			'ntfarchive'  : 'Arşiv oluşturuluyor',
			'ntfextract'  : 'Arşivden dosyalar çıkartılıyor',
			'ntfsearch'   : 'Dosyalar aranıyor',
			'ntfresize'   : 'Resimler boyutlandırılıyor',
			'ntfsmth'     : 'İşlem yapılıyor >_<',
			'ntfloadimg'  : 'Resim yükleniyor',
			'ntfnetmount' : 'Ağ birimine bağlanılıyor', // added 18.04.2012
			'ntfnetunmount': 'Ağ birimi bağlantısı kesiliyor', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Resim boyutu alınıyor', // added 20.05.2013
			'ntfreaddir'  : 'Klasör bilgisi okunuyor', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Bağlantının URL\'si alınıyor', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Dosya modu değiştiriliyor', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Verifying upload file name', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'Creating a file for download', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Getting path infomation', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Processing the uploaded file', // from v2.1.17 added 2.11.2016

			/************************************ dates **********************************/
			'dateUnknown' : 'Bilinmiyor',
			'Today'       : 'Bugün',
			'Yesterday'   : 'Dün',
			'msJan'       : 'Oca',
			'msFeb'       : 'Şub',
			'msMar'       : 'Mar',
			'msApr'       : 'Nis',
			'msMay'       : 'May',
			'msJun'       : 'Haz',
			'msJul'       : 'Tem',
			'msAug'       : 'Ağu',
			'msSep'       : 'Eyl',
			'msOct'       : 'Ekm',
			'msNov'       : 'Kas',
			'msDec'       : 'Ara',
			'January'     : 'Ocak',
			'February'    : 'Şubat',
			'March'       : 'Mart',
			'April'       : 'Nisan',
			'May'         : 'Mayıs',
			'June'        : 'Haziran',
			'July'        : 'Temmuz',
			'August'      : 'Ağustos',
			'September'   : 'Eylül',
			'October'     : 'Ekim',
			'November'    : 'Kasım',
			'December'    : 'Aralık',
			'Sunday'      : 'Pazar',
			'Monday'      : 'Pazartesi',
			'Tuesday'     : 'Salı',
			'Wednesday'   : 'Çarşamba',
			'Thursday'    : 'Perşembe',
			'Friday'      : 'Cuma',
			'Saturday'    : 'Cumartesi',
			'Sun'         : 'Paz',
			'Mon'         : 'Pzt',
			'Tue'         : 'Sal',
			'Wed'         : 'Çar',
			'Thu'         : 'Per',
			'Fri'         : 'Cum',
			'Sat'         : 'Cmt',

			/******************************** sort variants ********************************/
			'sortname'          : 'Ada göre',
			'sortkind'          : 'Türe göre',
			'sortsize'          : 'Boyuta göre',
			'sortdate'          : 'Tarihe göre',
			'sortFoldersFirst'  : 'Önce klasörler',
			'sortperm'          : 'by permission', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'by mode',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'by owner',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'by group',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Also Treeview',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'YeniDosya.txt', // added 10.11.2015
			'untitled folder'   : 'YeniKlasor',   // added 10.11.2015
			'Archive'           : 'YeniArsiv',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Onay gerekli',
			'confirmRm'       : 'Dosyaları kaldırmak istediğinden emin misin?<br/>Bu işlem geri alınamaz!',
			'confirmRepl'     : 'Eski dosya yenisi ile değiştirilsin mi?',
			'confirmConvUTF8' : 'UTF-8 değil<br/>UTF-8\'e dönüştürülsün mü?<br/>Dönüştürme sonrası kaydedebilmek için içeriğin UTF-8 olması gerekir.', // from v2.1 added 08.04.2014
			'confirmNotSave'  : 'Düzenlenmiş içerik.<br/>Değişiklikleri kaydetmek istemiyorsanız son yapılanlar kaybolacak.', // from v2.1 added 15.7.2015
			'apllyAll'        : 'Tümüne uygula',
			'name'            : 'İsim',
			'size'            : 'Boyut',
			'perms'           : 'Yetkiler',
			'modify'          : 'Değiştirildi',
			'kind'            : 'Tür',
			'read'            : 'oku',
			'write'           : 'yaz',
			'noaccess'        : 'erişim yok',
			'and'             : 've',
			'unknown'         : 'bilinimiyor',
			'selectall'       : 'Tüm dosyaları seç',
			'selectfiles'     : 'Dosya(lar)ı seç',
			'selectffile'     : 'İlk dosyayı seç',
			'selectlfile'     : 'Son dosyayı seç',
			'viewlist'        : 'Liste görünümü',
			'viewicons'       : 'Simge görünümü',
			'places'          : 'Yerler',
			'calc'            : 'Hesapla',
			'path'            : 'Yol',
			'aliasfor'        : 'Takma adı:',
			'locked'          : 'Kilitli',
			'dim'             : 'Ölçüler',
			'files'           : 'Dosyalar',
			'folders'         : 'Klasörler',
			'items'           : 'Nesneler',
			'yes'             : 'evet',
			'no'              : 'hayır',
			'link'            : 'Bağlantı',
			'searcresult'     : 'Arama sonuçları',
			'selected'        : 'Seçili öğeler',
			'about'           : 'Hakkında',
			'shortcuts'       : 'Kısayollar',
			'help'            : 'Yardım',
			'webfm'           : 'Web dosyası yöneticisi',
			'ver'             : 'Sürüm',
			'protocolver'     : 'protokol sürümü',
			'homepage'        : 'Proje Anasayfası',
			'docs'            : 'Belgeler',
			'github'          : 'Github\'ta bizi takip edin',
			'twitter'         : 'Twitter\'da bizi takip edin',
			'facebook'        : 'Facebook\'ta bize katılın',
			'team'            : 'Takım',
			'chiefdev'        : 'geliştirici şefi',
			'developer'       : 'geliştirici',
			'contributor'     : 'iştirakçi',
			'maintainer'      : 'bakıcı',
			'translator'      : 'çeviri',
			'icons'           : 'Simgeler',
			'dontforget'      : 've havlunuzu almayı unutmayın',
			'shortcutsof'     : 'Shortcuts disabled',
			'dropFiles'       : 'Dosyaları buraya taşı',
			'or'              : 'veya',
			'selectForUpload' : 'Yüklemek için dosyaları seçin',
			'moveFiles'       : 'Dosyaları taşı',
			'copyFiles'       : 'Dosyaları kopyala',
			'rmFromPlaces'    : 'Remove from places',
			'aspectRatio'     : 'Görünüm oranı',
			'scale'           : 'Ölçeklendir',
			'width'           : 'Genişlik',
			'height'          : 'Yükseklik',
			'resize'          : 'Boyutlandır',
			'crop'            : 'Kırp',
			'rotate'          : 'Döndür',
			'rotate-cw'       : '90 derece sağa döndür',
			'rotate-ccw'      : '90 derece sola döndür',
			'degree'          : 'Derece',
			'netMountDialogTitle' : 'Bağlı (Mount) ağ birimi', // added 18.04.2012
			'protocol'            : 'Protokol', // added 18.04.2012
			'host'                : 'Sunucu', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'Kullanıcı', // added 18.04.2012
			'pass'                : 'Şifre', // added 18.04.2012
			'confirmUnmount'      : 'Bağlantı kesilsin mi $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Dosyaları tarayıcıdan yapıştır veya bırak', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Dosyaları buraya yapıştır veya bırak', // from v2.1 added 07.04.2014
			'encoding'        : 'Kodlama', // from v2.1 added 19.12.2014
			'locale'          : 'Yerel',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'Hedef: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Giriş MIME Türüne Göre Arama', // from v2.1 added 22.5.2015
			'owner'           : 'Sahibi', // from v2.1 added 20.6.2015
			'group'           : 'Grup', // from v2.1 added 20.6.2015
			'other'           : 'Diğer', // from v2.1 added 20.6.2015
			'execute'         : 'Çalıştır', // from v2.1 added 20.6.2015
			'perm'            : 'Yetki', // from v2.1 added 20.6.2015
			'mode'            : 'Mod', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'Klasör boş', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'Klasör boş\\A Eklemek için sürükleyin', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'Klasör boş\\A Eklemek için basılı tutun', // from v2.1.6 added 30.12.2015
			'quality'         : 'Kalite', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Auto sync',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Move up',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Get URL link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Selected items ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Folder ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Allow offline access', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'To re-authenticate', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Now loading...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Open multiple files', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'You are trying to open the $1 files. Are you sure you want to open in browser?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'No match results in search targets', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'You are editing a file.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'You have selected $1 items.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'You have $1 items in the clipboard.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Incremental search is only from the current view.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Reinstate', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 complete', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Context menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Page turning', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Volume roots', // from v2.1.16 added 16.9.2016
			'reset'           : 'Reset', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Arkaplan rengi', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Renk seçici', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px tablo', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Enabled', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Disabled', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'No match results in current view', // from v2.1.16 added 5.10.2016
			'textLabel'       : 'Text lable', // from v2.1.17 added 13.10.2016

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Bilinmiyor',
			'kindRoot'        : 'Sürücü Kök dizini', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Klasör',
			'kindAlias'       : 'Alias (Takma ad)',
			'kindAliasBroken' : 'Bozuk alias',
			// applications
			'kindApp'         : 'Uygulama',
			'kindPostscript'  : 'Postscript dosyası',
			'kindMsOffice'    : 'Microsoft Office dosyası',
			'kindMsWord'      : 'Microsoft Word dosyası',
			'kindMsExcel'     : 'Microsoft Excel dosyası',
			'kindMsPP'        : 'Microsoft Powerpoint sunumu',
			'kindOO'          : 'Open Office dosyası',
			'kindAppFlash'    : 'Flash uygulaması',
			'kindPDF'         : 'PDF',
			'kindTorrent'     : 'Bittorrent dosyası',
			'kind7z'          : '7z arşivi',
			'kindTAR'         : 'TAR arşivi',
			'kindGZIP'        : 'GZIP arşivi',
			'kindBZIP'        : 'BZIP arşivi',
			'kindXZ'          : 'XZ arşivi',
			'kindZIP'         : 'ZIP arşivi',
			'kindRAR'         : 'RAR arşivi',
			'kindJAR'         : 'Java JAR dosyası',
			'kindTTF'         : 'True Type fontu',
			'kindOTF'         : 'Open Type fontu',
			'kindRPM'         : 'RPM paketi',
			// texts
			'kindText'        : 'Metin dosyası',
			'kindTextPlain'   : 'Düz metin',
			'kindPHP'         : 'PHP kodu',
			'kindCSS'         : 'CSS dosyası',
			'kindHTML'        : 'HTML dosyası',
			'kindJS'          : 'Javascript kodu',
			'kindRTF'         : 'Zengin Metin Belgesi',
			'kindC'           : 'C kodu',
			'kindCHeader'     : 'C başlık kodu',
			'kindCPP'         : 'C++ kodu',
			'kindCPPHeader'   : 'C++ başlık kodu',
			'kindShell'       : 'Unix shell scripti',
			'kindPython'      : 'Python kodu',
			'kindJava'        : 'Java kodu',
			'kindRuby'        : 'Ruby kodu',
			'kindPerl'        : 'Perl scripti',
			'kindSQL'         : 'SQL kodu',
			'kindXML'         : 'XML dosyası',
			'kindAWK'         : 'AWK kodu',
			'kindCSV'         : 'CSV',
			'kindDOCBOOK'     : 'Docbook XML dosyası',
			'kindMarkdown'    : 'Markdown dosyası', // added 20.7.2015
			// images
			'kindImage'       : 'Resim',
			'kindBMP'         : 'BMP dosyası',
			'kindJPEG'        : 'JPEG dosyası',
			'kindGIF'         : 'GIF dosyası',
			'kindPNG'         : 'PNG dosyası',
			'kindTIFF'        : 'TIFF dosyası',
			'kindTGA'         : 'TGA dosyası',
			'kindPSD'         : 'Adobe Photoshop dosyası',
			'kindXBITMAP'     : 'X bitmap dosyası',
			'kindPXM'         : 'Pixelmator dosyası',
			// media
			'kindAudio'       : 'Ses ortamı',
			'kindAudioMPEG'   : 'MPEG ses',
			'kindAudioMPEG4'  : 'MPEG-4 ses',
			'kindAudioMIDI'   : 'MIDI ses',
			'kindAudioOGG'    : 'Ogg Vorbis ses',
			'kindAudioWAV'    : 'WAV ses',
			'AudioPlaylist'   : 'MP3 listesi',
			'kindVideo'       : 'Video ortamı',
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

