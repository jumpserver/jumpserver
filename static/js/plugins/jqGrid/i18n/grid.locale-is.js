;(function($){
/**
 * jqGrid Icelandic Translation
 * jtm@hi.is Univercity of Iceland
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = $.jgrid || {};
$.extend($.jgrid,{
	defaults : {
		recordtext: "Skoða {0} - {1} af {2}",
	    emptyrecords: "Engar færslur",
		loadtext: "Hleður...",
		pgtext : "Síða {0} af {1}"
	},
	search : {
	    caption: "Leita...",
	    Find: "Leita",
	    Reset: "Endursetja",
	    odata: [{ oper:'eq', text:"sama og"},{ oper:'ne', text:"ekki sama og"},{ oper:'lt', text:"minna en"},{ oper:'le', text:"minna eða jafnt og"},{ oper:'gt', text:"stærra en"},{ oper:'ge', text:"stærra eða jafnt og"},{ oper:'bw', text:"byrjar á"},{ oper:'bn', text:"byrjar ekki á"},{ oper:'in', text:"er í"},{ oper:'ni', text:"er ekki í"},{ oper:'ew', text:"endar á"},{ oper:'en', text:"endar ekki á"},{ oper:'cn', text:"inniheldur"},{ oper:'nc', text:"inniheldur ekki"},{ oper:'nu', text:'is null'},{ oper:'nn', text:'is not null'}],
	    groupOps: [	{ op: "AND", text: "allt" },	{ op: "OR",  text: "eða" }	],
		operandTitle : "Click to select search operation.",
		resetTitle : "Reset Search Value"
	},
	edit : {
	    addCaption: "Bæta við færslu",
	    editCaption: "Breyta færslu",
	    bSubmit: "Vista",
	    bCancel: "Hætta við",
		bClose: "Loka",
		saveData: "Gögn hafa breyst! Vista breytingar?",
		bYes : "Já",
		bNo : "Nei",
		bExit : "Hætta við",
	    msg: {
	        required:"Reitur er nauðsynlegur",
	        number:"Vinsamlega settu inn tölu",
	        minValue:"gildi verður að vera meira en eða jafnt og ",
	        maxValue:"gildi verður að vera minna en eða jafnt og ",
	        email: "er ekki löglegt email",
	        integer: "Vinsamlega settu inn tölu",
			date: "Vinsamlega setti inn dagsetningu",
			url: "er ekki löglegt URL. Vantar ('http://' eða 'https://')",
			nodefined : " er ekki skilgreint!",
			novalue : " skilagildi nauðsynlegt!",
			customarray : "Fall skal skila fylki!",
			customfcheck : "Fall skal vera skilgreint!"
		}
	},
	view : {
	    caption: "Skoða færslu",
	    bClose: "Loka"
	},
	del : {
	    caption: "Eyða",
	    msg: "Eyða völdum færslum ?",
	    bSubmit: "Eyða",
	    bCancel: "Hætta við"
	},
	nav : {
		edittext: " ",
	    edittitle: "Breyta færslu",
		addtext:" ",
	    addtitle: "Ný færsla",
	    deltext: " ",
	    deltitle: "Eyða færslu",
	    searchtext: " ",
	    searchtitle: "Leita",
	    refreshtext: "",
	    refreshtitle: "Endurhlaða",
	    alertcap: "Viðvörun",
	    alerttext: "Vinsamlega veldu færslu",
		viewtext: "",
		viewtitle: "Skoða valda færslu"
	},
	col : {
	    caption: "Sýna / fela dálka",
	    bSubmit: "Vista",
	    bCancel: "Hætta við"	
	},
	errors : {
		errcap : "Villa",
		nourl : "Vantar slóð",
		norecords: "Engar færslur valdar",
	    model : "Lengd colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Sun", "Mán", "Þri", "Mið", "Fim", "Fös", "Lau",
				"Sunnudagur", "Mánudagur", "Þriðjudagur", "Miðvikudagur", "Fimmtudagur", "Föstudagur", "Laugardagur"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Maí", "Jún", "Júl", "Ágú", "Sep", "Oct", "Nóv", "Des",
				"Janúar", "Febrúar", "Mars", "Apríl", "Maí", "Júný", "Júlý", "Ágúst", "September", "Október", "Nóvember", "Desember"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd/m/Y',
			parseRe : /[#%\\\/:_;.,\t\s-]/,
			masks : {
	            ISO8601Long:"Y-m-d H:i:s",
	            ISO8601Short:"Y-m-d",
	            ShortDate: "n/j/Y",
	            LongDate: "l, F d, Y",
	            FullDateTime: "l, F d, Y g:i:s A",
	            MonthDay: "F d",
	            ShortTime: "g:i A",
	            LongTime: "g:i:s A",
	            SortableDateTime: "Y-m-d\\TH:i:s",
	            UniversalSortableDateTime: "Y-m-d H:i:sO",
	            YearMonth: "F, Y"
	        },
	        reformatAfterEdit : false
		},
		baseLinkUrl: '',
		showAction: '',
	    target: '',
	    checkbox : {disabled:true},
		idName : 'id'
	}
});
})(jQuery);
