$(document).ready(function () {
    let table = $('#personTable');
    table.on('click-row.bs.table', function (row, $element, field, columns) {
        if (columns === "edit") {
            return false;
        }
        let person = $element.name;
        $.ajax({
            type: "POST",
            url: $('#personSelectUrl').val(),
            data: {
                csrfmiddlewaretoken: table.find("[name='csrfmiddlewaretoken']").val(),
                person: person
            },
            success: function (data) {
                $('#selectedClassString').text(person);
                addMessage("Person Selection", "fa-check text-success", "The selected person has been saved successfully!", 5, true);
                let next = $('#nextValue').val();
                if (next !== "") {
                    location.href = location.protocol + "//" + location.host + next;
                }
            },
            error: function (xhr, ajaxOptions, thrownError) {
                addMessage("Person Selection", "fa-exclamation-circle text-error", "The selected person could not be saved!", 0, true);
            }
        });
        field.find("[name='selected']").prop("checked", "true");
        return false;
    });

    $('#addPersonButton').on('click', function () {
        let inputName = $('#inputName');
        let inputDescription = $('#inputDescription');
        $.ajax({
            type: "POST",
            url: $('#personAddUrl').val(),
            data: {
                csrfmiddlewaretoken: table.find("[name='csrfmiddlewaretoken']").val(),
                name: inputName.val(),
                description: inputDescription.val()
            },
            success: function (data) {
                if (data.trim() === "") {
                    inputName.val("");
                    inputDescription.val("");
                    addMessage("Add Person", "fa-check text-success", "Your person has been added successfully!", 5, false);
                    location.reload();
                } else {
                    errorAlert(data);
                }
            },
            error: function (data) {
                errorAlert(data.responseText);
            }
        });
        return false;
    });
});

function errorAlert(errorText) {
    let alert = $('#select-person-error-alert');
    alert.html("Person could not be added:\n" + errorText);
    alert.removeClass('d-none');
}