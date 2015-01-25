var defaults = {
  port: 4000
};

exports.run = function(options) {

  for (var prop in defaults) {
    if (options[prop] === undefined) {
      options[prop] = defaults[prop];
    }
  }

  var spawn = require('child_process').spawn,
    tail = spawn('tail', ['-f', options.file]);

  var app = require('http').createServer(function(req, res) {
    fs.readFile(__dirname + '/../view/index.html', function (err, data) {
      if (err) {
        res.writeHead(500);
        return res.end('Error loading index.html');
      }

      data = data.toString().replace(/{{port}}/g, options.port);

      res.writeHead(200);
      res.end(data);
    });
  });

  var io = require('socket.io').listen(app),
    fs = require('fs');

  io.set('log level', 1);

  io.sockets.on('connection', function (socket) {

    tail.stdout.on("data", function (data) {
      socket.emit('log', data.toString("utf8"));
    });

  });

  app.listen(options.port);

  console.log('listen %s on http://localhost:%s/', options.file, options.port);
}
