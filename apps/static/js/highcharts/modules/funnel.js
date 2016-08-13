/*
 
 Highcharts funnel module

 (c) 2010-2014 Torstein Honsi

 License: www.highcharts.com/license
*/
(function(b){var d=b.getOptions(),v=d.plotOptions,q=b.seriesTypes,E=b.merge,D=function(){},A=b.each;v.funnel=E(v.pie,{animation:!1,center:["50%","50%"],width:"90%",neckWidth:"30%",height:"100%",neckHeight:"25%",reversed:!1,dataLabels:{connectorWidth:1,connectorColor:"#606060"},size:!0,states:{select:{color:"#C0C0C0",borderColor:"#000000",shadow:!1}}});q.funnel=b.extendClass(q.pie,{type:"funnel",animate:D,singularTooltips:!0,translate:function(){var a=function(j,a){return/%$/.test(j)?a*parseInt(j,
10)/100:parseInt(j,10)},B=0,f=this.chart,c=this.options,g=c.reversed,b=f.plotWidth,n=f.plotHeight,o=0,f=c.center,h=a(f[0],b),d=a(f[0],n),q=a(c.width,b),k,r,e=a(c.height,n),s=a(c.neckWidth,b),t=a(c.neckHeight,n),w=e-t,a=this.data,x,y,v=c.dataLabels.position==="left"?1:0,z,l,C,p,i,u,m;this.getWidthAt=r=function(j){return j>e-t||e===t?s:s+(q-s)*((e-t-j)/(e-t))};this.getX=function(j,a){return h+(a?-1:1)*(r(g?n-j:j)/2+c.dataLabels.distance)};this.center=[h,d,e];this.centerX=h;A(a,function(a){B+=a.y});
A(a,function(a){m=null;y=B?a.y/B:0;l=d-e/2+o*e;i=l+y*e;k=r(l);z=h-k/2;C=z+k;k=r(i);p=h-k/2;u=p+k;l>w?(z=p=h-s/2,C=u=h+s/2):i>w&&(m=i,k=r(w),p=h-k/2,u=p+k,i=w);g&&(l=e-l,i=e-i,m=m?e-m:null);x=["M",z,l,"L",C,l,u,i];m&&x.push(u,m,p,m);x.push(p,i,"Z");a.shapeType="path";a.shapeArgs={d:x};a.percentage=y*100;a.plotX=h;a.plotY=(l+(m||i))/2;a.tooltipPos=[h,a.plotY];a.slice=D;a.half=v;o+=y})},drawPoints:function(){var a=this,b=a.options,f=a.chart.renderer;A(a.data,function(c){var g=c.graphic,d=c.shapeArgs;
g?g.animate(d):c.graphic=f.path(d).attr({fill:c.color,stroke:b.borderColor,"stroke-width":b.borderWidth}).add(a.group)})},sortByAngle:function(a){a.sort(function(a,b){return a.plotY-b.plotY})},drawDataLabels:function(){var a=this.data,b=this.options.dataLabels.distance,f,c,g,d=a.length,n,o;for(this.center[2]-=2*b;d--;)g=a[d],c=(f=g.half)?1:-1,o=g.plotY,n=this.getX(o,f),g.labelPos=[0,o,n+(b-5)*c,o,n+b*c,o,f?"right":"left",0];q.pie.prototype.drawDataLabels.call(this)}});d.plotOptions.pyramid=b.merge(d.plotOptions.funnel,
{neckWidth:"0%",neckHeight:"0%",reversed:!0});b.seriesTypes.pyramid=b.extendClass(b.seriesTypes.funnel,{type:"pyramid"})})(Highcharts);
