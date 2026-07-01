
var UKeyError = {
	SAR_OK   				       : 0x00000000, //成功
	SAR_FAIL                       : 0x0A000001, //失败
	SAR_UNKNOWNERR                 : 0x0A000002, //异常错误
	SAR_NOTSUPPORTYETERR           : 0x0A000003, //不支持的服务
	SAR_FILEERR                    : 0x0A000004, //文件操作错误
	SAR_INVALIDHANDLEERR           : 0x0A000005, //无效的句柄
	SAR_INVALIDPARAMERR            : 0x0A000006, //无效的参数
	SAR_READFILEERR                : 0x0A000007, //读文件错误
	SAR_WRITEFILEERR               : 0x0A000008, //写文件错误
	SAR_NAMELENERR                 : 0x0A000009, //名称长度错误
	SAR_KEYUSAGEERR                : 0x0A00000A, //密钥用途错误
	SAR_MODULUSLENERR              : 0x0A00000B, //模的长度错误
	SAR_NOTINITIALIZEERR           : 0x0A00000C, //未初始化
	SAR_OBJERR                     : 0x0A00000D, //对象错误
	SAR_MEMORYERR                  : 0x0A00000E, //内存错误
	SAR_TIMEOUTERR                 : 0x0A00000F, //超时
	SAR_INDATALENERR               : 0x0A000010, //输入数据长度错误
	SAR_INDATAERR                  : 0x0A000011, //输入数据错误
	SAR_GENRANDERR                 : 0x0A000012, //生成随机数错误
	SAR_HASHOBJERR                 : 0x0A000013, //HASH对象错
	SAR_HASHERR                    : 0x0A000014, //HASH运算错误
	SAR_GENRSAKEYERR               : 0x0A000015, //产生RSA密钥错
	SAR_RSAMODULUSLENERR           : 0x0A000016, //RSA密钥模长错误
	SAR_CSPIMPRTPUBKEYERR          : 0x0A000017, //CSP服务导入公钥错误
	SAR_RSAENCERR                  : 0x0A000018, //RSA加密错误
	SAR_RSADECERR                  : 0x0A000019, //RSA解密错误
	SAR_HASHNOTEQUALERR            : 0x0A00001A, //HASH值不相等
	SAR_KEYNOTFOUNTERR             : 0x0A00001B, //密钥未发现
	SAR_CERTNOTFOUNTERR            : 0x0A00001C, //证书未发现
	SAR_NOTEXPORTERR               : 0x0A00001D, //对象未导出
	SAR_DECRYPTPADERR              : 0x0A00001E, //解密时做补丁错误
	SAR_MACLENERR                  : 0x0A00001F, //MAC长度错误
	SAR_BUFFER_TOO_SMALL           : 0x0A000020, //缓冲区不足
	SAR_KEYINFOTYPEERR             : 0x0A000021, //密钥类型错误
	SAR_NOT_EVENTERR               : 0x0A000022, //无事件错误
	SAR_DEVICE_REMOVED             : 0x0A000023, //设备已移除
	SAR_PIN_INCORRECT              : 0x0A000024, //PIN不正确
	SAR_PIN_LOCKED                 : 0x0A000025, //PIN被锁死
	SAR_PIN_INVALID                : 0x0A000026, //PIN无效
	SAR_PIN_LEN_RANGE              : 0x0A000027, //PIN长度错误
	SAR_USER_ALREADY_LOGGED_IN     : 0x0A000028, //用户已经登录
	SAR_USER_PIN_NOT_INITIALIZED   : 0x0A000029, //没有初始化用户口令
	SAR_USER_TYPE_INVALID          : 0x0A00002A, //PIN类型错误
	SAR_APPLICATION_NAME_INVALID   : 0x0A00002B, //应用名称无效
	SAR_APPLICATION_EXISTS         : 0x0A00002C, //应用已经存在
	SAR_USER_NOT_LOGGED_IN         : 0x0A00002D, //用户没有登录
	SAR_APPLICATION_NOT_EXISTS     : 0x0A00002E, //应用不存在
	SAR_FILE_ALREADY_EXIST         : 0x0A00002F, //文件已经存在
	SAR_NO_ROOM                    : 0x0A000030, //空间不足
	SAR_FILE_NOT_EXIST             : 0x0A000031, //文件不存在
	SAR_REACH_MAX_CONTAINER_COUNT  : 0x0A000032, //已达到最大可管理容器数
	SAR_LIBRARYLOADERR		       : 0x0B000001, //动态库加载错误
	SAR_CERTENCODEERR		       : 0x0B000002, //证书编码格式错误
	SAR_CERTINVALIDERR	           : 0x0B000003, //证书无效
	SAR_ENCRYPTDATAERR		       : 0x0B000004, //对称算法的加密数据失败
	SAR_DECRYPTDATAERR		       : 0x0B000005, //对称算法的解密数据失败
	SAR_PASSWORDSAME		       : 0x0B000006, //修改密码与原密码相同
	SAR_ONLYONEKEYERR		   	   : 0x0B000007, //当前功能只能插入一个key
	SAR_NETWORK_ERR		           : 0x0B000008, //网络异常
	SAR_REQUEST_ERR  		       : 0x0B000009, //请求异常
	SAR_JSONFORMAT_ERR		       : 0x0B000010, //Json格式错误
	SAR_USER_CANCEL		      	   : 0x0B000011, //用户取消操作
	SAR_ADMINKEY_SETERR			   : 0x0B000012, //管理员Key设置错误
	}

