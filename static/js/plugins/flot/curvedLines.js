/* The MIT License

 Copyright (c) 2011 by Michael Zinsmaier and nergal.dev
 Copyright (c) 2012 by Thomas Ritou

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
 */

/*

 ____________________________________________________

 what it is:
 ____________________________________________________

 curvedLines is a plugin for flot, that tries to display lines in a smoother way.
 The plugin is based on nergal.dev's work https://code.google.com/p/flot/issues/detail?id=226
 and further extended with a mode that forces the min/max points of the curves to be on the
 points. Both modes are achieved through adding of more data points
 => 1) with large data sets you may get trouble
 => 2) if you want to display the points too, you have to plot them as 2nd data series over the lines

 && 3) consecutive x data points are not allowed to have the same value

 This is version 0.5 of curvedLines so it will probably not work in every case. However
 the basic form of use descirbed next works (:

 Feel free to further improve the code

 ____________________________________________________

 how to use it:
 ____________________________________________________

 var d1 = [[5,5],[7,3],[9,12]];

 var options = { series: { curvedLines: {  active: true }}};

 $.plot($("#placeholder"), [{data = d1, lines: { show: true}, curvedLines: {apply: true}}], options);

 _____________________________________________________

 options:
 _____________________________________________________

 active:           bool true => plugin can be used
 apply:            bool true => series will be drawn as curved line
 fit:              bool true => forces the max,mins of the curve to be on the datapoints
 curvePointFactor  int  defines how many "virtual" points are used per "real" data point to
 emulate the curvedLines (points total = real points * curvePointFactor)
 fitPointDist:     int  defines the x axis distance of the additional two points that are used
 to enforce the min max condition.

 + line options (since v0.5 curved lines use flots line implementation for drawing
 => line options like fill, show ... are supported out of the box)

 */

/*
 *  v0.1   initial commit
 *  v0.15  negative values should work now (outcommented a negative -> 0 hook hope it does no harm)
 *  v0.2   added fill option (thanks to monemihir) and multi axis support (thanks to soewono effendi)
 *  v0.3   improved saddle handling and added basic handling of Dates
 *  v0.4   rewritten fill option (thomas ritou) mostly from original flot code (now fill between points rather than to graph bottom), corrected fill Opacity bug
 *  v0.5   rewritten instead of implementing a own draw function CurvedLines is now based on the processDatapoints flot hook (credits go to thomas ritou).
 * 		   This change breakes existing code however CurvedLines are now just many tiny straight lines to flot and therefore all flot lines options (like gradient fill,
 * 	       shadow) are now supported out of the box
 *  v0.6   flot 0.8 compatibility and some bug fixes
 */

