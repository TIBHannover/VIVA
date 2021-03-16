class HTMLInputRadioSimSearch extends HTMLInputRadio {
    setValue(value) {
        super.setValue(value);
        $(this.selector + "[value=" + value + "]").parent().trigger('click');
    }
}

$(function () {
    $('#selectAnnotatedImages').on('hidden.bs.modal', function () {
        // this event also get triggered when a modal above this modal is closed - if this is the case do nothing
        if ($('#selectAnnotatedImages').hasClass('show')) {
            return;
        }
        let selectedElement = simSearchSelectionGrid.getSelectedElement();
        if (selectedElement === null) {
            $('#simSearchModeUploadLabel').trigger('click');
        } else {
            $('#simSearchSelect').attr('placeholder', 'Currently selected image ID: ' + selectedElement.data('id'));
            $('#simSearchSelectValue').val(selectedElement.data('id'));
        }
    });
});

function simSearchLoadingAnimation() {
    $('#simSearchBtn').prop('disabled', true);
    $('#simSearchSpinner').removeAttr('hidden');
    $('#simSearchSpinnerText').removeAttr('hidden');
    $('#simSearchText').attr('hidden', true);
}

function simSearchLoadingReset() {
    $('#simSearchBtn').removeAttr('disabled');
    $('#simSearchSpinner').attr('hidden', true);
    $('#simSearchSpinnerText').attr('hidden', true);
    $('#simSearchText').removeAttr('hidden');
}

function setSimSearchMode(searchMode) {
    if (searchMode === "upload") {
        $("#simSearchUpload").removeClass("d-none");
        $("#simSearchSelect").addClass("d-none");
        $("#simSearchUrl").addClass("d-none");
    } else if (searchMode === "url") {
        $("#simSearchUrl").removeClass("d-none");
        $("#simSearchSelect").addClass("d-none");
        $("#simSearchUpload").addClass("d-none");
    } else if (searchMode === "select") {
        $("#simSearchSelect").removeClass("d-none");
        $("#simSearchUpload").addClass("d-none");
        $("#simSearchUrl").addClass("d-none");
    }
    $(".sim-search-mode").removeAttr('checked');
    $(".sim-search-mode[value=\"" + searchMode + "\"]").attr('checked', true);
}

function fileExceedsUploadLimit(simSearchFile) {
    let file = simSearchFile.getValue();
    if (typeof file !== "undefined" && file.size > UploadLimit * 1024 ** 2) {
        addMessage("Similarity Search", "fa-exclamation-circle text-danger",
            "Image too large. File may be no larger than " + UploadLimit + " MiB.", 7);
        return true;
    }
    return false;
}