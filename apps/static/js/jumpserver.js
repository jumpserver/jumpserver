//jumpserver 自定义js 2015-01-29

//此函数用于checkbox的全选和反选
var checked=false;
function check_all(form) {
    var checkboxes = document.getElementById(form);
    if (checked === false) {
        checked = true;
    } else {
        checked = false;
    }
    for (var i = 0; i < checkboxes.elements.length; i++) {
        if (checkboxes.elements[i].type == "checkbox") {
            checkboxes.elements[i].checked = checked;
        }
    }
}

function checkAll(id, name){
    var checklist = document.getElementsByName(name);
    if(document.getElementById(id).checked)
        {
        for(var i=0;i<checklist.length;i++)
        {
          checklist[i].checked = 1;
        }
    }else{
        for(var j=0;j<checklist.length;j++)
        {
         checklist[j].checked = 0;
        }
    }
}

//提取指定行的数据，JSON格式
function GetRowData(row){
    var rowData = {};
    for(var j=0;j<row.cells.length; j++) {
        name = row.parentNode.rows[0].cells[j].getAttribute("Name");
        if (name) {
            var value = row.cells[j].getAttribute("Value");
            if (!value) {
                value = row.cells[j].innerHTML;
            }
            rowData[name] = value;
        }
    }
    return rowData;
}

//此函数用于在多选提交时至少要选择一行
function GetTableDataBox() {
    var tabProduct = document.getElementById("editable");
    var tableData = [];
    var returnData = [];
    var checkboxes = document.getElementById("contents_form");
    var id_list = [];
    len = checkboxes.elements.length;
    for (var i=0; i < len; i++) {
        if (checkboxes.elements[i].type == "checkbox" && checkboxes.elements[i].checked === true && checkboxes.elements[i].value != "checkall") {
            id_list.push(i);
         }
        }
    for (i in id_list) {
        tableData.push(GetRowData(tabProduct.rows[id_list[i]]));
    }

    if (id_list.length === 0){
        alert('请至少选择一行！');
    }
    returnData.push(tableData);
    returnData.push(id_list.length);
    return returnData;
}

function move(from, to, from_o, to_o) {
    $("#" + from + " option").each(function () {
        if ($(this).prop("selected") === true) {
            $("#" + to).append(this);
            if( typeof from_o !== 'undefined'){
                $("#"+to_o).append($("#"+from_o +" option[value='"+this.value+"']"));
            }
        }
    });
}

function move_left(from, to, from_o, to_o) {
    $("#" + from + " option").each(function () {
        if ($(this).prop("selected") === true) {
            $("#" + to).append(this);
            if( typeof from_o !== 'undefined'){
                $("#"+to_o).append($("#"+from_o +" option[value='"+this.value+"']"));
            }
        }
        $(this).attr("selected",'true');
    });
}


function selectAll(){
    // Select all check box
    $('option').each(function(){
        $(this).attr('selected', true);
    });
}


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                // break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function setAjaxCSRFToken() {
    var csrftoken = getCookie('csrftoken');
    var sessionid = getCookie('sessionid');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

function activeNav() {
    var url_array = document.location.pathname.split("/");
    var app = url_array[1];
    var resource = url_array[2];
    if (app === ''){
        $('#index').addClass('active');
    }
    else if (app === 'xpack' && resource === 'cloud') {
        var item = url_array[3];
        $("#" + app).addClass('active');
        $('#' + app + ' #' + resource).addClass('active');
        $('#' + app + ' #' + resource + ' #' + item + ' a').css('color', '#ffffff');
    }
    else if (app === 'settings'){
        $("#" + app).addClass('active');
    }
    else {
        $("#" + app).addClass('active');
        $('#' + app + ' #' + resource).addClass('active');
    }
}

