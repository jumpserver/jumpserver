var app = require('express')();
var http = require('http').Server(app);
var io = require('socket.io')(http);
var spawn = require('child_process').spawn;



var Tail = require('tail').Tail;


app.get('/', function(req, res){
    res.send('<h1>Welcome Realtime Server</h1>');
});

//在线用户
var onlineUsers = {};
//当前在线人数
var onlineCount = 0;

io.on('connection', function(socket){
    console.log('a user connected');

    //监听新用户加入
    socket.on('login', function(obj){
        //将新加入用户的唯一标识当作socket的名称，后面退出的时候会用到
        socket.name = obj.userid;
        socket.fileName = obj.filename;
        var  tail = new Tail(obj.filename);
	console.log(obj.filename);
        tail.on('line',function(data) {
            console.log(data);
           var newData = {userid:obj.userid,username:obj.username,content:data};
            socket.emit('message',newData);
        });
//        var tail = spawn("tail", ['-f', obj.filename]);
//        tail.stdout.on('data',function(data){
//            var content = data.toString();
//            console.log(content);
//            var newData = {userid:obj.userid,username:obj.username,content:content};
//            socket.emit('message',newData);
//        });


        socket.tail = tail;

        //检查在线列表，如果不在里面就加入
        if(!onlineUsers.hasOwnProperty(obj.userid)) {
            onlineUsers[obj.userid] = obj.username;
            //在线人数+1
            onlineCount++;
        }

        //向所有客户端广播用户加入
        io.emit('login', {onlineUsers:onlineUsers, onlineCount:onlineCount, user:obj});
        console.log(obj.username+'加入了聊天室');
    });

    //监听用户退出
    socket.on('disconnect', function(){
        //将退出的用户从在线列表中删除
        if(onlineUsers.hasOwnProperty(socket.name)) {
            //退出用户的信息
            var obj = {userid:socket.name, username:onlineUsers[socket.name]};

            if( socket.tail){
                socket.tail.unwatch();
            }

            //删除
            delete onlineUsers[socket.name];
            //在线人数-1
            onlineCount--;

            //向所有客户端广播用户退出
            io.emit('logout', {onlineUsers:onlineUsers, onlineCount:onlineCount, user:obj});
            console.log(obj.username+'退出了聊天室');
        }
    });

    //监听用户发布聊天内容
    socket.on('message', function(obj){
        //向所有客户端广播发布的消息
        io.emit('message', obj);
        socket.emit('message',obj);
        //console.log(obj.username+'说：'+obj.content);
    });

});

http.listen(3000, function(){
    console.log('listening on *:3000');
});
