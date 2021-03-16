$(document).ready(function () {
    let table = $('#conceptTable');
    table.on('click-row.bs.table', function (row, $element, field, columns) {
        if (columns === "edit") {
            return false;
        }
        let concept = $element.name;
        $.ajax({
            type: "POST",
            url: $('#conceptSelectUrl').val(),
            data: {
                csrfmiddlewaretoken: table.find("[name='csrfmiddlewaretoken']").val(),
                concept: concept
            },
            success: function (data) {
                $('#selectedClassString').text(concept);
                addMessage("Concept Selection", "fa-check text-success", "The selected concept has been saved successfully!", 5, true);
                let next = $('#nextValue').val();
                if (next !== "") {
                    location.href = location.protocol + "//" + location.host + next;
                }
            },
            error: function (xhr, ajaxOptions, thrownError) {
                addMessage("Concept Selection", "fa-exclamation-circle text-error", "The selected concept could not be saved!", 0, true);
            }
        });
        field.find("[name='selected']").prop("checked", "true");
        return false;
    });

    $('#addConceptButton').on('click', function () {
        let inputName = $('#inputName');
        let inputDescription = $('#inputDescription');
        $.ajax({
            type: "POST",
            url: $('#conceptAddUrl').val(),
            data: {
                csrfmiddlewaretoken: table.find("[name='csrfmiddlewaretoken']").val(),
                name: inputName.val(),
                description: inputDescription.val()
            },
            success: function (data) {
                if (data.trim() === "") {
                    inputName.val("");
                    inputDescription.val("");
                    addMessage("Add Concept", "fa-check text-success", "Your concept has been added successfully!", 5, false);
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
    let alert = $('#select-concept-error-alert');
    alert.html("Concept could not be added:\n" + errorText);
    alert.removeClass('d-none');
}