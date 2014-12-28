;(function($){
/**
 * jqGrid Bulgarian Translation 
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = $.jgrid || {};
$.extend($.jgrid,{
	defaults : {
		recordtext: "{0} - {1} от {2}",
		emptyrecords: "Няма запис(и)",
		loadtext: "Зареждам...",
		pgtext : "Стр. {0} от {1}"
	},
	search : {
		caption: "Търсене...",
		Find: "Намери",
		Reset: "Изчисти",
		odata: [{ oper:'eq', text:"равно"},{ oper:'ne', text:"различно"},{ oper:'lt', text:"по-малко"},{ oper:'le', text:"по-малко или="},{ oper:'gt', text:"по-голямо"},{ oper:'ge', text:"по-голямо или ="},{ oper:'bw', text:"започва с"},{ oper:'bn', text:"не започва с"},{ oper:'in', text:"се намира в"},{ oper:'ni', text:"не се намира в"},{ oper:'ew', text:"завършва с"},{ oper:'en', text:"не завършава с"},{ oper:'cn', text:"съдържа"},{ oper:'nc', text:"не съдържа"},{ oper:'nu', text:'е NULL'},{ oper:'nn', text:'не е NULL'}],
	    groupOps: [	{ op: "AND", text: "&nbsp;И " },	{ op: "OR",  text: "ИЛИ" }	],
		operandTitle : "Натисни за избор на операнд.",
		resetTitle : "Изчисти стойността"
	},
	edit : {
		addCaption: "Нов Запис",
		editCaption: "Редакция Запис",
		bSubmit: "Запиши",
		bCancel: "Изход",
		bClose: "Затвори",
		saveData: "Данните са променени! Да съхраня ли промените?",
		bYes : "Да",
		bNo : "Не",
		bExit : "Отказ",
		msg: {
			required:"Полето е задължително",
			number:"Въведете валидно число!",
			minValue:"стойността трябва да е по-голяма или равна от",
			maxValue:"стойността трябва да е по-малка или равна от",
			email: "не е валиден ел. адрес",
			integer: "Въведете валидно цяло число",
			date: "Въведете валидна дата",
			url: "e невалиден URL. Изискава се префикс('http://' или 'https://')",
			nodefined : " е недефинирана!",
			novalue : " изисква връщане на стойност!",
			customarray : "Потреб. Функция трябва да върне масив!",
			customfcheck : "Потребителска функция е задължителна при този тип елемент!"
		}
	},
	view : {
		caption: "Преглед запис",
		bClose: "Затвори"
	},
	del : {
		caption: "Изтриване",
		msg: "Да изтрия ли избраният запис?",
		bSubmit: "Изтрий",
		bCancel: "Отказ"
	},
	nav : {
		edittext: " ",
		edittitle: "Редакция избран запис",
		addtext:" ",
		addtitle: "Добавяне нов запис",
		deltext: " ",
		deltitle: "Изтриване избран запис",
		searchtext: " ",
		searchtitle: "Търсене запис(и)",
		refreshtext: "",
		refreshtitle: "Обнови таблица",
		alertcap: "Предупреждение",
		alerttext: "Моля, изберете запис",
		viewtext: "",
		viewtitle: "Преглед избран запис"
	},
	col : {
		caption: "Избери колони",
		bSubmit: "Ок",
		bCancel: "Изход"	
	},
	errors : {
		errcap : "Грешка",
		nourl : "Няма посочен url адрес",
		norecords: "Няма запис за обработка",
		model : "Модела не съответства на имената!"	
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:" лв.", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"Нед", "Пон", "Вт", "Ср", "Чет", "Пет", "Съб",
				"Неделя", "Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота"
			],
			monthNames: [
				"Яну", "Фев", "Мар", "Апр", "Май", "Юни", "Юли", "Авг", "Сеп", "Окт", "Нов", "Дек",
				"Януари", "Февруари", "Март", "Април", "Май", "Юни", "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"
			],
			AmPm : ["","","",""],
			S: function (j) {
				if(j==7 || j==8 || j== 27 || j== 28) {
					return 'ми';
				}
				return ['ви', 'ри', 'ти'][Math.min((j - 1) % 10, 2)];
			},
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
