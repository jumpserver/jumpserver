//jumpserver 自定义js 2015-01-29

//此函数用于checkbox的全选和反选
var checked = false;

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

function checkAll(id, name) {
    var checklist = document.getElementsByName(name);
    if (document.getElementById(id).checked) {
        for (var i = 0; i < checklist.length; i++) {
            checklist[i].checked = 1;
        }
    } else {
        for (var j = 0; j < checklist.length; j++) {
            checklist[j].checked = 0;
        }
    }
}

//提取指定行的数据，JSON格式
function GetRowData(row) {
    var rowData = {};
    for (var j = 0; j < row.cells.length; j++) {
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
    for (var i = 0; i < len; i++) {
        if (checkboxes.elements[i].type == "checkbox" && checkboxes.elements[i].checked === true && checkboxes.elements[i].value != "checkall") {
            id_list.push(i);
        }
    }
    for (i in id_list) {
        tableData.push(GetRowData(tabProduct.rows[id_list[i]]));
    }

    if (id_list.length === 0) {
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
            if (typeof from_o !== 'undefined') {
                $("#" + to_o).append($("#" + from_o + " option[value='" + this.value + "']"));
            }
        }
    });
}

function move_left(from, to, from_o, to_o) {
    $("#" + from + " option").each(function () {
        if ($(this).prop("selected") === true) {
            $("#" + to).append(this);
            if (typeof from_o !== 'undefined') {
                $("#" + to_o).append($("#" + from_o + " option[value='" + this.value + "']"));
            }
        }
        $(this).attr("selected", 'true');
    });
}


function selectAll() {
    // Select all check box
    $('option').each(function () {
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
    let prefix = getCookie('SESSION_COOKIE_NAME_PREFIX');
    if (!prefix || [`""`, `''`].indexOf(prefix) > -1) {
        prefix = '';
    }
    var csrftoken = getCookie(`${prefix}csrftoken`);
    var sessionid = getCookie(`${prefix}sessionid`);

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

function activeNav(prefix) {
    if (!prefix) {
        prefix = '/core'
    }
    var path = document.location.pathname;
    path = path.replace(prefix, '');
    var urlArray = path.split("/");
    var app = urlArray[1];
    var resource = urlArray[2];
    if (app === '') {
        $('#index').addClass('active');
    } else if (app === 'xpack' && resource === 'cloud') {
        var item = urlArray[3];
        $("#" + app).addClass('active');
        $('#' + app + ' #' + resource).addClass('active');
        $('#' + app + ' #' + resource + ' #' + item + ' a').css('color', '#ffffff');
    } else if (app === 'settings') {
        $("#" + app).addClass('active');
    } else {
        $("#" + app).addClass('active');
        $('#' + app + ' #' + resource).addClass('active');
        $('#' + app + ' #' + resource.replace(/-/g, '_')).addClass('active');
    }
}

function formSubmit(props) {
    /*
    {
      "form": $("form"),
      "data": {},
      "url": "",
      "method": "POST",
      "redirect_to": "",
      "success": function(data, textStatue, jqXHR){},
      "error": function(jqXHR, textStatus, errorThrown) {},
      "message": "",
    }
    */
    props = props || {};
    var data = props.data || props.form.serializeObject();
    var redirectTo = props.redirect_to || props.redirectTo;
    $.ajax({
        url: props.url,
        type: props.method || 'POST',
        data: JSON.stringify(data),
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json"
    }).done(function (data, textState, jqXHR) {
        if (redirectTo) {
            location.href = redirectTo;
        } else if (typeof props.success === 'function') {
            return props.success(data, textState, jqXHR);
        }
    }).fail(function (jqXHR, textStatus, errorThrown) {
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
                props.form.prepend('<div class="alert alert-danger has-error" style="display: none"></div>');
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
                var fieldRef = props.form.find('[name="' + k + '"]');
                var formGroupRef = fieldRef.parents('.form-group');
                var parentRef = fieldRef.parent();
                var helpBlockRef = parentRef.children('.help-block.error');
                if (helpBlockRef.length === 0) {
                    parentRef.append('<div class="help-block error"></div>');
                    helpBlockRef = parentRef.children('.help-block.error');
                }
                if (fieldRef.length === 1 && formGroupRef.length === 1) {
                    formGroupRef.addClass('has-error');
                    var help_msg = v.join("<br/>");
                    helpBlockRef.html(help_msg);
                } else {
                    $.each(v, function (kk, vv) {
                        if (typeof vv === "object") {
                            $.each(vv, function (kkk, vvv) {
                                noneFieldErrorMsg += " " + vvv + '<br/>';
                            })
                        } else {
                            noneFieldErrorMsg += vv + '<br/>';
                        }
                    })
                }
            });
            if (noneFieldErrorRef.length === 1 && noneFieldErrorMsg !== '') {
                noneFieldErrorRef.css('display', 'block');
                noneFieldErrorRef.html(noneFieldErrorMsg);
            }
            $('.has-error :visible').get(0).scrollIntoView();
        }
    })
}

