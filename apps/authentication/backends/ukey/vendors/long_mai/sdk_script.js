/******************************************************* 
* 
* 使用此JS脚本之前请先仔细阅读帮助文档! 
* 
* @author longmai 
* @version 4.1.22.0915
* @date 2024/11/18 
* 
**********************************************************/

var split;
var _curDevName = "";
var separatorExp;
// Avoid running twice; that would break the `nativeSplit` reference
split = split || function (undef) {

    var nativeSplit = String.prototype.split,
        compliantExecNpcg = /()??/.exec("")[1] === undef, // NPCG: nonparticipating capturing group
        self;

    self = function (str, separator, limit) {
        // If `separator` is not a regex, use `nativeSplit`
        if (Object.prototype.toString.call(separator) !== "[object RegExp]") {
            return nativeSplit.call(str, separator, limit);
        }
        var output = [],
            flags = (separator.ignoreCase ? "i" : "") +
                (separator.multiline ? "m" : "") +
                (separator.extended ? "x" : "") + // Proposed for ES6
                (separator.sticky ? "y" : ""), // Firefox 3+
            lastLastIndex = 0,
            // Make `global` and avoid `lastIndex` issues by working with a copy
            separatorExp = new RegExp(separator.source, flags + "g"),
            separator2, match, lastIndex, lastLength;
        str += ""; // Type-convert
        if (!compliantExecNpcg) {
            // Doesn't need flags gy, but they don't hurt
            separator2 = new RegExp("^" + separator.source + "$(?!\\s)", flags);
        }
        /* Values for `limit`, per the spec:
         * If undefined: 4294967295 // Math.pow(2, 32) - 1
         * If 0, Infinity, or NaN: 0
         * If positive number: limit = Math.floor(limit); if (limit > 4294967295) limit -= 4294967296;
         * If negative number: 4294967296 - Math.floor(Math.abs(limit))
         * If other: Type-convert, then use the above rules
         */
        limit = limit === undef ?
            -1 >>> 0 : // Math.pow(2, 32) - 1
            limit >>> 0; // ToUint32(limit)
        while (match = separatorExp.exec(str)) {
            // `separator.lastIndex` is not reliable cross-browser
            lastIndex = match.index + match[0].length;
            if (lastIndex > lastLastIndex) {
                output.push(str.slice(lastLastIndex, match.index));
                // Fix browsers whose `exec` methods don't consistently return `undefined` for
                // nonparticipating capturing groups
                if (!compliantExecNpcg && match.length > 1) {
                    match[0].replace(separator2, function () {
                        for (var i = 1; i < arguments.length - 2; i++) {
                            if (arguments[i] === undef) {
                                match[i] = undef;
                            }
                        }
                    });
                }
                if (match.length > 1 && match.index < str.length) {
                    Array.prototype.push.apply(output, match.slice(1));
                }
                lastLength = match[0].length;
                lastLastIndex = lastIndex;
                if (output.length >= limit) {
                    break;
                }
            }
            if (separatorExp.lastIndex === match.index) {
                separatorExp.lastIndex++; // Avoid an infinite loop
            }
        }
        if (lastLastIndex === str.length) {
            if (lastLength || !separatorExp.test("")) {
                output.push("");
            }
        } else {
            output.push(str.slice(lastLastIndex));
        }
        return output.length > limit ? output.slice(0, limit) : output;
    };

    // For convenience
    String.prototype.split = function (separator, limit) {
        return self(this, separator, limit);
    };

    return self;

}();


