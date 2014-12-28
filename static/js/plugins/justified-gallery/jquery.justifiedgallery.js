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

(function($){
 
   $.fn.justifiedGallery = function(options){

   		//TODO fare impostazione 'rel' che sostituisce tutti i link con il rel specificato

		var settings = $.extend( {
			'sizeRangeSuffixes' : {'lt100':'_t', 'lt240':'_m', 'lt320':'_n', 'lt500':'', 'lt640':'_z', 'lt1024':'_b'},
			'rowHeight' : 120,
			'margins' : 1,
			'justifyLastRow' : true,
			'fixedHeight' : false,
			'captions' : true,
			'rel' : null, //rewrite the rel of each analyzed links
			'target' : null, //rewrite the target of all links
			'extension' : /\.[^.]+$/,
			'refreshTime' : 500,
			'onComplete' : null
		}, options);

		function getErrorHtml(message, classOfError){
			return "<div class=\"jg-error " + classOfError + "\"style=\"\">" + message + "</div>";
		}

		return this.each(function(index, cont){
			$(cont).addClass("justifiedGallery");

			var loaded = 0;
			var images = new Array($(cont).find("img").length);

			if(images.length == 0) return;
			
			$(cont).append("<div class=\"jg-loading\"><div class=\"jg-loading-img\"></div></div>");

			$(cont).find("a").each(function(index, entry){
				var imgEntry = $(entry).find("img");

				images[index] = new Array(5);
				images[index]["src"] = (typeof $(imgEntry).data("safe-src") != 'undefined') ? $(imgEntry).data("safe-src") : $(imgEntry).attr("src");
				images[index]["alt"] = $(imgEntry).attr("alt");
				images[index]["href"] = $(entry).attr("href");
				images[index]["title"] = $(entry).attr("title");
				images[index]["rel"] = (settings.rel != null) ? settings.rel : $(entry).attr("rel");
				images[index]["target"] = (settings.target != null) ? settings.target : $(entry).attr("target");
				images[index]["extension"] = images[index]["src"].match(settings.extension)[0];
				
				$(entry).remove(); //remove the image, we have its data
				
				var img = new Image();
  
				$(img).load(function() {
					if(images[index]["height"] != settings.rowHeight)
						images[index]["width"] = Math.ceil(this.width / (this.height / settings.rowHeight));
					else
						images[index]["width"] = this.width;
					images[index]["height"] = settings.rowHeight;

					var usedSizeRangeRegExp = new RegExp("(" + settings.sizeRangeSuffixes.lt100 + "|" 
														 + settings.sizeRangeSuffixes.lt240 + "|"  
														 + settings.sizeRangeSuffixes.lt320 + "|" 
														 + settings.sizeRangeSuffixes.lt500 + "|" 
														 + settings.sizeRangeSuffixes.lt640 + "|" 
														 + settings.sizeRangeSuffixes.lt1024 + ")$");
					
					images[index]["src"] = images[index]["src"].replace(settings.extension, "").replace(usedSizeRangeRegExp, "");

		    		if(++loaded == images.length) startProcess(cont, images, settings);
				});
				
				$(img).error(function() {
					$(cont).prepend(getErrorHtml("The image can't be loaded: \"" + images[index]["src"] +"\"", "jg-usedPrefixImageNotFound"));
					images[index] = null;
					if(++loaded == images.length) startProcess(cont, images, settings);
				});
				
				$(img).attr('src', images[index]["src"]);

			});
		});
		
		function startProcess(cont, images, settings){
			//FadeOut the loading image and FadeIn the images after their loading
			$(cont).find(".jg-loading").fadeOut(500, function(){
				$(this).remove(); //remove the loading image
				processesImages($, cont, images, 0, settings);
				if($.isFunction(settings.onComplete)) settings.onComplete.call(this, cont);
			});
		}

		function buildImage(image, suffix, nw, nh, l, minRowHeight, settings){
			var ris;
			ris =  "<div class=\"jg-image\" style=\"left:" + l + "px\">";
			ris += " <a href=\"" + image["href"] + "\" ";

			if (typeof image["rel"] != 'undefined') ris += "rel=\"" + image["rel"] + "\"";
			if (typeof image["target"] != 'undefined') ris += "target=\"" + image["target"] + "\"";

			ris +=     "title=\"" + image["title"] + "\">";
			ris += "  <img alt=\"" + image["alt"] + "\" src=\"" + image["src"] + suffix + image.extension + "\"";
			ris +=        "style=\"width: " + nw + "px; height: " + nh + "px;\">";
			
			if(settings.captions)
				ris += "  <div style=\"bottom:" + (nh - minRowHeight) + "px;\" class=\"jg-image-label\">" + image["alt"] + "</div>";

			ris += " </a></div>";
			return ris;
		}

		function buildContRow(row, images, extraW, settings){
			var j, l = 0;
			var minRowHeight;
			for(var j = 0; j < row.length; j++){
				row[j]["nh"] = Math.ceil(images[row[j]["indx"]]["height"] * 
					            ((images[row[j]["indx"]]["width"] + extraW) / 
							 	images[row[j]["indx"]]["width"]));
				
				row[j]["nw"] = images[row[j]["indx"]]["width"] + extraW;

				row[j]["suffix"] = getSuffix(row[j]["nw"], row[j]["nh"], settings);

				row[j]["l"] = l;

				if(!settings.fixedHeight){
					if(j == 0) 
						minRowHeight = row[j]["nh"];
					else
						if(minRowHeight > row[j]["nh"]) minRowHeight = row[j]["nh"];
				}
				 
				l += row[j]["nw"] + settings.margins;
			}

			if(settings.fixedHeight) minRowHeight = settings.rowHeight;
			
			var rowCont = "";
			for(var j = 0; j < row.length; j++){
				rowCont += buildImage(images[row[j]["indx"]], row[j]["suffix"], 
					                  row[j]["nw"], row[j]["nh"], row[j]["l"], minRowHeight, settings);
			}
			
			return "<div class=\"jg-row\" style=\"height: " + minRowHeight + "px; margin-bottom:" + settings.margins + "px;\">" + rowCont + "</div>";
		}

		function getSuffix(nw, nh, settings){
			var n;
			if(nw > nh) n = nw; else n = nh;
			if(n <= 100){
				return settings.sizeRangeSuffixes.lt100; //thumbnail (longest side:100)
			}else if(n <= 240){
				return settings.sizeRangeSuffixes.lt240; //small (longest side:240)
			}else if(n <= 320){
				return settings.sizeRangeSuffixes.lt320; //small (longest side:320)
			}else if(n <= 500){
				return settings.sizeRangeSuffixes.lt500; //small (longest side:320)
			}else if(n <= 640){
				return settings.sizeRangeSuffixes.lt640; //medium (longest side:640)
			}else{
				return settings.sizeRangeSuffixes.lt1024; //large (longest side:1024)
			}
		}

		function processesImages($, cont, images, lastRowWidth, settings){	
			var row = new Array();
			var row_i, i;
			var partialRowWidth = 0;
			var extraW;
			var rowWidth = $(cont).width();

			for(i = 0, row_i = 0; i < images.length; i++){
				if(images[i] == null) continue;
				if(partialRowWidth + images[i]["width"] + settings.margins <= rowWidth){
					//we can add the image
					partialRowWidth += images[i]["width"] + settings.margins;
					row[row_i] = new Array(5);
					row[row_i]["indx"] = i;
					row_i++;
				}else{
					//the row is full
					extraW = Math.ceil((rowWidth - partialRowWidth + 1) / row.length); 
					$(cont).append(buildContRow(row, images, extraW, settings));

					row = new Array();
					row[0] = new Array(5);
					row[0]["indx"] = i;
					row_i = 1;
					partialRowWidth = images[i]["width"] + settings.margins;
				}
			}

			//last row----------------------
			//now we have all the images index loaded in the row arra
			if(settings.justifyLastRow){
				extraW = Math.ceil((rowWidth - partialRowWidth + 1) / row.length);	
			}else{
				extraW = 0;
			}
			$(cont).append(buildContRow(row, images, extraW, settings));
			//---------------------------

			//Captions---------------------
			if(settings.captions){
				$(cont).find(".jg-image").mouseenter(function(sender){
					$(sender.currentTarget).find(".jg-image-label").stop();
					$(sender.currentTarget).find(".jg-image-label").fadeTo(500, 0.7);
				});
				$(cont).find(".jg-image").mouseleave(function(sender){
					$(sender.currentTarget).find(".jg-image-label").stop();
					$(sender.currentTarget).find(".jg-image-label").fadeTo(500, 0);
				});
			}
			
			$(cont).find(".jg-resizedImageNotFound").remove();
			
			//fade in the images that we have changed and need to be reloaded
			$(cont).find(".jg-image img").load(function(){
					$(this).fadeTo(500, 1);
			}).error(function(){
				$(cont).prepend(getErrorHtml("The image can't be loaded: \"" +  $(this).attr("src") +"\"", "jg-resizedImageNotFound"));
			}).each(function(){
					if(this.complete) $(this).load();
			});

			checkWidth($, cont, images, rowWidth, settings);	
			
		}

		function checkWidth($, cont, images, lastRowWidth, settings){
			var id = setInterval(function(){

				if(lastRowWidth != $(cont).width()){
					$(cont).find(".jg-row").remove();
					clearInterval(id);
					processesImages($, cont, images, lastRowWidth, settings);
					return;
				}

			}, settings.refreshTime);
		}

   }
 
})(jQuery);