function formSubmit(props) {
    /*
    {
      "form": $("form"),
      "url": "",
      "method": "POST",
      "redirect_to": "",
      "success": function(data, textStatue, jqXHR){},
      "error": function(jqXHR, textStatus, errorThrown) {}
    }
    */
    props = props || {};
    var data = props.data || props.form.serializeObject();
    var redirect_to = props.redirect_to;
    $.ajax({
        url: props.url,
        type: props.method || 'POST',
        data: JSON.stringify(data),
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json"
    }).done(function (data, textState, jqXHR) {
        if (redirect_to) {
            location.href = redirect_to;
        } else if (typeof props.success === 'function') {
            return props.success(data, textState, jqXHR);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        if (typeof props.error === 'function') {
            return props.error(jqXHR, textStatus, errorThrown)
        }
        if (!props.form) {
            alert(jqXHR.responseText);
            return
        }
        if (jqXHR.status === 400) {
            var errors = jqXHR.responseJSON;
            var noneFieldErrorRef = props.form.children('.alert-danger');
            if (noneFieldErrorRef.length !== 1) {
                props.form.prepend('<div class="alert alert-danger" style="display: none"></div>');
                noneFieldErrorRef = props.form.children('.alert-danger');
            }
            var noneFieldErrorMsg = "";
            noneFieldErrorRef.css("display", "none");
            noneFieldErrorRef.html("");
            props.form.find(".help-block.error").html("");
            props.form.find(".form-group.has-error").removeClass("has-error");

            if (typeof errors !== "object") {
                noneFieldErrorMsg = errors;
                if (noneFieldErrorRef.length === 1) {
                    noneFieldErrorRef.css('display', 'block');
                    noneFieldErrorRef.html(noneFieldErrorMsg);
                }
                return
            }
            $.each(errors, function (k, v) {
                var fieldRef = props.form.find('input[name="' + k + '"]');
                var formGroupRef = fieldRef.parents('.form-group');
                var parentRef = fieldRef.parent();
                var helpBlockRef = parentRef.children('.help-block.error');
                if (helpBlockRef.length === 0) {
                    parentRef.append('<div class="help-block error"></div>');
                    helpBlockRef = parentRef.children('.help-block.error');
                }
                if (fieldRef.length === 1 && formGroupRef.length === 1) {
                    formGroupRef.addClass('has-error');
                    var help_msg = v.join("<br/>") ;
                    helpBlockRef.html(help_msg);
                } else {
                    noneFieldErrorMsg += v + '<br/>';
                }
            });
            if (noneFieldErrorRef.length === 1 && noneFieldErrorMsg !== '') {
                noneFieldErrorRef.css('display', 'block');
                noneFieldErrorRef.html(noneFieldErrorMsg);
            }
        }

    })
}

function APIUpdateAttr(props) {
    // props = {url: .., body: , success: , error: , method: ,}
    props = props || {};
    var user_success_message = props.success_message;
    var default_success_message = gettext('Update is successful!');
    var user_fail_message = props.fail_message;
    var default_failed_message = gettext('An unknown error occurred while updating..');
    var flash_message = props.flash_message || true;
    if (props.flash_message === false){
        flash_message = false;
    }

    $.ajax({
        url: props.url,
        type: props.method || "PATCH",
        data: props.body,
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json"
    }).done(function(data, textStatue, jqXHR) {
        if (flash_message) {
            var msg = "";
            if (user_fail_message) {
                msg = user_success_message;
            } else {
                msg = default_success_message;
            }
            toastr.success(msg);
        }
        if (typeof props.success === 'function') {
            return props.success(data);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        if (flash_message) {
            var msg = "";
            if (user_fail_message) {
                msg = user_fail_message;
            } else if (jqXHR.responseJSON) {
                if (jqXHR.responseJSON.error) {
                    msg = jqXHR.responseJSON.error
                } else if (jqXHR.responseJSON.msg) {
                    msg = jqXHR.responseJSON.msg
                }
            }
            if (msg === "") {
                msg = default_failed_message;
            }
            toastr.error(msg);
        }
        if (typeof props.error === 'function') {
            console.log(jqXHR);
            return props.error(jqXHR.responseText, jqXHR.status);
        }
    });
  // return true;
}

// Sweet Alert for Delete
function objectDelete(obj, name, url, redirectTo) {
    function doDelete() {
        var body = {};
        var success = function() {
            // swal('Deleted!', "[ "+name+"]"+" has been deleted ", "success");
            if (!redirectTo) {
                $(obj).parent().parent().remove();
            } else {
                window.location.href=redirectTo;
            }
        };
        var fail = function() {
            // swal("错误", "删除"+"[ "+name+" ]"+"遇到错误", "error");
            swal(gettext('Error'), "[ "+name+" ]" + gettext("Being used by the asset, please unbind the asset first."), "error");
        };
        APIUpdateAttr({
            url: url,
            body: JSON.stringify(body),
            method: 'DELETE',
            success_message: gettext("Delete the success"),
            success: success,
            error: fail
        });
    }
    swal({
        title: gettext('Are you sure about deleting it?'),
        text: " [" + name + "] ",
        type: "warning",
        showCancelButton: true,
        cancelButtonText: gettext('Cancel'),
        confirmButtonColor: "#ed5565",
        confirmButtonText: gettext('Confirm'),
        closeOnConfirm: true,
    }, function () {
        doDelete()
    });
}

function orgDelete(obj, name, url, redirectTo){
    function doDelete() {
        var body = {};
        var success = function() {
            if (!redirectTo) {
                $(obj).parent().parent().remove();
            } else {
                window.location.href=redirectTo;
            }
        };
        var fail = function(responseText, status) {
            if (status === 400){
                swal(gettext("Error"),  "[ " + name + " ] " + gettext("The organization contains undeleted information. Please try again after deleting"), "error");
            }
            else if (status === 405){
                swal(gettext("Error"), " [ "+ name + " ] " + gettext("Do not perform this operation under this organization. Try again after switching to another organization"), "error");
            }
        };
        APIUpdateAttr({
            url: url,
            body: JSON.stringify(body),
            method: 'DELETE',
            success_message: gettext("Delete the success"),
            success: success,
            error: fail
        });
    }
    swal({
        title: gettext("Please ensure that the following information in the organization has been deleted"),
        text: gettext("User list、User group、Asset list、Domain list、Admin user、System user、Labels、Asset permission"),
        type: "warning",
        showCancelButton: true,
        cancelButtonText: gettext('Cancel'),
        confirmButtonColor: "#ed5565",
        confirmButtonText: gettext('Confirm'),
        closeOnConfirm: true
    }, function () {
        doDelete();
    });
}

$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};

function makeLabel(data) {
    return "<label class='detail-key'><b>" + data[0] + ": </b></label>" + data[1] + "</br>"
}



var jumpserver = {};
jumpserver.checked = false;
jumpserver.selected = {};
jumpserver.language = {
    processing: gettext('Loading ...'),
    search: gettext('Search'),
    select: {
        rows: {
            _:  gettext("Selected item %d"),
            0: ""
        }
    },
    lengthMenu: gettext("Per page _MENU_"),
    info: gettext('Displays the results of items _START_ to _END_; A total of _TOTAL_ entries'),
    infoFiltered: "",
    infoEmpty: "",
    zeroRecords: gettext("No match"),
    emptyTable: gettext('No record'),
    paginate: {
        first: "«",
        previous: "‹",
        next: "›",
        last: "»"
    }
};
jumpserver.initDataTable = function (options) {
  // options = {
  //    ele *: $('#dataTable_id'),
  //    ajax_url *: '{% url 'users:user-list-api' %}',
  //    columns *: [{data: ''}, ....],
  //    dom: 'fltip',
  //    i18n_url: '{% static "js/...../en-us.json" %}',
  //    order: [[1, 'asc'], [2, 'asc'], ...],
  //    buttons: ['excel', 'pdf', 'print'],
  //    columnDefs: [{target: 0, createdCell: ()=>{}}, ...],
  //    uc_html: '<a>header button</a>',
  //    op_html: 'div.btn-group?',
  //    paging: true
  // }
  var ele = options.ele || $('.dataTable');
  var columnDefs = [
      {
          targets: 0,
          orderable: false,
          createdCell: function (td, cellData) {
              $(td).html('<input type="checkbox" class="text-center ipt_check" id=99991937>'.replace('99991937', cellData));
          }
      },
      {className: 'text-center', render: $.fn.dataTable.render.text(), targets: '_all'}
  ];
  columnDefs = options.columnDefs ? options.columnDefs.concat(columnDefs) : columnDefs;
  var select = {
            style: 'multi',
            selector: 'td:first-child'
      };
  var table = ele.DataTable({
        pageLength: options.pageLength || 15,
        dom: options.dom || '<"#uc.pull-left">flt<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        order: options.order || [],
        // select: options.select || 'multi',
        buttons: [],
        columnDefs: columnDefs,
        ajax: {
            url: options.ajax_url,
            dataSrc: ""
        },
        columns: options.columns || [],
        select: options.select || select,
        language: jumpserver.language,
        lengthMenu: [[10, 15, 25, 50, -1], [10, 15, 25, 50, "All"]]
    });
    table.on('select', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', true);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = true
    }).on('deselect', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', false);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = false
    }).on('draw', function(){
        $('#op').html(options.op_html || '');
        $('#uc').html(options.uc_html || '');
        $('[data-toggle="popover"]').popover({
            html: true,
            placement: 'bottom',
            // trigger: 'hover',
            container: 'body'
        });
    });
    $('.ipt_check_all').on('click', function() {
      if ($(this).prop("checked")) {
          $(this).closest('table').find('.ipt_check').prop('checked', true);
          jumpserver.checked = true;
          table.rows({search:'applied', page:'current'}).select();
      } else {
          $(this).closest('table').find('.ipt_check').prop('checked', false);
          jumpserver.checked = false;
          table.rows({search:'applied', page:'current'}).deselect();
      }
    });

    return table;
};

