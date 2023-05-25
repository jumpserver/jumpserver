// content_script.js

// 获取所有的 <a> 标签元素
const links = document.getElementsByTagName('a');

// 遍历 <a> 标签元素并修改链接属性
for (let i = 0; i < links.length; i++) {
    links[i].target = '_self'; // 将 target 属性设置为 _self，当前窗口打开
}

chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        $("iframe").attr("src", request.url);
        sendResponse({farewell: "goodbye"});
    }
)

document.addEventListener("contextmenu", function (event) {
    event.preventDefault();
});

chrome.runtime.sendMessage({greeting: "hello"}, function (response) {
});
