/**
 * Highcharts Drilldown plugin
 * 
 * Author: Torstein Honsi
 * License: MIT License
 *
 * Demo: http://jsfiddle.net/highcharts/Vf3yT/
 */

/*global HighchartsAdapter*/
(function (H) {

	"use strict";

	var noop = function () {},
		defaultOptions = H.getOptions(),
		each = H.each,
		extend = H.extend,
		format = H.format,
		wrap = H.wrap,
		Chart = H.Chart,
		seriesTypes = H.seriesTypes,
		PieSeries = seriesTypes.pie,
		ColumnSeries = seriesTypes.column,
		fireEvent = HighchartsAdapter.fireEvent,
		inArray = HighchartsAdapter.inArray;

	// Utilities
	function tweenColors(startColor, endColor, pos) {
		var rgba = [
				Math.round(startColor[0] + (endColor[0] - startColor[0]) * pos),
				Math.round(startColor[1] + (endColor[1] - startColor[1]) * pos),
				Math.round(startColor[2] + (endColor[2] - startColor[2]) * pos),
				startColor[3] + (endColor[3] - startColor[3]) * pos
			];
		return 'rgba(' + rgba.join(',') + ')';
	}

	// Add language
	extend(defaultOptions.lang, {
		drillUpText: '◁ Back to {series.name}'
	});
	defaultOptions.drilldown = {
		activeAxisLabelStyle: {
			cursor: 'pointer',
			color: '#0d233a',
			fontWeight: 'bold',
			textDecoration: 'underline'			
		},
		activeDataLabelStyle: {
			cursor: 'pointer',
			color: '#0d233a',
			fontWeight: 'bold',
			textDecoration: 'underline'			
		},
		animation: {
			duration: 500
		},
		drillUpButton: {
			position: { 
				align: 'right',
				x: -10,
				y: 10
			}
			// relativeTo: 'plotBox'
			// theme
		}
	};	

	/**
	 * A general fadeIn method
	 */
	H.SVGRenderer.prototype.Element.prototype.fadeIn = function (animation) {
		this
		.attr({
			opacity: 0.1,
			visibility: 'inherit'
		})
		.animate({
			opacity: 1
		}, animation || {
			duration: 250
		});
	};

	Chart.prototype.addSeriesAsDrilldown = function (point, ddOptions) {
		this.addSingleSeriesAsDrilldown(point, ddOptions);
		this.applyDrilldown();
	};
	Chart.prototype.addSingleSeriesAsDrilldown = function (point, ddOptions) {
		var oldSeries = point.series,
			xAxis = oldSeries.xAxis,
			yAxis = oldSeries.yAxis,
			newSeries,
			color = point.color || oldSeries.color,
			pointIndex,
			levelSeries = [],
			levelSeriesOptions = [],
			level,
			levelNumber;

		levelNumber = oldSeries.levelNumber || 0;
			
		ddOptions = extend({
			color: color
		}, ddOptions);
		pointIndex = inArray(point, oldSeries.points);

		// Record options for all current series
		each(oldSeries.chart.series, function (series) {
			if (series.xAxis === xAxis) {
				levelSeries.push(series);
				levelSeriesOptions.push(series.userOptions);
				series.levelNumber = series.levelNumber || 0;
			}
		});
		
		// Add a record of properties for each drilldown level
		level = {
			levelNumber: levelNumber,
			seriesOptions: oldSeries.userOptions,
			levelSeriesOptions: levelSeriesOptions,
			levelSeries: levelSeries,
			shapeArgs: point.shapeArgs,
			bBox: point.graphic.getBBox(),
			color: color,
			lowerSeriesOptions: ddOptions,
			pointOptions: oldSeries.options.data[pointIndex],
			pointIndex: pointIndex,
			oldExtremes: {
				xMin: xAxis && xAxis.userMin,
				xMax: xAxis && xAxis.userMax,
				yMin: yAxis && yAxis.userMin,
				yMax: yAxis && yAxis.userMax
			}
		};

		// Generate and push it to a lookup array
		if (!this.drilldownLevels) {
			this.drilldownLevels = [];
		}
		this.drilldownLevels.push(level);

		newSeries = level.lowerSeries = this.addSeries(ddOptions, false);
		newSeries.levelNumber = levelNumber + 1;
		if (xAxis) {
			xAxis.oldPos = xAxis.pos;
			xAxis.userMin = xAxis.userMax = null;
			yAxis.userMin = yAxis.userMax = null;
		}

		// Run fancy cross-animation on supported and equal types
		if (oldSeries.type === newSeries.type) {
			newSeries.animate = newSeries.animateDrilldown || noop;
			newSeries.options.animation = true;
		}
	};

	Chart.prototype.applyDrilldown = function () {
		var drilldownLevels = this.drilldownLevels, 
			levelToRemove = drilldownLevels[drilldownLevels.length - 1].levelNumber;
		
		each(this.drilldownLevels, function (level) {
			if (level.levelNumber === levelToRemove) {
				each(level.levelSeries, function (series) {
					if (series.levelNumber === levelToRemove) { // Not removed, not added as part of a multi-series drilldown
						series.remove(false);
					}
				});
			}
		});
		
		this.redraw();
		this.showDrillUpButton();
	};

	Chart.prototype.getDrilldownBackText = function () {
		var lastLevel = this.drilldownLevels[this.drilldownLevels.length - 1];
		lastLevel.series = lastLevel.seriesOptions;
		return format(this.options.lang.drillUpText, lastLevel);

	};

	Chart.prototype.showDrillUpButton = function () {
		var chart = this,
			backText = this.getDrilldownBackText(),
			buttonOptions = chart.options.drilldown.drillUpButton,
			attr,
			states;
			

		if (!this.drillUpButton) {
			attr = buttonOptions.theme;
			states = attr && attr.states;
						
			this.drillUpButton = this.renderer.button(
				backText,
				null,
				null,
				function () {
					chart.drillUp(); 
				},
				attr, 
				states && states.hover,
				states && states.select
			)
			.attr({
				align: buttonOptions.position.align,
				zIndex: 9
			})
			.add()
			.align(buttonOptions.position, false, buttonOptions.relativeTo || 'plotBox');
		} else {
			this.drillUpButton.attr({
				text: backText
			})
			.align();
		}
	};

	Chart.prototype.drillUp = function () {
		var chart = this,
			drilldownLevels = chart.drilldownLevels,
			levelNumber = drilldownLevels[drilldownLevels.length - 1].levelNumber,
			i = drilldownLevels.length,
			chartSeries = chart.series,
			seriesI = chartSeries.length,
			level,
			oldSeries,
			newSeries,
			oldExtremes,
			addSeries = function (seriesOptions) {
				var addedSeries;
				each(chartSeries, function (series) {
					if (series.userOptions === seriesOptions) {
						addedSeries = series;
					}
				});

				addedSeries = addedSeries || chart.addSeries(seriesOptions, false);
				if (addedSeries.type === oldSeries.type && addedSeries.animateDrillupTo) {
					addedSeries.animate = addedSeries.animateDrillupTo;
				}
				if (seriesOptions === level.seriesOptions) {
					newSeries = addedSeries;
				}
			};
		
		while (i--) {

			level = drilldownLevels[i];
			if (level.levelNumber === levelNumber) {
				drilldownLevels.pop();
				
				// Get the lower series by reference or id
				oldSeries = level.lowerSeries;
				if (!oldSeries.chart) {  // #2786
					while (seriesI--) {
						if (chartSeries[seriesI].options.id === level.lowerSeriesOptions.id) {
							oldSeries = chartSeries[seriesI];
							break;
						}
					}
				}
				oldSeries.xData = []; // Overcome problems with minRange (#2898)

				each(level.levelSeriesOptions, addSeries);
				
				fireEvent(chart, 'drillup', { seriesOptions: level.seriesOptions });

				if (newSeries.type === oldSeries.type) {
					newSeries.drilldownLevel = level;
					newSeries.options.animation = chart.options.drilldown.animation;

					if (oldSeries.animateDrillupFrom) {
						oldSeries.animateDrillupFrom(level);
					}
				}
				newSeries.levelNumber = levelNumber;
				
				oldSeries.remove(false);

				// Reset the zoom level of the upper series
				if (newSeries.xAxis) {
					oldExtremes = level.oldExtremes;
					newSeries.xAxis.setExtremes(oldExtremes.xMin, oldExtremes.xMax, false);
					newSeries.yAxis.setExtremes(oldExtremes.yMin, oldExtremes.yMax, false);
				}
			}
		}

		this.redraw();

		if (this.drilldownLevels.length === 0) {
			this.drillUpButton = this.drillUpButton.destroy();
		} else {
			this.drillUpButton.attr({
				text: this.getDrilldownBackText()
			})
			.align();
		}
	};


	ColumnSeries.prototype.supportsDrilldown = true;
	
	/**
	 * When drilling up, keep the upper series invisible until the lower series has
	 * moved into place
	 */
	ColumnSeries.prototype.animateDrillupTo = function (init) {
		if (!init) {
			var newSeries = this,
				level = newSeries.drilldownLevel;

			each(this.points, function (point) {
				point.graphic.hide();
				if (point.dataLabel) {
					point.dataLabel.hide();
				}
				if (point.connector) {
					point.connector.hide();
				}
			});


			// Do dummy animation on first point to get to complete
			setTimeout(function () {
				each(newSeries.points, function (point, i) {  
					// Fade in other points			  
					var verb = i === (level && level.pointIndex) ? 'show' : 'fadeIn',
						inherit = verb === 'show' ? true : undefined;
					point.graphic[verb](inherit);
					if (point.dataLabel) {
						point.dataLabel[verb](inherit);
					}
					if (point.connector) {
						point.connector[verb](inherit);
					}
				});
			}, Math.max(this.chart.options.drilldown.animation.duration - 50, 0));

			// Reset
			this.animate = noop;
		}

	};
	
	ColumnSeries.prototype.animateDrilldown = function (init) {
		var series = this,
			drilldownLevels = this.chart.drilldownLevels,
			animateFrom = this.chart.drilldownLevels[this.chart.drilldownLevels.length - 1].shapeArgs,
			animationOptions = this.chart.options.drilldown.animation;
			
		if (!init) {
			each(drilldownLevels, function (level) {
				if (series.userOptions === level.lowerSeriesOptions) {
					animateFrom = level.shapeArgs;
				}
			});

			animateFrom.x += (this.xAxis.oldPos - this.xAxis.pos);
	
			each(this.points, function (point) {
				if (point.graphic) {
					point.graphic
						.attr(animateFrom)
						.animate(point.shapeArgs, animationOptions);
				}
				if (point.dataLabel) {
					point.dataLabel.fadeIn(animationOptions);
				}
			});
			this.animate = null;
		}
		
	};

	/**
	 * When drilling up, pull out the individual point graphics from the lower series
	 * and animate them into the origin point in the upper series.
	 */
	ColumnSeries.prototype.animateDrillupFrom = function (level) {
		var animationOptions = this.chart.options.drilldown.animation,
			group = this.group,
			series = this;

		// Cancel mouse events on the series group (#2787)
		each(series.trackerGroups, function (key) {
			if (series[key]) { // we don't always have dataLabelsGroup
				series[key].on('mouseover');
			}
		});
			

		delete this.group;
		each(this.points, function (point) {
			var graphic = point.graphic,
				startColor = H.Color(point.color).rgba,
				endColor = H.Color(level.color).rgba,
				complete = function () {
					graphic.destroy();
					if (group) {
						group = group.destroy();
					}
				};

			if (graphic) {
			
				delete point.graphic;

				if (animationOptions) {
					/*jslint unparam: true*/
					graphic.animate(level.shapeArgs, H.merge(animationOptions, {
						step: function (val, fx) {
							if (fx.prop === 'start' && startColor.length === 4 && endColor.length === 4) {
								this.attr({
									fill: tweenColors(startColor, endColor, fx.pos)
								});
							}
						},
						complete: complete
					}));
					/*jslint unparam: false*/
				} else {
					graphic.attr(level.shapeArgs);
					complete();
				}
			}
		});
	};

	if (PieSeries) {
		extend(PieSeries.prototype, {
			supportsDrilldown: true,
			animateDrillupTo: ColumnSeries.prototype.animateDrillupTo,
			animateDrillupFrom: ColumnSeries.prototype.animateDrillupFrom,

			animateDrilldown: function (init) {
				var level = this.chart.drilldownLevels[this.chart.drilldownLevels.length - 1],
					animationOptions = this.chart.options.drilldown.animation,
					animateFrom = level.shapeArgs,
					start = animateFrom.start,
					angle = animateFrom.end - start,
					startAngle = angle / this.points.length,
					startColor = H.Color(level.color).rgba;

				if (!init) {
					each(this.points, function (point, i) {
						var endColor = H.Color(point.color).rgba;

						/*jslint unparam: true*/
						point.graphic
							.attr(H.merge(animateFrom, {
								start: start + i * startAngle,
								end: start + (i + 1) * startAngle
							}))[animationOptions ? 'animate' : 'attr'](point.shapeArgs, H.merge(animationOptions, {
								step: function (val, fx) {
									if (fx.prop === 'start' && startColor.length === 4 && endColor.length === 4) {
										this.attr({
											fill: tweenColors(startColor, endColor, fx.pos)
										});
									}
								}
							}));
						/*jslint unparam: false*/
					});
					this.animate = null;
				}
			}
		});
	}
	
	H.Point.prototype.doDrilldown = function (_holdRedraw) {
		var series = this.series,
			chart = series.chart,
			drilldown = chart.options.drilldown,
			i = (drilldown.series || []).length,
			seriesOptions;
		
		while (i-- && !seriesOptions) {
			if (drilldown.series[i].id === this.drilldown) {
				seriesOptions = drilldown.series[i];
			}
		}

		// Fire the event. If seriesOptions is undefined, the implementer can check for 
		// seriesOptions, and call addSeriesAsDrilldown async if necessary.
		fireEvent(chart, 'drilldown', { 
			point: this,
			seriesOptions: seriesOptions
		});
		
		if (seriesOptions) {
			if (_holdRedraw) {
				chart.addSingleSeriesAsDrilldown(this, seriesOptions);
			} else {
				chart.addSeriesAsDrilldown(this, seriesOptions);
			}
		}

	};
	
	wrap(H.Point.prototype, 'init', function (proceed, series, options, x) {
		var point = proceed.call(this, series, options, x),
			chart = series.chart,
			tick = series.xAxis && series.xAxis.ticks[x],
			tickLabel = tick && tick.label;
		
		if (point.drilldown) {
			
			// Add the click event to the point label
			H.addEvent(point, 'click', function () {
				point.doDrilldown();
			});
			
			// Make axis labels clickable
			if (tickLabel) {
				if (!tickLabel._basicStyle) {
					tickLabel._basicStyle = tickLabel.element.getAttribute('style');
				}
				tickLabel
					.addClass('highcharts-drilldown-axis-label')
					.css(chart.options.drilldown.activeAxisLabelStyle)
					.on('click', function () {
						each(tickLabel.ddPoints, function (point) {
							if (point.doDrilldown) {
								point.doDrilldown(true);
							}
						});
						chart.applyDrilldown();
					});
				if (!tickLabel.ddPoints) {
					tickLabel.ddPoints = [];
				}
				tickLabel.ddPoints.push(point);
					
			}
		} else if (tickLabel && tickLabel._basicStyle) {
			tickLabel.element.setAttribute('style', tickLabel._basicStyle);
		}
		
		return point;
	});

	wrap(H.Series.prototype, 'drawDataLabels', function (proceed) {
		var css = this.chart.options.drilldown.activeDataLabelStyle;

		proceed.call(this);

		each(this.points, function (point) {
			if (point.drilldown && point.dataLabel) {
				point.dataLabel
					.attr({
						'class': 'highcharts-drilldown-data-label'
					})
					.css(css)
					.on('click', function () {
						point.doDrilldown();
					});
			}
		});
	});

	// Mark the trackers with a pointer 
	var type, 
		drawTrackerWrapper = function (proceed) {
			proceed.call(this);
			each(this.points, function (point) {
				if (point.drilldown && point.graphic) {
					point.graphic
						.attr({
							'class': 'highcharts-drilldown-point'
						})
						.css({ cursor: 'pointer' });
				}
			});
		};
	for (type in seriesTypes) {
		if (seriesTypes[type].prototype.supportsDrilldown) {
			wrap(seriesTypes[type].prototype, 'drawTracker', drawTrackerWrapper);
		}
	}
		
}(Highcharts));
