;(function ($) {
/**
 * jqGrid Persian Translation
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
**/
	$.jgrid = $.jgrid || {};
	$.extend($.jgrid,{
        defaults: {
            recordtext: "نمابش {0} - {1} از {2}",
            emptyrecords: "رکوردی یافت نشد",
            loadtext: "بارگزاري...",
            pgtext: "صفحه {0} از {1}"
        },
        search: {
            caption: "جستجو...",
            Find: "يافته ها",
            Reset: "از نو",
            odata: [{ oper:'eq', text:"برابر"},{ oper:'ne', text:"نا برابر"},{ oper:'lt', text:"به"},{ oper:'le', text:"کوچکتر"},{ oper:'gt', text:"از"},{ oper:'ge', text:"بزرگتر"},{ oper:'bw', text:"شروع با"},{ oper:'bn', text:"شروع نشود با"},{ oper:'in', text:"نباشد"},{ oper:'ni', text:"عضو این نباشد"},{ oper:'ew', text:"اتمام با"},{ oper:'en', text:"تمام نشود با"},{ oper:'cn', text:"حاوی"},{ oper:'nc', text:"نباشد حاوی"},{ oper:'nu', text:'is null'},{ oper:'nn', text:'is not null'}],
            groupOps: [{
                op: "AND",
                text: "کل"
            },
            {
                op: "OR",
                text: "مجموع"
            }],
			operandTitle : "Click to select search operation.",
			resetTitle : "Reset Search Value"
        },
        edit: {
            addCaption: "اضافه کردن رکورد",
            editCaption: "ويرايش رکورد",
            bSubmit: "ثبت",
            bCancel: "انصراف",
            bClose: "بستن",
            saveData: "دیتا تعییر کرد! ذخیره شود؟",
            bYes: "بله",
            bNo: "خیر",
            bExit: "انصراف",
            msg: {
                required: "فيلدها بايد ختما پر شوند",
                number: "لطفا عدد وعتبر وارد کنيد",
                minValue: "مقدار وارد شده بايد بزرگتر يا مساوي با",
                maxValue: "مقدار وارد شده بايد کوچکتر يا مساوي",
                email: "پست الکترونيک وارد شده معتبر نيست",
                integer: "لطفا يک عدد صحيح وارد کنيد",
                date: "لطفا يک تاريخ معتبر وارد کنيد",
                url: "این آدرس صحیح نمی باشد. پیشوند نیاز است ('http://' یا 'https://')",
                nodefined: " تعریف نشده!",
                novalue: " مقدار برگشتی اجباری است!",
                customarray: "تابع شما باید مقدار آرایه داشته باشد!",
                customfcheck: "برای داشتن متد دلخواه شما باید سطون با چکینگ دلخواه داشته باشید!"
            }
        },
        view: {
            caption: "نمایش رکورد",
            bClose: "بستن"
        },
        del: {
            caption: "حذف",
            msg: "از حذف گزينه هاي انتخاب شده مطمئن هستيد؟",
            bSubmit: "حذف",
            bCancel: "ابطال"
        },
        nav: {
            edittext: " ",
            edittitle: "ويرايش رديف هاي انتخاب شده",
            addtext: " ",
            addtitle: "افزودن رديف جديد",
            deltext: " ",
            deltitle: "حذف ردبف هاي انتیاب شده",
            searchtext: " ",
            searchtitle: "جستجوي رديف",
            refreshtext: "",
            refreshtitle: "بازيابي مجدد صفحه",
            alertcap: "اخطار",
            alerttext: "لطفا يک رديف انتخاب کنيد",
            viewtext: "",
            viewtitle: "نمایش رکورد های انتخاب شده"
        },
        col: {
            caption: "نمايش/عدم نمايش ستون",
            bSubmit: "ثبت",
            bCancel: "انصراف"
        },
        errors: {
            errcap: "خطا",
            nourl: "هيچ آدرسي تنظيم نشده است",
            norecords: "هيچ رکوردي براي پردازش موجود نيست",
            model: "طول نام ستون ها محالف ستون هاي مدل مي باشد!"
        },
        formatter: {
            integer: {
                thousandsSeparator: " ",
                defaultValue: "0"
            },
            number: {
                decimalSeparator: ".",
                thousandsSeparator: " ",
                decimalPlaces: 2,
                defaultValue: "0.00"
            },
            currency: {
                decimalSeparator: ".",
                thousandsSeparator: " ",
                decimalPlaces: 2,
                prefix: "",
                suffix: "",
                defaultValue: "0"
            },
            date: {
                dayNames: ["يک", "دو", "سه", "چهار", "پنج", "جمع", "شنب", "يکشنبه", "دوشنبه", "سه شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"],
                monthNames: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "ژانويه", "فوريه", "مارس", "آوريل", "مه", "ژوئن", "ژوئيه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "December"],
                AmPm: ["ب.ظ", "ب.ظ", "ق.ظ", "ق.ظ"],
                S: function (b) {
                    return b < 11 || b > 13 ? ["st", "nd", "rd", "th"][Math.min((b - 1) % 10, 3)] : "th"
                },
                srcformat: "Y-m-d",
                newformat: "d/m/Y",
				parseRe : /[#%\\\/:_;.,\t\s-]/,
                masks: {
                    ISO8601Long: "Y-m-d H:i:s",
                    ISO8601Short: "Y-m-d",
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
                reformatAfterEdit: false
            },
            baseLinkUrl: "",
            showAction: "نمايش",
            target: "",
            checkbox: {
                disabled: true
            },
            idName: "id"
        }
    });
})(jQuery);