jumpserver.initStaticTable = function (selector) {
    $(selector).DataTable({
        "searching": false,
        "bInfo": false,
        "paging": false,
        "order": [],
        "language": jumpserver.language
    });
};

jumpserver.initServerSideDataTable = function (options) {
  // options = {
  //    ele *: $('#dataTable_id'),
  //    ajax_url *: '{% url 'users:user-list-api' %}',
  //    columns *: [{data: ''}, ....],
  //    dom: 'fltip',
  //    i18n_url: '{% static "js/...../en-us.json" %}',
  //    order: [[1, 'asc'], [2, 'asc'], ...],
  //    buttons: ['excel', 'pdf', 'print'],
  //    columnDefs: [{target: 0, createdCell: ()=>{}}, ...],
  //    uc_html: '<a>header button</a>',
  //    op_html: 'div.btn-group?',
  //    paging: true
  // }
  var ele = options.ele || $('.dataTable');
  var columnDefs = [
      {
          targets: 0,
          orderable: false,
          createdCell: function (td, cellData) {
              $(td).html('<input type="checkbox" class="text-center ipt_check" id=99991937>'.replace('99991937', cellData));
          }
      },
      {
          targets: '_all',
          className: 'text-center',
          render: $.fn.dataTable.render.text()
      }
  ];
  columnDefs = options.columnDefs ? options.columnDefs.concat(columnDefs) : columnDefs;
  var select = {
            style: 'multi',
            selector: 'td:first-child'
      };
  var table = ele.DataTable({
        pageLength: options.pageLength || 15,
        dom: options.dom || '<"#uc.pull-left">fltr<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        order: options.order || [],
        buttons: [],
        columnDefs: columnDefs,
        serverSide: true,
        processing: true,
        ajax: {
            url: options.ajax_url ,
            error: function(jqXHR, textStatus, errorThrown) {
                var msg = gettext("Unknown error occur");
                if (jqXHR.responseJSON) {
                    if (jqXHR.responseJSON.error) {
                        msg = jqXHR.responseJSON.error
                    } else if (jqXHR.responseJSON.msg) {
                        msg = jqXHR.responseJSON.msg
                    }
                }
                alert(msg)
            },
            data: function (data) {
                delete data.columns;
                if (data.length !== null){
                    data.limit = data.length;
                    delete data.length;
                }
                if (data.start !== null) {
                    data.offset = data.start;
                    delete data.start;
                }
                if (data.search !== null) {
                    var search_val = data.search.value;
                    var search_list = search_val.split(" ");
                    var search_attr = {};
                    var search_raw = [];

                    search_list.map(function (val, index) {
                       var kv = val.split(":");
                       if (kv.length === 2) {
                           search_attr[kv[0]] = kv[1]
                       } else {
                           search_raw.push(kv)
                       }
                    });
                    data.search = search_raw.join("");
                    $.each(search_attr, function (k, v) {
                        data[k] = v
                    })
                }
                if (data.order !== null && data.order.length === 1) {
                    var col = data.order[0].column;
                    var order = options.columns[col].data;
                    if (data.order[0].dir === "desc") {
                        order = "-" + order;
                    }
                    data.order = order;
                }
            },
            dataFilter: function(data){
                var json = jQuery.parseJSON( data );
                json.recordsTotal = json.count;
                json.recordsFiltered = json.count;
                return JSON.stringify(json); // return JSON string
            },
            dataSrc: "results"
        },
        columns: options.columns || [],
        select: options.select || select,
        language: jumpserver.language,
        lengthMenu: [[15, 25, 50, 9999], [15, 25, 50, 'All']]
    });
    table.selected = [];
    table.selected_rows = [];
    table.on('select', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', true);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = true;
        if (type === 'row') {
            var rows = table.rows(indexes).data();
            $.each(rows, function (id, row) {
                table.selected_rows.push(row);
                if (row.id && $.inArray(row.id, table.selected) === -1){
                    table.selected.push(row.id)
                }
            })
        }
    }).on('deselect', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', false);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = false;
        if (type === 'row') {
            var rows = table.rows(indexes).data();
            $.each(rows, function (id, row) {
                if (row.id){
                    var index = table.selected.indexOf(row.id);
                    if (index > -1){
                        table.selected.splice(index, 1)
                    }
                }
            })
        }
    }).on('draw', function(){
        $('#op').html(options.op_html || '');
        $('#uc').html(options.uc_html || '');
        var table_data = [];
        $.each(table.rows().data(), function (id, row) {
            if (row.id) {
                table_data.push(row.id)
            }
        });

        $.each(table.selected, function (id, data) {
            var index = table_data.indexOf(data);
            if (index > -1){
                table.rows(index).select()
            }
        });
    });
    var table_id = table.settings()[0].sTableId;
    $('#' + table_id + ' .ipt_check_all').on('click', function() {
        if ($(this).prop("checked")) {
            $(this).closest('table').find('.ipt_check').prop('checked', true);
            table.rows({search:'applied', page:'current'}).select();
        } else {
            $(this).closest('table').find('.ipt_check').prop('checked', false);
            table.rows({search:'applied', page:'current'}).deselect();
        }
    });

    // jumpserver.table = table;
    return table;
};