function mToken(obj) {
    this.obj = obj;

    this.SAR_OK = 0;
    this.SAR_FALSE = 1;

    //分组加密算法标识
    this.SGD_SM1_ECB = 0x00000101;
    this.SGD_SM1_CBC = 0x00000102;
    this.SGD_SM1_CFB = 0x00000104;
    this.SGD_SM1_OFB = 0x00000108;
    this.SGD_SM1_MAC = 0x00000110;
    this.SGD_SSF33_ECB = 0x00000201;
    this.SGD_SSF33_CBC = 0x00000202;
    this.SGD_SSF33_CFB = 0x00000204;
    this.SGD_SSF33_OFB = 0x00000208;
    this.SGD_SSF33_MAC = 0x00000210;
    this.SGD_SM4_ECB = 0x00000401;
    this.SGD_SM4_CBC = 0x00000402;
    this.SGD_SM4_CFB = 0x00000404;
    this.SGD_SM4_OFB = 0x00000408;
    this.SGD_SM4_MAC = 0x00000410;

    this.SGD_VENDOR_DEFINED = 0x80000000;
    this.SGD_DES_ECB = this.SGD_VENDOR_DEFINED + 0x00000211
    this.SGD_DES_CBC = this.SGD_VENDOR_DEFINED + 0x00000212

    this.SGD_3DES168_ECB = this.SGD_VENDOR_DEFINED + 0x00000241
    this.SGD_3DES168_CBC = this.SGD_VENDOR_DEFINED + 0x00000242

    this.SGD_3DES112_ECB = this.SGD_VENDOR_DEFINED + 0x00000221
    this.SGD_3DES112_CBC = this.SGD_VENDOR_DEFINED + 0x00000222

    this.SGD_AES128_ECB = this.SGD_VENDOR_DEFINED + 0x00000111
    this.SGD_AES128_CBC = this.SGD_VENDOR_DEFINED + 0x00000112

    this.SGD_AES192_ECB = this.SGD_VENDOR_DEFINED + 0x00000121
    this.SGD_AES192_CBC = this.SGD_VENDOR_DEFINED + 0x00000122

    this.SGD_AES256_ECB = this.SGD_VENDOR_DEFINED + 0x00000141
    this.SGD_AES256_CBC = this.SGD_VENDOR_DEFINED + 0x00000142


    //非对称密码算法标识
    this.SGD_RSA = 0x00010000;
    this.SGD_SM2_1 = 0x00020100; //ECC签名
    this.SGD_SM2_2 = 0x00020200; //ECC密钥交换
    this.SGD_SM2_3 = 0x00020400; //ECC加密

    //密码杂凑算法标识
    this.SGD_SM3 = 0x00000001;
    this.SGD_SHA1 = 0x00000002;
    this.SGD_SHA256 = 0x00000004;
    this.SGD_RAW = 0x00000080;
    this.SGD_MD5 = 0x00000081;
    this.SGD_SHA384 = 0x00000082;
    this.SGD_SHA512 = 0x00000083;


    this.SGD_CERT_VERSION = 0x00000001;
    this.SGD_CERT_SERIAL = 0x00000002;
    this.SGD_CERT_ISSUE = 0x00000005;
    this.SGD_CERT_VALID_TIME = 0x00000006;
    this.SGD_CERT_SUBJECT = 0x00000007;
    this.SGD_CERT_DER_PUBLIC_KEY = 0x00000008;
    this.SGD_CERT_DER_EXTENSIONS = 0x00000009;
    this.SGD_CERT_NOT_BEFORE = 0x00000010;
    this.SGD_CERT_ISSUER_CN = 0x00000021;
    this.SGD_CERT_ISSUER_O = 0x00000022;
    this.SGD_CERT_ISSUER_OU = 0x00000023;
    this.SGD_CERT_ISSUER_C = 0x00000024;
    this.SGD_CERT_ISSUER_P = 0x00000025;
    this.SGD_CERT_ISSUER_L = 0x00000026;
    this.SGD_CERT_ISSUER_S = 0x00000027;
    this.SGD_CERT_ISSUER_EMAIL = 0x00000028;

    this.SGD_CERT_SUBJECT_CN = 0x00000031;
    this.SGD_CERT_SUBJECT_O = 0x00000032;
    this.SGD_CERT_SUBJECT_OU = 0x00000033;
    this.SGD_CERT_SUBJECT_EMALL = 0x00000034;
    this.SGD_REMAIN_TIME = 0x00000035;
    this.SGD_SIGNATURE_ALG = 0x00000036;
    this.SGD_CERT_SUBJECT_C = 0x00000037;
    this.SGD_CERT_SUBJECT_P = 0x00000038;
    this.SGD_CERT_SUBJECT_L = 0x00000039;
    this.SGD_CERT_SUBJECT_S = 0x0000003A;

    this.SGD_CERT_CRL = 0x00000041;


    this.SGD_DEVICE_SORT = 0x00000201;
    this.SGD_DEVICE_TYPE = 0x00000202;
    this.SGD_DEVICE_NAME = 0x00000203;
    this.SGD_DEVICE_MANUFACTURER = 0x00000204;
    this.SGD_DEVICE_HARDWARE_VERSION = 0x00000205;
    this.SGD_DEVICE_SOFTWARE_VERSION = 0x00000206;
    this.SGD_DEVICE_STANDARD_VERSION = 0x00000207;
    this.SGD_DEVICE_SERIAL_NUMBER = 0x00000208;
    this.SGD_DEVICE_SUPPORT_SYM_ALG = 0x00000209;
    this.SGD_DEVICE_SUPPORT_ASYM_ALG = 0x0000020A;
    this.SGD_DEVICE_SUPPORT_HASH_ALG = 0x0000020B;
    this.SGD_DEVICE_SUPPORT_STORANGE_SPACE = 0x0000020C;
    this.SGD_DEVICE_SUPPORT_FREE_SAPCE = 0x0000020D;
    this.SGD_DEVICE_RUNTIME = 0x0000020E;
    this.SGD_DEVICE_USED_TIMES = 0x0000020F;
    this.SGD_DEVICE_LOCATION = 0x00000210;
    this.SGD_DEVICE_DESCRIPTION = 0x00000211;
    this.SGD_DEVICE_MANAGER_INFO = 0x00000212;
    this.SGD_DEVICE_MAX_DATA_SIZE = 0x00000213;

    this.TRUE = 1;
    this.FALSE = 0;

    this.GM3000PCSC = 0;
    this.GM3000 = 1;
    this.K7 = 2;
    this.K5 = 3;
    this.TF = 4;

    this.TYPE_UKEY = 1; //普通UKEY
    this.TYPE_FPKEY = 2; //指纹UKEY

    var g_mTokenPlugin = null;
    var ret = "";
    function isIe() {
        return ("ActiveXObject" in window);
    }

    function isMobile() {
        var browser = {
            versions: function () {
                var u = navigator.userAgent;
                return {//移动终端浏览器版本信息   
                    trident: u.indexOf('Trident') > -1, //IE内核  
                    presto: u.indexOf('Presto') > -1, //opera内核  
                    webKit: u.indexOf('AppleWebKit') > -1, //苹果、谷歌内核  
                    gecko: u.indexOf('Gecko') > -1 && u.indexOf('KHTML') == -1, //火狐内核  
                    mobile: !!u.match(/AppleWebKit.*Mobile.*/), //是否为移动终端  
                    ios: !!u.match(/\(i[^;]+;( U;)? CPU.+Mac OS X/), //ios终端  
                    android: u.indexOf('Android') > -1 || u.indexOf('Linux') > -1, //android终端或者uc浏览器  
                    iPhone: u.indexOf('iPhone') > -1, //是否为iPhone或者QQHD浏览器  
                    iPad: u.indexOf('iPad') > -1, //是否iPad    
                    webApp: u.indexOf('Safari') == -1
                    //是否web应该程序，没有头部与底部  
                };
            }(),
            language: (navigator.browserLanguage || navigator.language).toLowerCase()
        }
        if (browser.versions.mobile) {
            return true;
        }
        else {
            return false;
        }
    }

    this.SOF_LoadLibrary = function (type) {
        if (g_mTokenPlugin == null) {
            g_mTokenPlugin = new mTokenPlugin();
        }

        if (type == this.GM3000PCSC) {
            if (isMobile()) {
                ret = g_mTokenPlugin.SOF_LoadLibrary("1", "mToken OTG", "com.longmai.security.plugin.driver.otg.OTGDriver");
            }
            else {
                ret = g_mTokenPlugin.SOF_LoadLibrary("mtoken_gm3000_pcsc.dll", "libgm3000_scard.1.0.so", "libgm3000_scard.1.0.dylib");
            }
        }
        else if (type == this.GM3000) {
            if (isMobile()) {
                ret = g_mTokenPlugin.SOF_LoadLibrary("1", "mToken OTG", "com.longmai.security.plugin.driver.otg.OTGDriver");
            }
            else {
                ret = g_mTokenPlugin.SOF_LoadLibrary("mtoken_gm3000.dll", "libgm3000.1.0.so", "libgm3000.1.0.dylib");
            }
        }
        else if (type == this.K7) {
            ret = g_mTokenPlugin.SOF_LoadLibrary("mtoken_k7.dll", "libk7.1.0.so", "libk7.1.0.dylib");
        }
        else if (type == this.K5) {
            if (isMobile()) {
                ret = g_mTokenPlugin.SOF_LoadLibrary("2", "mToken K5 Bluetooth", "com.longmai.security.plugin.driver.ble.BLEDriver");
            }
            else {
                ret = g_mTokenPlugin.SOF_LoadLibrary("mtoken_k5.dll", "libk5.1.0.so", "libk5.1.0.dylib");
            }
        }
        else if (type == this.TF) {
            if (isMobile()) {
                ret = g_mTokenPlugin.SOF_LoadLibrary("0", "mToken TF/SD Card", "com.longmai.security.plugin.driver.tf.TFDriver");
            } else {
                ret = g_mTokenPlugin.SOF_LoadLibrary("mtoken_tf.dll", "libtf.so", "libtf.dylib");
            }

        }
        if (ret == "-3") {
            return ret;
        }
        return ret.rtn;
    };

    this.SOF_GetLastError = function () {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_GetLastError();
        if (ret == "-3") {
            return ret;
        }
        return ret.rtn.toString(16);
    }

    this.SOF_EnumDevice = function () {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EnumDevice();
        if (ret.array == null || ret.array.length <= 0) {
            return null;
        }
        return ret.array.split("||");
    };

    this.SOF_DevAuth = function (deviceName, authCode) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DevAuth(deviceName, authCode);
        return ret.rtn;
    };

    this.SOF_ChangeDevAuthKey = function (deviceName, newAuthCode) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ChangeDevAuthKey(deviceName, newAuthCode);
        return ret.rtn;
    }

    this.SOF_CreateApplication = function (deviceName, applicationName, adminPin, adminPinRetryCount, userPin, userPinRetryCount, fileRights) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_CreateApplication(deviceName, applicationName, adminPin, adminPinRetryCount, userPin, userPinRetryCount, fileRights);
        return ret.rtn;
    }

    this.SOF_GetApplicationList = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetApplicationList(deviceName);
        if (ret.array == null || ret.array.length <= 0) {
            return null;
        }
        return ret.array.split("||");
    }

    this.SOF_DeleteApplication = function (deviceName, applicationName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DeleteApplication(deviceName, applicationName);
        return ret.rtn;
    }

    this.SOF_CheckExists = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_CheckExists(deviceName);
        if (ret.rtn == 0) {
            return ret.isExist;
        }
        return ret.rtn;
    }


    this.SOF_GetVersion = function () {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetVersion();
        if (ret.rtn == 0) {
            return ret.version;
        }
        return null;
    };


    this.SOF_GetDeviceInstance = function (DeviceName, ApplicationName) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        _curDevName = DeviceName;
        ret = g_mTokenPlugin.SOF_GetDeviceInstance(DeviceName, ApplicationName);
        return ret.rtn;
    };

    this.SOF_ReleaseDeviceInstance = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        _curDevName = deviceName;
        ret = g_mTokenPlugin.SOF_ReleaseDeviceInstance(deviceName);
        return ret.rtn;
    }


    this.SOF_GetUserList = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return null;
        }

        var array = g_mTokenPlugin.SOF_GetUserList(deviceName);
        if (array == null || array.length <= 0) {
            return null;
        }

        var list = [];
        var user = array.array.split("&&&"); // 用 "&&&" 分割字符串
        for (var i = 0; i < user.length; i++) {
            list[i] = user[i].split("||"); // 对每个子字符串用 "||" 分割
        }

        return list;
    };

    this.SOF_ExportUserCert = function (ContainerName, KeySpec) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ExportUserCert(ContainerName, KeySpec);
        if (ret.rtn == 0) {
            return ret.cert;
        }
        return null;
    };


    this.SOF_GetDeviceInfo = function (deviceName, Type) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetDeviceInfo(deviceName, Type);
        if (ret.rtn == 0) {
            return ret.info;
        } else {
            return null;
        }

    };


    this.SOF_GetCertInfo = function (Base64EncodeCert, Type) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetCertInfo(Base64EncodeCert, Type);
        if (ret.rtn == 0) {
            return ret.info;
        }
        return null;
    };

    this.SOF_GetCertInfoByOid = function (Base64EncodeCert, OID) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetCertInfoByOid(Base64EncodeCert, OID);
        if (ret.rtn == 0) {
            return ret.info;
        }
        return null;
    }

    this.SOF_Login = function (PassWd) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_Login(PassWd);
        return ret.rtn;
    };

    this.SOF_LoginSoPin = function (PassWd) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_LoginSoPin(PassWd);
        return ret.rtn;
    }


    this.SOF_LogOut = function () {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_LogOut();
        return ret.rtn;
    };
    this.SOF_GetPinRetryCountInfo = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return -1;
        }

        return g_mTokenPlugin.SOF_GetPinRetryCountInfo(deviceName);
    };

    this.SOF_SetLabel = function (deviceName, Label) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_SetLabel(deviceName, Label);
        return ret.rtn;
    }

    this.SOF_ChangePassWd = function (OldPassWd, NewPassWd) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_ChangePassWd(OldPassWd, NewPassWd);
        return ret.rtn;
    };

    this.SOF_ChangeSoPin = function (OldPassWd, NewPassWd) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_ChangeSoPin(OldPassWd, NewPassWd);
        return ret.rtn;
    };
    this.SOF_UnblockUserPin = function (sopin, upin) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_UnblockUserPin(sopin, upin);
        return ret.rtn;
    };


    this.SOF_SetDigestMethod = function (DigestMethod) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_SetDigestMethod(DigestMethod);
        return ret.rtn;
    };


    this.SOF_SetUserID = function (UserID) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_SetUserID(UserID);
        return ret.rtn;
    };


    this.SOF_SetEncryptMethodAndIV = function (EncryptMethod, EncryptIV) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_SetEncryptMethodAndIV(EncryptMethod, EncryptIV);
        return ret.rtn;
    };


    this.SOF_EncryptFileToPKCS7 = function (Cert, InFile, OutFile, type) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_EncryptFileToPKCS7(Cert, InFile, OutFile, type);
        if (ret.rtn == 0) {
            return ret.envelopData;
        }
        return null;
    };


    this.SOF_SignFileToPKCS7 = function (ContainerName, KeySpec, InFile) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_SignFileToPKCS7(ContainerName, KeySpec, InFile);
        if (ret.rtn == 0) {
            return ret.signed;
        }
        return null;
    };

    this.SOF_VerifyFileToPKCS7 = function (strPkcs7Data, InFilePath) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_VerifyFileToPKCS7(strPkcs7Data, InFilePath);
        return ret.rtn;
    };

    this.SOF_DecryptFileToPKCS7 = function (ContainerName, keySpec, Pkcs7Data, InFile, OutFile, type) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_DecryptFileToPKCS7(ContainerName, keySpec, Pkcs7Data, InFile, OutFile, type);
        return ret.rtn;
    };

    this.SOF_DigestData = function (deviceName, ContainerName, nData, InDataLen) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DigestData(deviceName, ContainerName, nData, InDataLen);
        if (ret.rtn == 0) {
            return ret.digest;
        }
        return null;
    };

    this.SOF_SignData = function (ContainerName, ulKeySpec, InData, InDataLen, mode) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SignData(ContainerName, ulKeySpec, InData, InDataLen, mode);
        if (ret.rtn == 0) {
            return ret.signed;
        }
        return null;
    };

    this.SOF_SignDataInteractive = function (ContainerName, ulKeySpec, InData, InDataLen) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SignDataInteractive(ContainerName, ulKeySpec, InData, InDataLen);
        if (ret.rtn == 0) {
            return ret.signed;
        }
        return null;
    }

    this.SOF_VerifySignedData = function (Base64EncodeCert, digestMethod, InData, SignedValue, mode) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_VerifySignedData(Base64EncodeCert, digestMethod, InData, SignedValue, mode);
        return ret.rtn;
    };

    this.SOF_EncryptDataPKCS7EX = function (Base64EncodeCert, InData, InDataLen) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EncryptDataPKCS7EX(Base64EncodeCert, InData, InDataLen);
        if (ret.rtn == 0) {
            return ret.encrypedData;
        }
        return null;
    };

    this.SOF_DecryptDataPKCS7EX = function (ContainerName, ulKeySpec, InData) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DecryptDataPKCS7EX(ContainerName, ulKeySpec, InData);
        if (ret.rtn == 0) {
            return ret.decryptedData;
        }
        return null;
    };

    this.SOF_GenRemoteUnblockRequest = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GenRemoteUnblockRequest(deviceName);
        if (ret.rtn == 0) {
            return ret.request;
        }
        return null;
    };


    this.SOF_GenResetpwdResponse = function (deviceName, request, soPin, userPin) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GenResetpwdResponse(deviceName, request, soPin, userPin);
        if (ret.rtn == 0) {
            return ret.request;
        }
        return null;
    };


    this.SOF_RemoteUnblockPIN = function (deviceName, request) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_RemoteUnblockPIN(deviceName, request);
        return ret.rtn;
    };


    this.SOF_SignDataToPKCS7 = function (ContainerName, ulKeySpec, InData, ulDetached) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SignDataToPKCS7(ContainerName, ulKeySpec, InData, ulDetached);
        if (ret.rtn == 0) {
            return ret.pkcs7;
        }
        return null;
    };


    this.SOF_VerifyDataToPKCS7 = function (strPkcs7Data, OriginalText, ulDetached) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_VerifyDataToPKCS7(strPkcs7Data, OriginalText, ulDetached);
        return ret.rtn;
    };

    //按expType导出的公钥，格式为国密规范指定的格式或DER格式或裸数据格式
    //expType=1: 国密格式； 2:DER; 3:RAW (SM2 public key ONLY: X|Y, X,Y各为32字节)
    this.SOF_ExportPubKey = function (containerName, cerType, expType) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ExportPubKey(containerName, cerType, expType);
        if (ret.rtn == 0) {
            return ret.pubKey;
        }
        return null;
    }

    this.SOF_PublicVerify = function (pubKey, inData, signedValue, digestMethod) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_PublicVerify(pubKey, inData, signedValue, digestMethod);
        return ret.rtn;
    }

    this.SOF_EncryptByPubKey = function (strPubKey, strInput, cerType) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EncryptByPubKey(strPubKey, strInput, cerType);
        if (ret.rtn == 0) {
            return ret.asymCipher;
        }
        return null;
    }

    this.SOF_DecryptByPrvKey = function (containerName, cerType, strAsymCipher) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DecryptByPrvKey(containerName, cerType, strAsymCipher);
        if (ret.rtn == 0) {
            return ret.asymPlain;
        }
        return null;
    }

    this.SOF_GenerateP10Request = function (container, dn, asymAlg, keySpec, keyLength) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GenerateP10Request(container, dn, asymAlg, keySpec, keyLength);
        if (ret.rtn == 0) {
            return ret.outData;
        }
        return null;
    }

    this.SOF_CreateContainer = function (containerName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_CreateContainer(containerName);
        return ret.rtn;
    }

    this.SOF_EnumCertContiner = function () {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EnumCertContiner();
        if (ret.rtn == 0) {
            return ret.containerName.split("||");
        }
        return null;
    }


    this.SOF_FindContainer = function (certSN) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_FindContainer(certSN);
        if (ret.rtn == 0) {
            return ret.containerName;
        }
        return null;
    }

    this.SOF_DeleteCert = function (certSN) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DeleteCert(certSN);
        if (ret.rtn == 0) {
            return ret.containerName;
        }
        return null;
    }

    this.SOF_DeleteContainer = function (certSN) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DeleteContainer(certSN);
        if (ret.rtn == 0) {
            return ret.containerName;
        }
        return null;
    }


    this.SOF_ImportCert = function (container, cert, keySpec) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ImportCert(container, cert, keySpec);
        return ret.rtn;
    }

    this.SOF_ImportCryptoCertAndKey = function (container, cert, nAsymAlg, EncryptedSessionKeyData, symAlg, EncryptedPrivateKeyData, mode) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ImportCryptoCertAndKey(container, cert, nAsymAlg, EncryptedSessionKeyData, symAlg, EncryptedPrivateKeyData, mode);
        return ret.rtn;
    }

    this.SOF_GenerateRandom = function (deviceName, length) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GenerateRandom(deviceName, length);
        if (ret.rtn == 0) {
            return ret.outData;
        }
        return null;
    }

    this.SOF_SymEncryptFile = function (deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SymEncryptFile(deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV);
        return ret.rtn;
    }

    this.SOF_SymDecryptFile = function (deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SymDecryptFile(deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV);
        return ret.rtn;
    }

    this.SOF_SymEncryptData = function (deviceName, sessionKey, inData) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SymEncryptData(deviceName, sessionKey, inData);
        if (ret.rtn == 0) {
            return ret.outData;
        }
        return null;
    }

    this.SOF_SymDecryptData = function (deviceName, sessionKey, inData) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SymDecryptData(deviceName, sessionKey, inData);
        if (ret.rtn == 0) {
            return ret.outData;
        }
        return null;
    }

    this.SOF_GetHardwareType = function () {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_GetHardwareType();
        if (ret.rtn == 0) {
            return ret.type;
        }
        return ret.rtn;
    }

    this.SOF_VerifyFingerprintEx = function (deviceName) {
        if (g_mTokenPlugin == null) {
            return null;
        }

        return g_mTokenPlugin.SOF_VerifyFingerprintEx(deviceName);
    }

    this.SOF_EnumFiles = function () {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EnumFiles();
        if (ret.rtn == 0) {
            return ret.array.split("||");
        }
        return null;
    }

    this.SOF_ReadFile = function (fileName, offset, length) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_ReadFile(fileName, Number(offset), Number(length));
        if (ret.rtn == 0) {
            return ret.outData;
        }
        return null;
    }

    this.SOF_WriteFile = function (fileName, offset, data) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_WriteFile(fileName, offset, data);
        return ret.rtn;
    }

    this.SOF_CreateFile = function (fileName, length, readRight, writeRight) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_CreateFile(fileName, length, readRight, writeRight);
        return ret.rtn;
    }

    this.SOF_DeleteFile = function (fileName) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DeleteFile(fileName);
        return ret.rtn;
    }

    this.SOF_SetCrossAccess = function (crossAccess) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_SetCrossAccess(crossAccess);
        return ret.rtn;
    }


    this.SOF_CreateKeyPair = function (container, keySpec, asymAlg, keyLength) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_CreateKeyPair(container, keySpec, asymAlg, keyLength);
        return ret.rtn;
    }

    this.SOF_VerifyCode = function (code) {
        if (g_mTokenPlugin == null) {
            return -1;
        }
        ret = g_mTokenPlugin.SOF_VerifyCode(code);
        return ret.rtn;
    };
    this.SOF_GetFingerInfo = function (deviceName, userType) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        return g_mTokenPlugin.SOF_GetFingerInfo(deviceName, userType);
    }

    this.SOF_EnrollFinger = function (DeviceName, userType, ulFingerID) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_EnrollFinger(DeviceName, userType, ulFingerID);
        if (ret.rtn == 0) {
            return ret.FingerId;
        }
        return ret.rtn;
    }
    this.SOF_DeleteFinger = function (DeviceName, userType, ulFingerID) {
        if (g_mTokenPlugin == null) {
            return null;
        }
        ret = g_mTokenPlugin.SOF_DeleteFinger(DeviceName, userType, ulFingerID);
        return ret.rtn;
    }
}

