//jumpserver 自定义js 2015-01-29

//此函数用于checkbox的全选和反选
var checked=false;
function check_all(form) {
    var checkboxes = document.getElementById(form);
    if (checked == false) {
        checked = true
    } else {
        checked = false
    }
    for (var i = 0; i < checkboxes.elements.length; i++) {
        if (checkboxes.elements[i].type == "checkbox") {
            checkboxes.elements[i].checked = checked;
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
    var tableData = new Array();
    var returnData = new Array();
    var checkboxes = document.getElementById("contents_form");
    var id_list = new Array();
    len = checkboxes.elements.length;
    for (var i=0; i < len; i++) {
        if (checkboxes.elements[i].type == "checkbox" && checkboxes.elements[i].checked == true && checkboxes.elements[i].value != "checkall") {
            id_list.push(i);
         }
        }
    console.log(id_list);
    for (i in id_list) {
        console.log(tabProduct);
        tableData.push(GetRowData(tabProduct.rows[id_list[i]]));
    }

    if (id_list.length == 0){
        alert('请至少选择一行！');
    }
    returnData.push(tableData);
    returnData.push(id_list.length);
    return returnData;
}

function move(from, to) {
    $("#" + from + " option").each(function () {
        if ($(this).prop("selected") == true) {
            $("#" + to).append(this);
        }
    });
}

function move_left(from, to) {
    $("#" + from + " option").each(function () {
        if ($(this).prop("selected") == true) {
            $("#" + to).append(this);
        }
        $(this).attr("selected",'true');
    });
}

function move_all(from, to) {
    $("#" + from).children().each(function () {
        $("#" + to).append(this);
    });
}


function selectAll(){
         var checklist = document.getElementsByName ("selected");
            if(document.getElementById("select_all").checked)
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


function move_all(from, to){
    $("#"+from).children().each(function(){
        $("#"+to).append(this);
    });
}

