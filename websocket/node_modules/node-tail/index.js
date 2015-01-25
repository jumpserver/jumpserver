var tail = require('./src/node-tail.js');

tail.run({
  port: 3000,
  file: process.argv[2]
});
