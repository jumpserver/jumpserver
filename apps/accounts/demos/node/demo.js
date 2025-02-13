const axios = require('axios');
const crypto = require('crypto');
const moment = require('moment');

const API_URL = process.env.API_URL || "http://127.0.0.1:8080";
const KEY_ID = process.env.API_KEY_ID || "72b0b0aa-ad82-4182-a631-ae4865e8ae0e";
const KEY_SECRET = process.env.API_KEY_SECRET || "6fuSO7P1m4cj8SSlgaYdblOjNAmnxDVD7tr8";
const ORG_ID = process.env.ORG_ID || "00000000-0000-0000-0000-000000000002";

class APIClient {
    constructor() {
        this.apiUrl = API_URL;
        this.keyId = KEY_ID;
        this.keySecret = KEY_SECRET;
        this.orgId = ORG_ID;
    }

    signRequest(method, url, params, headers) {
        const date = moment().utc().format('ddd, DD MMM YYYY HH:mm:ss [GMT]');
        const queryString = Object.keys(params).length ? `?${new URLSearchParams(params).toString()}` : "";
        const requestTarget = `${method.toLowerCase()} ${url}${queryString}`;
        headers['Date'] = date;
        headers['X-JMS-ORG'] = this.orgId;
        const signingString = `(request-target): ${requestTarget}\naccept: application/json\ndate: ${date}\nx-jms-org: ${this.orgId}`;
        const signature = crypto.createHmac('sha256', this.keySecret).update(signingString).digest('base64');
        headers['Authorization'] = `Signature keyId="${this.keyId}",algorithm="hmac-sha256",headers="(request-target) accept date x-jms-org",signature="${signature}"`;
    }

    async getAccountSecret(asset, account) {
        const url = `/api/v1/accounts/integration-applications/account-secret/`;
        const params = { asset: asset, account: account };
        const headers = {
            'Accept': 'application/json',
            'X-Source': 'jms-pam'
        };
        this.signRequest('GET', url, params, headers);

        try {
            const response = await axios.get(`${this.apiUrl}${url}`, {
                headers: headers,
                params: params,
                timeout: 10000
            });
            return response.data;
        } catch (error) {
            console.error(`API 请求失败: ${error}`);
            return null;
        }
    }
}

(async () => {
    const client = new APIClient();
    const result = await client.getAccountSecret("ubuntu_docker", "root");
    console.log(result);
})();
