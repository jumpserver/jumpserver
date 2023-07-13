// content_script.js

const debug = console.log

// 创建一个 Mutation Observer 实例
const observer = new MutationObserver(function (mutationsList) {
    // 遍历每个发生变化的 mutation
    for (let mutation of mutationsList) {
        // 检查是否有节点添加
        if (mutation.type === 'childList') {
            // 获取所有的 <a> 标签元素
            const links = document.getElementsByTagName('a');

            // 遍历 <a> 标签元素并修改链接属性
            debug("开始替换标签")
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

document.addEventListener("contextmenu", function (event) {
    debug('On context')
    event.preventDefault();
});

const AllowedKeys = ['P', 'F', 'C', 'V']
window.addEventListener("keydown", function (e) {
    if (e.key === "F12" || (e.ctrlKey && !AllowedKeys.includes(e.key.toUpperCase()))) {
        e.preventDefault();
        e.stopPropagation();
        debug('Press key: ', e.ctrlKey ? 'Ctrl' : '', e.shiftKey ? ' Shift' : '', e.key)
    }
}, true);

// 修改 window.open 函数
window.open = function (url, target, features) {
    // 将 target 强制设置为 "_self"，使得新页面在当前标签页中打开
    target = "_self";
    debug('Open url: ', url, target, features)
    // 调用原始的 window.open 函数
    window.href = url
    // return originalOpen.call(this, url, target, features);
};
