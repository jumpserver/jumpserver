$(function() {
    var graph = new Rickshaw.Graph( {
        element: document.querySelector("#chart"),
        series: [{
            color: '#1ab394',
            data: [
                { x: 0, y: 40 },
                { x: 1, y: 49 },
                { x: 2, y: 38 },
                { x: 3, y: 30 },
                { x: 4, y: 32 } ]
        }]
    });
    graph.render();

    var graph2 = new Rickshaw.Graph( {
        element: document.querySelector("#rickshaw_multi"),
        renderer: 'area',
        stroke: true,
        series: [ {
            data: [ { x: 0, y: 40 }, { x: 1, y: 49 }, { x: 2, y: 38 }, { x: 3, y: 20 }, { x: 4, y: 16 } ],
            color: '#1ab394',
            stroke: '#17997f'
        }, {
            data: [ { x: 0, y: 22 }, { x: 1, y: 25 }, { x: 2, y: 38 }, { x: 3, y: 44 }, { x: 4, y: 46 } ],
            color: '#eeeeee',
            stroke: '#d7d7d7'
        } ]
    } );
    graph2.renderer.unstack = true;
    graph2.render();

    var graph3 = new Rickshaw.Graph({
        element: document.querySelector("#rickshaw_line"),
        renderer: 'line',
        series: [ {
            data: [ { x: 0, y: 40 }, { x: 1, y: 49 }, { x: 2, y: 38 }, { x: 3, y: 30 }, { x: 4, y: 32 } ],
            color: '#1ab394'
        } ]
    } );
    graph3.render();

    var graph4 = new Rickshaw.Graph({
        element: document.querySelector("#rickshaw_multi_line"),
        renderer: 'line',
        series: [{
            data: [ { x: 0, y: 40 }, { x: 1, y: 49 }, { x: 2, y: 38 }, { x: 3, y: 30 }, { x: 4, y: 32 } ],
            color: '#1ab394'
        }, {
            data: [ { x: 0, y: 20 }, { x: 1, y: 24 }, { x: 2, y: 19 }, { x: 3, y: 15 }, { x: 4, y: 16 } ],
            color: '#d7d7d7'
        }]
    });
    graph4.render();

    var graph5 = new Rickshaw.Graph( {
        element: document.querySelector("#rickshaw_bars"),
        renderer: 'bar',
        series: [ {
            data: [ { x: 0, y: 40 }, { x: 1, y: 49 }, { x: 2, y: 38 }, { x: 3, y: 30 }, { x: 4, y: 32 } ],
            color: '#1ab394'
        } ]
    } );
    graph5.render();

    var graph6 = new Rickshaw.Graph( {
        element: document.querySelector("#rickshaw_bars_stacked"),
        renderer: 'bar',
        series: [
            {
                data: [ { x: 0, y: 40 }, { x: 1, y: 49 }, { x: 2, y: 38 }, { x: 3, y: 30 }, { x: 4, y: 32 } ],
                color: '#1ab394'
            }, {
                data: [ { x: 0, y: 20 }, { x: 1, y: 24 }, { x: 2, y: 19 }, { x: 3, y: 15 }, { x: 4, y: 16 } ],
                color: '#d7d7d7'
            } ]
    } );
    graph6.render();

    var graph7 = new Rickshaw.Graph( {
        element: document.querySelector("#rickshaw_scatterplot"),
        renderer: 'scatterplot',
        stroke: true,
        padding: { top: 0.05, left: 0.05, right: 0.05 },
        series: [ {
            data: [ { x: 0, y: 15 },
                { x: 1, y: 18 },
                { x: 2, y: 10 },
                { x: 3, y: 12 },
                { x: 4, y: 15 },
                { x: 5, y: 24 },
                { x: 6, y: 28 },
                { x: 7, y: 31 },
                { x: 8, y: 22 },
                { x: 9, y: 18 },
                { x: 10, y: 16 }
            ],
            color: '#1ab394'
        } ]
    } );
    graph7.render();

});