(function($) {

    var options = {
        series : {
            curvedLines : {
                active : false,
                apply: false,
                fit : false,
                curvePointFactor : 20,
                fitPointDist : undefined
            }
        }
    };

    function init(plot) {

        plot.hooks.processOptions.push(processOptions);

        //if the plugin is active register processDatapoints method
        function processOptions(plot, options) {
            if (options.series.curvedLines.active) {
                plot.hooks.processDatapoints.unshift(processDatapoints);
            }
        }

        //only if the plugin is active
        function processDatapoints(plot, series, datapoints) {
            var nrPoints = datapoints.points.length / datapoints.pointsize;
            var EPSILON = 0.5; //pretty large epsilon but save

            if (series.curvedLines.apply == true && series.originSeries === undefined && nrPoints > (1 + EPSILON)) {
                if (series.lines.fill) {

                    var pointsTop = calculateCurvePoints(datapoints, series.curvedLines, 1)
                        ,pointsBottom = calculateCurvePoints(datapoints, series.curvedLines, 2); //flot makes sure for us that we've got a second y point if fill is true !

                    //Merge top and bottom curve
                    datapoints.pointsize = 3;
                    datapoints.points = [];
                    var j = 0;
                    var k = 0;
                    var i = 0;
                    var ps = 2;
                    while (i < pointsTop.length || j < pointsBottom.length) {
                        if (pointsTop[i] == pointsBottom[j]) {
                            datapoints.points[k] = pointsTop[i];
                            datapoints.points[k + 1] = pointsTop[i + 1];
                            datapoints.points[k + 2] = pointsBottom[j + 1];
                            j += ps;
                            i += ps;

                        } else if (pointsTop[i] < pointsBottom[j]) {
                            datapoints.points[k] = pointsTop[i];
                            datapoints.points[k + 1] = pointsTop[i + 1];
                            datapoints.points[k + 2] = k > 0 ? datapoints.points[k-1] : null;
                            i += ps;
                        } else {
                            datapoints.points[k] = pointsBottom[j];
                            datapoints.points[k + 1] = k > 1 ? datapoints.points[k-2] : null;
                            datapoints.points[k + 2] = pointsBottom[j + 1];
                            j += ps;
                        }
                        k += 3;
                    }
                } else if (series.lines.lineWidth > 0) {
                    datapoints.points = calculateCurvePoints(datapoints, series.curvedLines, 1);
                    datapoints.pointsize = 2;
                }
            }
        }

        //no real idea whats going on here code mainly from https://code.google.com/p/flot/issues/detail?id=226
        //if fit option is selected additional datapoints get inserted before the curve calculations in nergal.dev s code.
        function calculateCurvePoints(datapoints, curvedLinesOptions, yPos) {

            var points = datapoints.points, ps = datapoints.pointsize;
            var num = curvedLinesOptions.curvePointFactor * (points.length / ps);

            var xdata = new Array;
            var ydata = new Array;

            var curX = -1;
            var curY = -1;
            var j = 0;

            if (curvedLinesOptions.fit) {
                //insert a point before and after the "real" data point to force the line
                //to have a max,min at the data point.

                var fpDist;
                if(typeof curvedLinesOptions.fitPointDist == 'undefined') {
                    //estimate it
                    var minX = points[0];
                    var maxX = points[points.length-ps];
                    fpDist = (maxX - minX) / (500 * 100); //x range / (estimated pixel length of placeholder * factor)
                } else {
                    //use user defined value
                    fpDist = curvedLinesOptions.fitPointDist;
                }

                for (var i = 0; i < points.length; i += ps) {

                    var frontX;
                    var backX;
                    curX = i;
                    curY = i + yPos;

                    //add point X s
                    frontX = points[curX] - fpDist;
                    backX = points[curX] + fpDist;

                    var factor = 2;
                    while (frontX == points[curX] || backX == points[curX]) {
                        //inside the ulp
                        frontX = points[curX] - (fpDist * factor);
                        backX = points[curX] + (fpDist * factor);
                        factor++;
                    }

                    //add curve points
                    xdata[j] = frontX;
                    ydata[j] = points[curY];
                    j++;

                    xdata[j] = points[curX];
                    ydata[j] = points[curY];
                    j++;

                    xdata[j] = backX;
                    ydata[j] = points[curY];
                    j++;
                }
            } else {
                //just use the datapoints
                for (var i = 0; i < points.length; i += ps) {
                    curX = i;
                    curY = i + yPos;

                    xdata[j] = points[curX];
                    ydata[j] = points[curY];
                    j++;
                }
            }

            var n = xdata.length;

            var y2 = new Array();
            var delta = new Array();
            y2[0] = 0;
            y2[n - 1] = 0;
            delta[0] = 0;

            for (var i = 1; i < n - 1; ++i) {
                var d = (xdata[i + 1] - xdata[i - 1]);
                if (d == 0) {
                    //point before current point and after current point need some space in between
                    return [];
                }

                var s = (xdata[i] - xdata[i - 1]) / d;
                var p = s * y2[i - 1] + 2;
                y2[i] = (s - 1) / p;
                delta[i] = (ydata[i + 1] - ydata[i]) / (xdata[i + 1] - xdata[i]) - (ydata[i] - ydata[i - 1]) / (xdata[i] - xdata[i - 1]);
                delta[i] = (6 * delta[i] / (xdata[i + 1] - xdata[i - 1]) - s * delta[i - 1]) / p;
            }

            for (var j = n - 2; j >= 0; --j) {
                y2[j] = y2[j] * y2[j + 1] + delta[j];
            }

            //   xmax  - xmin  / #points
            var step = (xdata[n - 1] - xdata[0]) / (num - 1);

            var xnew = new Array;
            var ynew = new Array;
            var result = new Array;

            xnew[0] = xdata[0];
            ynew[0] = ydata[0];

            result.push(xnew[0]);
            result.push(ynew[0]);

            for ( j = 1; j < num; ++j) {
                //new x point (sampling point for the created curve)
                xnew[j] = xnew[0] + j * step;

                var max = n - 1;
                var min = 0;

                while (max - min > 1) {
                    var k = Math.round((max + min) / 2);
                    if (xdata[k] > xnew[j]) {
                        max = k;
                    } else {
                        min = k;
                    }
                }

                //found point one to the left and one to the right of generated new point
                var h = (xdata[max] - xdata[min]);

                if (h == 0) {
                    //similar to above two points from original x data need some space between them
                    return [];
                }

                var a = (xdata[max] - xnew[j]) / h;
                var b = (xnew[j] - xdata[min]) / h;

                ynew[j] = a * ydata[min] + b * ydata[max] + ((a * a * a - a) * y2[min] + (b * b * b - b) * y2[max]) * (h * h) / 6;

                result.push(xnew[j]);
                result.push(ynew[j]);
            }

            return result;
        }

    }//end init

    $.plot.plugins.push({
        init : init,
        options : options,
        name : 'curvedLines',
        version : '0.5'
    });

})(jQuery);
