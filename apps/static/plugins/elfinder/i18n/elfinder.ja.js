/**
 * Japanese translation
 * @author Tomoaki Yoshida <info@yoshida-studio.jp>
 * @author Naoki Sawada <hypweb+elfinder@gmail.com>
 * @version 2019-07-27
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
	elFinder.prototype.i18.ja = {
		translator : 'Tomoaki Yoshida &lt;info@yoshida-studio.jp&gt;, Naoki Sawada &lt;hypweb+elfinder@gmail.com&gt;',
		language   : 'Japanese',
		direction  : 'ltr',
		dateFormat : 'Y/m/d h:i A', // will show like: 2018/08/24 04:37 PM
		fancyDateFormat : '$1 h:i A', // will show like: 今日 04:37 PM
		nonameDateFormat : 'ymd-His', // noname upload will show like: 180824-163717
		messages   : {

			/********************************** errors **********************************/
			'error'                : 'エラー',
			'errUnknown'           : '不明なエラーです。',
			'errUnknownCmd'        : '不明なコマンドです。',
			'errJqui'              : '無効な jQuery UI 設定です。Selectable, Draggable, Droppable コンポーネントを含める必要があります。',
			'errNode'              : 'elFinder は DOM Element が必要です。',
			'errURL'               : '無効な elFinder 設定です！ URLを設定されていません。',
			'errAccess'            : 'アクセスが拒否されました。',
			'errConnect'           : 'バックエンドとの接続ができません。',
			'errAbort'             : '接続が中断されました。',
			'errTimeout'           : '接続がタイムアウトしました。',
			'errNotFound'          : 'バックエンドが見つかりません。',
			'errResponse'          : '無効なバックエンドレスポンスです。',
			'errConf'              : 'バックエンドの設定が有効ではありません。',
			'errJSON'              : 'PHP JSON モジュールがインストールされていません。',
			'errNoVolumes'         : '読み込み可能なボリュームがありません。',
			'errCmdParams'         : 'コマンド "$1"のパラメーターが無効です。',
			'errDataNotJSON'       : 'JSONデータではありません。',
			'errDataEmpty'         : '空のデータです。',
			'errCmdReq'            : 'バックエンドリクエストはコマンド名が必要です。',
			'errOpen'              : '"$1" を開くことができません。',
			'errNotFolder'         : 'オブジェクトがフォルダではありません。',
			'errNotFile'           : 'オブジェクトがファイルではありません。',
			'errRead'              : '"$1" を読み込むことができません。',
			'errWrite'             : '"$1" に書き込むことができません。',
			'errPerm'              : '権限がありません。',
			'errLocked'            : '"$1" はロックされているので名前の変更、移動、削除ができません。',
			'errExists'            : '"$1" というアイテム名はすでに存在しています。',
			'errInvName'           : '無効なファイル名です。',
			'errInvDirname'        : '無効なフォルダ名です。',  // from v2.1.24 added 12.4.2017
			'errFolderNotFound'    : 'フォルダが見つかりません。',
			'errFileNotFound'      : 'ファイルが見つかりません。',
			'errTrgFolderNotFound' : 'ターゲットとするフォルダ "$1" が見つかりません。',
			'errPopup'             : 'ポップアップウィンドウが開けません。ファイルを開くにはブラウザの設定を変更してください。',
			'errMkdir'             : 'フォルダ "$1" を作成することができません。',
			'errMkfile'            : 'ファイル "$1" を作成することができません。',
			'errRename'            : '"$1" の名前を変更することができません。',
			'errCopyFrom'          : '"$1" からのファイルコピーは許可されていません。',
			'errCopyTo'            : '"$1" へのファイルコピーは許可されていません。',
			'errMkOutLink'         : 'ボリュームルート外へのリンクを作成することはできません。', // from v2.1 added 03.10.2015
			'errUpload'            : 'アップロードエラー',  // old name - errUploadCommon
			'errUploadFile'        : '"$1" をアップロードすることができません。', // old name - errUpload
			'errUploadNoFiles'     : 'アップロードされたファイルはありません。',
			'errUploadTotalSize'   : 'データが許容サイズを超えています。', // old name - errMaxSize
			'errUploadFileSize'    : 'ファイルが許容サイズを超えています。', //  old name - errFileMaxSize
			'errUploadMime'        : '許可されていないファイル形式です。',
			'errUploadTransfer'    : '"$1" 転送エラーです。',
			'errUploadTemp'        : 'アップロード用一時ファイルを作成できません。', // from v2.1 added 26.09.2015
			'errNotReplace'        : 'アイテム "$1" はすでにこの場所にあり、アイテムのタイプが違うので置き換えることはできません。', // new
			'errReplace'           : '"$1" を置き換えることができません。',
			'errSave'              : '"$1" を保存することができません。',
			'errCopy'              : '"$1" をコピーすることができません。',
			'errMove'              : '"$1" を移動することができません。',
			'errCopyInItself'      : '"$1" をそれ自身の中にコピーすることはできません。',
			'errRm'                : '"$1" を削除することができません。',
			'errTrash'             : 'ごみ箱に入れることができません。', // from v2.1.24 added 30.4.2017
			'errRmSrc'             : '元ファイルを削除することができません。',
			'errExtract'           : '"$1" を解凍することができません。',
			'errArchive'           : 'アーカイブを作成することができません。',
			'errArcType'           : 'サポート外のアーカイブ形式です。',
			'errNoArchive'         : 'アーカイブでないかサポートされていないアーカイブ形式です。',
			'errCmdNoSupport'      : 'サポートされていないコマンドです。',
			'errReplByChild'       : 'フォルダ "$1" に含まれてるアイテムを置き換えることはできません。',
			'errArcSymlinks'       : 'シンボリックリンクまたは許容されないファイル名を含むアーカイブはセキュリティ上、解凍できません。', // edited 24.06.2012
			'errArcMaxSize'        : 'アーカイブが許容されたサイズを超えています。',
			'errResize'            : '"$1" のリサイズまたは回転ができません。',
			'errResizeDegree'      : 'イメージの回転角度が不正です。',  // added 7.3.2013
			'errResizeRotate'      : 'イメージを回転できません。',  // added 7.3.2013
			'errResizeSize'        : '指定されたイメージサイズが不正です。',  // added 7.3.2013
			'errResizeNoChange'    : 'イメージサイズなどの変更点がありません。',  // added 7.3.2013
			'errUsupportType'      : 'このファイルタイプはサポートされていません。',
			'errNotUTF8Content'    : 'ファイル "$1" には UTF-8 以外の文字が含まれているので編集できません。',  // added 9.11.2011
			'errNetMount'          : '"$1" をマウントできません。', // added 17.04.2012
			'errNetMountNoDriver'  : 'サポートされていないプロトコルです。',     // added 17.04.2012
			'errNetMountFailed'    : 'マウントに失敗しました。',         // added 17.04.2012
			'errNetMountHostReq'   : 'ホスト名は必須です。', // added 18.04.2012
			'errSessionExpires'    : 'アクションがなかったため、セッションが期限切れになりました。',
			'errCreatingTempDir'   : '一時ディレクトリを作成できません："$1"',
			'errFtpDownloadFile'   : 'FTP からファイルをダウンロードできません："$1"',
			'errFtpUploadFile'     : 'FTP へファイルをアップロードできません："$1"',
			'errFtpMkdir'          : 'FTP にリモートディレクトリを作成できません："$1"',
			'errArchiveExec'       : 'ファイルのアーカイブ中にエラーが発生しました："$1"',
			'errExtractExec'       : 'ファイルの抽出中にエラーが発生しました："$1"',
			'errNetUnMount'        : 'アンマウントできません。', // from v2.1 added 30.04.2012
			'errConvUTF8'          : 'UTF-8 に変換できませんでした。', // from v2.1 added 08.04.2014
			'errFolderUpload'      : 'フォルダをアップロードしたいのであれば、モダンブラウザを試してください。', // from v2.1 added 26.6.2015
			'errSearchTimeout'     : '"$1" を検索中にタイムアウトしました。検索結果は部分的です。', // from v2.1 added 12.1.2016
			'errReauthRequire'     : '再認可が必要です。', // from v2.1.10 added 24.3.2016
			'errMaxTargets'        : '選択可能な最大アイテム数は $1 個です。', // from v2.1.17 added 17.10.2016
			'errRestore'           : '宛先の特定ができないため、ごみ箱から戻せません。', // from v2.1.24 added 3.5.2017
			'errEditorNotFound'    : 'このファイルタイプのエディターがありません。', // from v2.1.25 added 23.5.2017
			'errServerError'       : 'サーバー側でエラーが発生しました。', // from v2.1.25 added 16.6.2017
			'errEmpty'             : 'フォルダ"$1"を空にすることができません。', // from v2.1.25 added 22.6.2017
			'moreErrors'           : 'さらに $1 件のエラーがあります。', // from v2.1.44 added 9.12.2018

			/******************************* commands names ********************************/
			'cmdarchive'   : 'アーカイブ作成',
			'cmdback'      : '戻る',
			'cmdcopy'      : 'コピー',
			'cmdcut'       : 'カット',
			'cmddownload'  : 'ダウンロード',
			'cmdduplicate' : '複製',
			'cmdedit'      : 'ファイル編集',
			'cmdextract'   : 'アーカイブを解凍',
			'cmdforward'   : '進む',
			'cmdgetfile'   : 'ファイル選択',
			'cmdhelp'      : 'このソフトウェアについて',
			'cmdhome'      : 'ルート',
			'cmdinfo'      : '情報',
			'cmdmkdir'     : '新規フォルダ',
			'cmdmkdirin'   : '新規フォルダへ', // from v2.1.7 added 19.2.2016
			'cmdmkfile'    : '新規ファイル',
			'cmdopen'      : '開く',
			'cmdpaste'     : 'ペースト',
			'cmdquicklook' : 'プレビュー',
			'cmdreload'    : 'リロード',
			'cmdrename'    : 'リネーム',
			'cmdrm'        : '削除',
			'cmdtrash'     : 'ごみ箱へ', //from v2.1.24 added 29.4.2017
			'cmdrestore'   : '復元', //from v2.1.24 added 3.5.2017
			'cmdsearch'    : 'ファイルを探す',
			'cmdup'        : '親フォルダへ移動',
			'cmdupload'    : 'ファイルアップロード',
			'cmdview'      : 'ビュー',
			'cmdresize'    : 'リサイズと回転',
			'cmdsort'      : 'ソート',
			'cmdnetmount'  : 'ネットワークボリュームをマウント', // added 18.04.2012
			'cmdnetunmount': 'アンマウント', // from v2.1 added 30.04.2012
			'cmdplaces'    : 'よく使う項目へ', // added 28.12.2014
			'cmdchmod'     : '属性変更', // from v2.1 added 20.6.2015
			'cmdopendir'   : 'フォルダを開く', // from v2.1 added 13.1.2016
			'cmdcolwidth'  : '列幅リセット', // from v2.1.13 added 12.06.2016
			'cmdfullscreen': 'フルスクリーン', // from v2.1.15 added 03.08.2016
			'cmdmove'      : '移動', // from v2.1.15 added 21.08.2016
			'cmdempty'     : 'フォルダを空に', // from v2.1.25 added 22.06.2017
			'cmdundo'      : '元に戻す', // from v2.1.27 added 31.07.2017
			'cmdredo'      : 'やり直し', // from v2.1.27 added 31.07.2017
			'cmdpreference': '個人設定', // from v2.1.27 added 03.08.2017
			'cmdselectall' : 'すべて選択', // from v2.1.28 added 15.08.2017
			'cmdselectnone': '選択解除', // from v2.1.28 added 15.08.2017
			'cmdselectinvert': '選択を反転', // from v2.1.28 added 15.08.2017
			'cmdopennew'   : '新しいウィンドウで開く', // from v2.1.38 added 3.4.2018
			'cmdhide'      : '非表示 (個人設定)', // from v2.1.41 added 24.7.2018

			/*********************************** buttons ***********************************/
			'btnClose'  : '閉じる',
			'btnSave'   : '保存',
			'btnRm'     : '削除',
			'btnApply'  : '適用',
			'btnCancel' : 'キャンセル',
			'btnNo'     : 'いいえ',
			'btnYes'    : 'はい',
			'btnMount'  : 'マウント',  // added 18.04.2012
			'btnApprove': '$1へ行き認可する', // from v2.1 added 26.04.2012
			'btnUnmount': 'アンマウント', // from v2.1 added 30.04.2012
			'btnConv'   : '変換', // from v2.1 added 08.04.2014
			'btnCwd'    : 'この場所',      // from v2.1 added 22.5.2015
			'btnVolume' : 'ボリューム',    // from v2.1 added 22.5.2015
			'btnAll'    : '全て',       // from v2.1 added 22.5.2015
			'btnMime'   : 'MIMEタイプ', // from v2.1 added 22.5.2015
			'btnFileName':'ファイル名',  // from v2.1 added 22.5.2015
			'btnSaveClose': '保存して閉じる', // from v2.1 added 12.6.2015
			'btnBackup' : 'バックアップ', // fromv2.1 added 28.11.2015
			'btnRename'    : 'リネーム',      // from v2.1.24 added 6.4.2017
			'btnRenameAll' : 'リネーム(全て)', // from v2.1.24 added 6.4.2017
			'btnPrevious' : '前へ ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnNext'     : '次へ ($1/$2)', // from v2.1.24 added 11.5.2017
			'btnSaveAs'   : '別名保存', // from v2.1.25 added 24.5.2017

			/******************************** notifications ********************************/
			'ntfopen'     : 'フォルダを開いています',
			'ntffile'     : 'ファイルを開いています',
			'ntfreload'   : 'フォルダを再読込しています',
			'ntfmkdir'    : 'フォルダを作成しています',
			'ntfmkfile'   : 'ファイルを作成しています',
			'ntfrm'       : 'アイテムを削除しています',
			'ntfcopy'     : 'アイテムをコピーしています',
			'ntfmove'     : 'アイテムを移動しています',
			'ntfprepare'  : '既存アイテムを確認しています',
			'ntfrename'   : 'ファイル名を変更しています',
			'ntfupload'   : 'ファイルをアップロードしています',
			'ntfdownload' : 'ファイルをダウンロードしています',
			'ntfsave'     : 'ファイルを保存しています',
			'ntfarchive'  : 'アーカイブ作成しています',
			'ntfextract'  : 'アーカイブを解凍しています',
			'ntfsearch'   : 'ファイル検索中',
			'ntfresize'   : 'リサイズしています',
			'ntfsmth'     : '処理をしています',
			'ntfloadimg'  : 'イメージを読み込んでいます',
			'ntfnetmount' : 'ネットボリュームをマウント中', // added 18.04.2012
			'ntfnetunmount': 'ネットボリュームをアンマウント中', // from v2.1 added 30.04.2012
			'ntfdim'      : '画像サイズを取得しています', // added 20.05.2013
			'ntfreaddir'  : 'フォルダ情報を読み取っています', // from v2.1 added 01.07.2013
			'ntfurl'      : 'リンクURLを取得しています', // from v2.1 added 11.03.2014
			'ntfchmod'    : 'ファイル属性を変更しています', // from v2.1 added 20.6.2015
			'ntfpreupload': 'アップロードファイル名を検証中', // from v2.1 added 31.11.2015
			'ntfzipdl'    : 'ダウンロード用ファイルを作成中', // from v2.1.7 added 23.1.2016
			'ntfparents'  : 'パス情報を取得しています', // from v2.1.17 added 2.11.2016
			'ntfchunkmerge': 'アップロード済みファイルを処理中', // from v2.1.17 added 2.11.2016
			'ntftrash'    : 'ごみ箱に入れています', // from v2.1.24 added 2.5.2017
			'ntfrestore'  : 'ごみ箱から元に戻しています', // from v2.1.24 added 3.5.2017
			'ntfchkdir'   : '宛先フォルダを確認しています', // from v2.1.24 added 3.5.2017
			'ntfundo'     : '前の操作を取り消して元に戻しています', // from v2.1.27 added 31.07.2017
			'ntfredo'     : '元に戻した操作をやり直しています', // from v2.1.27 added 31.07.2017
			'ntfchkcontent' : 'コンテンツをチェックしています', // from v2.1.41 added 3.8.2018

			/*********************************** volumes *********************************/
			'volume_Trash' : 'ごみ箱', //from v2.1.24 added 29.4.2017

			/************************************ dates **********************************/
			'dateUnknown' : '不明',
			'Today'       : '今日',
			'Yesterday'   : '昨日',
			'msJan'       : '1月',
			'msFeb'       : '2月',
			'msMar'       : '3月',
			'msApr'       : '4月',
			'msMay'       : '5月',
			'msJun'       : '6月',
			'msJul'       : '7月',
			'msAug'       : '8月',
			'msSep'       : '9月',
			'msOct'       : '10月',
			'msNov'       : '11月',
			'msDec'       : '12月',
			'January'     : '1月',
			'February'    : '2月',
			'March'       : '3月',
			'April'       : '4月',
			'May'         : '5月',
			'June'        : '6月',
			'July'        : '7月',
			'August'      : '8月',
			'September'   : '9月',
			'October'     : '10月',
			'November'    : '11月',
			'December'    : '12月',
			'Sunday'      : '日曜日',
			'Monday'      : '月曜日',
			'Tuesday'     : '火曜日',
			'Wednesday'   : '水曜日',
			'Thursday'    : '木曜日',
			'Friday'      : '金曜日',
			'Saturday'    : '土曜日',
			'Sun'         : '(日)',
			'Mon'         : '(月)',
			'Tue'         : '(火)',
			'Wed'         : '(水)',
			'Thu'         : '(木)',
			'Fri'         : '(金)',
			'Sat'         : '(土)',

			/******************************** sort variants ********************************/
			'sortname'          : '名前順',
			'sortkind'          : '種類順',
			'sortsize'          : 'サイズ順',
			'sortdate'          : '日付順',
			'sortFoldersFirst'  : 'フォルダ優先',
			'sortperm'          : '権限順', // from v2.1.13 added 13.06.2016
			'sortmode'          : '属性順',       // from v2.1.13 added 13.06.2016
			'sortowner'         : 'オーナー順',      // from v2.1.13 added 13.06.2016
			'sortgroup'         : 'グループ順',      // from v2.1.13 added 13.06.2016
			'sortAlsoTreeview'  : 'ツリービューも',  // from v2.1.15 added 01.08.2016

			/********************************** new items **********************************/
			'untitled file.txt' : '新規ファイル.txt', // added 10.11.2015
			'untitled folder'   : '新規フォルダ',   // added 10.11.2015
			'Archive'           : '新規アーカイブ',  // from v2.1 added 10.11.2015
			'untitled file'     : '新規ファイル.$1',  // from v2.1.41 added 6.8.2018
			'extentionfile'     : '$1: ファイル',     // from v2.1.41 added 6.8.2018
			'extentiontype'     : '$1: $2',      // from v2.1.43 added 17.10.2018

			/********************************** messages **********************************/
			'confirmReq'      : '処理を実行しますか？',
			'confirmRm'       : 'アイテムを完全に削除してもよろしいですか？<br/>この操作は取り消しできません！',
			'confirmRepl'     : '古いファイルを新しいファイルで上書きしますか？ (フォルダが含まれている場合は統合されます。置き換える場合は「バックアップ」選択してください。)',
			'confirmRest'     : '既存のアイテムをごみ箱のアイテムで上書きしますか？', // fromv2.1.24 added 5.5.2017
			'confirmConvUTF8' : 'UTF-8 以外の文字が含まれています。<br/>UTF-8  に変換しますか？<br/>変換後の保存でコンテンツは UTF-8 になります。', // from v2.1 added 08.04.2014
			'confirmNonUTF8'  : 'このファイルの文字エンコーディングを判別できませんでした。編集するには一時的に UTF-8 に変換する必要があります。<br/>文字エンコーディングを指定してください。', // from v2.1.19 added 28.11.2016
			'confirmNotSave'  : '変更されています。<br/>保存せずに閉じると編集内容が失われます。', // from v2.1 added 15.7.2015
			'confirmTrash'    : 'アイテムをごみ箱に移動してもよろしいですか？', //from v2.1.24 added 29.4.2017
			'confirmMove'     : 'アイテムを"$1"に移動してもよろしいですか？', //from v2.1.50 added 27.7.2019
			'apllyAll'        : '全てに適用します',
			'name'            : '名前',
			'size'            : 'サイズ',
			'perms'           : '権限',
			'modify'          : '更新',
			'kind'            : '種類',
			'read'            : '読み取り',
			'write'           : '書き込み',
			'noaccess'        : 'アクセス禁止',
			'and'             : ',',
			'unknown'         : '不明',
			'selectall'       : 'すべてのアイテムを選択',
			'selectfiles'     : 'アイテム選択',
			'selectffile'     : '最初のアイテムを選択',
			'selectlfile'     : '最後のアイテムを選択',
			'viewlist'        : 'リスト形式で表示',
			'viewicons'       : 'アイコン形式で表示',
			'viewSmall'       : '小アイコン', // from v2.1.39 added 22.5.2018
			'viewMedium'      : '中アイコン', // from v2.1.39 added 22.5.2018
			'viewLarge'       : '大アイコン', // from v2.1.39 added 22.5.2018
			'viewExtraLarge'  : '特大アイコン', // from v2.1.39 added 22.5.2018
			'places'          : 'よく使う項目',
			'calc'            : '計算中',
			'path'            : 'パス',
			'aliasfor'        : 'エイリアス',
			'locked'          : 'ロック',
			'dim'             : '画素数',
			'files'           : 'ファイル',
			'folders'         : 'フォルダ',
			'items'           : 'アイテム',
			'yes'             : 'はい',
			'no'              : 'いいえ',
			'link'            : 'リンク',
			'searcresult'     : '検索結果',
			'selected'        : '選択されたアイテム',
			'about'           : '概要',
			'shortcuts'       : 'ショートカット',
			'help'            : 'ヘルプ',
			'webfm'           : 'ウェブファイルマネージャー',
			'ver'             : 'バージョン',
			'protocolver'     : 'プロトコルバージョン',
			'homepage'        : 'プロジェクトホーム',
			'docs'            : 'ドキュメンテーション',
			'github'          : 'Github でフォーク',
			'twitter'         : 'Twitter でフォロー',
			'facebook'        : 'Facebookグループ に参加',
			'team'            : 'チーム',
			'chiefdev'        : 'チーフデベロッパー',
			'developer'       : 'デベロッパー',
			'contributor'     : 'コントリビュータ',
			'maintainer'      : 'メインテナー',
			'translator'      : '翻訳者',
			'icons'           : 'アイコン',
			'dontforget'      : 'タオル忘れちゃだめよ～',
			'shortcutsof'     : 'ショートカットは利用できません',
			'dropFiles'       : 'ここにファイルをドロップ',
			'or'              : 'または',
			'selectForUpload' : 'ファイルを選択',
			'moveFiles'       : 'アイテムを移動',
			'copyFiles'       : 'アイテムをコピー',
			'restoreFiles'    : 'アイテムを元に戻す', // from v2.1.24 added 5.5.2017
			'rmFromPlaces'    : 'ここから削除',
			'aspectRatio'     : '縦横比維持',
			'scale'           : '表示縮尺',
			'width'           : '幅',
			'height'          : '高さ',
			'resize'          : 'リサイズ',
			'crop'            : '切り抜き',
			'rotate'          : '回転',
			'rotate-cw'       : '90度左回転',
			'rotate-ccw'      : '90度右回転',
			'degree'          : '度',
			'netMountDialogTitle' : 'ネットワークボリュームのマウント', // added 18.04.2012
			'protocol'            : 'プロトコル', // added 18.04.2012
			'host'                : 'ホスト名', // added 18.04.2012
			'port'                : 'ポート', // added 18.04.2012
			'user'                : 'ユーザー名', // added 18.04.2012
			'pass'                : 'パスワード', // added 18.04.2012
			'confirmUnmount'      : '$1をアンマウントしますか?',  // from v2.1 added 30.04.2012
			'dropFilesBrowser': 'ブラウザからファイルをドロップまたは貼り付け', // from v2.1 added 30.05.2012
			'dropPasteFiles'  : 'ここにファイルをドロップ または URLリスト, 画像(クリップボード) を貼り付け', // from v2.1 added 07.04.2014
			'encoding'        : 'エンコーディング', // from v2.1 added 19.12.2014
			'locale'          : 'ロケール',   // from v2.1 added 19.12.2014
			'searchTarget'    : '検索範囲: $1',                // from v2.1 added 22.5.2015
			'searchMime'      : '指定した MIME タイプで検索', // from v2.1 added 22.5.2015
			'owner'           : 'オーナー', // from v2.1 added 20.6.2015
			'group'           : 'グループ', // from v2.1 added 20.6.2015
			'other'           : 'その他', // from v2.1 added 20.6.2015
			'execute'         : '実行', // from v2.1 added 20.6.2015
			'perm'            : 'パーミッション', // from v2.1 added 20.6.2015
			'mode'            : '属性', // from v2.1 added 20.6.2015
			'emptyFolder'     : '空のフォルダ', // from v2.1.6 added 30.12.2015
			'emptyFolderDrop' : '空のフォルダ\\Aアイテムを追加するにはここへドロップ', // from v2.1.6 added 30.12.2015
			'emptyFolderLTap' : '空のフォルダ\\Aアイテムを追加するにはここをロングタップ', // from v2.1.6 added 30.12.2015
			'quality'         : '品質', // from v2.1.6 added 5.1.2016
			'autoSync'        : '自動更新',  // from v2.1.6 added 10.1.2016
			'moveUp'          : '上へ移動',  // from v2.1.6 added 18.1.2016
			'getLink'         : 'リンクURLを取得', // from v2.1.7 added 9.2.2016
			'selectedItems'   : '選択アイテム ($1)', // from v2.1.7 added 2.19.2016
			'folderId'        : 'フォルダID', // from v2.1.10 added 3.25.2016
			'offlineAccess'   : 'オフライン アクセスを可能にする', // from v2.1.10 added 3.25.2016
			'reAuth'          : '再認証する', // from v2.1.10 added 3.25.2016
			'nowLoading'      : '読み込んでいます...', // from v2.1.12 added 4.26.2016
			'openMulti'       : '複数ファイルオープン', // from v2.1.12 added 5.14.2016
			'openMultiConfirm': '$1 個のファイルを開こうとしています。このままブラウザで開きますか？', // from v2.1.12 added 5.14.2016
			'emptySearch'     : '検索対象に該当するアイテムはありません。', // from v2.1.12 added 5.16.2016
			'editingFile'     : 'ファイルを編集中です。', // from v2.1.13 added 6.3.2016
			'hasSelected'     : '$1 個のアイテムを選択中です。', // from v2.1.13 added 6.3.2016
			'hasClipboard'    : '$1 個のアイテムがクリップボードに入っています。', // from v2.1.13 added 6.3.2016
			'incSearchOnly'   : '逐次検索対象は現在のビューのみです。', // from v2.1.13 added 6.30.2016
			'reinstate'       : '元に戻す', // from v2.1.15 added 3.8.2016
			'complete'        : '$1 完了', // from v2.1.15 added 21.8.2016
			'contextmenu'     : 'コンテキストメニュー', // from v2.1.15 added 9.9.2016
			'pageTurning'     : 'ページめくり', // from v2.1.15 added 10.9.2016
			'volumeRoots'     : 'ボリュームルート', // from v2.1.16 added 16.9.2016
			'reset'           : 'リセット', // from v2.1.16 added 1.10.2016
			'bgcolor'         : '背景色', // from v2.1.16 added 1.10.2016
			'colorPicker'     : 'カラーピッカー', // from v2.1.16 added 1.10.2016
			'8pxgrid'         : '8pxグリッド', // from v2.1.16 added 4.10.2016
			'enabled'         : '有効', // from v2.1.16 added 4.10.2016
			'disabled'        : '無効', // from v2.1.16 added 4.10.2016
			'emptyIncSearch'  : '現在のビュー内に該当するアイテムはありません。\\A[Enter]キーで検索対象を拡げます。', // from v2.1.16 added 5.10.2016
			'emptyLetSearch'  : '現在のビュー内に指定された文字で始まるアイテムはありません。', // from v2.1.23 added 24.3.2017
			'textLabel'       : 'テキストラベル', // from v2.1.17 added 13.10.2016
			'minsLeft'        : '残り$1分', // from v2.1.17 added 13.11.2016
			'openAsEncoding'  : '選択したエンコーディングで開き直す', // from v2.1.19 added 2.12.2016
			'saveAsEncoding'  : '選択したエンコーディングで保存', // from v2.1.19 added 2.12.2016
			'selectFolder'    : 'フォルダを選択', // from v2.1.20 added 13.12.2016
			'firstLetterSearch': '一文字目で検索', // from v2.1.23 added 24.3.2017
			'presets'         : 'プリセット', // from v2.1.25 added 26.5.2017
			'tooManyToTrash'  : 'アイテム数が多すぎるのでごみ箱に入れられません。', // from v2.1.25 added 9.6.2017
			'TextArea'        : 'テキストエリア', // from v2.1.25 added 14.6.2017
			'folderToEmpty'   : 'フォルダ"$1"を空にします。', // from v2.1.25 added 22.6.2017
			'filderIsEmpty'   : 'フォルダ"$1"にアイテムはありません。', // from v2.1.25 added 22.6.2017
			'preference'      : '個人設定', // from v2.1.26 added 28.6.2017
			'language'        : '言語', // from v2.1.26 added 28.6.2017
			'clearBrowserData': 'ブラウザに保存された設定を初期化する', // from v2.1.26 added 28.6.2017
			'toolbarPref'     : 'ツールバー設定', // from v2.1.27 added 2.8.2017
			'charsLeft'       : '... 残り $1 文字',  // from v2.1.29 added 30.8.2017
			'sum'             : '合計', // from v2.1.29 added 28.9.2017
			'roughFileSize'   : '大まかなファイルサイズ', // from v2.1.30 added 2.11.2017
			'autoFocusDialog' : 'マウスオーバーでダイアログの要素にフォーカスする',  // from v2.1.30 added 2.11.2017
			'select'          : '選択', // from v2.1.30 added 23.11.2017
			'selectAction'    : 'ファイル選択時の動作', // from v2.1.30 added 23.11.2017
			'useStoredEditor' : '前回使用したエディターで開く', // from v2.1.30 added 23.11.2017
			'selectinvert'    : '選択アイテムを反転', // from v2.1.30 added 25.11.2017
			'renameMultiple'  : '選択した $1 個のアイテムを $2 のようにリネームしますか？<br/>この操作は取り消しできません！', // from v2.1.31 added 4.12.2017
			'batchRename'     : '一括リネーム', // from v2.1.31 added 8.12.2017
			'plusNumber'      : '+ 連番', // from v2.1.31 added 8.12.2017
			'asPrefix'        : '先頭に追加', // from v2.1.31 added 8.12.2017
			'asSuffix'        : '末尾に追加', // from v2.1.31 added 8.12.2017
			'changeExtention' : '拡張子変更', // from v2.1.31 added 8.12.2017
			'columnPref'      : '列項目設定(リストビュー)', // from v2.1.32 added 6.2.2018
			'reflectOnImmediate' : '全ての変更は、直ちにアーカイブに反映されます。', // from v2.1.33 added 2.3.2018
			'reflectOnUnmount'   : 'このボリュームをアンマウントするまで、変更は反映されません。', // from v2.1.33 added 2.3.2018
			'unmountChildren' : 'このボリュームにマウントされている以下のボリュームもアンマウントされます。アンマウントしますか？', // from v2.1.33 added 5.3.2018
			'selectionInfo'   : '選択情報', // from v2.1.33 added 7.3.2018
			'hashChecker'     : 'ファイルハッシュを表示するアルゴリズム', // from v2.1.33 added 10.3.2018
			'infoItems'       : '情報項目 (選択情報パネル)', // from v2.1.38 added 28.3.2018
			'pressAgainToExit': 'もう一度押すと終了します。', // from v2.1.38 added 1.4.2018
			'toolbar'         : 'ツールバー', // from v2.1.38 added 4.4.2018
			'workspace'       : 'ワークスペース', // from v2.1.38 added 4.4.2018
			'dialog'          : 'ダイアログ', // from v2.1.38 added 4.4.2018
			'all'             : 'すべて', // from v2.1.38 added 4.4.2018
			'iconSize'        : 'アイコンサイズ (アイコンビュー)', // from v2.1.39 added 7.5.2018
			'editorMaximized' : 'エディターウィンドウを最大化して開く', // from v2.1.40 added 30.6.2018
			'editorConvNoApi' : '現在 API による変換は利用できないので、Web サイトで変換を行ってください。', //from v2.1.40 added 8.7.2018
			'editorConvNeedUpload' : '変換後に変換されたファイルを保存するには、アイテムの URL またはダウンロードしたファイルをアップロードする必要があります。', //from v2.1.40 added 8.7.2018
			'convertOn'       : '$1 のサイト上で変換する', // from v2.1.40 added 10.7.2018
			'integrations'    : '統合', // from v2.1.40 added 11.7.2018
			'integrationWith' : 'この elFinder は次の外部サービスが統合されています。それらの利用規約、プライバシーポリシーなどをご確認の上、ご利用ください。', // from v2.1.40 added 11.7.2018
			'showHidden'      : '非表示アイテムを表示', // from v2.1.41 added 24.7.2018
			'hideHidden'      : '非表示アイテムを隠す', // from v2.1.41 added 24.7.2018
			'toggleHidden'    : '非表示アイテムの表示/非表示', // from v2.1.41 added 24.7.2018
			'makefileTypes'   : '「新しいファイル」で有効にするファイルタイプ', // from v2.1.41 added 7.8.2018
			'typeOfTextfile'  : 'テキストファイルのタイプ', // from v2.1.41 added 7.8.2018
			'add'             : '追加', // from v2.1.41 added 7.8.2018
			'theme'           : 'テーマ', // from v2.1.43 added 19.10.2018
			'default'         : 'デフォルト', // from v2.1.43 added 19.10.2018
			'description'     : '説明', // from v2.1.43 added 19.10.2018
			'website'         : 'ウェブサイト', // from v2.1.43 added 19.10.2018
			'author'          : '作者', // from v2.1.43 added 19.10.2018
			'email'           : 'Email', // from v2.1.43 added 19.10.2018
			'license'         : 'ライセンス', // from v2.1.43 added 19.10.2018
			'exportToSave'    : 'このアイテムは保存できません。 編集内容を失わないようにするには、PCにエクスポートする必要があります。', // from v2.1.44 added 1.12.2018
			'dblclickToSelect': 'ファイルをダブルクリックして選択します。', // from v2.1.47 added 22.1.2019
			'useFullscreen'   : 'フルスクリーンモードの利用', // from v2.1.47 added 19.2.2019

			/********************************** mimetypes **********************************/
			'kindUnknown'     : '不明',
			'kindRoot'        : 'ボリュームルート', // from v2.1.16 added 16.10.2016
			'kindFolder'      : 'フォルダ',
			'kindSelects'     : '複数選択', // from v2.1.29 added 29.8.2017
			'kindAlias'       : '別名',
			'kindAliasBroken' : '宛先不明の別名',
			// applications
			'kindApp'         : 'アプリケーション',
			'kindPostscript'  : 'Postscript ドキュメント',
			'kindMsOffice'    : 'Microsoft Office ドキュメント',
			'kindMsWord'      : 'Microsoft Word ドキュメント',
			'kindMsExcel'     : 'Microsoft Excel ドキュメント',
			'kindMsPP'        : 'Microsoft Powerpoint プレゼンテーション',
			'kindOO'          : 'Open Office ドキュメント',
			'kindAppFlash'    : 'Flash アプリケーション',
			'kindPDF'         : 'PDF',
			'kindTorrent'     : 'Bittorrent ファイル',
			'kind7z'          : '7z アーカイブ',
			'kindTAR'         : 'TAR アーカイブ',
			'kindGZIP'        : 'GZIP アーカイブ',
			'kindBZIP'        : 'BZIP アーカイブ',
			'kindXZ'          : 'XZ アーカイブ',
			'kindZIP'         : 'ZIP アーカイブ',
			'kindRAR'         : 'RAR アーカイブ',
			'kindJAR'         : 'Java JAR ファイル',
			'kindTTF'         : 'True Type フォント',
			'kindOTF'         : 'Open Type フォント',
			'kindRPM'         : 'RPM パッケージ',
			// texts
			'kindText'        : 'Text ドキュメント',
			'kindTextPlain'   : 'プレインテキスト',
			'kindPHP'         : 'PHP ソース',
			'kindCSS'         : 'スタイルシート',
			'kindHTML'        : 'HTML ドキュメント',
			'kindJS'          : 'Javascript ソース',
			'kindRTF'         : 'Rich Text フォーマット',
			'kindC'           : 'C ソース',
			'kindCHeader'     : 'C ヘッダーソース',
			'kindCPP'         : 'C++ ソース',
			'kindCPPHeader'   : 'C++ ヘッダーソース',
			'kindShell'       : 'Unix shell スクリプト',
			'kindPython'      : 'Python ソース',
			'kindJava'        : 'Java ソース',
			'kindRuby'        : 'Ruby ソース',
			'kindPerl'        : 'Perl スクリプト',
			'kindSQL'         : 'SQL ソース',
			'kindXML'         : 'XML ドキュメント',
			'kindAWK'         : 'AWK ソース',
			'kindCSV'         : 'CSV',
			'kindDOCBOOK'     : 'Docbook XML ドキュメント',
			'kindMarkdown'    : 'Markdown テキスト', // added 20.7.2015
			// images
			'kindImage'       : 'イメージ',
			'kindBMP'         : 'BMP イメージ',
			'kindJPEG'        : 'JPEG イメージ',
			'kindGIF'         : 'GIF イメージ',
			'kindPNG'         : 'PNG イメージ',
			'kindTIFF'        : 'TIFF イメージ',
			'kindTGA'         : 'TGA イメージ',
			'kindPSD'         : 'Adobe Photoshop イメージ',
			'kindXBITMAP'     : 'X bitmap イメージ',
			'kindPXM'         : 'Pixelmator イメージ',
			// media
			'kindAudio'       : 'オーディオメディア',
			'kindAudioMPEG'   : 'MPEG オーディオ',
			'kindAudioMPEG4'  : 'MPEG-4 オーディオ',
			'kindAudioMIDI'   : 'MIDI オーディオ',
			'kindAudioOGG'    : 'Ogg Vorbis オーディオ',
			'kindAudioWAV'    : 'WAV オーディオ',
			'AudioPlaylist'   : 'MP3 プレイリスト',
			'kindVideo'       : 'ビデオメディア',
			'kindVideoDV'     : 'DV ムービー',
			'kindVideoMPEG'   : 'MPEG ムービー',
			'kindVideoMPEG4'  : 'MPEG-4 ムービー',
			'kindVideoAVI'    : 'AVI ムービー',
			'kindVideoMOV'    : 'Quick Time ムービー',
			'kindVideoWM'     : 'Windows Media ムービー',
			'kindVideoFlash'  : 'Flash ムービー',
			'kindVideoMKV'    : 'Matroska ムービー',
			'kindVideoOGG'    : 'Ogg ムービー'
		}
	};
}));

