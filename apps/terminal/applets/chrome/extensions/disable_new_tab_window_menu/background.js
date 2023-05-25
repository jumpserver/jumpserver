// background.js

// 监听标签页的创建事件
chrome.tabs.onCreated.addListener(function (tab) {
    // 获取当前窗口的所有标签页
    chrome.tabs.query({currentWindow: true}, function (tabs) {
        // 如果当前窗口的标签页数量大于1，则关闭新创建的标签页
        if (tabs.length > 1) {
            chrome.tabs.remove(tab.id);
        }
    });
});

document.addEventListener("contextmenu", function (event) {
    event.preventDefault();
});
