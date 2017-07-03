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
    console.log(id_list);
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

//function move_all(from, to) {
//    $("#" + from).children().each(function () {
//        $("#" + to).append(this);
//    });
//}
//

//function selectAllOption(){
//         var checklist = document.getElementsByName ("selected");
//            if(document.getElementById("select_all").checked)
//            {
//            for(var i=0;i<checklist.length;i++)
//            {
//              checklist[i].checked = 1;
//            }
//            }else{
//            for(var j=0;j<checklist.length;j++)
//            {
//             checklist[j].checked = 0;
//            }
//            }
//
//        }


function selectAll(){
    // Select all check box
    $('option').each(function(){
        $(this).attr('selected', true);
    });
}


// function getIDall() {
//     var check_array = [];
//     $(".gradeX input:checked").each(function () {
//         var id = $(this).attr("value");
//         check_array.push(id);
//     });
//     return check_array.join(",");
// }

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
    var success_message = props.success_message || 'Update Successfully!';
    var fail_message = props.fail_message || 'Error occurred while updating.';
    $.ajax({
        url: props.url,
        type: props.method || "PATCH",
        data: props.body,
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json"
    }).done(function(data, textStatue, jqXHR) {
        toastr.success(success_message);
        if (typeof props.success === 'function') {
            return props.success(data);
        } 
      
    }).fail(function(jqXHR, textStatue, errorThrown) {
        toastr.error(fail_message);
        if (typeof props.error === 'function') {
            return props.error(errorThrown);
        } 
    });
  // return true;
}

// Sweet Alert for Delete
function objectDelete(obj, name, url, redirectTo) {
    function doDelete() {
        var body = {};
        var success = function() {
            swal('Deleted!', "[ "+name+"]"+" has been deleted ", "success");
            if (!redirectTo) {
                $(obj).parent().parent().remove();
            } else {
                window.location.href=redirectTo;
            }
        };
        var fail = function() {
            swal("Failed", "Delete"+"[ "+name+" ]"+"failed", "error");
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
        title: 'Are you sure delete ?',
        text: " [" + name + "] ",
        type: "warning",
        showCancelButton: true,
        cancelButtonText: 'Cancel',
        confirmButtonColor: "#DD6B55",
        confirmButtonText: 'Confirm',
        closeOnConfirm: false
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
  //    op_html: 'div.btn-group?'
  // }
  var ele = options.ele || $('.dataTable');
  var columnDefs = [
    {
      targets: 0,
      orderable: false,
      createdCell: function(td, cellData) {
          $(td).html('<input type="checkbox" class="text-center ipt_check" id=99991937>'.replace('99991937', cellData));
      }},
    {className: 'text-center', targets: '_all'}
  ];
  columnDefs = options.columnDefs ? options.columnDefs.concat(columnDefs) : columnDefs;
  var table = ele.DataTable({
        pageLength: options.pageLength || 15,
        dom: options.dom || '<"#uc.pull-left">flt<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        language: {
            url: options.i18n_url || "/static/js/plugins/dataTables/i18n/zh-hans.json"
        },
        order: options.order || [[ 1, 'asc' ]],
        select: options.select || 'multi',
        buttons: [],
        columnDefs: columnDefs,
        ajax: {
            url: options.ajax_url ,
            dataSrc: ""
        },
        columns: options.columns || [],
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
    });
    $('.ipt_check_all').on('click', function() {
      if (!jumpserver.checked) {
          $(this).closest('table').find('.ipt_check').prop('checked', true);
          jumpserver.checked = true;
          table.rows().select();
      } else {
          $(this).closest('table').find('.ipt_check').prop('checked', false);
          jumpserver.checked = false;
          table.rows().deselect();
      }
    });

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
}
