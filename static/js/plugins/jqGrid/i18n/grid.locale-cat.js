;(function($){
/**
 * jqGrid Catalan Translation
 * Traducció jqGrid en Catatà per Faserline, S.L.
 * http://www.faserline.com
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = $.jgrid || {};
$.extend($.jgrid,{
	defaults : {
		recordtext: "Mostrant {0} - {1} de {2}",
	    emptyrecords: "Sense registres que mostrar",
		loadtext: "Carregant...",
		pgtext : "Pàgina {0} de {1}"
	},
	search : {
		caption: "Cerca...",
		Find: "Cercar",
		Reset: "Buidar",
	    odata: [{ oper:'eq', text:"equal"},{ oper:'ne', text:"not equal"},{ oper:'lt', text:"less"},{ oper:'le', text:"less or equal"},{ oper:'gt', text:"greater"},{ oper:'ge', text:"greater or equal"},{ oper:'bw', text:"begins with"},{ oper:'bn', text:"does not begin with"},{ oper:'in', text:"is in"},{ oper:'ni', text:"is not in"},{ oper:'ew', text:"ends with"},{ oper:'en', text:"does not end with"},{ oper:'cn', text:"contains"},{ oper:'nc', text:"does not contain"},{ oper:'nu', text:'is null'},{ oper:'nn', text:'is not null'}],
	    groupOps: [	{ op: "AND", text: "tot" },	{ op: "OR",  text: "qualsevol" }	],
		operandTitle : "Click to select search operation.",
		resetTitle : "Reset Search Value"
	},
	edit : {
		addCaption: "Afegir registre",
		editCaption: "Modificar registre",
		bSubmit: "Guardar",
		bCancel: "Cancelar",
		bClose: "Tancar",
		saveData: "Les dades han canviat. Guardar canvis?",
		bYes : "Yes",
		bNo : "No",
		bExit : "Cancel",
		msg: {
		    required:"Camp obligatori",
		    number:"Introdueixi un nombre",
		    minValue:"El valor ha de ser major o igual que ",
		    maxValue:"El valor ha de ser menor o igual a ",
		    email: "no és una direcció de correu vàlida",
		    integer: "Introdueixi un valor enter",
			date: "Introdueixi una data correcta ",
			url: "no és una URL vàlida. Prefix requerit ('http://' or 'https://')",
			nodefined : " is not defined!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
		}
	},
	view : {
		caption: "Veure registre",
		bClose: "Tancar"
	},
	del : {
		caption: "Eliminar",
		msg: "¿Desitja eliminar els registres seleccionats?",
		bSubmit: "Eliminar",
		bCancel: "Cancelar"
	},
	nav : {
		edittext: " ",
		edittitle: "Modificar fila seleccionada",
		addtext:" ",
		addtitle: "Agregar nova fila",
		deltext: " ",
		deltitle: "Eliminar fila seleccionada",
		searchtext: " ",
		searchtitle: "Cercar informació",
		refreshtext: "",
		refreshtitle: "Refrescar taula",
		alertcap: "Avís",
		alerttext: "Seleccioni una fila",
		viewtext: " ",
		viewtitle: "Veure fila seleccionada"
	},
// setcolumns module
	col : {
		caption: "Mostrar/ocultar columnes",
		bSubmit: "Enviar",
		bCancel: "Cancelar"	
	},
	errors : {
		errcap : "Error",
		nourl : "No s'ha especificat una URL",
		norecords: "No hi ha dades per processar",
		model : "Les columnes de noms són diferents de les columnes del model"
	},
	formatter : {
		integer : {thousandsSeparator: ".", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, defaultValue: '0,00'},
		currency : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, prefix: "", suffix:"", defaultValue: '0,00'},
		date : {
			dayNames:   [
				"Dg", "Dl", "Dt", "Dc", "Dj", "Dv", "Ds",
				"Diumenge", "Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte"
			],
			monthNames: [
				"Gen", "Febr", "Març", "Abr", "Maig", "Juny", "Jul", "Ag", "Set", "Oct", "Nov", "Des",
				"Gener", "Febrer", "Març", "Abril", "Maig", "Juny", "Juliol", "Agost", "Setembre", "Octubre", "Novembre", "Desembre"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th'},
			srcformat: 'Y-m-d',
			newformat: 'd-m-Y',
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
		showAction: 'show',
	    target: '',
	    checkbox : {disabled:true},
		idName : 'id'
	}
});
})(jQuery);
