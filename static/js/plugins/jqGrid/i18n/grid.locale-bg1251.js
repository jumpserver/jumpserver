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
		recordtext: "{0} - {1} �� {2}",
		emptyrecords: "���� �����(�)",
		loadtext: "��������...",
		pgtext : "���. {0} �� {1}"
	},
	search : {
		caption: "�������...",
		Find: "������",
		Reset: "�������",
		odata : [{ oper:'eq', text:'�����'}, { oper:'ne', text:'��������'}, { oper:'lt', text:'��-�����'}, { oper:'le', text:'��-����� ���='},{ oper:'gt', text:'��-������'},{ oper:'ge', text:'��-������ ��� ='}, { oper:'bw', text:'������� �'},{ oper:'bn', text:'�� ������� �'},{ oper:'in', text:'�� ������ �'},{ oper:'ni', text:'�� �� ������ �'},{ oper:'ew', text:'�������� �'},{ oper:'en', text:'�� ��������� �'},,{ oper:'cn', text:'�������'}, ,{ oper:'nc', text:'�� �������'} ],
	    groupOps: [	{ op: "AND", text: " � " },	{ op: "OR",  text: "���" }	]
	},
	edit : {
		addCaption: "��� �����",
		editCaption: "�������� �����",
		bSubmit: "������",
		bCancel: "�����",
		bClose: "�������",
		saveData: "������� �� ���������! �� ������� �� ���������?",
		bYes : "��",
		bNo : "��",
		bExit : "�����",
		msg: {
		    required:"������ � ������������",
		    number:"�������� ������� �����!",
		    minValue:"���������� ������ �� � ��-������ ��� ����� ��",
		    maxValue:"���������� ������ �� � ��-����� ��� ����� ��",
		    email: "�� � ������� ��. �����",
		    integer: "�������� ������� ���� �����",
			date: "�������� ������� ����",
			url: "e ��������� URL. �������� �� �������('http://' ��� 'https://')",
			nodefined : " � ������������!",
			novalue : " ������� ������� �� ��������!",
			customarray : "������. ������� ������ �� ����� �����!",
			customfcheck : "������������� ������� � ������������ ��� ���� ��� �������!"
		}
	},
	view : {
	    caption: "������� �����",
	    bClose: "�������"
	},
	del : {
		caption: "���������",
		msg: "�� ������ �� ��������� �����?",
		bSubmit: "������",
		bCancel: "�����"
	},
	nav : {
		edittext: " ",
		edittitle: "�������� ������ �����",
		addtext:" ",
		addtitle: "�������� ��� �����",
		deltext: " ",
		deltitle: "��������� ������ �����",
		searchtext: " ",
		searchtitle: "������� �����(�)",
		refreshtext: "",
		refreshtitle: "������ �������",
		alertcap: "��������������",
		alerttext: "����, �������� �����",
		viewtext: "",
		viewtitle: "������� ������ �����"
	},
	col : {
		caption: "����� ������",
		bSubmit: "��",
		bCancel: "�����"	
	},
	errors : {
		errcap : "������",
		nourl : "���� ������� url �����",
		norecords: "���� ����� �� ���������",
		model : "������ �� ����������� �� �������!"	
	},
	formatter : {
		integer : {thousandsSeparator: " ", defaultValue: '0'},
		number : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, defaultValue: '0.00'},
		currency : {decimalSeparator:".", thousandsSeparator: " ", decimalPlaces: 2, prefix: "", suffix:" ��.", defaultValue: '0.00'},
		date : {
			dayNames:   [
				"���", "���", "��", "��", "���", "���", "���",
				"������", "����������", "�������", "�����", "���������", "�����", "������"
			],
			monthNames: [
				"���", "���", "���", "���", "���", "���", "���", "���", "���", "���", "���", "���",
				"������", "��������", "����", "�����", "���", "���", "���", "������", "���������", "��������", "�������", "��������"
			],
			AmPm : ["","","",""],
			S: function (j) {
				if(j==7 || j==8 || j== 27 || j== 28) {
					return '��';
				}
				return ['��', '��', '��'][Math.min((j - 1) % 10, 2)];
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
