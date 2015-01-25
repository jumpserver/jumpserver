var Blob = require('../');
var expect = require('expect.js');

if (!Blob) {
  return;
}

describe('blob', function() {
  it('should encode a proper sized blob when given a string argument', function() {
    var b = new Blob(['hi']);
    expect(b.size).to.be(2);
  });

  it('should encode a blob with proper size when given two strings as arguments', function() {
    var b = new Blob(['hi', 'hello']);
    expect(b.size).to.be(7);
  });

  it('should encode arraybuffers with right content', function() {
    var ary = new Uint8Array(5);
    for (var i = 0; i < 5; i++) ary[i] = i;
    var b = new Blob([ary.buffer]);
    var fr = new FileReader();
    fr.onload = function() {
      var newAry = new Uint8Array(this.result);
      for (var i = 0; i < 5; i++) expect(newAry[i]).to.be(i);
    };
  });

  it('should encode with blobs', function() {
    var ary = new Uint8Array(5);
    for (var i = 0; i < 5; i++) ary[i] = i;
    var b = new Blob([new Blob([ary.buffer])]);
    var fr = new FileReader();
    fr.onload = function() {
      var newAry = new Uint8Array(this.result);
      for (var i = 0; i < 5; i++) expect(newAry[i]).to.be(i);
    };
  });

  it('should enode mixed contents to right size', function() {
    var ary = new Uint8Array(5);
    for (var i = 0; i < 5; i++) ary[i] = i;
    var b = new Blob([ary.buffer, 'hello']);
    expect(b.size).to.be(10);
  });

  it('should accept mime type', function() {
    var b = new Blob(['hi', 'hello'], { type: 'text/html' });
    expect(b.type).to.be('text/html');
  });
});
