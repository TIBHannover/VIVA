function sequenceAnnotationLoadingAnimation() {
    $('#sequenceAnnotationBtn').prop('disabled', true);
    $('#sequenceAnnotationSpinner').removeAttr('hidden');
    $('#sequenceAnnotationSpinnerText').removeAttr('hidden');
    $('#sequenceAnnotationText').attr('hidden', true);
}

function sequenceAnnotationLoadingReset() {
    $('#sequenceAnnotationBtn').removeAttr('disabled');
    $('#sequenceAnnotationSpinner').attr('hidden', true);
    $('#sequenceAnnotationSpinnerText').attr('hidden', true);
    $('#sequenceAnnotationText').removeAttr('hidden');
}

function fileExceedsUploadLimit(sequenceAnnotationFile) {
    let file = sequenceAnnotationFile.getValue();
    if (typeof file !== "undefined" && file.size > UploadLimit * 1024 ** 2) {
        addMessage("Sequence Annotation", "fa-exclamation-circle text-danger",
            "Image too large. File may be no larger than " + UploadLimit + " MiB.", 7);
        return true;
    }
    return false;
}