function requestApi(props) {
    // props = {url: .., body: , success: , error: , method: ,}
    props = props || {};
    var user_success_message = props.success_message;
    var default_success_message = gettext('Update is successful!');
    var user_fail_message = props.fail_message;
    var default_failed_message = gettext('An unknown error occurred while updating..');
    var flash_message = props.flash_message || true;
    if (props.flash_message === false) {
        flash_message = false;
    }
    var dataBody = props.body || props.data;
    if (typeof (dataBody) === "object") {
        dataBody = JSON.stringify(dataBody)
    }
    var headers = props.headers || {}

    $.ajax({
        url: props.url,
        type: props.method || "PATCH",
        headers: headers,
        data: dataBody,
        contentType: props.content_type || "application/json; charset=utf-8",
        dataType: props.data_type || "json"
    }).done(function (data, textStatue, jqXHR) {
        if (flash_message) {
            var msg = "";
            if (user_success_message) {
                msg = user_success_message;
            } else {
                msg = default_success_message;
            }
            toastr.success(msg);
        }
        if (typeof props.success === 'function') {
            return props.success(data);
        }
    }).fail(function (jqXHR, textStatus, errorThrown) {
        if (flash_message) {
            var msg = "";
            if (user_fail_message) {
                msg = user_fail_message;
            } else if (jqXHR.responseJSON) {
                if (jqXHR.responseJSON.error) {
                    msg = jqXHR.responseJSON.error
                } else if (jqXHR.responseJSON.msg) {
                    msg = jqXHR.responseJSON.msg
                } else if (jqXHR.responseJSON.detail) {
                    msg = jqXHR.responseJSON.detail
                }
            }
            if (msg === "") {
                msg = default_failed_message;
            }
            toastr.error(msg);
        }
        if (typeof props.error === 'function') {
            return props.error(jqXHR.responseText, jqXHR.responseJSON, jqXHR.status);
        }
    });
    // return true;
}

