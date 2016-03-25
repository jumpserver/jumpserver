/**
 * Created by liuzheng on 3/25/16.
 */
'use strict';

var NgApp = angular.module('NgApp', ['ngRoute']);
NgApp.config(['$httpProvider', function ($httpProvider) {
    $httpProvider.defaults.transformRequest = function (obj) {
        var str = [];
        for (var p in obj) {
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(obj[p]));
        }
        return str.join("&");
    };
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    $httpProvider.defaults.headers.post = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
}]);
NgApp.controller('TerminalRecordCtrl', function ($scope, $http) {
    $http.post(window.location.href).success(function (data) {
        var toggle = true;
        var totalTime = 0;
        var TICK = 33;
        var TIMESTEP = 33;
        var time = 33;
        var timer;
        var pos = 0;

        // Thanks http://stackoverflow.com/a/2998822
        function zeroPad(num, size) {
            var s = "0" + num;
            return s.substr(s.length - size);
        }

        $scope.scrub = function () {
            var setPercent = document.getElementById('scrubber').value;
            time = (setPercent / 100) * totalTime;
            $scope.restart(time);
        };

        function buildTimeString(millis) {
            var hours = zeroPad(Math.floor(millis / (1000 * 60 * 60)), 2);
            millis -= hours * (1000 * 60 * 60);
            var minutes = zeroPad(Math.floor(millis / (1000 * 60)), 2);
            millis -= minutes * (1000 * 60);
            var seconds = zeroPad(Math.floor(millis / 1000), 2);
            return hours + ':' + minutes + ':' + seconds;
        }

        function advance() {
            document.getElementById('scrubber').value =
                Math.ceil((time / totalTime) * 100);
            document.getElementById("beforeScrubberText").innerHTML = buildTimeString(time);
            for (; pos < timelist.length; pos++) {
                if (timelist[pos] * 1000 <= time) {
                    term.write(data[timelist[pos]]);
                } else {
                    break;
                }
            }

            if (pos >= timelist.length) {
                clearInterval(timer);
            }

            time += TIMESTEP;
        }

        $scope.pause = function (test) {
            if (!toggle && test) {
                return;
            }
            if (toggle) {
                clearInterval(timer);
                toggle = !toggle;
            } else {
                timer = setInterval(advance, TICK);
                toggle = !toggle;
            }
        };

        $scope.setSpeed = function () {
            var speed = document.getElementById('speed').value;
            if (speed == 0) {
                TIMESTEP = TICK;
            } else if (speed < 0) {
                TIMESTEP = TICK / -speed;
            } else {
                TIMESTEP = TICK * speed;
            }
        };

        $scope.restart = function (millis) {
            clearInterval(timer);
            term.reset();
            time = millis;
            pos = 0;
            toggle = true;
            timer = setInterval(advance, TICK);
        };

        var rc = textSize();
        var term = new Terminal({
            rows: rc.y,
            cols: rc.x,
            useStyle: true,
            screenKeys: true
        });
        var timelist = [];
        for (var i in data) {
            totalTime = totalTime > i ? totalTime : i;
            timelist.push(i);
        }
        timelist = timelist.sort();
        totalTime = totalTime * 1000;
        document.getElementById("afterScrubberText").innerHTML = buildTimeString(totalTime);
        term.open(document.getElementById('terminal'));
        timer = setInterval(advance, TICK);
    })

})

function textSize() {
    var charSize = getCharSize();
    var windowSize = getwindowSize();
    var size = {
        x: Math.floor(windowSize.width / charSize.width)
        , y: Math.floor(windowSize.height / charSize.height)
    };
    if (size.x > 150)size.x = 150;
    if (size.y > 35)size.y = 35;
    size.x = 140;
    size.y = 30;
    return size;
}
function getCharSize() {
    var $span = $("<span>", {text: "qwertyuiopasdfghjklzxcvbnm"});
    $('body').append($span);
    var size = {
        width: $span.outerWidth() / 30
        , height: $span.outerHeight() * 1.1
    };
    $span.remove();
    return size;
}
function getwindowSize() {
    var e = window,
        a = 'inner';
    if (!('innerWidth' in window )) {
        a = 'client';
        e = document.documentElement || document.body;
    }
    return {width: e[a + 'Width'] - 300, height: e[a + 'Height'] - 120};
}
