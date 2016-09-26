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
                break;
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
  success_message = props.success_message || 'Update Successfully!';
  fail_message = props.fail_message || 'Error occurred while updating.';

  $.ajax({
    url: props.url,
    type: props.method || "PATCH",
    data: props.body,
    contentType: props.content_type || "application/json; charset=utf-8",
    dataType: props.data_type || "json",
  }).done(function(data, textStatue, jqXHR) {
    if (typeof props.success === 'function') {
      return props.success(data);
    } else {
      toastr.success(success_message);
    }
  }).fail(function(jqXHR, textStatue, errorThrown) {
    if (typeof props.error === 'function') {
      return props.error(errorThrown);
    } else {
      toastr.error(fail_message);
    }
  });
  return true;
}

// Sweet Alert for Delete
function objectDelete(obj, name, url){
    swal({
        title: 'Are you sure delete ?',
        text: "【" + name + "】",
        type: "warning",
        showCancelButton: true,
        cancelButtonText: 'Cancel',
        confirmButtonColor: "#DD6B55",
        confirmButtonText: 'Yes, delete it!',
        closeOnConfirm: false
    }, function () {
        $.ajax({
            type : "post",
            url : url,
            data : {
            },
            dataType : "text",
            success : function(data) {
                swal('Deleted!' , "【"+name+"】"+"has been deleted.", "success");
                $(obj).parent().parent().remove();
            }
        });
    });
}

var jumpserver = {};
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
