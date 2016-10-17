/*
WSSH Javascript Client

Usage:

var client = new WSSHClient();

client.connect({
    // Connection and authentication parameters
    username: 'root',
    hostname: 'localhost',
    authentication_method: 'password', // can either be password or private_key
    password: 'secretpassword', // do not provide when using private_key
    key_passphrase: 'secretpassphrase', // *may* be provided if the private_key is encrypted

    // Callbacks
    onError: function(error) {
        // Called upon an error
        console.error(error);
    },
    onConnect: function() {
        // Called after a successful connection to the server
        console.debug('Connected!');

        client.send('ls\n'); // You can send data back to the server by using WSSHClient.send()
    },
    onClose: function() {
        // Called when the remote closes the connection
        console.debug('Connection Reset By Peer');
    },
    onData: function(data) {
        // Called when data is received from the server
        console.debug('Received: ' + data);
    }
});

*/

function WSSHClient() {
}

WSSHClient.prototype._generateEndpoint = function(options) {
    console.log(options);
    if (window.location.protocol == 'https:') {
        var protocol = 'wss://';
    } else {
        var protocol = 'ws://';
    }

    var endpoint = protocol + window.location.host + ':8080' + '/terminal';
    return endpoint;
};

WSSHClient.prototype.connect = function(options) {
    var endpoint = this._generateEndpoint(options);

    if (window.WebSocket) {
        this._connection = new WebSocket(endpoint);
    }
    else if (window.MozWebSocket) {
        this._connection = MozWebSocket(endpoint);
    }
    else {
        options.onError('WebSocket Not Supported');
        return ;
    }

    this._connection.onopen = function() {
        options.onConnect();
    };

    this._connection.onmessage = function (evt) {
        var data = JSON.parse(evt.data.toString());
        if (data.error !== undefined) {
            options.onError(data.error);
        }
        else {
            options.onData(data.data);
        }
    };

    this._connection.onclose = function(evt) {
        options.onClose();
    };
};

WSSHClient.prototype.send = function(data) {
    this._connection.send(JSON.stringify({'data': data}));
};