/**
 * 替换所有匹配exp的字符串为指定字符串
 * @param exp 被替换部分的正则
 * @param newStr 替换成的字符串
 */
String.prototype.replaceAll = function (exp, newStr) {
    return this.replace(new RegExp(exp, "gm"), newStr);
};

/**
 * 原型：字符串格式化
 * @param args 格式化参数值
 */
String.prototype.format = function(args) {
    var result = this;
    if (arguments.length < 1) {
        return result;
    }

    var data = arguments;
    if (arguments.length == 1 && typeof (args) == "object") {
        data = args;
    }
    for ( var key in data) {
        var value = data[key];
        if (undefined != value) {
            result = result.replaceAll("\\{" + key + "\\}", value);
        }
    }
    return result;
};

function setCookie(key, value, time) {
    var expires = new Date();
    if (!time) {
        time =  expires.getTime() + (24 * 60 * 60 * 1000);
    }
    expires.setTime(time);
    document.cookie = key + '=' + value + ';expires=' + expires.toUTCString() + ';path=/';
}


function delCookie(key) {
    var expires = new Date();
    expires.setTime(expires.getTime() - 1);
    var val = getCookie(key);
    if (val !== null) {
        document.cookie = key + '=' + val + ";expires" + expires.toUTCString() + ';path=/';
    }
}

