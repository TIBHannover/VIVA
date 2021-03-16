$(document).ready(function () {
    // This enables tooltips for edit user page.
    $('[data-toggle="edit-user-tooltip"]').tooltip();

    let setGroupsModal = $('#setGroupsModal');
    let setGroupsError = $('#setGroupsError');
    let setGroupsForm = $('#setGroupsForm');

    setGroupsForm.on('submit', function () {
        let groupIds = [];
        let boxes = $('.group-checkbox:checkbox');
        for (let i = 0; i < boxes.length; i++) {
            if (boxes[i].checked) {
                groupIds.push(boxes[i].value);
            }
        }
        $.ajax({
            type: "POST",
            url: setGroupsForm.attr('action'),
            data: {
                csrfmiddlewaretoken: setGroupsForm.find("[name='csrfmiddlewaretoken']").val(),
                username: $('#inputUsername').val(),
                checked: groupIds.length === 0 ? [''] : groupIds,
            },
            success: function (data) {
                $('#inputGroups').val(data);
                setGroupsModal.modal('hide');
            },
            error: function (xhr, ajaxOptions, thrownError) {
                setGroupsError.html(xhr.responseText).removeClass('d-none');
            }
        });
        return false;
    });
});