function UKeyAPI(object) {
	this.object = object;

	this.UKeyError = UKeyError;
	
	var g_UKeyPlugin = null;

	this.UKey_CheckInstall = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_CheckInstall();
	}

	this.UKey_GetVersion = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetVersion();
	}

	this.UKey_GetDevSN = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetDevSN();
	}

	this.UKey_VerifyPIN = function(userPin) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_VerifyPIN(userPin);
	}

	this.UKey_ClearAuth = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ClearAuth();
	}

	this.UKey_GetCertCN = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetCertCN();
	}

	this.UKey_GetCertInfo = function(signFlag,certInfoType) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetCertInfo(signFlag,certInfoType);
	}

	this.UKey_GetCertInfoList = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetCertInfoList();
	}

	this.UKey_SetAdminKey = function(type,certTheme,certSN) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_SetAdminKey(type,certTheme,certSN);
	}

	this.UKey_SetCurCert = function(ID,certTheme,certSN) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_SetCurCert(ID,certTheme,certSN);
	}

	this.UKey_GetExtCertInfo = function(certInfoType,certData) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetExtCertInfo(certInfoType,certData);
	}

	this.UKey_GetCert = function(signFlag) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetCert(signFlag);
	}

	this.UKey_SignData = function(digestAlg,plainText) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_SignData(digestAlg,plainText);
	}

	this.UKey_ChangePIN = function(oldPIN, newPIN) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ChangePIN(oldPIN, newPIN);
	}

	this.UKey_UnblockPIN = function(adminPIN, newPIN) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_UnblockPIN(adminPIN, newPIN);
	}

	this.UKey_GetRetryCount = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetRetryCount();
	}

	this.UKey_GetPINInfo = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GetPINInfo();
	}

	this.UKey_GenRandom = function(randomSize) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GenRandom(randomSize);
	}

	this.UKey_CreateFile = function(filename,filesize) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_CreateFile(filename,filesize);
	}

	this.UKey_ReadFile = function(filename) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ReadFile(filename);
	}

	this.UKey_WriteFile = function(filename,filedata) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_WriteFile(filename,filedata);
	}

	this.UKey_EnumFiles = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_EnumFiles();
	}

	this.UKey_DeleteCons = function() {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_DeleteCons();
	}

	this.UKey_SM2Encrypt = function (pubKey,plainText) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_SM2Encrypt(pubKey,plainText);
	}

	this.UKey_ExportPublicKey = function(bSignFlag) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ExportPublicKey(bSignFlag);
	}

	this.UKey_ImportPfxCert = function(strPfxCert) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ImportPfxCert(strPfxCert);
	}

	this.UKey_GenKeyPair = function (iAlgType) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GenKeyPair(iAlgType);
	}

	this.UKey_ImportCertAndKeyPair = function (SignCert,EncCert,EncKeyPair) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_ImportCertAndKeyPair(SignCert,EncCert,EncKeyPair);
	}

	this.UKey_GenCSR = function (dnData) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_GenCSR(dnData);
	}

	this.UKey_DeleteFile = function (filename) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_DeleteFile(filename);
	}

	this.UKey_DigestData = function(digestAlg,plaintext) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_DigestData(digestAlg,plaintext);
	}

	this.UKey_P7SignAttach = function (digestAlg, plaintext) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7SignAttach(digestAlg, plaintext);
	}

	this.UKey_P7AttachVerify = function (digestAlg, signValue) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7AttachVerify(digestAlg, signValue);
	}

	this.UKey_P7SignDetach = function (digestAlg, plaintext) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7SignDetach(digestAlg, plaintext);
	}

	this.UKey_P7DetachVerify = function (digestAlg,plaintext ,signValue) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7DetachVerify(digestAlg,plaintext, signValue);
	}

	this.UKey_VerifyData = function (digestAlg,pubKey,srcData,signValue) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_VerifyData(digestAlg,pubKey,srcData,signValue);
	}

	this.UKey_P7EnvlopeEncryptData = function(SymAlg,IVData,CertData,Plaintext) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7EnvlopeEncryptData(SymAlg,IVData,CertData,Plaintext);
	}

	this.UKey_P7EnvlopeDecryptData = function(encryptData) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_P7EnvlopeDecryptData(encryptData);
	}

	this.UKey_Base64EnCode = function(srcData) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_Base64EnCode(srcData);
	}

	this.UKey_Base64DeCode = function(srcData) {
		if (null == g_UKeyPlugin)
			g_UKeyPlugin = new UKeyPlugin();
		return g_UKeyPlugin.UKey_Base64DeCode(srcData);
	}
}

