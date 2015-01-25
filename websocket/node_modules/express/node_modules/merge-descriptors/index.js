module.exports = function (dest, src) {
  Object.getOwnPropertyNames(src).forEach(function (name) {
    var descriptor = Object.getOwnPropertyDescriptor(src, name)
    Object.defineProperty(dest, name, descriptor)
  })

  return dest
}