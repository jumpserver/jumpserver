;(function($){
/**
 * jqGrid Romanian Translation
 * Alexandru Emil Lupu contact@alecslupu.ro
 * http://www.alecslupu.ro/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = $.jgrid || {};
$.extend($.jgrid,{
	defaults : {
		recordtext: "Vizualizare {0} - {1} din {2}",
		emptyrecords: "Nu există înregistrări de vizualizat",
		loadtext: "Încărcare...",
		pgtext : "Pagina {0} din {1}"
	},
	search : {
		caption: "Caută...",
		Find: "Caută",
		Reset: "Resetare",
		odata: [{ oper:'eq', text:"egal"},{ oper:'ne', text:"diferit"},{ oper:'lt', text:"mai mic"},{ oper:'le', text:"mai mic sau egal"},{ oper:'gt', text:"mai mare"},{ oper:'ge', text:"mai mare sau egal"},{ oper:'bw', text:"începe cu"},{ oper:'bn', text:"nu începe cu"},{ oper:'in', text:"se găsește în"},{ oper:'ni', text:"nu se găsește în"},{ oper:'ew', text:"se termină cu"},{ oper:'en', text:"nu se termină cu"},{ oper:'cn', text:"conține"},{ oper:'nc', text:""},{ oper:'nu', text:'is null'},{ oper:'nn', text:'is not null'}],
		groupOps: [	{ op: "AND", text: "toate" },	{ op: "OR",  text: "oricare" }	],
		operandTitle : "Click to select search operation.",
		resetTitle : "Reset Search Value"
	},
	edit : {
		addCaption: "Adăugare înregistrare",
		editCaption: "Modificare înregistrare",
		bSubmit: "Salvează",
		bCancel: "Anulare",
		bClose: "Închide",
		saveData: "Informațiile au fost modificate! Salvați modificările?",
		bYes : "Da",
		bNo : "Nu",
		bExit : "Anulare",
		msg: {
			required:"Câmpul este obligatoriu",
			number:"Vă rugăm introduceți un număr valid",
			minValue:"valoarea trebuie sa fie mai mare sau egală cu",
			maxValue:"valoarea trebuie sa fie mai mică sau egală cu",
			email: "nu este o adresă de e-mail validă",
			integer: "Vă rugăm introduceți un număr valid",
			date: "Vă rugăm să introduceți o dată validă",
			url: "Nu este un URL valid. Prefixul  este necesar('http://' or 'https://')",
			nodefined : " is not defined!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
		caption: "Vizualizare înregistrare",
		bClose: "Închidere"
	},
	del : {
		caption: "Ștegere",
		msg: "Ștergeți înregistrarea (înregistrările) selectate?",
		bSubmit: "Șterge",
		bCancel: "Anulare"
	},
	nav : {
		edittext: "",
		edittitle: "Modifică rândul selectat",
		addtext:"",
		addtitle: "Adaugă rând nou",
		deltext: "",
		deltitle: "Șterge rândul selectat",
		searchtext: "",
		searchtitle: "Căutare înregistrări",
		refreshtext: "",
		refreshtitle: "Reîncarcare Grid",
		alertcap: "Avertisment",
		alerttext: "Vă rugăm să selectați un rând",
		viewtext: "",
		viewtitle: "Vizualizează rândul selectat"
	},
	col : {
		caption: "Arată/Ascunde coloanele",
		bSubmit: "Salvează",
		bCancel: "Anulare"
	},
	errors : {
		errcap : "Eroare",
		nourl : "Niciun url nu este setat",
		norecords: "Nu sunt înregistrări de procesat",
		model : "Lungimea colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Dum", "Lun", "Mar", "Mie", "Joi", "Vin", "Sâm",
				"Duminică", "Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă"
			],
			monthNames: [
				"Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Noi", "Dec",
				"Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"
			],
			AmPm : ["am","pm","AM","PM"],
			/*
			 Here is a problem in romanian: 
					M	/	F
			 1st = primul / prima
			 2nd = Al doilea / A doua
			 3rd = Al treilea / A treia 
			 4th = Al patrulea/ A patra
			 5th = Al cincilea / A cincea 
			 6th = Al șaselea / A șasea
			 7th = Al șaptelea / A șaptea
			 .... 
			 */
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
