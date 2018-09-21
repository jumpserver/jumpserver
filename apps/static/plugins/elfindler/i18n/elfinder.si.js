/**
 * Sinhala translation
 * @author CodeLyokoXtEAM <XcodeLyokoTEAM@gmail.com>
 * @version 2018-03-26
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
	elFinder.prototype.i18.si = {
		translator : 'CodeLyokoXtEAM &lt;XcodeLyokoTEAM@gmail.com&gt;',
		language   : 'Sinhala',
		direction  : 'ltr',
		dateFormat : 'Y.m.d h:i A', // Mar 13, 2012 05:27 PM
		fancyDateFormat : '$1 h:i A', // will produce smth like: Today 12:25 PM
		nonameDateFormat : 'Ymd-His', // to apply if upload file is noname: 120513172700
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'දෝෂයකි.',
			'errUnknown'           : 'නොදන්නා දෝෂයකි.',
			'errUnknownCmd'        : 'නොදන්නා විධානයකි.',
			'errJqui'              : 'වලංගු නොවන jQuery UI සැකැස්මකි. තේරිය හැකි, ඇදගෙන යාම සහ ඇද දැමිය හැකි කොටස් ඇතුළත් කළ යුතුය.',
			'errNode'              : 'ElFinder විසින් DOM Element නිර්මාණය කිරීමට අවශ්‍යව අැත.',
			'errURL'               : 'වලංගු නොවන elFinder සැකැස්මකි! URL විකල්පය සැකසා නැත.',
			'errAccess'            : 'භාවිතය අත්හිටුවා ඇත.',
			'errConnect'           : 'පසුබිම(Backend) වෙත සම්බන්ධ වීමට නොහැකිය.',
			'errAbort'             : 'සම්බන්ධතාවය වසාදමා ඇත.',
			'errTimeout'           : 'සම්බන්ධතා කල් ඉකුත්වී ඇත.',
			'errNotFound'          : 'පසුබිම(Backend) සොයාගත නොහැකි විය.',
			'errResponse'          : 'වලංගු නොවන පසුබිම(Backend) ප්‍රතිචාරය.',
			'errConf'              : 'වලංගු නොවන Backend සැකැස්මකි.',
			'errJSON'              : 'PHP JSON මොඩියුලය ස්ථාපනය කර නැත.',
			'errNoVolumes'         : 'කියවිය හැකි එ්කක(volumes) නොමැත.',
			'errCmdParams'         : '"$1" නම් විධානය වලංගු නොවන පරාමිතියකි.',
			'errDataNotJSON'       : 'JSON දත්ත නොවේ.',
			'errDataEmpty'         : 'හිස් දත්තයකි.',
			'errCmdReq'            : 'Backend සඳහා ඉල්ලන ලද විධානයේ නම අවශ්‍ය වේ.',
			'errOpen'              : '"$1" විවෘත කළ නොහැක.',
			'errNotFolder'         : 'අායිත්තම(object) ෆොල්ඩරයක් නොවේ.',
			'errNotFile'           : 'අායිත්තම(object) ගොනුවක් නොවේ.',
			'errRead'              : '"$1" කියවීමට නොහැක.',
			'errWrite'             : '"$1" තුල ලිවීමට නොහැකිය.',
			'errPerm'              : 'අවසරය නොමැත.',
			'errLocked'            : '"$1" අගුළු දමා ඇති අතර එය නැවත නම් කිරීම, සම්පූර්ණයෙන් විස්ථාපනය කිරීම හෝ ඉවත් කිරීම කළ නොහැක.',
			'errExists'            : '"$1" නම් ගොනුව දැනටමත් පවතී.',
			'errInvName'           : 'ගොනු නම වලංගු නොවේ.',
			'errInvDirname'        : 'ෆෝල්ඩර් නම වලංගු නොවේ.',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'ෆෝල්ඩරය හමු නොවිණි.',
			'errFileNotFound'      : 'ගොනුව හමු නොවිණි.',
			'errTrgFolderNotFound' : 'ඉලක්කගත ෆෝල්ඩරය "$1" හමු නොවිනි.',
			'errPopup'             : 'බ්‍රවුසරය උත්පතන කවුළුව විවෘත කිරීම වළක්වයි. ගොනු විවෘත කිරීම සඳහා බ්‍රවුසරයේ විකල්ප තුළ එය සක්රිය කරන්න.',
			'errMkdir'             : '"$1" ෆෝල්ඩරය සෑදීමට නොහැකිය.',
			'errMkfile'            : '"$1" ගොනුව සෑදිය නොහැක.',
			'errRename'            : '"$1" නැවත නම් කිරීමට නොහැකි විය.',
			'errCopyFrom'          : '"$1" volume යෙන් ගොනු පිටපත් කිරීම තහනම්ය.',
			'errCopyTo'            : '"$1" volume යට ගොනු පිටපත් කිරීම තහනම්ය.',
			'errMkOutLink'         : 'volume root යෙන් පිටතට සබැඳිය(link) නිර්මාණය කිරීමට නොහැකි විය.', // from v2.1 added 03.10.2015
			'errUpload'            : 'උඩුගත(upload) කිරීමේ දෝෂයකි.',  // old name - errUploadCommon
			'errUploadFile'        : '"$1" උඩුගත(upload) කිරීමට නොහැකි විය.', // old name - errUpload
			'errUploadNoFiles'     : 'උඩුගත(upload) කිරීම සඳහා ගොනු කිසිවක් සොයාගත නොහැකි විය.',
			'errUploadTotalSize'   : 'දත්ත අවසර දී අැති උපරිම ප්‍රමාණය ඉක්මවා ඇත.', // old name - errMaxSize
			'errUploadFileSize'    : 'ගොනු අවසර දී අැති උපරිම ප්‍රමාණය ඉක්මවා ඇත.', //  old name - errFileMaxSize
			'errUploadMime'        : 'ගොනු වර්ගයට අවසර නැත.',
			'errUploadTransfer'    : '"$1" ව මාරු කිරීමේ දෝෂයකි.',
			'errUploadTemp'        : 'upload කිරීම සඳහා තාවකාලික ගොනුව සෑදිය නොහැක.', // from v2.1 added 26.09.2015
			'errNotReplace'        : '"$1" අායිත්තම(object) දැනටමත් මෙම ස්ථානයේ පවතී, වෙනත් වර්ගයකිනි ප්‍රතිස්ථාපනය කළ නොහැක.', // new
			'errReplace'           : '"$1" ප්‍රතිස්ථාපනය කළ නොහැක.',
			'errSave'              : '"$1" සුරැකීමට නොහැක.',
			'errCopy'              : '"$1" පිටපත් කිරීමට නොහැක.',
			'errMove'              : '"$1" සම්පූර්ණයෙන් විස්ථාපනය කිරීමට නොහැක.',
			'errCopyInItself'      : '"$1" තුලට පිටපත් කිරීමට නොහැක.',
			'errRm'                : '"$1" ඉවත් කිරීමට නොහැකි විය.',
			'errTrash'             : 'කුණු-කූඩය තුලට දැමීමට නොහැක.', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : 'මූලාශ්‍රය ගොනු(ව) ඉවත් කළ නොහැක.',
			'errExtract'           : '"$1" වෙතින් ගොනු දිග හැරීමට නොහැක.',
			'errArchive'           : 'සංරක්ෂිතය සෑදීමට නොහැකි විය.',
			'errArcType'           : 'නොගැලපෙන සංරක්ෂණ වර්ගයකි.',
			'errNoArchive'         : 'ගොනුව නොගැලපෙන සංරක්ෂණ වර්ගයක් හෝ සංරක්ෂිතයක් නොවේ.',
			'errCmdNoSupport'      : 'පසුබිම(Backend) මෙම විධානය නොදනී.',
			'errReplByChild'       : '"$1" ෆෝල්ඩරය එහිම අඩංගු අයිතමයක් මගින් ප්‍රතිස්ථාපනය කළ නොහැක.',
			'errArcSymlinks'       : 'ආරක්ෂිත හේතුව නිසා අනුමත නොකෙරෙන සබැඳි සම්බන්දතා හෝ ලිපිගොනු නම් අඩංගු බැවින් සංරක්ෂිතය දිග හැරීම කිරීමට ඉඩ නොදෙන.', // edited 24.06.2012
			'errArcMaxSize'        : 'සංරක්ෂිතය ලිපිගොනු උපරිම ප්‍රමාණය ඉක්මවා ඇත.',
			'errResize'            : 'ප්‍රතිප්‍රමාණය කිරීමට නොහැකි විය.',
			'errResizeDegree'      : 'වලංගු නොවන භ්‍රමණ කෝණයකි.',  // added 7.3.2013
			'errResizeRotate'      : 'රූපය භ්‍රමණය කිරීමට නොහැකි විය.',  // added 7.3.2013
			'errResizeSize'        : 'රූපයේ ප්‍රමාණය වලංගු නොවේ.',  // added 7.3.2013
			'errResizeNoChange'    : 'රූපයේ ප්‍රමාණය වෙනස් නොවුණි.',  // added 7.3.2013
			'errUsupportType'      : 'නොගැලපෙන ගොනු වර්ගයකි.',
			'errNotUTF8Content'    : '"$1" ගොනුව UTF-8 හි නොමැති අතර සංස්කරණය කළ නොහැක.',  // added 9.11.2011
			'errNetMount'          : '"$1" සවි(mount) කිරීමට නොහැක.', // added 17.04.2012
			'errNetMountNoDriver'  : 'ප්‍රොටොකෝලය(protocol) නොගැලපේ.',     // added 17.04.2012
			'errNetMountFailed'    : 'සවි කිරීම(mount කිරීම) අසාර්ථක විය.',         // added 17.04.2012
			'errNetMountHostReq'   : 'ධාරකය(Host) අවශ්‍ය වේ.', // added 18.04.2012
			'errSessionExpires'    : 'ඔබේ අක්‍රියතාව හේතුවෙන් සැසිය(session) කල් ඉකුත් වී ඇත.',
			'errCreatingTempDir'   : 'තාවකාලික ඩිරෙක්ටරයක්(directory) ​​සෑදිය නොහැක: "$1"',
			'errFtpDownloadFile'   : 'FTP වලින් ගොනුව බාගත(download) කිරීමට නොහැකි විය: "$1"',
			'errFtpUploadFile'     : 'ගොනුව FTP වෙත උඩුගත(upload) කිරීමට නොහැකි විය: "$1"',
			'errFtpMkdir'          : 'FTP මත දුරස්ථ නාමාවලියක්(remote directory) නිර්මාණය කිරීමට නොහැකි විය: "$1"',
			'errArchiveExec'       : 'ගොනු සංරක්ෂණය(archiving) කිරීමේදී දෝෂයක් ඇතිවිය: "$1"',
			'errExtractExec'       : 'ගොනු දිගහැරීමේදී(extracting) දෝෂයක් ඇතිවිය: "$1"',
			'errNetUnMount'        : 'විසන්ධි කිරීමට(unmount) නොහැක.', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'UTF-8 වෙත පරිවර්තනය කළ නොහැක.', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'ඔබ ෆෝල්ඩරය උඩුගත(upload) කිරීමට කැමති නම් නවීන බ්‍රවුසරයකින් උත්සාහ කරන්න.', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : '"$1" සෙවීම කල් ඉකුත්වී ඇත. සෙවුම් ප්‍රතිඵල අර්ධ වශයෙන් දිස්වේ.', // from v2.1 added 12.1.2016
			'errReauthRequire'     : 'නැවත බලය(Re-authorization) ලබා දීම අවශ්‍ය වේ.', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : 'තෝරා ගත හැකි උපරිම අයිතම සංඛ්‍යාව $1 ක් වේ.', // from v2.1.17 added 17.10.2016
			'errRestore'           : 'කුණු කූඩයෙන් නැවත ලබා ගත නොහැක. යළි පිහිටුවීමේ ගමනාන්තය(restore destination) හඳුනාගත නොහැක.', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'මෙම ගොනු වර්ගයේ සංස්කාරකය හමු නොවිණි.', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'සේවාදායකයේ පැත්තෙන්(server side) දෝශයක් ඇතිවිය.', // from v2.1.25 added 16.6.2017
			'errEmpty'             : '"$1" ෆෝල්ඩරය හිස් කිරීමට නොහැක.', // from v2.1.25 added 22.6.2017

			/******************************* commands names ********************************/
			'cmdarchive'   : 'සංරක්ෂිතය(archive) නිර්මාණය කරන්න',
			'cmdback'      : 'ආපසු',
			'cmdcopy'      : 'පිටපත් කරන්න',
			'cmdcut'       : 'මුළුමනින්ම පිටපත් කරන්න(Cut)',
			'cmddownload'  : 'බාගත කරන්න(Download)',
			'cmdduplicate' : 'අනුපිටපත් කරන්න(Duplicate)',
			'cmdedit'      : 'ගොනුව සංස්කරණය කරන්න',
			'cmdextract'   : 'සංරක්ෂිතයේ ගොනු දිගහරින්න(Extract)',
			'cmdforward'   : 'ඉදිරියට',
			'cmdgetfile'   : 'ගොනු තෝරන්න',
			'cmdhelp'      : 'මෙම මෘදුකාංගය පිළිබඳව',
			'cmdhome'      : 'නිවහන(Home)',
			'cmdinfo'      : 'තොරතුරු ලබාගන්න',
			'cmdmkdir'     : 'අළුත් ෆෝල්ඩරයක්',
			'cmdmkdirin'   : 'අළුත් ෆෝල්ඩරයක් තුළට', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : 'නව ගොනුවක්',
			'cmdopen'      : 'විවෘත කරන්න',
			'cmdpaste'     : 'දමන්න(Paste)',
			'cmdquicklook' : 'පූර්ව දර්ශනයක්(Preview)',
			'cmdreload'    : 'නැවත අළුත් කරන්න(Reload)',
			'cmdrename'    : 'නම වෙනස් කරන්න',
			'cmdrm'        : 'මකන්න',
			'cmdtrash'     : 'කුණු කූඩයට දමන්න', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : 'යළි පිහිටුවන්න(Restore)', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'ගොනු සොයන්න',
			'cmdup'        : 'ප්‍ර්‍රධාන නාමාවලිය(parent directory) වෙත යන්න',
			'cmdupload'    : 'ගොනු උඩුගත(Upload) කරන්න',
			'cmdview'      : 'දර්ශනය(View)',
			'cmdresize'    : 'ප්‍රථිප්‍රමාණය සහ භ්‍රමණය',
			'cmdsort'      : 'වර්ගීකරණය කරන්න',
			'cmdnetmount'  : 'ජාල එ්කකයක් සවි කරන්න(Mount network volume)', // added 18.04.2012
			'cmdnetunmount': 'ගලවන්න(Unmount)', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'පහසු ස්ථානයට(To Places)', // added 28.12.2014
			'cmdchmod'     : 'ක්‍රමය වෙනස් කරන්න', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'ෆෝල්ඩරය විවෘත කරන්න', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : 'නැවත තීරු පළල පිහිටුවන්න', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'පුළුල් තිරය', // from v2.1.15 added 03.08.2016
			'cmdmove'      : 'මාරු කරන්න(Move)', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'ෆෝල්ඩරය හිස් කරන්න', // from v2.1.25 added 22.06.2017
			'cmdundo'      : 'නිෂ්ප්‍රභ කරන්න', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'නැවත කරන්න', // from v2.1.27 added 31.07.2017
			'cmdpreference': 'අභිමතයන් (Preferences)', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'සියල්ල තෝරන්න', // from v2.1.28 added 15.08.2017
			'cmdselectnone': 'කිසිවක් තෝරන්න එපා', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': 'විරුද්ධ අාකාරයට තෝරන්න', // from v2.1.28 added 15.08.2017

			/*********************************** buttons ***********************************/
			'btnClose'  : 'වසන්න',
			'btnSave'   : 'සුරකින්න',
			'btnRm'     : 'ඉවත් කරන්න',
			'btnApply'  : 'යොදන්න(Apply)',
			'btnCancel' : 'අවලංගු කරන්න',
			'btnNo'     : 'නැත',
			'btnYes'    : 'ඔව්',
			'btnMount'  : 'සවිකිරීම(Mount)',  // added 18.04.2012
			'btnApprove': 'කරුණාකර $1 අනුමත කරන්න', // from v2.1 added 26.04.2012
			'btnUnmount': 'ගලවන්න(Unmount)', // from v2.1 added 30.04.2012
			'btnConv'   : 'පරිවර්තනය කරන්න', // from v2.1 added 08.04.2014
			'btnCwd'    : 'මෙතන',      // from v2.1 added 22.5.2015
			'btnVolume' : 'එ්කකය(Volume)',    // from v2.1 added 22.5.2015
			'btnAll'    : 'සියල්ල',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIME වර්ගය', // from v2.1 added 22.5.2015
			'btnFileName':'ගොනුවේ නම',  // from v2.1 added 22.5.2015
			'btnSaveClose': 'සුරකින්න සහ වසන්න', // from v2.1 added 12.6.2015
			'btnBackup' : 'උපස්ථ(Backup) කරන්න', // fromv2.1 added 28.11.2015
			'btnRename'    : 'නම වෙනස් කරන්න',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'නම වෙනස් කරන්න(සියල්ල)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : 'පෙර ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : 'ඊළඟ ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : 'වෙනත් නමකින් සුරකිමින්(Save As)', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'ෆෝල්ඩරය විවෘත කරමින්',
			'ntffile'     : 'ගොනුව විවෘත කරමින්',
			'ntfreload'   : 'ෆෝල්ඩර් අන්තර්ගතය නැවත අළුත් කරමින්(Reloading)',
			'ntfmkdir'    : 'ෆෝල්ඩරයක් නිර්මාණය කරමින්',
			'ntfmkfile'   : 'ගොනුව නිර්මාණය කරමින්',
			'ntfrm'       : 'අයිතමයන් මකමින්',
			'ntfcopy'     : 'අයිතමයන් පිටපත් කරමින්',
			'ntfmove'     : 'අයිතමයන් සම්පූර්ණයෙන් විස්ථාපනය කරමින්',
			'ntfprepare'  : 'පවතින අයිතම පිරික්සමින්',
			'ntfrename'   : 'ගොනු නැවත නම් කරමින්',
			'ntfupload'   : 'ගොනු උඩුගත(uploading) කරමින්',
			'ntfdownload' : 'ගොනු බාගත(downloading) කරමින්',
			'ntfsave'     : 'ගොනු සුරකිමින්',
			'ntfarchive'  : 'සංරක්ෂණය(archive) සාදමින්',
			'ntfextract'  : 'සංරක්ෂණයෙන්(archive) ගොනු දිගහරිමින්(Extracting)',
			'ntfsearch'   : 'ගොනු සොයමින්',
			'ntfresize'   : 'රූප ප්‍රමාණය වෙනස් කරමින්',
			'ntfsmth'     : 'දෙයක් කරමින්',
			'ntfloadimg'  : 'පින්තූරය පූරණය කරමින්(Loading)',
			'ntfnetmount' : 'ජාල එ්කකයක් සවිකරමින්(Mounting network volume)', // added 18.04.2012
			'ntfnetunmount': 'ජාල එ්කකයක් ගලවමින්(Unmounting network volume)', // from v2.1 added 30.04.2012
			'ntfdim'      : 'පිංතූරයේ මානය(dimension) ලබාගනිමින්', // added 20.05.2013
			'ntfreaddir'  : 'ෆෝල්ඩරයේ තොරතුරු කියවමින්', // from v2.1 added 01.07.2013
			'ntfurl'      : 'Getting URL of link', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'ගොනු ආකරය වෙනස් කරමින්', // from v2.1 added 20.6.2015
			'ntfpreupload': 'උඩුගත(upload) කරන ලද ගොනු නාමය සත්‍යාපනය කරමින්(Verifying)', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'බාගත කරගැනීම(download) සඳහා ගොනුවක් නිර්මාණය කරමින්', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'මාර්ග(path) තොරතුරු ලබා ගනිමින්', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'උඩුගත කරන ලද(uploaded) ගොනුව සකසමින්', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'කුණු කූඩයට දමමින්', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'කුණු කූඩයට දැමීම යළි පිහිටුවමින්(Doing restore)', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : 'ගමනාන්ත(destination) ෆෝල්ඩරය පරීක්ෂා කරමින්', // from v2.1.24 added 3.5.2017
			'ntfundo'     : 'පෙර මෙහෙයුම(operation) ඉවත් කරමින්', // from v2.1.27 added 31.07.2017
			'ntfredo'     : 'පෙර ආපසු හැරවීම යළි සැකසමින්', // from v2.1.27 added 31.07.2017

			/*********************************** volumes *********************************/
			'volume_Trash' : 'කුණු කූඩය', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : 'නොදනී',
			'Today'       : 'අද',
			'Yesterday'   : 'ඊයේ',
			'msJan'       : 'ජනවා.',
			'msFeb'       : 'පෙබ.',
			'msMar'       : 'මාර්.',
			'msApr'       : 'අප්‍රේ.',
			'msMay'       : 'මැයි',
			'msJun'       : 'ජූනි',
			'msJul'       : 'ජුලි',
			'msAug'       : 'අගෝ.',
			'msSep'       : 'සැප්.',
			'msOct'       : 'ඔක්තෝ.',
			'msNov'       : 'නොවැ.',
			'msDec'       : 'දෙසැ.',
			'January'     : 'ජනවාරි',
			'February'    : 'පෙබරවාරි',
			'March'       : 'මාර්තු',
			'April'       : 'අප්‍රේල්',
			'May'         : 'මැයි',
			'June'        : 'ජූනි',
			'July'        : 'ජුලි',
			'August'      : 'අගෝස්තු',
			'September'   : 'සැප්තැම්බර්',
			'October'     : 'ඔක්තෝම්බර්',
			'November'    : 'නොවැම්බර්',
			'December'    : 'දෙසැම්බර්',
			'Sunday'      : 'ඉරිදා',
			'Monday'      : 'සඳුදා',
			'Tuesday'     : 'අඟහරුවාදා',
			'Wednesday'   : 'බදාදා',
			'Thursday'    : 'බ්‍රහස්පතින්දා',
			'Friday'      : 'සිකුරාදා',
			'Saturday'    : 'සෙනසුරාදා',
			'Sun'         : 'ඉරිදා',
			'Mon'         : 'සඳු.',
			'Tue'         : 'අඟහ.',
			'Wed'         : 'බදාදා',
			'Thu'         : 'බ්‍රහස්.',
			'Fri'         : 'සිකු.',
			'Sat'         : 'සෙන.',

			/******************************** sort variants ********************************/
			'sortname'          : 'නම අනුව',
			'sortkind'          : 'වර්ගය අනුව',
			'sortsize'          : 'ප්‍රමාණය අනුව',
			'sortdate'          : 'දිනය අනුව',
			'sortFoldersFirst'  : 'ෆෝල්ඩර වලට පළමු තැන',
			'sortperm'          : 'අවසරය අනුව', // from v2.1.13 added 13.06.2016
			'sortmode'          : 'අාකාරය අනුව',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'හිමිකරු අනුව',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'කණ්ඩායම අනුව',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'එලෙසටම රුක්සටහනත්(Treeview)',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : 'NewFile.txt', // added 10.11.2015
			'untitled folder'   : 'නව ෆෝල්ඩරයක්',   // added 10.11.2015
			'Archive'           : 'NewArchive',  // from v2.1 added 10.11.2015

			/********************************** messages **********************************/
			'confirmReq'      : 'තහවුරු කිරීම අවශ්‍යයි',
			'confirmRm'       : 'අයිතමයන් සදහටම ඉවත් කිරීමට අවශ්‍ය බව ඔබට විශ්වාසද?<br/>මෙය අාපසු හැරවිය නොහැකිය!',
			'confirmRepl'     : 'පැරණි අයිතමය නව එකක මගින් ප්‍රතිස්ථාපනය කරන්නද?',
			'confirmRest'     : 'දැනට පවතින අයිතමය කුණු කූඩය තුළ පවතින අයිතමය මගින් ප්‍රතිස්ථාපනය කරන්නද?', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'UTF-8 හි නොවේ<br/> UTF-8 වෙත පරිවර්තනය කරන්න ද?<br/>සුරැකීමෙන් පසු අන්තර්ගතය UTF-8 බවට පරිවර්තනය වේ.', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'මෙම ගොනුවෙහි කේතන කේත(Character encoding) හඳුනාගත නොහැකි විය. සංස්කරණ කිරීමට එය තාවකාලිකව UTF-8 වෙත පරිවර්තනය කිරීම අවශ්‍ය වේ.<br/>කරුණාකර මෙම ගොනුවෙහි අක්ෂර කේතන කේත(character encoding) තෝරන්න.', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : 'මෙය වෙනස් කර ඇත.<br/>ඔබට වෙනස්කම් සුරැකීමට නොහැකි නම් සිදු කරනු ලැබූ වෙනස්කම් අහිමි වේ.', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'කුණු කූඩය තුලට අයිතමය යැවීමට ඔබට අවශ්‍ය ද?', //from v2.1.24 added 29.4.2017
			'apllyAll'        : 'සියල්ලටම යොදන්න',
			'name'            : 'නම',
			'size'            : 'ප්‍රමාණය',
			'perms'           : 'අවසරය',
			'modify'          : 'නවීකරණය කෙරුණ ලද්දේ',
			'kind'            : 'ජාතිය',
			'read'            : 'කියවන්න',
			'write'           : 'ලියන්න',
			'noaccess'        : 'ප්‍රවේශයක් නොමැත',
			'and'             : 'සහ',
			'unknown'         : 'නොහඳුනයි',
			'selectall'       : 'සියලු ගොනු තෝරන්න',
			'selectfiles'     : 'ගොනු(ව) තෝරන්න',
			'selectffile'     : 'පළමු ගොනුව තෝරන්න',
			'selectlfile'     : 'අවසාන ගොනුව තෝරන්න',
			'viewlist'        : 'ලැයිස්තු අාකාරය',
			'viewicons'       : 'අයිකන අාකාරය',
			'places'          : 'Places',
			'calc'            : 'ගණනය කරන්න',
			'path'            : 'මාර්ගය',
			'aliasfor'        : 'Alias for',
			'locked'          : 'අගුළු දමා ඇත',
			'dim'             : 'මාන(Dimensions)',
			'files'           : 'ගොනු',
			'folders'         : 'ෆෝල්ඩර',
			'items'           : 'අයිතම(Items)',
			'yes'             : 'ඔව්',
			'no'              : 'නැත',
			'link'            : 'සබැඳිය(Link)',
			'searcresult'     : 'සෙවුම් ප්‍රතිඵල',
			'selected'        : 'තෝරාගත් අයිතම',
			'about'           : 'මේ ගැන',
			'shortcuts'       : 'කෙටිමං',
			'help'            : 'උදව්',
			'webfm'           : 'වෙබ් ගොනු කළමනාකරු',
			'ver'             : 'අනුවාදය(version)',
			'protocolver'     : 'ප්‍රොටොකෝලය අනුවාදය(protocol version)',
			'homepage'        : 'ව්‍යාපෘතිය නිවහන',
			'docs'            : 'ලේඛනගත කිරීම',
			'github'          : 'Github හරහා සංවාදයේ යෙදෙන්න',
			'twitter'         : 'Twitter හරහා අපව සම්බන්ධ වන්න',
			'facebook'        : 'Facebook හරහා අප සමඟ එකතු වන්න',
			'team'            : 'කණ්ඩායම',
			'chiefdev'        : 'ප්‍රධාන සංස්කරු(chief developer)',
			'developer'       : 'සංස්කරු(developer)',
			'contributor'     : 'දායකයා(contributor)',
			'maintainer'      : 'නඩත්තු කරන්නා(maintainer)',
			'translator'      : 'පරිවර්තකයා',
			'icons'           : 'අයිකන',
			'dontforget'      : 'and don\'t forget to take your towel',
			'shortcutsof'     : 'කෙටිමං අක්‍රීය කර ඇත',
			'dropFiles'       : 'ගොනු මෙතැනට ඇද දමන්න',
			'or'              : 'හෝ',
			'selectForUpload' : 'ගොනු තෝරන්න',
			'moveFiles'       : 'අායිත්තම සම්පූර්ණයෙන් විස්ථාපනය',
			'copyFiles'       : 'අයිතමයන් පිටපත් කරන්න',
			'restoreFiles'    : 'Restore items', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'Remove from places',
			'aspectRatio'     : 'දර්ශන අනුපාතය(Aspect ratio)',
			'scale'           : 'පරිමාණය',
			'width'           : 'පළල',
			'height'          : 'උස',
			'resize'          : 'ප්‍රතිප්‍රමානණය',
			'crop'            : 'Crop',
			'rotate'          : 'කැරකැවීම',
			'rotate-cw'       : 'අංශක 90කින් කරකවන්න CW',
			'rotate-ccw'      : 'අංශක 90කින් කරකවන්න CCW',
			'degree'          : '°',
			'netMountDialogTitle' : 'Mount network volume', // added 18.04.2012
			'protocol'            : 'Protocol', // added 18.04.2012
			'host'                : 'Host', // added 18.04.2012
			'port'                : 'Port', // added 18.04.2012
			'user'                : 'පරිශීලක', // added 18.04.2012
			'pass'                : 'මුරපදය', // added 18.04.2012
			'confirmUnmount'      : 'Are you unmount $1?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'Drop or Paste files from browser', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'Drop files, Paste URLs or images(clipboard) here', // from v2.1 added 07.04.2014
			'encoding'        : 'කේතීකරණය(Encoding)', // from v2.1 added 19.12.2014
			'locale'          : 'Locale',   // from v2.1 added 19.12.2014
			'searchTarget'    : 'ඉලක්කය: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : 'Search by input MIME Type', // from v2.1 added 22.5.2015
			'owner'           : 'හිමිකරු', // from v2.1 added 20.6.2015
			'group'           : 'සමූහය', // from v2.1 added 20.6.2015
			'other'           : 'වෙනත්', // from v2.1 added 20.6.2015
			'execute'         : 'ක්‍රයාත්මක කරන්න', // from v2.1 added 20.6.2015
			'perm'            : 'අවසරය', // from v2.1 added 20.6.2015
			'mode'            : 'Mode', // from v2.1 added 20.6.2015
			'emptyFolder'     : 'ෆෝල්ඩරය හිස්', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : 'ෆාේල්ඩරය හිස්\\A අායිත්තම අතහැරීමෙන් අැතුලු කරන්න', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : 'ෆාේල්ඩරය හිස්\\A දිර්ඝ එබීමෙන් අායිත්තම අැතුලු කරන්න', // from v2.1.6 added 30.12.2015
			'quality'         : 'ගුණාත්මකභාවය', // from v2.1.6 added 5.1.2016
			'autoSync'        : 'Auto sync',  // from v2.1.6 added 10.1.2016
			'moveUp'          : 'Move up',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'Get URL link', // from v2.1.7 added 9.2.2016
			'selectedItems'   : 'තෝරාගත් අයිතම ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'Folder ID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'Allow offline access', // from v2.1.10 added 3.25.2016
			'reAuth'          : 'To re-authenticate', // from v2.1.10 added 3.25.2016
			'nowLoading'      : 'Now loading...', // from v2.1.12 added 4.26.2016
			'openMulti'       : 'බහු ගොනු විවෘත කරන්න', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': 'ඔබ $1 ගොනු විවෘත කිරීමට උත්සාහ කරයි. බ්‍රව්සරයෙන් ඔබට විවෘත කිරීමට අවශ්‍ය බව ඔබට විශ්වාසද?', // from v2.1.12 added 5.14.2016
			'emptySearch'     : 'සෙවුම් ඉලක්කයේ ගවේෂණ ප්‍රතිඵල නොමැත.', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'එය ගොනුව සංස්කරණය කිරීමකි.', // from v2.1.13 added 6.3.2016
			'hasSelected'     : 'ඔබ අයිතම $1 ප්‍රමාණයක් තෝරාගෙන ඇත.', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : 'You have $1 items in the clipboard.', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : 'Incremental search is only from the current view.', // from v2.1.13 added 6.30.2016
			'reinstate'       : 'යථා තත්ත්වයට පත් කරන්න', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 සම්පූර්ණයි', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'Context menu', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'Page turning', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'Volume roots', // from v2.1.16 added 16.9.2016
			'reset'           : 'යළි පිහිටුවන්න(Reset)', // from v2.1.16 added 1.10.2016
			'bgcolor'         : 'පසුබිම් වර්ණය', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'Color picker', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : 'පික්සල් 8ක දැල', // from v2.1.16 added 4.10.2016
			'enabled'         : 'සක්‍රීයයි', // from v2.1.16 added 4.10.2016
			'disabled'        : 'අක්‍රීයයි', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : 'වර්තමාන දර්ශනය තුළ සෙවුම් ප්‍රතිපල හිස්ව ඇත. \\A සෙවුම් ඉලක්කය පුළුල් කිරීම සඳහා [Enter] යතුර ඔබන්න.', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : 'වර්තමාන දර්ශනයේ පළමු අකුර සෙවුම් ප්‍රතිපල හිස්ව පවතී.', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'ලේබල්වල නම්', // from v2.1.17 added 13.10.2016
			'minsLeft'        : 'විනාඩි $1 ක් ගතවේ', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : 'Reopen with selected encoding', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : 'Save with the selected encoding', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'ෆෝල්ඩරය තෝරන්න', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': 'පළමු අකුරෙන් සෙවීම', // from v2.1.23 added 24.3.2017
			'presets'         : 'Presets', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'It\'s too many items so it can\'t into trash.', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'TextArea', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'Empty the folder "$1".', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'There are no items in a folder "$1".', // from v2.1.25 added 22.6.2017
			'preference'      : 'Preference', // from v2.1.26 added 28.6.2017
			'language'        : 'Language setting', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'Initialize the settings saved in this browser', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'Toolbar setting', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... $1 ක් අකුරු ඉතිරිව පවතී',  // from v2.1.29 added 30.8.2017
			'sum'             : 'එකතුව', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : 'Rough file size', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'Focus on the element of dialog with mouseover',  // from v2.1.30 added 2.11.2017
			'select'          : 'තෝරන්න', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'ගොනුවක් තේරූ විට සිදුකල යුතු දේ', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : 'Open with the editor used last time', // from v2.1.30 added 23.11.2017
			'selectinvert'    : 'ප්‍රතිවිරුද්ධ අාකාරයට තෝරන්න', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : 'Are you sure you want to rename $1 selected items like $2?<br/>This cannot be undone!', // from v2.1.31 added 4.12.2017
			'batchRename'     : 'Batch rename', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ Number', // from v2.1.31 added 8.12.2017
			'asPrefix'        : 'Add prefix', // from v2.1.31 added 8.12.2017
			'asSuffix'        : 'Add suffix', // from v2.1.31 added 8.12.2017
			'changeExtention' : 'Change extention', // from v2.1.31 added 8.12.2017
			'columnPref'      : 'Columns settings (List view)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : 'All changes will reflect immediately to the archive.', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'Any changes will not reflect until un-mount this volume.', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'The following volume(s) mounted on this volume also unmounted. Are you sure to unmount it?', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : 'තෝරාගැනීම්වල තොරතුරු', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'Algorithms to show the file hash', // from v2.1.33 added 10.3.2018

			/********************************** mimetypes **********************************/
			'kindUnknown'     : 'නොදන්නා',
			'kindRoot'        : 'Volume Root', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'ෆෝල්ඩරය',
			'kindSelects'     : 'තේරීම්', // from v2.1.29 added 29.8.2017
			'kindAlias'       : 'Alias',
			'kindAliasBroken' : 'Broken alias',
			// applications
			'kindApp'         : 'Application',
			'kindPostscript'  : 'Postscript ලේඛනය',
			'kindMsOffice'    : 'Microsoft Office ලේඛනය',
			'kindMsWord'      : 'Microsoft Word ලේඛනය',
			'kindMsExcel'     : 'Microsoft Excel ලේඛනය',
			'kindMsPP'        : 'Microsoft Powerpoint presentation',
			'kindOO'          : 'Open Office ලේඛනය',
			'kindAppFlash'    : 'Flash application',
			'kindPDF'         : 'Portable Document Format (PDF)',
			'kindTorrent'     : 'Bittorrent file',
			'kind7z'          : '7z archive',
			'kindTAR'         : 'TAR archive',
			'kindGZIP'        : 'GZIP archive',
			'kindBZIP'        : 'BZIP archive',
			'kindXZ'          : 'XZ archive',
			'kindZIP'         : 'ZIP archive',
			'kindRAR'         : 'RAR archive',
			'kindJAR'         : 'Java JAR file',
			'kindTTF'         : 'True Type font',
			'kindOTF'         : 'Open Type font',
			'kindRPM'         : 'RPM package',
			// texts
			'kindText'        : 'Text ලේඛනය',
			'kindTextPlain'   : 'Plain text',
			'kindPHP'         : 'PHP මූලාශ්‍රය',
			'kindCSS'         : 'Cascading style sheet',
			'kindHTML'        : 'HTML ලේඛනය',
			'kindJS'          : 'Javascript මූලාශ්‍රය',
			'kindRTF'         : 'Rich Text Format',
			'kindC'           : 'C මූලාශ්‍රය',
			'kindCHeader'     : 'C header මූලාශ්‍රය',
			'kindCPP'         : 'C++ මූලාශ්‍රය',
			'kindCPPHeader'   : 'C++ header මූලාශ්‍රය',
			'kindShell'       : 'Unix shell රචනයකි',
			'kindPython'      : 'Python මූලාශ්‍රය',
			'kindJava'        : 'Java මූලාශ්‍රය',
			'kindRuby'        : 'Ruby මූලාශ්‍රය',
			'kindPerl'        : 'Perl රචනයකි',
			'kindSQL'         : 'SQL මූලාශ්‍රය',
			'kindXML'         : 'XML ලේඛනය',
			'kindAWK'         : 'AWK මූලාශ්‍රය',
			'kindCSV'         : 'කොමාවන් වෙන් කළ අගයන්',
			'kindDOCBOOK'     : 'Docbook XML ලේඛනය',
			'kindMarkdown'    : 'Markdown text', // added 20.7.2015
			// images
			'kindImage'       : 'පින්තූරය',
			'kindBMP'         : 'BMP පින්තූරය',
			'kindJPEG'        : 'JPEG පින්තූරය',
			'kindGIF'         : 'GIF පින්තූරය',
			'kindPNG'         : 'PNG පින්තූරය',
			'kindTIFF'        : 'TIFF පින්තූරය',
			'kindTGA'         : 'TGA පින්තූරය',
			'kindPSD'         : 'Adobe Photoshop පින්තූරය',
			'kindXBITMAP'     : 'X bitmap පින්තූරය',
			'kindPXM'         : 'Pixelmator පින්තූරය',
			// media
			'kindAudio'       : 'ශබ්ධ මාධ්‍ය',
			'kindAudioMPEG'   : 'MPEG ශබ්ධපටය',
			'kindAudioMPEG4'  : 'MPEG-4 ශබ්ධපටය',
			'kindAudioMIDI'   : 'MIDI ශබ්ධපටය',
			'kindAudioOGG'    : 'Ogg Vorbis ශබ්ධපටය',
			'kindAudioWAV'    : 'WAV ශබ්ධපටය',
			'AudioPlaylist'   : 'MP3 playlist',
			'kindVideo'       : 'Video මාධ්‍ය',
			'kindVideoDV'     : 'DV චිත්‍රපටය',
			'kindVideoMPEG'   : 'MPEG චිත්‍රපටය',
			'kindVideoMPEG4'  : 'MPEG-4 චිත්‍රපටය',
			'kindVideoAVI'    : 'AVI චිත්‍රපටය',
			'kindVideoMOV'    : 'Quick Time චිත්‍රපටය',
			'kindVideoWM'     : 'Windows Media චිත්‍රපටය',
			'kindVideoFlash'  : 'Flash චිත්‍රපටය',
			'kindVideoMKV'    : 'Matroska චිත්‍රපටය',
			'kindVideoOGG'    : 'Ogg චිත්‍රපටය'
		}
	};
}));

