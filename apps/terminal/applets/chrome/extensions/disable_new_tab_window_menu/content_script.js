// content_script.js

// 获取所有的 <a> 标签元素
const links = document.getElementsByTagName('a');

// 遍历 <a> 标签元素并修改链接属性
for (let i = 0; i < links.length; i++) {
    links[i].target = '_self'; // 将 target 属性设置为 _self，当前窗口打开
}


chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        console.log(request.url);
        $("iframe").attr("src", request.url);
        sendResponse({farewell: "goodbye"});
    }
)

document.addEventListener("contextmenu", function (event) {
    console.log('On contextmenu event')
    event.preventDefault();
});

var AllowedKeys = ['P', 'F', 'p', 'f']
window.addEventListener("keydown", function (e) {
    if (e.key === "F12" || (e.ctrlKey && !AllowedKeys.includes(e.key))) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Press key: ', e.ctrlKey ? 'Ctrl' : '', e.shiftKey ? ' Shift' : '', e.key)
    }
}, true);


chrome.runtime.sendMessage({greeting: "hello"}, function (response) {
});
