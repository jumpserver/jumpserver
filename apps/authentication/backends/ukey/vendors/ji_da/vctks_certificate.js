/* Read only the signing certificate's SPKI. Core performs certificate verification. */
(function (root) {
    'use strict';

    root.VCTKSCertificateDigest = function (certificate) {
        function invalid() { throw new Error('Unsupported or invalid UKey signing certificate'); }
        if (typeof certificate !== 'string' || certificate.length > 32768) invalid();
        var encoded = certificate.replace(/\s/g, '');
        if (!/^[A-Za-z0-9+/]+={0,2}$/.test(encoded) || encoded.length % 4) invalid();
        var der = root.atob(encoded);
        if (!der.length || der.length > 16384) invalid();

        function node(offset, limit) {
            if (offset + 2 > limit) invalid();
            var tag = der.charCodeAt(offset++);
            var length = der.charCodeAt(offset++);
            if ((tag & 31) === 31) invalid();
            if (length & 128) {
                var count = length & 127;
                if (!count || count > 3 || offset + count > limit || !der.charCodeAt(offset)) invalid();
                length = 0;
                while (count--) length = length * 256 + der.charCodeAt(offset++);
                if (length < 128) invalid();
            }
            if (offset + length > limit) invalid();
            return { tag: tag, start: offset, end: offset + length };
        }

        function children(parent) {
            if (parent.tag !== 48) invalid();
            var result = [], offset = parent.start;
            while (offset < parent.end) {
                if (result.length >= 32) invalid();
                var child = node(offset, parent.end);
                result.push(child);
                offset = child.end;
            }
            return result;
        }

        function oid(part) {
            if (!part || part.tag !== 6) invalid();
            var hex = '';
            for (var i = part.start; i < part.end; i++) {
                hex += ('0' + der.charCodeAt(i).toString(16)).slice(-2);
            }
            return hex;
        }

        var outer = node(0, der.length);
        if (outer.end !== der.length) invalid();
        var cert = children(outer);
        if (cert.length !== 3 || cert[1].tag !== 48 || cert[2].tag !== 3) invalid();
        var tbs = children(cert[0]);
        var start = tbs[0] && tbs[0].tag === 160 ? 1 : 0;
        var tags = [2, 48, 48, 48, 48, 48];
        tags.forEach(function (tag, index) {
            if (!tbs[start + index] || tbs[start + index].tag !== tag) invalid();
        });
        var spki = children(tbs[start + 5]);
        if (spki.length !== 2 || spki[1].tag !== 3 || spki[1].end - spki[1].start < 2 ||
            der.charCodeAt(spki[1].start) !== 0) invalid();
        var algorithm = children(spki[0]);
        if (algorithm.length < 1 || algorithm.length > 2) invalid();
        var id = oid(algorithm[0]);
        var sm2 = '2a811ccf5501822d';
        if (id === '2a8648ce3d0201' && algorithm.length === 2 && oid(algorithm[1]) === sm2) return 1;
        if (algorithm.length === 2 &&
            (algorithm[1].tag !== 5 || algorithm[1].start !== algorithm[1].end)) invalid();
        if (id === sm2) return 1;
        if (id === '2a864886f70d010101') return 4;
        invalid();
    };
}(window));
