/* 
Justified Gallery
Version: 2.1
Author: Miro Mannino
Author URI: http://miromannino.it

Copyright 2012 Miro Mannino (miro.mannino@gmail.com)

This file is part of Justified Gallery.

This work is licensed under the Creative Commons Attribution 3.0 Unported License. 

To view a copy of this license, visit http://creativecommons.org/licenses/by/3.0/ 
or send a letter to Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.
*/

(function(d){d.fn.justifiedGallery=function(r){function n(b,i){return'<div class="jg-error '+i+'"style="">'+b+"</div>"}function o(b,i,j){d(b).find(".jg-loading").fadeOut(500,function(){d(this).remove();p(d,b,i,0,j);d.isFunction(j.onComplete)&&j.onComplete.call(this,b)})}function q(b,i,d,c){var a,h=0,g;for(a=0;a<b.length;a++){b[a].nh=Math.ceil(i[b[a].indx].height*((i[b[a].indx].width+d)/i[b[a].indx].width));b[a].nw=i[b[a].indx].width+d;var e=b[a],f=b[a].nw,m=b[a].nh,l=void 0,l=f>m?f:m;e.suffix=100>=
l?c.sizeRangeSuffixes.lt100:240>=l?c.sizeRangeSuffixes.lt240:320>=l?c.sizeRangeSuffixes.lt320:500>=l?c.sizeRangeSuffixes.lt500:640>=l?c.sizeRangeSuffixes.lt640:c.sizeRangeSuffixes.lt1024;b[a].l=h;c.fixedHeight||(0==a?g=b[a].nh:g>b[a].nh&&(g=b[a].nh));h+=b[a].nw+c.margins}c.fixedHeight&&(g=c.rowHeight);d="";for(a=0;a<b.length;a++)h=i[b[a].indx],e=b[a].nh,f=void 0,f='<div class="jg-image" style="left:'+b[a].l+'px">',f+=' <a href="'+h.href+'" ',"undefined"!=typeof h.rel&&(f+='rel="'+h.rel+'"'),"undefined"!=
typeof h.target&&(f+='target="'+h.target+'"'),f+='title="'+h.title+'">',f+='  <img alt="'+h.alt+'" src="'+h.src+b[a].suffix+h.extension+'"',f+='style="width: '+b[a].nw+"px; height: "+e+'px;">',c.captions&&(f+='  <div style="bottom:'+(e-g)+'px;" class="jg-image-label">'+h.alt+"</div>"),f+=" </a></div>",d+=f;return'<div class="jg-row" style="height: '+g+"px; margin-bottom:"+c.margins+'px;">'+d+"</div>"}function p(b,d,e,c,a){var c=[],h,g,k=0,f=b(d).width();for(h=g=0;g<e.length;g++)null!=e[g]&&(k+e[g].width+
a.margins<=f?(k+=e[g].width+a.margins,c[h]=Array(5),c[h].indx=g,h++):(h=Math.ceil((f-k+1)/c.length),b(d).append(q(c,e,h,a)),c=[],c[0]=Array(5),c[0].indx=g,h=1,k=e[g].width+a.margins));h=a.justifyLastRow?Math.ceil((f-k+1)/c.length):0;b(d).append(q(c,e,h,a));a.captions&&(b(d).find(".jg-image").mouseenter(function(a){b(a.currentTarget).find(".jg-image-label").stop();b(a.currentTarget).find(".jg-image-label").fadeTo(500,0.7)}),b(d).find(".jg-image").mouseleave(function(a){b(a.currentTarget).find(".jg-image-label").stop();
b(a.currentTarget).find(".jg-image-label").fadeTo(500,0)}));b(d).find(".jg-resizedImageNotFound").remove();b(d).find(".jg-image img").load(function(){b(this).fadeTo(500,1)}).error(function(){b(d).prepend(n("The image can't be loaded: \""+b(this).attr("src")+'"',"jg-resizedImageNotFound"))}).each(function(){this.complete&&b(this).load()});var m=setInterval(function(){if(f!=b(d).width()){b(d).find(".jg-row").remove();clearInterval(m);p(b,d,e,f,a)}},a.refreshTime)}var e=d.extend({sizeRangeSuffixes:{lt100:"_t",
lt240:"_m",lt320:"_n",lt500:"",lt640:"_z",lt1024:"_b"},rowHeight:120,margins:1,justifyLastRow:!0,fixedHeight:!1,captions:!0,rel:null,target:null,extension:/\.[^.]+$/,refreshTime:500,onComplete:null},r);return this.each(function(b,i){d(i).addClass("justifiedGallery");var j=0,c=Array(d(i).find("img").length);0!=c.length&&(d(i).append('<div class="jg-loading"><div class="jg-loading-img"></div></div>'),d(i).find("a").each(function(a,b){var g=d(b).find("img");c[a]=Array(5);c[a].src="undefined"!=typeof d(g).data("safe-src")?
d(g).data("safe-src"):d(g).attr("src");c[a].alt=d(g).attr("alt");c[a].href=d(b).attr("href");c[a].title=d(b).attr("title");c[a].rel=null!=e.rel?e.rel:d(b).attr("rel");c[a].target=null!=e.target?e.target:d(b).attr("target");c[a].extension=c[a].src.match(e.extension)[0];d(b).remove();g=new Image;d(g).load(function(){c[a].width=c[a].height!=e.rowHeight?Math.ceil(this.width/(this.height/e.rowHeight)):this.width;c[a].height=e.rowHeight;var b=RegExp("("+e.sizeRangeSuffixes.lt100+"|"+e.sizeRangeSuffixes.lt240+
"|"+e.sizeRangeSuffixes.lt320+"|"+e.sizeRangeSuffixes.lt500+"|"+e.sizeRangeSuffixes.lt640+"|"+e.sizeRangeSuffixes.lt1024+")$");c[a].src=c[a].src.replace(e.extension,"").replace(b,"");++j==c.length&&o(i,c,e)});d(g).error(function(){d(i).prepend(n("The image can't be loaded: \""+c[a].src+'"',"jg-usedPrefixImageNotFound"));c[a]=null;++j==c.length&&o(i,c,e)});d(g).attr("src",c[a].src)}))})}})(jQuery);