function mTokenPlugin() {
    var _xmlhttp;
    function AjaxIO(json_in) {
        var _url = "http://127.0.0.1:51235/alpha";
        var json = json_in;
        if (_xmlhttp == null) {
            if (window.XMLHttpRequest) { // code for IE7+, Firefox, Chrome, Opera, Safari
                _xmlhttp = new XMLHttpRequest();
            } else { // code for IE6, IE5
                _xmlhttp = new ActiveXObject("Microsoft.XMLHTTP");
            }
        }
        if ("https:" == document.location.protocol) {
            _url = "https://127.0.0.1:51245/alpha";
        }
        _xmlhttp.open("POST", _url, false);
        _xmlhttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        _xmlhttp.send("json=" + json);
    }

    function GetHttpResult() {
        if (_xmlhttp.readyState == 4 && _xmlhttp.status == 200) {
            try {
                var obj = JSON.parse(_xmlhttp.responseText);
                return obj;
            } catch (error) {
                //解析 JSON 失败
                return null;
            }
        } else {
            // 如果请求尚未完成或者不成功，返回 null。
            return null;
        }
    }


    this.SOF_GetLastError = function () {
        var json = '{"function":"SOF_GetLastError"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;

    }

    this.SOF_LoadLibrary = function (windows, linux, mac) {
        var json = '{"function":"SOF_LoadLibrary", "winDllName":"' + windows + '", "linuxSOName":"' + linux + '", "macDylibName":"' + mac + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;

    };


    this.SOF_EnumDevice = function () {
        var json = '{"function":"SOF_EnumDevice"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };
    this.SOF_DevAuth = function (deviceName, authCode) {
        var json = '{"function":"SOF_DevAuth", "deviceName":"' + deviceName + '", "authPassWd":"' + authCode + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_ChangeDevAuthKey = function (deviceName, newAuthCode) {
        var json = '{"function":"SOF_ChangeDevAuthKey", "deviceName":"' + deviceName + '", "authPassWd":"' + newAuthCode + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_CreateApplication = function (deviceName, ApplicationName, adminPin, adminPinRetryCount, userPin, userPinRetryCount, fileRights) {
        var json = '{"function":"SOF_CreateApplication", "deviceName":"' + deviceName + '", "applicationName":"' + ApplicationName + '", "soPin":"' + adminPin + '", "soPinRetryCount":' + adminPinRetryCount + ', "userPin":"' + userPin + '", "userPinRetryCount":' + userPinRetryCount + ',"rights":' + fileRights + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_DeleteApplication = function (deviceName, ApplicationName) {
        var json = '{"function":"SOF_DeleteApplication", "deviceName":"' + deviceName + '", "applicationName":"' + ApplicationName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_GetApplicationList = function (deviceName) {
        var json = '{"function":"SOF_GetApplicationList", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_CheckExists = function (deviceName) {
        var json = '{"function":"SOF_CheckExists", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GetVersion = function () {
        var json = '{"function":"SOF_GetVersion"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GetDeviceInstance = function (DeviceName, ApplicationName) {
        var json = '{"function":"SOF_GetDeviceInstance", "deviceName":"' + DeviceName + '", "applicationName":"' + ApplicationName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_ReleaseDeviceInstance = function (deviceName) {
        var json = '{"function":"SOF_ReleaseDeviceInstance", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_GetUserList = function (deviceName) {
        var json = '{"function":"SOF_GetUserList", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_ExportUserCert = function (ContainerName, KeySpec) {
        var json = '{"function":"SOF_ExportUserCert", "deviceName":"' + _curDevName + '", "containerName":"' + ContainerName + '", "keySpec":' + KeySpec + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GetDeviceInfo = function (deviceName, Type) {
        var json = '{"function":"SOF_GetDeviceInfo", "deviceName":"' + deviceName + '", "type":' + Type + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GetCertInfo = function (Base64EncodeCert, Type) {
        var json = '{"function":"SOF_GetCertInfo", "base64EncodeCert":"' + Base64EncodeCert + '", "type":' + Type + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GetCertInfoByOid = function (Base64EncodeCert, OID) {
        var json = '{"function":"SOF_GetCertInfoByOid", "base64EncodeCert":"' + Base64EncodeCert + '", "oid":"' + OID + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };



    this.SOF_Login = function (PassWd) {
        var json = '{"function":"SOF_Login", "deviceName":"' + _curDevName + '", "passWd":"' + PassWd + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_LoginSoPin = function (PassWd) {

        var json = '{"function":"SOF_LoginSoPin", "deviceName":"' + _curDevName + '", "passWd":"' + PassWd + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_LogOut = function () {
        var json = '{"function":"SOF_LogOut", "deviceName":"' + _curDevName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };
    this.SOF_GetPinRetryCountInfo = function (deviceName) {
        var json = '{"function":"SOF_GetPinRetryCount", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_ChangePassWd = function (OldPassWd, NewPassWd) {
        var json = '{"function":"SOF_ChangePassWd", "deviceName":"' + _curDevName + '",  "oldUpin":"' + OldPassWd + '", "newUpin":"' + NewPassWd + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_ChangeSoPin = function (OldPassWd, NewPassWd) {
        var json = '{"function":"SOF_ChangeSoPin", "deviceName":"' + _curDevName + '",  "oldUpin":"' + OldPassWd + '", "newUpin":"' + NewPassWd + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };
    this.SOF_UnblockUserPin = function (sopin, upin) {
        var json = '{"function":"SOF_UnblockUserPin", "deviceName":"' + _curDevName + '", "soPin":"' + sopin + '","newUpin":"' + upin + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_SetDigestMethod = function (DigestMethod) {
        var json = '{"function":"SOF_SetDigestMethod","deviceName":"' + _curDevName + '", "digestMethod":' + DigestMethod + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_SetUserID = function (UserID) {
        var json = '{"function":"SOF_SetUserID","deviceName":"' + _curDevName + '", "userID":"' + UserID + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_SetEncryptMethodAndIV = function (EncryptMethod, EncryptIV) {
        var json = '{"function":"SOF_SetEncryptMethodAndIV","deviceName":"' + _curDevName + '", "encryptMethod":' + EncryptMethod + ', "encryptIV":"' + EncryptIV + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_EncryptFileToPKCS7 = function (Cert, InFile, OutFile, type) {

        var json = '{"function":"SOF_EncryptFileToPKCS7", "deviceName":"' + _curDevName + '", "cert":"' + Cert + '", "inFile":"' + InFile.replace(/\\/g, '\\\\') + '", "outFile":"' + OutFile.replace(/\\/g, '\\\\') + '", "type":' + type + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_SignFileToPKCS7 = function (ContainerName, KeySpec, InFile) {
        var json = '{"function":"SOF_SignFileToPKCS7", "deviceName":"' + _curDevName + '",  "containerName":"' + ContainerName + '", "KeySpec":' + KeySpec + ', "inFile":"' + InFile.replace(/\\/g, '\\\\') + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_VerifyFileToPKCS7 = function (strPkcs7Data, InFilePath) {
        var json = '{"function":"SOF_VerifyFileToPKCS7", "deviceName":"' + _curDevName + '","strPkcs7Data":"' + strPkcs7Data + '", "inFile":"' + InFilePath.replace(/\\/g, '\\\\') + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_DecryptFileToPKCS7 = function (ContainerName, keySpec, Pkcs7Data, InFile, OutFile, type) {
        var json = '{"function":"SOF_DecryptFileToPKCS7", "deviceName":"' + _curDevName + '",  "containerName":"' + ContainerName + '", "keySpec":' + keySpec + ', "pkcs7Data":"' + Pkcs7Data + '", "inFile":"' + InFile.replace(/\\/g, '\\\\') + '", "outFile":"' + OutFile.replace(/\\/g, '\\\\') + '", "type":' + type + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_DigestData = function (deviceName, ContainerName, InData, InDataLen) {
        var json = '{"function":"SOF_DigestData","deviceName":"' + deviceName + '",  "containerName":"' + ContainerName + '", "inData":"' + InData + '", "inDataLen":' + InDataLen + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    //交互式签名
    this.SOF_SignDataInteractive = function (ContainerName, ulKeySpec, inData, InDataLen) {
        var json = '{"function":"SOF_SignDataInteractive", "deviceName":"' + _curDevName + '",  "containerName":"' + ContainerName + '", "keySpec":' + ulKeySpec + ', "inData":"' + inData + '", "inDataLen":' + InDataLen + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_SignData = function (ContainerName, ulKeySpec, InData, InDataLen, mode) {
        var json = '{"function":"SOF_SignDataEx", "deviceName":"' + _curDevName + '", "containerName":"' + ContainerName + '", "keySpec":' + ulKeySpec + ', "inData":"' + InData + '", "inDataLen":' + InDataLen + ', "mode":' + mode + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_VerifySignedData = function (Base64EncodeCert, digestMethod, InData, SignedValue, mode) {
        var json = '{"function":"SOF_VerifySignedDataEx","deviceName":"' + _curDevName + '", "base64EncodeCert":"' + Base64EncodeCert + '", "digestMethod":' + digestMethod + ', "inData":"' + InData + '", "signedValue":"' + SignedValue + '", "mode":' + mode + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_EncryptDataPKCS7EX = function (Base64EncodeCert, InData, InDataLen) {
        var json = '{"function":"SOF_EncryptDataPKCS7EX", "deviceName":"' + _curDevName + '", "base64EncodeCert":"' + Base64EncodeCert + '", "inData":"' + InData + '", "inDataLen":' + InDataLen + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_DecryptDataPKCS7EX = function (ContainerName, ulKeySpec, InData) {
        var json = '{"function":"SOF_DecryptDataPKCS7EX", "deviceName":"' + _curDevName + '", "containerName":"' + ContainerName + '", "keySpec":' + ulKeySpec + ', "inData":"' + InData + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GenRemoteUnblockRequest = function (deviceName) {
        var json = '{"function":"SOF_GenRemoteUnblockRequest", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_GenResetpwdResponse = function (deviceName, request, soPin, userPin) {
        var json = '{"function":"SOF_GenResetpwdResponse", "deviceName":"' + deviceName + '",  "request":"' + request + '", "soPin":"' + soPin + '", "userPin":"' + userPin + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_RemoteUnblockPIN = function (deviceName, request) {
        var json = '{"function":"SOF_RemoteUnblockPIN", "deviceName":"' + deviceName + '", "request":"' + request + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_SignDataToPKCS7 = function (ContainerName, ulKeySpec, InData, ulDetached) {
        var json = '{"function":"SOF_SignDataToPKCS7", "deviceName":"' + _curDevName + '", "containerName":"' + ContainerName + '", "keySpec":' + ulKeySpec + ', "inData":"' + InData + '",  "detached":' + ulDetached + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };


    this.SOF_VerifyDataToPKCS7 = function (strPkcs7Data, OriginalText, ulDetached) {
        var json = '{"function":"SOF_VerifyDataToPKCS7", "deviceName":"' + _curDevName + '", "pkcs7":"' + strPkcs7Data + '", "original":"' + OriginalText + '", "detached":' + ulDetached + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_VerifyDigestDataToPKCS7 = function (strPkcs7Data, OriginalText, ulDetached) {
        var json = '{"function":"SOF_VerifyDigestDataToPKCS7", "deviceName":"' + _curDevName + '", "pkcs7":"' + strPkcs7Data + '", "original":"' + OriginalText + '", "detached":' + ulDetached + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_ExportPubKey = function (containerName, keySpec, expType) {
        var json = '{"function":"SOF_ExportPubKeyEx","deviceName":"' + _curDevName + '",  "containerName":"' + containerName + '", "keySpec":' + keySpec + ', "expType":' + expType + '}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_PublicVerify = function (pubKey, inData, signedValue, digestMethod) {
        var json = '{"function":"SOF_PublicVerify", "deviceName":"' + _curDevName + '", "digestMethod":' + digestMethod + ', "pubKey":"' + pubKey + '", "inData":"' + inData + '",  "signedValue":"' + signedValue + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    //公钥加密
    this.SOF_EncryptByPubKey = function (strPubKey, strInput, cerType) {
        var json = '{"function":"SOF_EncryptByPubKey", "deviceName":"' + _curDevName + '", "pubKey":"' + strPubKey + '", "asymPlain":"' + strInput + '", "keySpec":' + cerType + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_DecryptByPrvKey = function (containerName, cerType, strAsymCipher) {
        var json = '{"function":"SOF_DecryptByPrvKey", "deviceName":"' + _curDevName + '", "containerName":"' + containerName + '", "asymCipher":"' + strAsymCipher + '", "keySpec":' + cerType + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_CreateKeyPair = function (container, keySpec, asymAlg, keyLength) {
        var json = '{"function":"SOF_CreateKeyPair","deviceName":"' + _curDevName + '",  "containerName":"' + container + '", "asymAlg":' + asymAlg + ', "keySpec":' + keySpec + ',"keyLength":' + keyLength + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_EnumCertContiner = function () {
        var json = '{"function":"SOF_EnumCertContiner", "deviceName":"' + _curDevName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_CreateContainer = function (containerName) {
        var json = '{"function":"SOF_CreateContainer","deviceName":"' + _curDevName + '",  "containerName":"' + containerName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }


    this.SOF_FindContainer = function (certSN) {
        var json = '{"function":"SOF_FindContainer","deviceName":"' + _curDevName + '",  "certSN":"' + certSN + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_DeleteCert = function (certSN) {
        var json = '{"function":"SOF_DeleteCert","deviceName":"' + _curDevName + '",  "certSN":"' + certSN + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_DeleteContainer = function (certSN) {
        var json = '{"function":"SOF_DeleteContainer", "deviceName":"' + _curDevName + '", "certSN":"' + certSN + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_GenerateP10Request = function (container, dn, asymAlg, keySpec, keyLength) {
        var json = '{"function":"SOF_GenerateP10Request", "deviceName":"' + _curDevName + '", "containerName":"' + container + '", "certDN":"' + dn + '", "asymAlg":' + asymAlg + ', "keySpec":' + keySpec + ',"keyLength":' + keyLength + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_ImportCert = function (container, cert, keySpec) {
        var json = '{"function":"SOF_ImportCert", "deviceName":"' + _curDevName + '", "containerName":"' + container + '", "cert":"' + cert + '", "keySpec":' + keySpec + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_ImportCryptoCertAndKey = function (container, cert, nAsymAlg, EncryptedSessionKeyData, symAlg, EncryptedPrivateKeyData, mode) {
        var json = '{"function":"SOF_ImportCryptoCertAndKey", "deviceName":"' + _curDevName + '", "containerName":"' + container + '", "cert":"' + cert + '", "asymAlg":' + nAsymAlg + ', "sessionKey":"' + EncryptedSessionKeyData + '", "symAlg":"' + symAlg + '", "encrypedData":"' + EncryptedPrivateKeyData + '", "mode":"' + mode + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_GenerateRandom = function (deviceName, length) {
        var json = '{"function":"SOF_GenRandom", "deviceName":"' + deviceName + '", "inDataLen":' + length + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SymEncryptFile = function (deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV) {
        var json = '{"function":"SOF_SymEncryptFile", "deviceName":"' + deviceName + '", "sessionKey":"' + sessionKey + '", "inFile":"' + srcfile.replace(/\\/g, '\\\\') + '", "outFile":"' + destfile.replace(/\\/g, '\\\\') + '", "type":' + type + ',"encryptMethod":' + encryptMethod + ',"encryptIV":"' + encryptIV + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SymDecryptFile = function (deviceName, sessionKey, srcfile, destfile, type, encryptMethod, encryptIV) {
        var json = '{"function":"SOF_SymDecryptFile", "deviceName":"' + deviceName + '", "sessionKey":"' + sessionKey + '", "inFile":"' + srcfile.replace(/\\/g, '\\\\') + '", "outFile":"' + destfile.replace(/\\/g, '\\\\') + '", "type":' + type + ',"encryptMethod":' + encryptMethod + ',"encryptIV":"' + encryptIV + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SymEncryptData = function (deviceName, sessionKey, inData) {
        var json = '{"function":"SOF_SymEncryptData", "deviceName":"' + deviceName + '", "sessionKey":"' + sessionKey + '", "inData":"' + inData + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SymDecryptData = function (deviceName, sessionKey, inData) {
        var json = '{"function":"SOF_SymDecryptData", "deviceName":"' + deviceName + '", "sessionKey":"' + sessionKey + '", "inData":"' + inData + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_GetHardwareType = function () {
        var json = '{"function":"SOF_GetHardwareType", "deviceName":"' + _curDevName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_VerifyFingerprintEx = function (deviceName) {
        var json = '{"function":"SOF_VerifyFingerprintEx", "deviceName":"' + deviceName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_EnumFiles = function () {
        var json = '{"function":"SOF_EnumFiles", "deviceName":"' + _curDevName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_ReadFile = function (fileName, offset, length) {
        var json = '{"function":"SOF_ReadFile", "deviceName":"' + _curDevName + '", "fileName":"' + fileName + '", "offset":' + offset + ',"length":' + length + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_WriteFile = function (fileName, offset, data) {
        var json = '{"function":"SOF_WriteFile", "deviceName":"' + _curDevName + '", "fileName":"' + fileName + '", "offset":' + offset + ',"inData":"' + data + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_CreateFile = function (fileName, length, readRight, writeRight) {
        var json = '{"function":"SOF_CreateFile", "deviceName":"' + _curDevName + '","fileName":"' + fileName + '", "length" :' + length + ', "readRight":' + readRight + ',"writeRight":' + writeRight + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }
    this.SOF_VerifyCode = function (code) {

        var json = '{"function":"SOF_VerifyCode", "deviceName":"' + _curDevName + '", "inData":"' + code + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_DeleteFile = function (fileName) {
        var json = '{"function":"SOF_DeleteFile", "deviceName":"' + _curDevName + '","fileName":"' + fileName + '"}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SetCrossAccess = function (crossAccess) {

        var json = '{"function":"SOF_SetCrossAccess", "deviceName":"' + _curDevName + '", "crossAccess":"' + crossAccess + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_SetLabel = function (deviceName, Label) {

        var json = '{"function":"SOF_SetLabel", "deviceName":"' + deviceName + '", "Label":"' + Label + '"}';
        try {
            AjaxIO(json);
        } catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    };

    this.SOF_GetFingerInfo = function (deviceName, userType) {
        var json = '{"function":"SOF_GetFingerInfo", "deviceName":"' + deviceName + '", "userType":' + userType + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }

    this.SOF_EnrollFinger = function (DeviceName, userType, ulFingerID) {
        var json = '{"function":"SOF_EnrollFinger", "deviceName":"' + DeviceName + '", "userType":' + userType + ', "FingerId":' + ulFingerID + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }
    this.SOF_DeleteFinger = function (DeviceName, userType, ulFingerID) {
        var json = '{"function":"SOF_DeleteFinger", "deviceName":"' + DeviceName + '", "userType":' + userType + ', "FingerId":' + ulFingerID + '}';
        try {
            AjaxIO(json);
        }
        catch (e) {
            return -3;
        }
        var ret = GetHttpResult();
        return ret;
    }


}
