// content_script.js

// 创建一个 Mutation Observer 实例
const observer = new MutationObserver(function (mutationsList) {
    // 遍历每个发生变化的 mutation
    for (let mutation of mutationsList) {
        // 检查是否有节点添加
        if (mutation.type === 'childList') {
            // 获取所有的 <a> 标签元素
            const links = document.getElementsByTagName('a');

            // 遍历 <a> 标签元素并修改链接属性
            console.log("开始替换标签")
            for (let i = 0; i < links.length; i++) {
                links[i].target = '_self'; // 将 target 属性设置为 _self，当前窗口打开
            }

            // 停止监听，已经完成替换操作
            observer.disconnect();

            // 退出循环，不再处理后续的 mutations
            break;
        }
    }
});

// 开始观察 document.body 的子节点变化
observer.observe(document.body, {childList: true, subtree: true});

chrome.runtime.onMessage.addListener(
    function (request, sender, sendResponse) {
        console.log(request.url);
        $("iframe").attr("src", request.url);
        sendResponse({farewell: "goodbye"});
    }
)

document.addEventListener("contextmenu", function (event) {
    console.log('On context')
    event.preventDefault();
});

var AllowedKeys = ['P', 'F', 'C', 'V']
window.addEventListener("keydown", function (e) {
    if (e.key === "F12" || (e.ctrlKey && !AllowedKeys.includes(e.key.toUpperCase()))) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Press key: ', e.ctrlKey ? 'Ctrl' : '', e.shiftKey ? ' Shift' : '', e.key)
    }
}, true);

// 保存原始的 window.open 函数引用
var originalOpen = window.open;

// 修改 window.open 函数
window.open = function (url, target, features) {
    // 将 target 强制设置为 "_self"，使得新页面在当前标签页中打开
    target = "_self";

    // 修改当前页面的 URL
    location.href = url;

    // 调用原始的 window.open 函数
    return originalOpen.call(this, url, target, features);
};


chrome.runtime.sendMessage({greeting: "hello"}, function (response) {
});
