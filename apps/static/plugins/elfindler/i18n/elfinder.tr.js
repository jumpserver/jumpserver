/**
 * Türkçe translation
 * @author I.Taskinoglu & A.Kaya <alikaya@armsyazilim.com>
 * @author Abdullah ELEN <abdullahelen@msn.com>
 * @author Osman KAYAN <osmnkayan@gmail.com>
 * @version 2018-04-13
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
		translator : 'I.Taskinoglu & A.Kaya &lt;alikaya@armsyazilim.com&gt;, Abdullah ELEN &lt;abdullahelen@msn.com&gt;, Osman KAYAN &lt;osmnkayan@gmail.com&gt;',
		language   : 'Türkçe',
		direction  : 'ltr',
		dateFormat : 'd.m.Y H:i', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 H:i', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'ymd-His', // to apply if upload file is noname: 120513172700
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
			'errInvDirname'        : 'Geçersiz klasör ismi',  // from v2.1.24 added 12.4.2017
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
			'errTrash'             : 'Çöp kutusuna taşınamıyor.', // from v2.1.24 added 30.4.2017
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
			'errFtpDownloadFile'   : 'Dosya FTP: "$1" adresinden indirilemiyor.',
			'errFtpUploadFile'     : 'Dosya FTP: "$1" adresine yüklenemiyor.',
			'errFtpMkdir'          : 'FTP: "$1" üzerinde uzak dizin oluşturulamıyor.',
			'errArchiveExec'       : '"$1" Dosyalarında arşivlenirken hata oluştu.',
			'errExtractExec'       : '"$1" Dosyaları arşivden çıkartılırken hata oluştu.',
			'errNetUnMount'        : 'Bağlantı kaldırılamıyor.', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'UTF-8\'e dönüştürülemez.', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'Klasör yükleyebilmek için daha modern bir tarayıcıya ihtiyacınız var.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : '"$1" araması zaman aşımına uğradı. Kısmi arama sonuçları listeleniyor.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'Yeniden yetkilendirme gerekiyor.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'Maksimum seçilebilir öge sayısı $1 adettir', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'Çöp kutusundan geri yüklenemiyor. Geri yükleme notkası belirlenemiyor.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'Editör bu dosya türünü bulamıyor.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'Sunucu tarafında beklenilmeyen bir hata oluştu.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : '"$1" klasörü boşaltılamıyor.', // from v2.1.25 added 22.6.2017

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
			'cmdmkdir'     : 'Yeni klasör',
			'cmdmkdirin'   : 'Yeni Klasör / aç', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'Yeni dosya',
			'cmdopen'      : 'Aç',
			'cmdpaste'     : 'Yapıştır',
			'cmdquicklook' : 'Ön izleme',
			'cmdreload'    : 'Geri Yükle',
			'cmdrename'    : 'Yeniden Adlandır',
			'cmdrm'        : 'Sil',
			'cmdtrash'     : 'Çöpe at', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'geri yükle', //from v2.1.24 added 3.5.2017
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
			'cmdopendir'   : 'Klasör aç', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'Sütun genişliğini sıfırla', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'Tam ekran', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'Taşı', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'Klasörü boşalt', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'Geri al', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'Yinele', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'Tercihler', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'Tümünü seç', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'Seçimi temizle', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'Diğerlerini seç', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : 'Yeni Sekmede aç', // from v2.1.38 added 3.4.2018

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
			'btnRename'    : 'Yeniden adlandır',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'Yeniden adlandır(Tümü)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'Önceki ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'Sonraki ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'Farklı Kaydet', // from v2.1.25 added 24.5.2017

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
			'ntfsmth'     : 'İşlem yapılıyor',
			'ntfloadimg'  : 'Resim yükleniyor',
			'ntfnetmount' : 'Ağ birimine bağlanılıyor', // added 18.04.2012
			'ntfnetunmount': 'Ağ birimi bağlantısı kesiliyor', // from v2.1 added 30.04.2012
			'ntfdim'      : 'Resim boyutu alınıyor', // added 20.05.2013
			'ntfreaddir'  : 'Klasör bilgisi okunuyor', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Bağlantının URL\'si alınıyor', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'Dosya modu değiştiriliyor', // from v2.1 added 20.6.2015
			'ntfpreupload': 'Yüklenen dosya ismi doğrulanıyor', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'İndirilecek dosya oluşturuluyor', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'Dosya yolu bilgileri alınıyor', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'Yüklenen dosya işleniyor', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'Çöp kutusuna atma', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'Çöp kutusundan geri yükle', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'Hedef klasör kontrol ediliyor', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'Önceki işlemi geri alma', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'Önceki geri almayı tekrarlama', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'Çöp', //from v2.1.24 added 29.4.2017

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
			'sortperm'          : 'izinlere göre', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'moduna göre',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'sahibine göre',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'grubuna göre',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'Ayrıca ağaç görünümü',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'YeniDosya.txt', // added 10.11.2015
			'untitled folder'   : 'YeniKlasor',   // added 10.11.2015
			'Archive'           : 'YeniArsiv',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'Onay gerekli',
			'confirmRm'       : 'Dosyaları kaldırmak istediğinden emin misin?<br/>Bu işlem geri alınamaz!',
			'confirmRepl'     : 'Eski dosya yenisi ile değiştirilsin mi?',
			'confirmRest'     : 'Mevcut öge çöp kutusundaki ögeyle değiştirilsin mi?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'UTF-8 değil<br/>UTF-8\'e dönüştürülsün mü?<br/>Dönüştürme sonrası kaydedebilmek için içeriğin UTF-8 olması gerekir.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'Bu dosyanın karakter kodlaması tespit edilemedi. Düzenleme için geçici olarak UTF-8\'e dönüştürülmesi gerekir.<br/>Lütfen bu dosyanın karakter kodlamasını seçin.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'Düzenlenmiş içerik.<br/>Değişiklikleri kaydetmek istemiyorsanız son yapılanlar kaybolacak.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'Öğeleri çöp kutusuna taşımak istediğinizden emin misiniz?', //from v2.1.24 added 29.4.2017
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
			'shortcutsof'     : 'Kısayollar devre dışı',
			'dropFiles'       : 'Dosyaları buraya taşı',
			'or'              : 'veya',
			'selectForUpload' : 'Yüklemek için dosyaları seçin',
			'moveFiles'       : 'Dosyaları taşı',
			'copyFiles'       : 'Dosyaları kopyala',
			'restoreFiles'    : 'Öğeleri geri yükle', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Yerlerinden sil',
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
			'port'                : 'Kapı(Port)', // added 18.04.2012
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
			'autoSync'        : 'Otomatik senkronizasyon',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Yukarı taşı',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'URL bağlantısı alın', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'Seçili öğeler ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Klasör kimliği', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Çevrimdışı erişime izin ver', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'Yeniden kimlik doğrulaması için', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Şimdi yükleniyor...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'Çoklu dosya aç', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': '$1 dosyalarını açmaya çalışıyorsunuz. Tarayıcıda açmak istediğinizden emin misiniz?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'Arama hedefinde eşleşen sonuç bulunamadı.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'Dosya düzenleniyor.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : '$1 öğe seçtiniz.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'Panonuzda $1 öğeniz var.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Artan arama yalnızca geçerli görünümden yapılır.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'Eski durumuna getir', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 tamamlandı', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Durum menüsü', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Sayfa çevir', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Disk kök dizini', // from v2.1.16 added 16.9.2016
			'reset'           : 'Sıfırla', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'Arkaplan rengi', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Renk seçici', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8px Izgara', // from v2.1.16 added 4.10.2016
			'enabled'         : 'Etkin', // from v2.1.16 added 4.10.2016
			'disabled'        : 'Engelli', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'Geçerli görünümde arama sonucu bulunamadı. Arama sonucunu genişletmek için \\APress [Enter]  yapın', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'Geçerli görünümde ilk harf arama sonuçları boş.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'Metin etiketi', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '$1 dakika kaldı', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Seçilen kodlamayla yeniden aç', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Seçilen kodlamayla kaydet', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'Klasör seç', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'İlk arama sayfası', // from v2.1.23 added 24.3.2017
			'presets'         : 'Hazır ayarlar', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'çok fazla öge var çöp kutusuna atılamaz.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'Metin alanı(TextArea)', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : '"$1" klasörünü boşalt.', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : '"$1" klasöründe öge yok.', // from v2.1.25 added 22.6.2017
			'preference'      : 'Tercih', // from v2.1.26 added 28.6.2017
			'language'        : 'Dil ayarları', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Bu tarayıcıda kayıtlı ayarları başlat', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Araç çubuğu ayarları', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... $1 karakter kaldı',  // from v2.1.29 added 30.8.2017
			'sum'             : 'Toplam', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Kaba dosya boyutu', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Fare ile üzerine gelince diyalog öğesi odaklansın',  // from v2.1.30 added 2.11.2017
			'select'          : 'Seç', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'Dosya seçildiğinde işleme al', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Geçen sefer kullanılan editörle aç', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'Zıt seçim', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : '$1 seçilen öğeleri $2 gibi yeniden adlandırmak istediğinizden emin misiniz?</br>Bu geri alınamaz!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Yığın adını değiştir', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Sayı', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Ön ek kele', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Son ek ekle', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Uzantıyı değiştir', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Sütun ayarları (Liste görünümü)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'Tüm değişiklikler hemen arşive yansıtılacaktır.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Herhangi bir değişiklik, bu birimi kaldırılıncaya kadar yansıtılmayacaktır.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'Bu cihaza monte edilen aşağıdaki birim (ler) de bağlanmamıştır. Çıkardığınızdan emin misiniz?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'Seçim Bilgisi', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Dosya imza(hash) algoritmaları', // from v2.1.33 added 10.3.2018
			'infoItems'       : 'öğelerin bilgisi (Seçim Bilgi Paneli)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'Çıkmak için tekrar basın.', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'Araç Çubuğu', // from v2.1.38 added 4.4.2018
			'workspace'       : 'Çalışma alanı', // from v2.1.38 added 4.4.2018
			'dialog'          : 'Diyalog', // from v2.1.38 added 4.4.2018
			'all'             : 'Tümü', // from v2.1.38 added 4.4.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'Bilinmiyor',
			'kindRoot'        : 'Sürücü Kök dizini', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'Klasör',
			'kindSelects'     : 'Seçim', // from v2.1.29 added 29.8.2017
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

