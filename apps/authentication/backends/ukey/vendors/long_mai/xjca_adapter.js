/* Caller-side adapter only. The existing Longmai driver and mToken API remain unchanged. */
function ExternalCertificateUKey(plugin) {
    var api = new mToken(plugin);
    var deviceName = '';
    var certificate = null;
    api.signingContainer = '';
    api.signingContainers = [];

    function clearCertificate() {
        certificate = null;
        api.signingContainer = '';
        api.signingContainers = [];
    }

    function currentDevice() {
        var devices = api.SOF_EnumDevice();
        if (!Array.isArray(devices) || devices.filter(Boolean).length !== 1) {
            deviceName = '';
            clearCertificate();
            throw new Error('Connect exactly one UKey');
        }
        return devices.filter(Boolean)[0];
    }

    function checkDevice() {
        if (currentDevice() !== deviceName) {
            clearCertificate();
            throw new Error('UKey changed; retry the operation');
        }
    }

    api.JMS_EnumDevice = function () {
        var name = currentDevice();
        if (name !== deviceName) clearCertificate();
        deviceName = name;
        return [name];
    };
    // Detection must not export certificates: some Keys require PIN login first.
    api.JMS_GetCachedCertificate = function () { return certificate; };
    api.JMS_Login = function (pin) {
        checkDevice();
        clearCertificate();
        return api.SOF_Login(pin);
    };
    api.JMS_ReadSigningCertificate = function () {
        checkDevice();
        certificate = null;
        var containers = api.SOF_EnumCertContiner();
        if (!Array.isArray(containers) || containers.length > 32) {
            clearCertificate();
            throw new Error('Cannot enumerate signing certificates');
        }
        var candidates = containers.filter(Boolean).map(function (name) {
            return { name: name, cert: api.SOF_ExportUserCert(name, 1) };
        }).filter(function (item) { return typeof item.cert === 'string' && item.cert.length > 0; });
        api.signingContainers = candidates.map(function (item) {
            var cn = api.SOF_GetCertInfo(item.cert, api.SGD_CERT_SUBJECT_CN) || '';
            return { name: item.name, label: cn ? cn + ' (' + item.name + ')' : item.name };
        });
        // A single certificate is unambiguous. With multiple certificates the
        // user must explicitly select one; never guess a vendor container name.
        if (!api.signingContainer && candidates.length === 1) api.signingContainer = candidates[0].name;
        var selected = candidates.find(function (item) { return item.name === api.signingContainer; });
        if (!selected) {
            api.signingContainer = '';
            return null;
        }
        certificate = selected.cert;
        return certificate;
    };
    return api;
}