function createPopover(dataset, title, callback) {
    if (callback !== undefined){
        var new_dataset = [];
        $.each(dataset, function (index, value) {
            new_dataset.push(callback(value))
        });
        dataset = new_dataset;
    }
    var data_content = dataset.join("</br>");

    var html = "<a data-toggle='popover' data-content='" + data_content + "'>" + dataset.length + "</a>";
    return html;
}


 $(function () {
    (function ($) {
        $.getUrlParam = function (name) {
            var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");
            var r = window.location.search.substr(1).match(reg);
            if (r != null) return unescape(r[2]); return null;
        }
    })(jQuery);
});

function getUrlParam(name) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");
    var r = window.location.search.substr(1).match(reg);
    if (r != null) return unescape(r[2]); return null;
}

function setUrlParam(url, name, value) {
    var urlArray = url.split("?");
    if (urlArray.length===1){
        url += "?" + name + "=" + value;
    } else {
        var oriParam = urlArray[1].split("&");
        var oriParamMap = {};
        $.each(oriParam, function (index, value) {
            var v = value.split("=");
            oriParamMap[v[0]] = v[1];
        });
        oriParamMap[name] = value;
        url = urlArray[0] + "?";
        var newParam = [];
        $.each(oriParamMap, function (index, value) {
            newParam.push(index + "=" + value);
        });
        url += newParam.join("&")
    }
    return url
}

