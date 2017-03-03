/**
 * @license  Highcharts JS v4.0.1 (2014-04-24)
 * Solid angular gauge module
 *
 * (c) 2010-2014 Torstein Honsi
 *
 * License: www.highcharts.com/license
 */

/*global Highcharts*/
(function (H) {
	"use strict";

	var defaultPlotOptions = H.getOptions().plotOptions,
		pInt = H.pInt,
		pick = H.pick,
		each = H.each,
		colorAxisMethods,
		UNDEFINED;

	// The default options
	defaultPlotOptions.solidgauge = H.merge(defaultPlotOptions.gauge, {
		colorByPoint: true
	});


	// These methods are defined in the ColorAxis object, and copied here.
	// If we implement an AMD system we should make ColorAxis a dependency.
	colorAxisMethods = {


		initDataClasses: function (userOptions) {
			var axis = this,
				chart = this.chart,
				dataClasses,
				colorCounter = 0,
				options = this.options;
			this.dataClasses = dataClasses = [];

			each(userOptions.dataClasses, function (dataClass, i) {
				var colors;

				dataClass = H.merge(dataClass);
				dataClasses.push(dataClass);
				if (!dataClass.color) {
					if (options.dataClassColor === 'category') {
						colors = chart.options.colors;
						dataClass.color = colors[colorCounter++];
						// loop back to zero
						if (colorCounter === colors.length) {
							colorCounter = 0;
						}
					} else {
						dataClass.color = axis.tweenColors(H.Color(options.minColor), H.Color(options.maxColor), i / (userOptions.dataClasses.length - 1));
					}
				}
			});
		},

		initStops: function (userOptions) {
			this.stops = userOptions.stops || [
				[0, this.options.minColor],
				[1, this.options.maxColor]
			];
			each(this.stops, function (stop) {
				stop.color = H.Color(stop[1]);
			});
		},
		/** 
		 * Translate from a value to a color
		 */
		toColor: function (value, point) {
			var pos,
				stops = this.stops,
				from,
				to,
				color,
				dataClasses = this.dataClasses,
				dataClass,
				i;

			if (dataClasses) {
				i = dataClasses.length;
				while (i--) {
					dataClass = dataClasses[i];
					from = dataClass.from;
					to = dataClass.to;
					if ((from === UNDEFINED || value >= from) && (to === UNDEFINED || value <= to)) {
						color = dataClass.color;
						if (point) {
							point.dataClass = i;
						}
						break;
					}   
				}

			} else {

				if (this.isLog) {
					value = this.val2lin(value);
				}
				pos = 1 - ((this.max - value) / (this.max - this.min));
				i = stops.length;
				while (i--) {
					if (pos > stops[i][0]) {
						break;
					}
				}
				from = stops[i] || stops[i + 1];
				to = stops[i + 1] || from;

				// The position within the gradient
				pos = 1 - (to[0] - pos) / ((to[0] - from[0]) || 1);
				
				color = this.tweenColors(
					from.color, 
					to.color,
					pos
				);
			}
			return color;
		},
		tweenColors: function (from, to, pos) {
			// Check for has alpha, because rgba colors perform worse due to lack of
			// support in WebKit.
			var hasAlpha = (to.rgba[3] !== 1 || from.rgba[3] !== 1);

			if (from.rgba.length === 0 || to.rgba.length === 0) {
				return 'none';
			}
			return (hasAlpha ? 'rgba(' : 'rgb(') + 
				Math.round(to.rgba[0] + (from.rgba[0] - to.rgba[0]) * (1 - pos)) + ',' + 
				Math.round(to.rgba[1] + (from.rgba[1] - to.rgba[1]) * (1 - pos)) + ',' + 
				Math.round(to.rgba[2] + (from.rgba[2] - to.rgba[2]) * (1 - pos)) + 
				(hasAlpha ? (',' + (to.rgba[3] + (from.rgba[3] - to.rgba[3]) * (1 - pos))) : '') + ')';
		}
	};

	// The series prototype
	H.seriesTypes.solidgauge = H.extendClass(H.seriesTypes.gauge, {
		type: 'solidgauge',

		bindAxes: function () {
			var axis;
			H.seriesTypes.gauge.prototype.bindAxes.call(this);

			axis = this.yAxis;
			H.extend(axis, colorAxisMethods);

			// Prepare data classes
			if (axis.options.dataClasses) {
				axis.initDataClasses(axis.options);
			}
			axis.initStops(axis.options);
		},

		/**
		 * Draw the points where each point is one needle
		 */
		drawPoints: function () {
			var series = this,
				yAxis = series.yAxis,
				center = yAxis.center,
				options = series.options,
				renderer = series.chart.renderer;

			H.each(series.points, function (point) {
				var graphic = point.graphic,
					rotation = yAxis.startAngleRad + yAxis.translate(point.y, null, null, null, true),
					radius = (pInt(pick(options.radius, 100)) * center[2]) / 200,
					innerRadius = (pInt(pick(options.innerRadius, 60)) * center[2]) / 200,
					shapeArgs,
					d,
					toColor = yAxis.toColor(point.y, point),
					fromColor;

				if (toColor !== 'none') {
					fromColor = point.color;
					point.color = toColor;
				}

				// Handle the wrap option
				if (options.wrap === false) {
					rotation = Math.max(yAxis.startAngleRad, Math.min(yAxis.endAngleRad, rotation));
				}
				rotation = rotation * 180 / Math.PI;

				shapeArgs = {
					x: center[0],
					y: center[1],
					r: radius,
					innerR: innerRadius,
					start: yAxis.startAngleRad,
					end: rotation / (180 / Math.PI)
				};

				if (graphic) {
					d = shapeArgs.d;

					/*jslint unparam: true*/
					graphic.attr({
						fill: point.color
					}).animate(shapeArgs, {
						step: function (value, fx) {
							graphic.attr('fill', colorAxisMethods.tweenColors(H.Color(fromColor), H.Color(toColor), fx.pos));
						}
					});
					/*jslint unparam: false*/
					shapeArgs.d = d; // animate alters it
				} else {
					point.graphic = renderer.arc(shapeArgs)
						.attr({
							stroke: options.borderColor || 'none',
							'stroke-width': options.borderWidth || 0,
							fill: point.color
						})
						.add(series.group);
				}
			});
		},
		animate: null
	});

}(Highcharts));
