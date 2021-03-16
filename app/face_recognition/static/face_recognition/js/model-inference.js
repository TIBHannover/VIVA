const infoUrl = "/info";
const jobStatus = {
    STOPPED: 0,
    RUNNING: 1,
    DONE: 2,
    FAILED: 3
};
let faceProcessingStatus = null, classificationStatus = null;
let faceProcessingControlTimeout = null;
let faceProcessingStartRuntime = -1, faceProcessingFinishedRuntime = -1;//, faceProcessingDone = false;
//let classificationRunning = false, classificationDone = false;
let classificationStartRuntime = -1, classificationFinishedRuntime = -1;
let totalClassifications = null;


function setFaceProcessingUrl(url) {
    this.startFaceProcessingUrl = url;
}

function setClassificationUrl(url) {
    this.startClassificationUrl = url;
}


function setFaceProcessingStatus(status) {
    faceProcessingStatus = status;
}


function setClassificationStatus(status) {
    classificationStatus = status;
}


function setInferenceVisibility() {
    if (faceProcessingStatus === jobStatus.FAILED) {
        $('#faceProcessingContent').addClass('d-none');
        $('#faceProcessingFeedbackContent').addClass('d-none');
        $('#faceProcessingStatusFailed').removeClass('d-none');
        $('#faceProcessingFeedbackStatusFailed').removeClass('d-none');
    } else {
        $('#faceProcessingContent').removeClass('d-none');
        $('#faceProcessingFeedbackContent').removeClass('d-none');
        $('#faceProcessingStatusFailed').addClass('d-none');
        $('#faceProcessingFeedbackStatusFailed').addClass('d-none');
        if (faceProcessingStatus === jobStatus.STOPPED) {
            $('#faceProcessingStatusException').addClass('d-none');
            $('#faceProcessingFeedbackStatusNoData').removeClass('d-none');
            $('#faceProcessingStatusStop').removeClass('d-none');
            $('#faceProcessingStatusRunning').addClass('d-none');
            $('#faceProcessingFeedbackStatsBox').addClass('d-none');
        } else if (faceProcessingStatus === jobStatus.RUNNING) {
            $('#faceProcessingStatusStop').addClass('d-none');
            $('#faceProcessingStatusRunning').removeClass('d-none');
            $('#faceProcessingFeedbackStatusNoData').addClass('d-none');
            $('#faceProcessingStatusException').addClass('d-none');
            $('#faceProcessingFeedbackStatsBox').removeClass('d-none');
            $('#faceProcessingFeedbackStatsBoxStopped').addClass('d-none');
        } else if (faceProcessingStatus === jobStatus.DONE) {
            $('#faceProcessingStatusStop').removeClass('d-none');
            $('#faceProcessingStatusRunning').addClass('d-none');
        }
    }

    if (classificationStatus === jobStatus.FAILED) {
        $('#classificationContent').addClass('d-none');
        $('#classificationFeedbackContent').addClass('d-none');
        $('#classificationStatusFailed').removeClass('d-none');
        $('#classificationFeedbackStatusFailed').removeClass('d-none');
    } else {
        $('#classificationContent').removeClass('d-none');
        $('#classificationFeedbackContent').removeClass('d-none');
        $('#classificationStatusFailed').addClass('d-none');
        $('#classificationFeedbackStatusFailed').addClass('d-none');
        if (classificationStatus === jobStatus.STOPPED) {
            $('#classificationStatusException').addClass('d-none');
            $('#classificationFeedbackStatusNoData').removeClass('d-none');
            $('#classificationStatusStop').removeClass('d-none');
            $('#classificationStatusRunning').addClass('d-none');
            $('#classificationFeedbackStatsBox').addClass('d-none');
        } else if (classificationStatus === jobStatus.RUNNING) {
            $('#classificationFeedbackStatusNoData').addClass('d-none');
            $('#classificationStatusStop').addClass('d-none');
            $('#classificationStatusRunning').removeClass('d-none');
            $('#classificationStatusException').addClass('d-none');
            $('#classificationFeedbackStatsBox').removeClass('d-none');
            $('#classificationFeedbackStatsBoxStopped').addClass('d-none');
        } else if (classificationStatus === jobStatus.DONE) {
            $('#classificationStatusException').addClass('d-none');
            $('#classificationStatusStop').removeClass('d-none');
            $('#classificationStatusRunning').addClass('d-none');
        }
    }
}

function updateFaceProcessingStats(data) {
    // sets start time and progressbars
    $('#faceProcessingTimeStart').text(timeConverter(faceProcessingStartRuntime));

    let detectionProgress = $('#detectionProgress');
    let embeddingProgress = $('#embeddingProgress');
    let widthDetection = 0;
    if (data['detection_processed'] != null && data['detection_total'] !== 0) {
        widthDetection = ((data['detection_processed'] * 100) / data['detection_total']);
    }
    let widthEmbedding = 0;
    if (data['embed_processed'] != null && data['embed_total'] !== 0) {
        widthEmbedding = ((data['embed_processed'] * 100) / data['embed_total']);
    }
    detectionProgress.width(widthDetection + "%");
    embeddingProgress.width(widthEmbedding + "%");
    detectionProgress.text(Math.round(widthDetection * 10) / 10 + " %");
    embeddingProgress.text(Math.round(widthEmbedding * 10) / 10 + " %");

    $('#detectionTotalCount').text(data['detection_total'] !== 0 ? data['detection_total'] : "-");
    $('#embeddingTotalCount').text(data['embed_total'] !== 0 ? data['embed_total'] : "-");
    $('#detectionTotalProcessed').text(data['detection_processed'] !== 0 ? data['detection_processed'] : "-");
    $('#embeddingTotalProcessed').text(data['embed_processed'] !== 0 ? data['embed_processed'] : "-");
}