// Password check rules
var rules_short_map_id = {
    'min': 'id_security_password_min_length',
    'upper': 'id_security_password_upper_case',
    'lower': 'id_security_password_lower_case',
    'number': 'id_security_password_number',
    'special': 'id_security_password_special_char'
};

var rules_id_map_label = {
    'id_security_password_min_length': gettext('Password minimum length {N} bits'),
    'id_security_password_upper_case': gettext('Must contain capital letters'),
    'id_security_password_lower_case': gettext('Must contain lowercase letters'),
    'id_security_password_number': gettext('Must contain numeric characters'),
    'id_security_password_special_char': gettext('Must contain special characters')
};

function getRuleLabel(rule){
    var label = '';
    if (rule.key === rules_short_map_id['min']){
        label = rules_id_map_label[rule.key].replace('{N}', rule.value)
    }
    else{
        label = rules_id_map_label[rule.key]
    }
    return label
}

// 校验密码-改变规则颜色
function checkPasswordRules(password, minLength) {
    if (wordMinLength(password, minLength)) {
        $('#'+rules_short_map_id['min']).css('color', 'green')
    }
    else {
        $('#'+rules_short_map_id['min']).css('color', '#908a8a')
    }

    if (wordUpperCase(password)) {
        $('#'+rules_short_map_id['upper']).css('color', 'green')
    }
    else {
        $('#'+rules_short_map_id['upper']).css('color', '#908a8a')
    }

    if (wordLowerCase(password)) {
        $('#'+rules_short_map_id['lower']).css('color', 'green')
    }
    else {
        $('#'+rules_short_map_id['lower']).css('color', '#908a8a')
    }

    if (wordNumber(password)) {
        $('#'+rules_short_map_id['number']).css('color', 'green')
    }
    else {
        $('#'+rules_short_map_id['number']).css('color', '#908a8a')
    }

    if (wordSpecialChar(password)) {
        $('#'+rules_short_map_id['special']).css('color', 'green')
    }
    else {
        $('#'+rules_short_map_id['special']).css('color', '#908a8a')
    }
}