function UKeyPlugin() {

	var urlDomain = "https://jitgmplugin.cn:36753/keyserver_plugin";
	
	// var urlIP     = "https://127.0.0.1:36753/keyserver_plugin";
	var urlIP     = "https://jitgmplugin.cn:36753/keyserver_plugin";

	// var urlHttp   = "http://127.0.0.1:36752/keyserver_plugin";
	var urlHttp   = "https://jitgmplugin.cn:36752/keyserver_plugin";

	var curUrl    = navigator.platform.toLowerCase().includes('win') ? urlDomain : urlIP;
	var xhr;

	function createXHR() {
		if (window.XMLHttpRequest) {
			return new XMLHttpRequest();
		} else {
			return new ActiveXObject("Microsoft.XMLHTTP");
		}
	}

	function KeyProcess(json) {
		if (!xhr) 
			xhr = createXHR(); 
		xhr.open("POST", curUrl, false);
		xhr.send(json);
	}

	this.UKey_CheckInstall = function(){
		try{
			this.UKey_GetVersion();
			return 0;
		}catch(e){
			try{
				curUrl = navigator.platform.toLowerCase().includes('win') ?  urlIP : urlDomain;
				this.UKey_GetVersion();
				return 0;
			}catch(e){
				if(!(navigator.platform.toLowerCase().includes('win'))){
					try{
						curUrl = urlHttp;
						this.UKey_GetVersion();
						return 0;
					}catch(e){
						throw e;
					}
				}else{
					throw e;
				}
			}
		}
	}

	this.UKey_GetVersion = function () {
		var json = {
			exec_name: "UKey_GetVersion",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GetDevSN = function () {
		var json = {
			exec_name: "UKey_GetDevInfo",
			exec_arg_real_list: [2]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_VerifyPIN = function (pin) {
		var json = {
			exec_name: "UKey_VerifyPIN",
			exec_arg_real_list: [pin]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_status;
			else{
				throw object.exec_status;
			}
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_ClearAuth = function () {
		var json = {
			exec_name: "UKey_ClearAuth",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_GetCertCN = function () {
		var json = {
			exec_name: "UKey_GetCertInfo",
			exec_arg_real_list: [1,9]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GetCertInfo = function (signFlag,certInfoType) {
		var json = {
			exec_name: "UKey_GetCertInfo",
			exec_arg_real_list: [signFlag,certInfoType]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GetCertInfoList = function () {
		var json = {
			exec_name: "UKey_GetCertInfoList",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_SetCurCert = function (ID,certTheme,certSN) {
		var json = {
			exec_name: "UKey_SetCurCert",
			exec_arg_real_list: [ID,certTheme,certSN]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_SetAdminKey = function(type,certTheme,certSN) {
		var json = {
			exec_name: "UKey_SetAdminKey",
			exec_arg_real_list: [type,certTheme,certSN]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GetExtCertInfo = function (certInfoType,certData) {
		var json = {
			exec_name: "UKey_GetExtCertInfo",
			exec_arg_real_list: [certInfoType,certData]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_GetCert = function (signFlg) {
		var json = {
			exec_name: "UKey_GetCert",
			exec_arg_real_list: [signFlg]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_ImportPfxCert = function(strPfxCert) {
		var json = {
			exec_name: "UKey_ImportPfxCert",
			exec_arg_real_list: [strPfxCert]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_SM2Encrypt = function	(pubKey,plainText) {
		var json = {
			exec_name: "UKey_SM2Encrypt",
			exec_arg_real_list: [pubKey,plainText]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_ExportPublicKey = function(bSignFlag) {
		var json = {
			exec_name: "UKey_ExportPublicKey",
			exec_arg_real_list: [bSignFlag]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_SignData = function (digestAlg,plainText) {
		var json = {
			exec_name: "UKey_SignData",
			exec_arg_real_list: [digestAlg,plainText]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_ChangePIN = function (oldPIN, newPIN) {
		var json = {
			exec_name: "UKey_ChangePIN",
			exec_arg_real_list: [oldPIN, newPIN]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_status;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_UnblockPIN = function (adminPIN, newPIN) {
		var json = {
			exec_name: "UKey_UnblockPIN",
			exec_arg_real_list: [adminPIN, newPIN]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else{
				throw object.exec_status;
			}
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_GetRetryCount = function () {
		var json = {
			exec_name: "UKey_GetPINInfo",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0){
				var info = JSON.parse(object.exec_result);
				return info.RemainRetryCount;
			}
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GetPINInfo = function () {
		var json = {
			exec_name: "UKey_GetPINInfo",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0){
				return object.exec_result;
			}
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GenRandom = function (randomSize) {
		var json = {
			exec_name: "UKey_GenRandom",
			exec_arg_real_list: [randomSize]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_CreateFile = function (filename,filesize) {
		var json = {
			exec_name: "UKey_CreateFile",
			exec_arg_real_list: [filename,filesize]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_ReadFile = function (filename) {
		var json = {
			exec_name: "UKey_ReadFile",
			exec_arg_real_list: [filename]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_WriteFile = function (filename,filedata) {
		var json = {
			exec_name: "UKey_WriteFile",
			exec_arg_real_list: [filename,filedata]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_EnumFiles = function () {
		var json = {
			exec_name: "UKey_EnumFiles",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GenKeyPair = function (iAlgType) {
		var json = {
			exec_name: "UKey_GenKeyPair",
			exec_arg_real_list: [iAlgType]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	
	this.UKey_DeleteCons = function () {
		var json = {
			exec_name: "UKey_DeleteCons",
			exec_arg_real_list: []
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_GenCSR = function (dnData) {

		var objectDN;
		try {
			objectDN = eval("(" + dnData + ")");
		} catch (e) {
			throw UKeyError.SAR_JSONFORMAT_ERR;
		}

		var json = {
			exec_name: "UKey_GenCSR",
			exec_arg_real_list: [objectDN]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_ImportCertAndKeyPair = function (SignCert,EncCert,EncKeyPair) {
		var json = {
			exec_name: "UKey_ImportCertAndKeyPair",
			exec_arg_real_list: [SignCert,EncCert,EncKeyPair]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_DeleteFile = function (filename) {
		var json = {
			exec_name: "UKey_DeleteFile",
			exec_arg_real_list: [filename]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_DigestData = function (digestAlg,plaintext) {
		var json = {
			exec_name: "UKey_DigestData",
			exec_arg_real_list: [digestAlg,plaintext]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7SignAttach = function (digestAlg,plaintext) {
		var json = {
			exec_name: "UKey_P7SignAttach",
			exec_arg_real_list: [digestAlg,plaintext]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7AttachVerify = function (digestAlg, signValue) {
		var json = {
			exec_name: "UKey_P7AttachVerify",
			exec_arg_real_list: [digestAlg,signValue]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7SignDetach = function (digestAlg, plaintext) {
		var json = {
			exec_name: "UKey_P7SignDetach",
			exec_arg_real_list: [digestAlg, plaintext]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7DetachVerify = function (digestAlg, plaintext,signValue) {
		var json = {
			exec_name: "UKey_P7DetachVerify",
			exec_arg_real_list: [digestAlg, plaintext,signValue]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_VerifyData = function (digestAlg, pubkey,srcData,signValue) {
		var json = {
			exec_name: "UKey_VerifyData",
			exec_arg_real_list: [digestAlg, pubkey,srcData,signValue]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7EnvlopeEncryptData = function (SymAlg,IVData,CertData,Plaintext) {
		var json = {
			exec_name: "UKey_P7EnvlopeEncryptData",
			exec_arg_real_list: [SymAlg,IVData,CertData,Plaintext]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_P7EnvlopeDecryptData = function (encryptData) {
		var json = {
			exec_name: "UKey_P7EnvlopeDecryptData",
			exec_arg_real_list: [encryptData]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

	this.UKey_Base64EnCode = function (srcData) {
		var json = {
			exec_name: "UKey_Base64EnCode",
			exec_arg_real_list: [srcData]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}


	this.UKey_Base64DeCode = function (srcData) {
		var json = {
			exec_name: "UKey_Base64DeCode",
			exec_arg_real_list: [srcData]
		};

		try {
			KeyProcess(JSON.stringify(json));
		} catch (e) {
			throw UKeyError.SAR_REQUEST_ERR;
		}

		if (4 == xhr.readyState && 200 == xhr.status) {
			var object = JSON.parse(xhr.responseText);
			if (object.exec_status == 0)
				return object.exec_result;
			else
				throw object.exec_status;
		} else {
			throw UKeyError.SAR_NETWORK_ERR;
		}
	}

}
