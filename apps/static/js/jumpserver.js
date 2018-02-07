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
        console.log(tabProduct);
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
    } else {
        $("#" + app).addClass('active');
        $('#' + app + ' #' + resource).addClass('active');
    }
}

function APIUpdateAttr(props) {
    // props = {url: .., body: , success: , error: , method: ,}
    props = props || {};
    var success_message = props.success_message || '更新成功!';
    var fail_message = props.fail_message || '更新时发生未知错误.';
    var flash_message = true;
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
            toastr.success(success_message);
        }
        if (typeof props.success === 'function') {
            return props.success(data);
        } 
    }).fail(function(jqXHR, textStatus, errorThrown) {
        if (flash_message) {
            toastr.error(fail_message);
        }
        if (typeof props.error === 'function') {
            return props.error(jqXHR.responseText);
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
            swal("错误", "删除"+"[ "+name+" ]"+"遇到错误", "error");
        };
        APIUpdateAttr({
            url: url,
            body: JSON.stringify(body),
            method: 'DELETE',
            success: success,
            error: fail
        });
    }
    swal({
        title: '你确定删除吗 ?',
        text: " [" + name + "] ",
        type: "warning",
        showCancelButton: true,
        cancelButtonText: '取消',
        confirmButtonColor: "#ed5565",
        confirmButtonText: '确认',
        closeOnConfirm: true,
    }, function () {
        doDelete()       
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
var jumpserver = {};
jumpserver.checked = false;
jumpserver.selected = {};
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
      {className: 'text-center', targets: '_all'}
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
            url: options.ajax_url ,
            dataSrc: ""
        },
        columns: options.columns || [],
        select: options.select || select,
        language: {
            search: "搜索",
            lengthMenu: "每页  _MENU_",
            info: "显示第 _START_ 至 _END_ 项结果; 总共 _TOTAL_ 项",
            infoFiltered:   "",
            infoEmpty:      "",
            zeroRecords:    "没有匹配项",
            emptyTable:     "没有记录",
            paginate: {
                first:      "«",
                previous:   "‹",
                next:       "›",
                last:       "»"
            }
        },
        lengthMenu: [[15, 25, 50, -1], [15, 25, 50, "All"]]
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
      {className: 'text-center', targets: '_all'}
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
        serverSide: true,
        processing: true,
        ajax: {
            url: options.ajax_url ,
            data: function (data) {
                delete data.columns;
                if (data.length !== null ){
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
                    if (data.order[0].dir = "desc") {
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
        language: {
            search: "搜索",
            lengthMenu: "每页  _MENU_",
            info: "显示第 _START_ 至 _END_ 项结果; 总共 _TOTAL_ 项",
            infoFiltered:   "",
            infoEmpty:      "",
            zeroRecords:    "没有匹配项",
            emptyTable:     "没有记录",
            paginate: {
                first:      "«",
                previous:   "‹",
                next:       "›",
                last:       "»"
            }
        },
        lengthMenu: [[15, 25, 50], [15, 25, 50]]
    });
    table.on('select', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', true);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = true
    }).on('deselect', function(e, dt, type, indexes) {
        var $node = table[ type ]( indexes ).nodes().to$();
        $node.find('input.ipt_check').prop('checked', false);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = false
    }).
    on('draw', function(){
        $('#op').html(options.op_html || '');
        $('#uc').html(options.uc_html || '');
    });
    $('.ipt_check_all').on('click', function() {
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

function setCookie(key, value) {
    var expires = new Date();
    expires.setTime(expires.getTime() + (24 * 60 * 60 * 1000));
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