// 最小长度
function wordMinLength(word, minLength) {
    //var minLength = {{ min_length }};
    var re = new RegExp("^(.{" + minLength + ",})$");
    return word.match(re)
}
// 大写字母
function wordUpperCase(word) {
    return word.match(/([A-Z]+)/)
}
// 小写字母
function wordLowerCase(word) {
    return word.match(/([a-z]+)/)
}
// 数字字符
function wordNumber(word) {
    return word.match(/([\d]+)/)
}
// 特殊字符
function wordSpecialChar(word) {
    return word.match(/[`,~,!,@,#,\$,%,\^,&,\*,\(,\),\-,_,=,\+,\{,\},\[,\],\|,\\,;,',:,",\,,\.,<,>,\/,\?]+/)
}


// 显示弹窗密码规则
function popoverPasswordRules(password_check_rules, $el) {
    var message = "";
    jQuery.each(password_check_rules, function (idx, rule) {
        message += "<li id=" + rule.key + " style='list-style-type:none;'> <i class='fa fa-check-circle-o' style='margin-right:10px;' ></i>" + getRuleLabel(rule) + "</li>";
    });
    //$('#id_password_rules').html(message);
    $el.html(message)
}

// 初始化弹窗popover
function initPopover($container, $progress, $idPassword, $el, password_check_rules, i18n_fallback){
    options = {};
    // User Interface
    options.ui = {
        container: $container,
        viewports: {
            progress: $progress
            //errors: $('.popover-content')
        },
        showProgressbar: true,
        showVerdictsInsideProgressBar: true
    };
    options.i18n = {
        fallback: i18n_fallback,
        t: function (key) {
            var result = '';
            result = options.i18n.fallback[key];
            return result === key ? '' : result;
        }
    };
    $idPassword.pwstrength(options);
    popoverPasswordRules(password_check_rules, $el);
}

// 解决input框中的资产和弹出表格中资产的显示不一致
function initSelectedAssets2Table(){
    var inputAssets = $('#id_assets').val();
    var selectedAssets = asset_table2.selected.concat();

    // input assets无，table assets选中，则取消勾选(再次click)
    if (selectedAssets.length !== 0){
        $.each(selectedAssets, function (index, assetId){
            if ($.inArray(assetId, inputAssets) === -1){
                $('#'+assetId).trigger('click');  // 取消勾选
            }
        });
    }

    // input assets有，table assets没选，则选中(click)
    if (inputAssets !== null){
        asset_table2.selected = inputAssets;
        $.each(inputAssets, function(index, assetId){
            var dom = document.getElementById(assetId);
            if (dom !== null){
                var selected = dom.parentElement.parentElement.className.indexOf('selected')
            }
            if (selected === -1){
                $('#'+assetId).trigger('click');
            }
        });
    }
}


function rootNodeAddDom(ztree, callback) {
    var refreshIcon = "<a id='tree-refresh'><i class='fa fa-refresh'></i></a>";
    var rootNode = ztree.getNodes()[0];
    var $rootNodeRef = $("#" + rootNode.tId + "_a");
    $rootNodeRef.after(refreshIcon);
    var refreshIconRef = $('#tree-refresh');
    refreshIconRef.bind('click', function () {
        ztree.destroy();
        callback()
    })
}

function APIExportData(props) {
    props = props || {};
    $.ajax({
        url: '/api/common/v1/resources/cache/',
        type: props.method || "POST",
        data: props.body,
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json",
        success: function (data) {
            var export_url = props.success_url;
            var params = props.params || {};
            params['format'] = props.format;
            params['spm'] = data.spm;
            for (var k in params){
                export_url = setUrlParam(export_url, k, params[k])
            }
            window.open(export_url);
        },
        error: function () {
            toastr.error(gettext('Export failed'));
        }
    })
}

function APIImportData(props){
    props = props || {};
    $.ajax({
        url: props.url,
        type: props.method || "POST",
        processData: false,
        data: props.body,
        contentType: props.content_type || 'text/csv',
        success: function (data) {
            if(props.method === 'POST'){
                $('#created_failed').html('');
                $('#created_failed_detail').html('');
                $('#success_created').html(gettext("Import Success"));
                $('#success_created_detail').html("Count" + ": " + data.length);
            }else{
                $('#updated_failed').html('');
                $('#updated_failed_detail').html('');
                $('#success_updated').html(gettext("Update Success"));
                $('#success_updated_detail').html("Count" + ": " + data.length);
            }

            props.data_table.ajax.reload()
        },
        error: function (error) {
            var data = error.responseJSON;
            if (data instanceof Array){
                var html = '';
                var li = '';
                var err = '';
                $.each(data, function (index, item){
                    err = '';
                    for (var prop in item) {
                        err += prop + ": " + item[prop][0] + " "
                    }
                    if (err) {
                        li = "<li>" + "Line " + (++index) + ". " + err + "</li>";
                        html += li
                    }
                });
                html = "<ul>" + html + "</ul>"
            }
            else {
                html = error.responseText
            }
            if(props.method === 'POST'){
                $('#success_created').html('');
                $('#success_created_detail').html('');
                $('#created_failed').html(gettext("Import failed"));
                $('#created_failed_detail').html(html);
            }else{
                $('#success_updated').html('');
                $('#success_updated_detail').html('');
                $('#updated_failed').html(gettext("Update failed"));
                $('#updated_failed_detail').html(html);
            }
        }
    })
}


function htmlEscape ( d ) {
    return typeof d === 'string' ?
        d.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') :
        d;
}
