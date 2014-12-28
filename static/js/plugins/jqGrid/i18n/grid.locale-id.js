;(function($){
/**
 * jqGrid English Translation
 * Tony Tomov tony@trirand.com
 * http://trirand.com/blog/ 
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
$.jgrid = $.jgrid || {};
$.extend($.jgrid,{
	defaults : {
		recordtext: "Data {0} - {1} dari {2}",
		emptyrecords: "Tidak ada data",
		loadtext: "Memuat...",
		pgtext : "Halaman {0} dari {1}"
	},
	search : {
		caption: "Pencarian",
		Find: "Cari !",
		Reset: "Segarkan",
		odata: [{ oper:'eq', text:"sama dengan"},{ oper:'ne', text:"tidak sama dengan"},{ oper:'lt', text:"kurang dari"},{ oper:'le', text:"kurang dari atau sama dengan"},{ oper:'gt', text:"lebih besar"},{ oper:'ge', text:"lebih besar atau sama dengan"},{ oper:'bw', text:"dimulai dengan"},{ oper:'bn', text:"tidak dimulai dengan"},{ oper:'in', text:"di dalam"},{ oper:'ni', text:"tidak di dalam"},{ oper:'ew', text:"diakhiri dengan"},{ oper:'en', text:"tidak diakhiri dengan"},{ oper:'cn', text:"mengandung"},{ oper:'nc', text:"tidak mengandung"},{ oper:'nu', text:'is null'},{ oper:'nn', text:'is not null'}],
		groupOps: [	{ op: "AND", text: "all" },	{ op: "OR",  text: "any" }	],
		operandTitle : "Click to select search operation.",
		resetTitle : "Reset Search Value"
	},
	edit : {
		addCaption: "Tambah Data",
		editCaption: "Sunting Data",
		bSubmit: "Submit",
		bCancel: "Tutup",
		bClose: "Tutup",
		saveData: "Data telah berubah! Simpan perubahan?",
		bYes : "Ya",
		bNo : "Tidak",
		bExit : "Tutup",
		msg: {
			required:"kolom wajib diisi",
			number:"hanya nomer yang diperbolehkan",
			minValue:"kolom harus lebih besar dari atau sama dengan",
			maxValue:"kolom harus lebih kecil atau sama dengan",
			email: "alamat e-mail tidak valid",
			integer: "hanya nilai integer yang diperbolehkan",
			date: "nilai tanggal tidak valid",
			url: "Bukan URL yang valid. Harap gunakan ('http://' or 'https://')",
			nodefined : " belum didefinisikan!",
			novalue : " return value is required!",
			customarray : "Custom function should return array!",
			customfcheck : "Custom function should be present in case of custom checking!"
			
		}
	},
	view : {
		caption: "Menampilkan data",
		bClose: "Tutup"
	},
	del : {
		caption: "Hapus",
		msg: "Hapus data terpilih?",
		bSubmit: "Hapus",
		bCancel: "Batalkan"
	},
	nav : {
		edittext: "",
		edittitle: "Sunting data terpilih",
		addtext:"",
		addtitle: "Tambah baris baru",
		deltext: "",
		deltitle: "Hapus baris terpilih",
		searchtext: "",
		searchtitle: "Temukan data",
		refreshtext: "",
		refreshtitle: "Segarkan Grid",
		alertcap: "Warning",
		alerttext: "Harap pilih baris",
		viewtext: "",
		viewtitle: "Tampilkan baris terpilih"
	},
	col : {
		caption: "Pilih Kolom",
		bSubmit: "Ok",
		bCancel: "Batal"
	},
	errors : {
		errcap : "Error",
		nourl : "Tidak ada url yang diset",
		norecords: "Tidak ada data untuk diproses",
		model : "Lebar dari colNames <> colModel!"
	},
	formatter : {
		integer : {thousandsSeparator: ".", defaultValue: '0'},
		number : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, defaultValue: '0'},
		currency : {decimalSeparator:",", thousandsSeparator: ".", decimalPlaces: 2, prefix: "Rp. ", suffix:"", defaultValue: '0'},
		date : {
			dayNames:   [
				"Ming", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab",
				"Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"
			],
			monthNames: [
				"Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
				"Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"
			],
			AmPm : ["am","pm","AM","PM"],
			S: function (j) {return j < 11 || j > 13 ? ['st', 'nd', 'rd', 'th'][Math.min((j - 1) % 10, 3)] : 'th';},
			srcformat: 'Y-m-d',
			newformat: 'n/j/Y',
			parseRe : /[#%\\\/:_;.,\t\s-]/,
			masks : {
				// see http://php.net/manual/en/function.date.php for PHP format used in jqGrid
				// and see http://docs.jquery.com/UI/Datepicker/formatDate
				// and https://github.com/jquery/globalize#dates for alternative formats used frequently
				// one can find on https://github.com/jquery/globalize/tree/master/lib/cultures many
				// information about date, time, numbers and currency formats used in different countries
				// one should just convert the information in PHP format
				ISO8601Long:"Y-m-d H:i:s",
				ISO8601Short:"Y-m-d",
				// short date:
				//    n - Numeric representation of a month, without leading zeros
				//    j - Day of the month without leading zeros
				//    Y - A full numeric representation of a year, 4 digits
				// example: 3/1/2012 which means 1 March 2012
				ShortDate: "n/j/Y", // in jQuery UI Datepicker: "M/d/yyyy"
				// long date:
				//    l - A full textual representation of the day of the week
				//    F - A full textual representation of a month
				//    d - Day of the month, 2 digits with leading zeros
				//    Y - A full numeric representation of a year, 4 digits
				LongDate: "l, F d, Y", // in jQuery UI Datepicker: "dddd, MMMM dd, yyyy"
				// long date with long time:
				//    l - A full textual representation of the day of the week
				//    F - A full textual representation of a month
				//    d - Day of the month, 2 digits with leading zeros
				//    Y - A full numeric representation of a year, 4 digits
				//    g - 12-hour format of an hour without leading zeros
				//    i - Minutes with leading zeros
				//    s - Seconds, with leading zeros
				//    A - Uppercase Ante meridiem and Post meridiem (AM or PM)
				FullDateTime: "l, F d, Y g:i:s A", // in jQuery UI Datepicker: "dddd, MMMM dd, yyyy h:mm:ss tt"
				// month day:
				//    F - A full textual representation of a month
				//    d - Day of the month, 2 digits with leading zeros
				MonthDay: "F d", // in jQuery UI Datepicker: "MMMM dd"
				// short time (without seconds)
				//    g - 12-hour format of an hour without leading zeros
				//    i - Minutes with leading zeros
				//    A - Uppercase Ante meridiem and Post meridiem (AM or PM)
				ShortTime: "g:i A", // in jQuery UI Datepicker: "h:mm tt"
				// long time (with seconds)
				//    g - 12-hour format of an hour without leading zeros
				//    i - Minutes with leading zeros
				//    s - Seconds, with leading zeros
				//    A - Uppercase Ante meridiem and Post meridiem (AM or PM)
				LongTime: "g:i:s A", // in jQuery UI Datepicker: "h:mm:ss tt"
				SortableDateTime: "Y-m-d\\TH:i:s",
				UniversalSortableDateTime: "Y-m-d H:i:sO",
				// month with year
				//    Y - A full numeric representation of a year, 4 digits
				//    F - A full textual representation of a month
				YearMonth: "F, Y" // in jQuery UI Datepicker: "MMMM, yyyy"
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