// Sweet Alert for Delete
function objectDelete(obj, name, url, redirectTo, title, success_message) {
    function doDelete() {
        var body = {};
        var success = function () {
            if (!redirectTo) {
                $(obj).parent().parent().remove();
            } else {
                window.location.href = redirectTo;
            }
        };
        var fail = function (responseText, responseJSON, status) {
            var errorMsg = '';
            if (responseJSON && responseJSON.error) {
                errorMsg = '';
            } else if (status === 404) {
                errorMsg = gettext("Not found")
            } else {
                errorMsg = gettext("Server error")
            }
            swal(gettext('Error'), "[ " + name + " ] " + errorMsg);
        };
        requestApi({
            url: url,
            body: JSON.stringify(body),
            method: 'DELETE',
            success_message: success_message || gettext("Delete the success"),
            success: success,
            error: fail
        });
    }

    swal({
        title: title || gettext('Are you sure about deleting it?'),
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

function orgDelete(obj, name, url, redirectTo) {
    function doDelete() {
        var body = {};
        var success = function () {
            if (!redirectTo) {
                $(obj).parent().parent().remove();
            } else {
                window.location.href = redirectTo;
            }
        };
        var fail = function (responseText, status) {
            if (status === 400) {
                swal(gettext("Error"), "[ " + name + " ] " + gettext("The organization contains undeleted information. Please try again after deleting"), "error");
            } else if (status === 405) {
                swal(gettext("Error"), " [ " + name + " ] " + gettext("Do not perform this operation under this organization. Try again after switching to another organization"), "error");
            }
        };
        requestApi({
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

$.fn.serializeObject = function () {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function () {
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
    return "<label class='detail-key'><b>" + data[0] + ": </b></label> " + data[1] + "</br>"
}

function parseTableFilter(value) {
    var cleanValues = [];
    if (!value) {
        return {}
    }
    var valuesArray = value.split(':');
    for (var i = 0; i < valuesArray.length; i++) {
        var v = valuesArray[i].trim();
        if (!v) {
            continue
        }
        // 如果是最后一个元素，直接push，不需要再处理了, 因为最后一个肯定不是key
        if (i === valuesArray.length - 1) {
            cleanValues.push(v);
            continue
        }
        v = v.split(' ');
        // 如果长度是1，直接push上
        // 如果长度不是1，根据空格分隔后，最后面的是key
        if (v.length === 1) {
            cleanValues.push(v[0]);
        } else {
            var leaveData = v.slice(0, -1).join(' ').trim();
            cleanValues.push(leaveData);
            cleanValues.push(v.slice(-1)[0]);
        }
    }
    var filter = {};
    var key = '';
    for (i = 0; i < cleanValues.length; i++) {
        if (i % 2 === 0) {
            key = cleanValues[i]
        } else {
            value = cleanValues[i];
            filter[key] = value
        }
    }
    return filter;
}


var jumpserver = {};
jumpserver.checked = false;
jumpserver.selected = {};
jumpserver.language = {};

function setDataTablePagerLength(num) {
    $.fn.DataTable.ext.pager.numbers_length = num;
}

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
    setDataTablePagerLength(5);
    var ele = options.ele || $('.dataTable');
    var columnDefs = [
        {
            targets: 0,
            orderable: false,
            width: "20px",
            createdCell: function (td, cellData) {
                $(td).html('<input type="checkbox" class="text-center ipt_check" id=99991937>'.replace('99991937', cellData));
            }
        },
        {
            className: 'text-center',
            render: $.fn.dataTable.render.text(),
            targets: '_all'
        }
    ];
    columnDefs = options.columnDefs ? options.columnDefs.concat(columnDefs) : columnDefs;
    var select = {
        style: 'multi',
        selector: 'td:first-child'
    };
    var table = ele.DataTable({
        pageLength: options.pageLength || 15,
        dom: options.dom || '<"#uc.pull-left"><"pull-right"<"inline"l><"#fb.inline"><"inline"f><"#fa.inline">>tr<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        order: options.order || [],
        // select: options.select || 'multi',
        searchDelay: 800,
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
    table.on('select', function (e, dt, type, indexes) {
        var $node = table[type](indexes).nodes().to$();
        $node.find('input.ipt_check').prop('checked', true);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = true
    }).on('deselect', function (e, dt, type, indexes) {
        var $node = table[type](indexes).nodes().to$();
        $node.find('input.ipt_check').prop('checked', false);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = false
    }).on('draw', function () {
        $('#op').html(options.op_html || '');
        $('#uc').html(options.uc_html || '');
        $('[data-toggle="popover"]').popover({
            html: true,
            placement: 'bottom',
            trigger: 'click',
            container: 'body'
        }).on('click', function (e) {
            $('[data-toggle="popover"]').not(this).popover('hide');
        });
    });
    $('.ipt_check_all').on('click', function () {
        if ($(this).prop("checked")) {
            $(this).closest('table').find('.ipt_check').prop('checked', true);
            jumpserver.checked = true;
            table.rows({search: 'applied', page: 'current'}).select();
        } else {
            $(this).closest('table').find('.ipt_check').prop('checked', false);
            jumpserver.checked = false;
            table.rows({search: 'applied', page: 'current'}).deselect();
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
    //    select_style: 'multi',
    //    columns *: [{data: ''}, ....],
    //    dom: 'fltip',
    //    i18n_url: '{% static "js/...../en-us.json" %}',
    //    order: [[1, 'asc'], [2, 'asc'], ...],
    //    buttons: ['excel', 'pdf', 'print'],
    //    columnDefs: [{target: 0, createdCell: ()=>{}}, ...],
    //    uc_html: '<a>header button</a>',
    //    op_html: 'div.btn-group?',
    //    paging: true,
    //    paging_numbers_length: 5;
    //    hideDefaultDefs: false;
    // }
    var pagingNumbersLength = 5;
    if (options.paging_numbers_length) {
        pagingNumbersLength = options.paging_numbers_length;
    }
    setDataTablePagerLength(pagingNumbersLength);
    var ele = options.ele || $('.dataTable');
    var columnDefs = [
        {
            targets: 0,
            orderable: false,
            width: "20px",
            createdCell: function (td, cellData) {
                var data = '<input type="checkbox" class="text-center ipt_check" id=Id>'.replace('Id', cellData);
                $(td).html(data);
            }
        },
        {
            targets: '_all',
            className: 'text-center',
            render: $.fn.dataTable.render.text()
        }
    ];
    if (options.hideDefaultDefs) {
        columnDefs = [];
    }
    var select_style = options.select_style || 'multi';
    columnDefs = options.columnDefs ? options.columnDefs.concat(columnDefs) : columnDefs;
    var select = {
        style: select_style,
        selector: 'td:first-child'
    };
    var dom = '<"#uc.pull-left"> <"pull-right"<"#lb.inline"> <"inline"l> <"#fb.inline"> <"inline"f><"#fa.inline">>' +
        'tr' +
        '<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>';
    var table = ele.DataTable({
        pageLength: options.pageLength || 15,
        // dom: options.dom || '<"#uc.pull-left">fltr<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        // dom: options.dom || '<"#uc.pull-left"><"pull-right"<"inline"l><"#fb.inline"><"inline"<"table-filter"f>><"#fa.inline">>tr<"row m-t"<"col-md-8"<"#op.col-md-6"><"col-md-6 text-center"i>><"col-md-4"p>>',
        dom: options.dom || dom,
        order: options.order || [],
        buttons: [],
        columnDefs: columnDefs,
        serverSide: true,
        processing: true,
        searchDelay: 800,
        oSearch: options.oSearch,
        ajax: {
            url: options.ajax_url,
            error: function (jqXHR, textStatus, errorThrown) {
                if (jqXHR.responseText && jqXHR.responseText.indexOf("%(value)s") !== -1) {
                    return
                }
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
                if (data.length !== null) {
                    data.limit = data.length;
                    delete data.length;
                }
                if (data.start !== null) {
                    data.offset = data.start;
                    delete data.start;
                }
                if (data.search !== null) {
                    var searchValue = data.search.value;
                    var searchFilter = parseTableFilter(searchValue);
                    if (Object.keys(searchFilter).length === 0) {
                        data.search = searchValue;
                    } else {
                        data.search = '';
                        $.each(searchFilter, function (k, v) {
                            data[k] = v
                        })
                    }
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
            dataFilter: function (data) {
                var json = jQuery.parseJSON(data);
                json.recordsTotal = json.count;
                json.recordsFiltered = json.count;
                return JSON.stringify(json); // return JSON string
            },
            dataSrc: "results"
        },
        columns: options.columns || [],
        select: options.select || select,
        language: jumpserver.language,
        lengthMenu: options.lengthMenu || [[15, 25, 50, 9999], [15, 25, 50, 'All']]
    });
    table.selected = [];
    table.selected_rows = [];
    table.on('select', function (e, dt, type, indexes) {
        var $node = table[type](indexes).nodes().to$();
        $node.find('input.ipt_check').prop('checked', true);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = true;
        if (type === 'row') {
            var rows = table.rows(indexes).data();
            $.each(rows, function (id, row) {
                if (row.id && $.inArray(row.id, table.selected) === -1) {
                    if (select.style === 'multi') {
                        table.selected.push(row.id);
                        table.selected_rows.push(row);
                    } else {
                        table.selected = [row.id];
                        table.selected_rows = [row];
                    }
                }
            })
        }
    }).on('deselect', function (e, dt, type, indexes) {
        var $node = table[type](indexes).nodes().to$();
        $node.find('input.ipt_check').prop('checked', false);
        jumpserver.selected[$node.find('input.ipt_check').prop('id')] = false;
        if (type === 'row') {
            var rows = table.rows(indexes).data();
            $.each(rows, function (id, row) {
                if (row.id) {
                    var index = table.selected.indexOf(row.id);
                    if (index > -1) {
                        table.selected.splice(index, 1);
                        table.selected_rows.splice(index, 1);
                    }
                }
            })
        }
    }).on('draw', function () {
        $('[data-toggle="popover"]').popover({
            html: true,
            placement: 'bottom',
            trigger: 'click',
            container: 'body'
        }).on('click', function (e) {
            $('[data-toggle="popover"]').not(this).popover('hide');
        });
        var table_data = [];
        $.each(table.rows().data(), function (id, row) {
            if (row.id) {
                table_data.push(row.id)
            }
        });

        $.each(table.selected, function (id, data) {
            var index = table_data.indexOf(data);
            if (index > -1) {
                table.rows(index).select()
            }
        });
    }).on("init", function () {
        $('#op').html(options.op_html || '');
        $('#uc').html(options.uc_html || '');
        $('#fb').html(options.fb_html || '');
        $('#fa').html(options.fa_html || '');
        $('#lb').html(options.lb_html || '');
    });
    var table_id = table.settings()[0].sTableId;
    $('#' + table_id + ' .ipt_check_all').on('click', function () {
        if (select_style !== 'multi') {
            return
        }
        if ($(this).prop("checked")) {
            $(this).closest('table').find('.ipt_check').prop('checked', true);
            table.rows({search: 'applied', page: 'current'}).select();
        } else {
            $(this).closest('table').find('.ipt_check').prop('checked', false);
            table.rows({search: 'applied', page: 'current'}).deselect();
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
String.prototype.format = function (args) {
    var result = this;
    if (arguments.length < 1) {
        return result;
    }

    var data = arguments;
    if (arguments.length == 1 && typeof (args) == "object") {
        data = args;
    }
    for (var key in data) {
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
        time = expires.getTime() + (24 * 60 * 60 * 1000);
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
    if (callback !== undefined) {
        var new_dataset = [];
        $.each(dataset, function (index, value) {
            new_dataset.push(callback(value))
        });
        dataset = new_dataset;
    }
    var data_content = dataset.join("<br>");
    var html = "<a data-toggle='popover' data-content='" + data_content + "'>" + dataset.length + "</a>";
    return html;
}


$(function () {
    (function ($) {
        $.getUrlParam = function (name) {
            var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");
            var r = window.location.search.substr(1).match(reg);
            if (r != null) return unescape(r[2]);
            return null;
        }
    })(jQuery);
});

function getUrlParam(name) {
    var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)");
    var r = window.location.search.substr(1).match(reg);
    if (r != null) return unescape(r[2]);
    return null;
}

function setUrlParam(url, name, value) {
    var urlArray = url.split("?");
    if (urlArray.length === 1) {
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

function getRuleLabel(rule) {
    var label = '';
    if (rule.key === rules_short_map_id['min']) {
        label = rules_id_map_label[rule.key].replace('{N}', rule.value)
    } else {
        label = rules_id_map_label[rule.key]
    }
    return label
}

// 校验密码-改变规则颜色
function checkPasswordRules(password, minLength) {
    if (wordMinLength(password, minLength)) {
        $('#' + rules_short_map_id['min']).css('color', 'green')
    } else {
        $('#' + rules_short_map_id['min']).css('color', '#908a8a')
    }

    if (wordUpperCase(password)) {
        $('#' + rules_short_map_id['upper']).css('color', 'green')
    } else {
        $('#' + rules_short_map_id['upper']).css('color', '#908a8a')
    }

    if (wordLowerCase(password)) {
        $('#' + rules_short_map_id['lower']).css('color', 'green')
    } else {
        $('#' + rules_short_map_id['lower']).css('color', '#908a8a')
    }

    if (wordNumber(password)) {
        $('#' + rules_short_map_id['number']).css('color', 'green')
    } else {
        $('#' + rules_short_map_id['number']).css('color', '#908a8a')
    }

    if (wordSpecialChar(password)) {
        $('#' + rules_short_map_id['special']).css('color', 'green')
    } else {
        $('#' + rules_short_map_id['special']).css('color', '#908a8a')
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
function initPopover($container, $progress, $idPassword, $el, password_check_rules, i18n_fallback) {
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


function rootNodeAddDom(ztree, callback) {
    var refreshIcon = "<a id='tree-refresh'><i class='fa fa-refresh'></i></a>";
    var rootNode = ztree.getNodes()[0];
    if (rootNode) {
        var $rootNodeRef = $("#" + rootNode.tId + "_a");
        $rootNodeRef.after(refreshIcon);
    } else {
        $rootNodeRef = $('#' + ztree.setting.treeId);
        $rootNodeRef.html(refreshIcon);
    }
    var refreshIconRef = $('#tree-refresh');
    refreshIconRef.bind('click', function () {
        ztree.destroy();
        callback()
    })
}

function htmlEscape(d) {
    return typeof d === 'string' ?
        d.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') :
        d;
}

function objectAttrsIsList(obj, attrs) {
    attrs.forEach(function (attr) {
        if (!obj[attr]) {
            obj[attr] = []
        } else if (obj[attr] && !(obj[attr] instanceof Array)) {
            obj[attr] = [obj[attr]]
        }
    })
}

function objectAttrsIsDatetime(obj, attrs) {
    attrs.forEach(function (attr) {
        obj[attr] = toSafeDateISOStr(obj[attr]);
    })
}

function objectAttrsIsBool(obj, attrs) {
    attrs.forEach(function (attr) {
        if (!obj[attr]) {
            obj[attr] = false
        } else {
            obj[attr] = ['on', '1', 'true', 'True'].includes(obj[attr]);
        }
    })
}

function objectAttrsIsNumber(obj, attrs) {
    attrs.forEach(function (attr) {
        if (!obj[attr]) {
            obj[attr] = null;
        }
    })
}

function cleanDateStr(d) {
    for (var i = 0; i < 3; i++) {
        if (!isNaN(Date.parse(d))) {
            return d;
        }
        if (!isNaN(Number(d))) {
            return d;
        }
        switch (i) {
            case 0:
                d = d.replaceAll('-', '/');
                break;
            case 1:
                d = d.split('+')[0].trimRight();
                break;
        }
    }
    return null;
}

function safeDate(s) {
    s = cleanDateStr(s);
    return new Date(s)
}

function toSafeDateISOStr(s) {
    var d = safeDate(s);
    return d.toISOString();
}

function toSafeLocalDateStr(d) {
    var date = safeDate(d);
    // var date_s = date.toLocaleString(getUserLang(), {hour12: false});
    var date_s = date.toLocaleString(getUserLang(), {hourCycle: "h23"});
    return date_s.split("/").join('-')
}

function getUrlParams(url) {
    url = url.split("?");
    var params = "";
    if (url.length === 2) {
        params = url[1];
    }
    return params
}

function getTimeUnits(u) {
    var units = {
        "d": "天",
        "h": "时",
        "m": "分",
        "s": "秒",
    };
    if (getUserLang() === "zh-CN") {
        return units[u]
    }
    return u
}

function timeOffset(a, b) {
    var start = safeDate(a);
    var end = safeDate(b);
    var offset = (end - start) / 1000;
    return readableSecond(offset)
}

function readableSecond(offset) {
    var days = offset / 3600 / 24;
    var hours = offset / 3600;
    var minutes = offset / 60;
    var seconds = offset;

    if (days > 1) {
        return days.toFixed(1) + " " + getTimeUnits("d");
    } else if (hours > 1) {
        return hours.toFixed(1) + " " + getTimeUnits("h");
    } else if (minutes > 1) {
        return minutes.toFixed(1) + " " + getTimeUnits("m")
    } else if (seconds > 1) {
        return seconds.toFixed(1) + " " + getTimeUnits("s")
    }
    return ""
}

function readFile(ref) {
    var files = ref.prop('files');
    var hasFile = files && files.length > 0;
    if (hasFile) {
        var reader = new FileReader();//新建一个FileReader
        reader.readAsText(files[0], "UTF-8");//读取文件
        reader.onload = function (evt) { //读取完文件之后会回来这里
            ref.trigger("onload", evt.target.result);
        };
    } else {
        ref.trigger("onload", null);
    }

    return ref
}


function select2AjaxInit(option) {
    /*
    {
      selector:
      url: ,
      disabledData: ,
      displayFormat,
      idFormat,
    }
     */
    var selector = option.selector;
    var url = option.url;
    var disabledData = option.disabledData;
    var displayFormat = option.displayFormat || function (data) {
        return data.name;
    };
    var idFormat = option.idFormat || function (data) {
        return data.id;
    };

    return $(selector).select2({
        closeOnSelect: false,
        ajax: {
            url: url,
            data: function (params) {
                var page = params.page || 1;
                var query = {
                    search: params.term,
                    offset: (page - 1) * 10,
                    limit: 10
                };
                return query
            },
            processResults: function (data) {
                var results = $.map(data.results, function (v, i) {
                    var display = displayFormat(v);
                    var id = idFormat(v);
                    var d = {id: id, text: display};
                    if (disabledData && disabledData.indexOf(v.id) !== -1) {
                        d.disabled = true;
                    }
                    return d;
                });
                var more = !!data.next;
                return {results: results, pagination: {"more": more}}
            }
        },
    })

}

function usersSelect2Init(selector, url, disabledData) {
    if (!url) {
        url = '/api/v1/users/users/'
    }

    function displayFormat(v) {
        return v.name + '(' + v.username + ')';
    }

    var option = {
        url: url,
        selector: selector,
        disabledData: disabledData,
        displayFormat: displayFormat
    };
    return select2AjaxInit(option)
}


function nodesSelect2Init(selector, url, disabledData) {
    if (!url) {
        url = '/api/v1/assets/nodes/'
    }

    function displayFormat(v) {
        return v.full_value;
    }

    var option = {
        url: url,
        selector: selector,
        disabledData: disabledData,
        displayFormat: displayFormat
    };
    return select2AjaxInit(option)
}

function showCeleryTaskLog(taskId) {
    var url = '/ops/celery/task/taskId/log/'.replace('taskId', taskId);
    window.open(url, '', 'width=900,height=600')
}

function getUserLang() {
    let userLangEN = document.cookie.indexOf('django_language=en');
    if (userLangEN === -1) {
        return 'zh-CN'
    } else {
        return 'en-US'
    }
}

function initDateRangePicker(selector, options) {
    if (!options) {
        options = {}
    }
    var zhLocale = {
        format: 'YYYY-MM-DD HH:mm',
        separator: ' ~ ',
        applyLabel: "应用",
        cancelLabel: "取消",
        resetLabel: "重置",
        daysOfWeek: ["日", "一", "二", "三", "四", "五", "六"],//汉化处理
        monthNames: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
    };
    var enLocale = {
        format: "YYYY-MM-DD HH:mm",
        separator: " - ",
        applyLabel: "Apply",
        cancelLabel: "Cancel",
        resetLabel: "Reset",
        daysOfWeek: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
        monthNames: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    };
    var defaultOption = {
        singleDatePicker: true,
        showDropdowns: true,
        timePicker: true,
        timePicker24Hour: true,
        autoApply: true,
    };
    if (getUserLang() === 'zh-CN') {
        defaultOption.locale = zhLocale;
    } else {
        // en-US
        defaultOption.locale = enLocale;
    }
    options = Object.assign(defaultOption, options);
    return $(selector).daterangepicker(options);
}

function reloadPage() {
    setTimeout(function () {
        window.location.reload();
    }, 300);
}

function isEmptyObject(obj) {
    return Object.keys(obj).length === 0
}

function getStatusIcon(status, mapping, title) {
    var navy = '<i class="fa fa-circle text-navy" title=""></i>';
    var danger = '<i class="fa fa-circle text-danger" title=""></i>';
    var warning = '<i class="fa fa-circle text-warning" title=""></i>';
    var icons = {
        navy: navy,
        danger: danger,
        warning: warning
    };
    var defaultMapping = {
        true: 'navy',
        false: 'danger',
        1: 'navy',
        0: 'danger',
        default: 'navy'
    };
    if (!mapping) {
        mapping = defaultMapping;
    }
    var name = mapping[status] || mapping['default'];
    var icon = icons[name];
    if (title) {
        icon = icon.replace('title=""', 'title="' + title + '"')
    }
    return icon;
}


function fillKey(key) {
    const KeyLength = 16
    if (key.length > KeyLength) {
        key = key.slice(0, KeyLength)
    }
    const filledKey = Buffer.alloc(KeyLength)
    const keys = Buffer.from(key)
    for (let i = 0; i < keys.length; i++) {
        filledKey[i] = keys[i]
    }
    return filledKey
}

function aesEncrypt(text, originKey) {
    const key = CryptoJS.enc.Utf8.parse(fillKey(originKey));
    return CryptoJS.AES.encrypt(text, key, {
        mode: CryptoJS.mode.ECB,
        padding: CryptoJS.pad.ZeroPadding
    }).toString();
}

function rsaEncrypt(text, pubKey) {
    if (!text) {
        return text
    }
    const jsEncrypt = new JSEncrypt();
    jsEncrypt.setPublicKey(pubKey);
    return jsEncrypt.encrypt(text);
}

function rsaDecrypt(cipher, pkey) {
    const jsEncrypt = new JSEncrypt();
    jsEncrypt.setPrivateKey(pkey);
    return jsEncrypt.decrypt(cipher)
}


window.rsaEncrypt = rsaEncrypt
window.rsaDecrypt = rsaDecrypt

function encryptPassword(password) {
    if (!password) {
        return ''
    }
    // public key 是 base64 存储的
    let rsaPublicKeyText = getCookie('jms_public_key')
    if (!rsaPublicKeyText) {
        return password
    }
    const aesKey = (Math.random() + 1).toString(36).substring(2)
    rsaPublicKeyText = rsaPublicKeyText.replaceAll('"', '')
    const rsaPublicKey = atob(rsaPublicKeyText)
    const keyCipher = rsaEncrypt(aesKey, rsaPublicKey)
    const passwordCipher = aesEncrypt(password, aesKey)
    return `${keyCipher}:${passwordCipher}`
}


function randomString(length) {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    const charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }

    return result;
}

function testEncrypt() {
    const radio = []
    const len2 = []
    for (let i = 1; i < 4096; i++) {
        const password = randomString(i)
        const cipher = encryptPassword(password)
        len2.push([password.length, cipher.length])
        radio.push(cipher.length / password.length)
    }
    return radio
}

window.encryptPassword = encryptPassword
