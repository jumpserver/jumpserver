function fillKey(key) {
    const keyLength = 16
    if (key.length > keyLength) {
        key = key.slice(0, keyLength)
    }
    const filledKey = Buffer.alloc(keyLength)
    const keys = Buffer.from(key)
    for (let i = 0; i < keys.length; i++) {
        filledKey[i] = keys[i]
    }
    return filledKey
}

function aesEncrypt(text, originKey) {
    const key = CryptoJS.enc.Utf8.parse(fillKey(originKey));
    return CryptoJS.AES.encrypt(text, key, {
        mode: CryptoJS.mode.ECB,
        padding: CryptoJS.pad.ZeroPadding
    }).toString();
}

function rsaEncrypt(text, pubKey) {
    if (!text) {
        return text
    }
    const jsEncrypt = new JSEncrypt();
    jsEncrypt.setPublicKey(pubKey);
    return jsEncrypt.encrypt(text);
}

function rsaDecrypt(cipher, pkey) {
    const jsEncrypt = new JSEncrypt();
    jsEncrypt.setPrivateKey(pkey);
    return jsEncrypt.decrypt(cipher)
}


window.rsaEncrypt = rsaEncrypt
window.rsaDecrypt = rsaDecrypt

function hexToBytes(hex) {
    if (!hex) return new Uint8Array([])
    hex = hex.toString().trim().toLowerCase()
    if (hex.startsWith('0x')) {
        hex = hex.slice(2)
    }
    // 确保是偶数长度
    const len = Math.floor(hex.length / 2)
    const bytes = new Uint8Array(len)
    for (let i = 0; i < len; i++) {
        bytes[i] = parseInt(hex.substr(i * 2, 2), 16)
    }
    return bytes
}

function bytesToBase64(bytes) {
    // Uint8Array -> base64（标准 base64）
    let binary = ''
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
}

function rsaEncryptPassword(password,  rsaPublicKey) {
    const aesKey = (Math.random() + 1).toString(36).substring(2)
    // public key 是 base64 存储的
    const keyCipher = rsaEncrypt(aesKey, rsaPublicKey)
    const passwordCipher = aesEncrypt(password, aesKey)
    return `${keyCipher}:${passwordCipher}`
}

function ensureSm2PublicKey(sm2PublicKey) {
    // sm2.min.js 的 doEncrypt 需要能被 decodePointHex 解析的公钥：
    // 通常为非压缩点 hex，格式 `04||x||y`（总长度 130）。
    // 但后端生成/下发的公钥有时是 `x||y`（长度 128），这里做归一化补齐 `04` 前缀。
    if (typeof sm2PublicKey === 'string') {
        sm2PublicKey = sm2PublicKey.replaceAll('"', '').trim()
        if (sm2PublicKey.startsWith('0x')) {
            sm2PublicKey = sm2PublicKey.slice(2)
        }
        // 后端下发的 SM2 公钥常见是 x||y（128 hex），sm-crypto 需要 04||x||y（130 hex）
        if (sm2PublicKey.length === 128 && !sm2PublicKey.startsWith('04')) {
            sm2PublicKey = '04' + sm2PublicKey
        }
    }
    return sm2PublicKey
}


function gmEncryptPassword(password,  sm2PublicKey) {
    sm2PublicKey = ensureSm2PublicKey(sm2PublicKey)
    // 只适配前端，不改后端：
    // 直接生成 16 字符 key（后端 padding_key 会保持原样，不再补齐）
    const sm4KeyRaw = randomString(16)
    const sm4KeyHex = Buffer.from(sm4KeyRaw).toString('hex')

    let keyCipher = ''
    try {
        // 与后端 gmssl.sm2.CryptSM2 默认 decrypt 的 mode 对齐：
        // gmssl 解析的格式是 C1C2C3（mode=0），前端这里输出也用 mode=0。
        keyCipher = sm2.doEncrypt(sm4KeyRaw, sm2PublicKey, 0)
    } catch (e) {
        console.error('gmEncryptPassword sm2.doEncrypt failed:', e)
        // 避免前端崩溃：失败时返回明文，由后端按原值流程处理（至少可继续登录/看报错）
        return password
    }

    const passwordCipher = sm4.encrypt(password, sm4KeyHex)
    // sm2/sm4 默认输出是 hex，但后端 gm.py/session.py 需要 base64：
    // - sm2_decrypt: base64.b64decode
    // - sm4 decrypt: base64.urlsafe_b64decode
    const keyCipherB64 = bytesToBase64(hexToBytes(keyCipher))
    const passwordCipherB64 = bytesToBase64(hexToBytes(passwordCipher))
    return `${keyCipherB64}:${passwordCipherB64}`
}


function encryptPassword(password) {
    if (!password) {
        console.log('password is empty')
        return ''
    }
    if (typeof password === 'number') {
        password = password.toString()
    }
    let publicKeyText = getCookie('jms_public_key')
    if (!publicKeyText) {
        console.log('publicKeyText is empty')
        return password
    }
    publicKeyText = publicKeyText.replaceAll('"', '')
    publicKeyText = atob(publicKeyText)
    let cipher = ''
    let jmsGMSSL = getCookie('jms_gm_ssl')
    if (publicKeyText.includes('PUBLIC KEY')) {
        jmsGMSSL = '0'
    }
    if (jmsGMSSL === '1') {
        cipher = gmEncryptPassword(password, publicKeyText)
    } else {
        cipher = rsaEncryptPassword(password, publicKeyText)
    }
    
    return cipher
}


function randomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }

    return result;
}

function testEncrypt() {
    const radio = []
    const len2 = []
    for (let i = 1; i < 4096; i++) {
        const password = randomString(i)
        const cipher = encryptPassword(password)
        len2.push([password.length, cipher.length])
        radio.push(cipher.length / password.length)
    }
    return radio
}

window.encryptPassword = encryptPassword