function setClassificationStartTime() {
    // sets classification start time
    classificationStartRuntime = Date.now() / 1000;
    $('#classificationTimeStart').text(timeConverter(classificationStartRuntime));
}

function updateClassificationFeedback() {
    if (classificationStatus === jobStatus.DONE) {
        $('#totalClassifications').text("" + totalClassifications + " ");
    } else {
        $('#totalClassifications').text(' - unknown - ');
    }
}

function setFaceProcessingTimeStrings() {
    // sets the face processing time strings to calculate the face processing runtime
    if (faceProcessingStatus === jobStatus.RUNNING) {
        $('#faceProcessingTimeRuntime').text(Math.floor(new Date().getTime() / 1000 - faceProcessingStartRuntime));
    } else if (faceProcessingStatus === jobStatus.DONE) {
        $('#faceProcessingFeedbackTimeRuntimeStopped').text(faceProcessingFinishedRuntime - faceProcessingStartRuntime);
    } else {
        $('#faceProcessingTimeRuntime').text(" - unknown -");
    }
    setTimeout(setFaceProcessingTimeStrings, 1000);
}


function setClassificationTimeStrings() {
    // sets the time strings to calculate the classification runtime
    if (classificationStatus === jobStatus.RUNNING) {
        $('#classificationTimeRuntime').text(Math.floor(new Date().getTime() / 1000 - classificationStartRuntime));
    } else if (classificationStatus === jobStatus.DONE) {
        $('#classificationFeedbackTimeRuntimeStopped').text(classificationFinishedRuntime - classificationStartRuntime);
    } else {
        $('#classificationTimeRuntime').text(" - unknown -");
    }
    setTimeout(setClassificationTimeStrings, 1000);
}


function setFaceProcessingButton() {
    // Change the state (enabled/disabled) of the buttons
    if (faceProcessingStatus === jobStatus.RUNNING) {
        $('#faceProcessingStart').prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
    } else {
        $('#faceProcessingStart').prop("disabled", false).removeClass("btn-secondary").addClass("btn-success");
    }
}


function disableFaceProcessingButton() {
    // disables the start button
    $('#faceProcessingStart').prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
}


function setClassificationButton() {
    // Change the state (enabled/disabled) of the buttons
    if (classificationStatus === jobStatus.RUNNING) {
        $('#controlStartClassification').prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
    } else {
        $('#controlStartClassification').prop("disabled", false).removeClass("btn-secondary").addClass("btn-success");
    }
}


function disableClassificationButton() {
    // disables the start button
    $('#controlStartClassification').prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
}


function startFaceProcessing() {
    disableFaceProcessingButton();
    disableClassificationButton();
    $.ajax({
        type: "POST",
        url: this.startFaceProcessingUrl,
        beforeSend: function (xhr) {
            faceProcessingStatus = jobStatus.RUNNING;
            faceProcessingStartRuntime = Date.now() / 1000;
            setInferenceVisibility();
            updateInfos();
            addMessage("Success", "fa-check text-success",
                "The Face Processing has been started successfully.", 2);
        },
        success: function (data) {

        },
        error: function (xhr, status, error) {
            faceProcessingStatus = jobStatus.FAILED;
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An error occurred while processing the request to start the Face Processing:\n"
                + error);
        },
        complete: function () {
            faceProcessingStatus = jobStatus.DONE;
            faceProcessingFinishedRuntime = Date.now() / 1000;
            updateInfos();
            setFaceProcessingButton();
            setClassificationButton();
        }
    });
}


function startClassification() {
    disableFaceProcessingButton();
    disableClassificationButton();
    updateClassificationFeedback();
    $.ajax({
        type: "POST",
        url: this.startClassificationUrl,
        beforeSend: function (xhr) {
            addMessage("Success", "fa-check text-success",
                "The Classification has been started successfully.", 2);
            classificationStatus = jobStatus.RUNNING;
            setClassificationStartTime();
            setInferenceVisibility();
        },
        success: function (data) {

        },
        error: function (xhr, status, error) {
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An error occurred while processing the request to start the Classification:\n"
                + error);
        },
        complete: function (xhr, status) {
            totalClassifications = JSON.parse(xhr.responseText)['total_classifications']
            classificationStatus = jobStatus.DONE;
            classificationFinishedRuntime = Date.now() / 1000;
            updateClassificationFeedback();
            setClassificationButton();
            setFaceProcessingButton();
            setInferenceVisibility();
            addMessage("Success", "fa-check text-success",
                "The Classification has been completed.", 2);
        }
    });
}


function updateInfos() {
    $.ajax({
        type: "GET",
        url: faceServiceUrl + infoUrl,
        success: function (data) {
            if (faceProcessingStatus === jobStatus.RUNNING) {
                updateFaceProcessingStats(data)
            } else if (faceProcessingStatus === jobStatus.DONE) {
                updateFaceProcessingStats(data)
            }
        },
        error: function (xhr, status, error) {
            faceProcessingStatus = jobStatus.FAILED;
            setFaceProcessingButton();
            setClassificationButton();
        },
        complete: function () {
            $('#faceProcessingLoadingSpinner').addClass('d-none');
            $('#faceProcessingFeedbackSpinner').addClass('d-none');
            $('#classificationLoadingSpinner').addClass('d-none');
            $('#classificationFeedbackSpinner').addClass('d-none');
            setInferenceVisibility();
            faceProcessingControlTimeout = setTimeout(function () {
                updateInfos();
            }, 10000);
        }
    });
}
