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
                    try{
                        var findResize = JSON.parse(data[timelist[pos]])['data'];
                        term.resize(findResize['resize']['cols'], findResize['resize']['rows'])
                    } catch (err) {
                        term.write(data[timelist[pos]]);
                    }
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

        var term = new Terminal({
            rows: 35,
            cols: 100,
            useStyle: true,
            screenKeys: true
        });
        var timelist = [];
        for (var i in data) {
            totalTime = Math.max(totalTime, i);
            timelist.push(i);
        }
        timelist = timelist.sort(function(a, b){return a-b});
        totalTime = totalTime * 1000;
        document.getElementById("afterScrubberText").innerHTML = buildTimeString(totalTime);
        term.open(document.getElementById('terminal'));
        timer = setInterval(advance, TICK);
    })

})