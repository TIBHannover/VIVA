const infoUrl = "/info";
const jobStatus = {
    STOPPED: 0,
    RUNNING: 1,
    DONE: 2,
    FAILED: 3
};
let trainingStatus = null;
let trainingStartRuntime = -1, trainingFinishedRuntime = -1;


function setTrainingUrl(url) {
    this.startTrainingUrl = url
}


function setTrainingStatus(status) {
    trainingStatus = status;
}

function setTrainingVisibility() {
    $('#trainingControlSpinner').addClass('d-none');
    $('#trainingFeedbackSpinner').addClass('d-none');
    if (trainingStatus === jobStatus.FAILED) {
        $('#trainingControlContent').addClass('d-none');
        $('#trainingFeedbackContent').addClass('d-none');
        $('#trainingControlStatusFailed').removeClass('d-none');
        $('#trainingFeedbackStatusFailed').removeClass('d-none');
    } else {
        $('#trainingControlContent').removeClass('d-none');
        $('#trainingFeedbackContent').removeClass('d-none');
        $('#trainingControlStatusFailed').addClass('d-none');
        $('#trainingFeedbackStatusFailed').addClass('d-none');
        if (trainingStatus === jobStatus.STOPPED) {
            $('#trainingControlStatusStop').removeClass('d-none');
            $('#trainingControlStatusRunning').addClass('d-none');
            $('#trainingControlStartOptions').removeClass('d-none');
            $('#trainingControlStatusBox').addClass('d-none');
            $('#trainingFeedbackStatusNoData').removeClass('d-none');
        } else if (trainingStatus === jobStatus.RUNNING) {
            $('#trainingControlStatusStop').addClass('d-none');
            $('#trainingControlStatusRunning').removeClass('d-none');
            $('#trainingControlStartOptions').addClass('d-none');
            $('#trainingControlStatusBox').removeClass('d-none');
            $('#trainingFeedbackStatsBox').removeClass('d-none');
            $('#trainingFeedbackStatusNoData').addClass('d-none');
        } else if (trainingStatus === jobStatus.DONE) {
            $('#trainingControlStatusException').addClass('d-none');
            $('#trainingControlStatusStop').removeClass('d-none');
            $('#trainingControlStatusRunning').addClass('d-none');

        }
    }
}


function enableStartButton() {
    $('#controlStart').prop("disabled", false).removeClass("btn-secondary").addClass("btn-success");
}


function disableStartButton() {
    $('#controlStart').prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
}


function setTrainingStartTime() {
    // sets classification start time
    trainingStartRuntime = Date.now() / 1000;
    $('#trainingTimeStart').text(timeConverter(trainingStartRuntime));
}


function setTrainingTimeStrings() {
    // sets the time strings to calculate the training runtime
    if (trainingStatus === jobStatus.RUNNING) {
        $('#trainingTimeRuntime').text(Math.floor(new Date().getTime() / 1000 - trainingStartRuntime));
    } else if (trainingStatus === jobStatus.DONE) {
        $('#trainingFeedbackTimeRuntimeStopped').text(trainingFinishedRuntime - trainingStartRuntime);
    } else {
        $('#trainingTimeRuntime').text(" - unknown -");
    }
    setTimeout(setTrainingTimeStrings, 1000);
}

function startTraining() {
    disableStartButton();
    $.ajax({
        type: "POST",
        url: this.startTrainingUrl,
        beforeSend: function (xhr) {
            trainingStatus = jobStatus.RUNNING;
            setTrainingVisibility();
            updateInfos();
            setTrainingStartTime();
            addMessage("Success", "fa-check text-success",
                "The training has been started successfully.", 2);
        },
        success: function (data) {

        },
        error: function (xhr) {
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An error occurred while processing the request to start the training:\n"
                + xhr.responseJSON.message);
            trainingStatus = jobStatus.FAILED;
        },
        complete: function (xhr, status) {
            trainingStatus = jobStatus.DONE;
            updateInfos();
            enableStartButton();
            setTrainingVisibility();
            addMessage("Success", "fa-check text-success",
                "The training has been completed.", 2);
        },
    });
}


function updateFaceProcessingStats(data) {
    // sets start time and progressbars
    //$('#faceProcessingTimeStart').text(timeConverter(faceProcessingStartRuntime));

    let embeddingProgress = $('#embeddingProgress');
    let widthEmbedding = 0;
    if (data['embed_processed'] != null && data['embed_total'] !== 0) {
        widthEmbedding = ((data['embed_processed'] * 100) / data['embed_total']);
    }
    embeddingProgress.width(widthEmbedding + "%");
    embeddingProgress.text(Math.round(widthEmbedding * 10) / 10 + " %");

    $('#embeddingTotalCount').text(data['embed_total'] !== 0 ? data['embed_total'] : "-");
    $('#embeddingTotalProcessed').text(data['embed_processed'] !== 0 ? data['embed_processed'] : "-");
    if (Math.round(widthEmbedding * 10) / 10 >= 100) {
        $('#trainingResults').text("Model is now training ...");
    } else {
        $('#trainingResults').text("");
    }
}

function deleteFaceProcessingStats(data) {
    let embeddingProgress = $('#embeddingProgress');
    let widthEmbedding = 0;
    embeddingProgress.width(widthEmbedding + "%");
    embeddingProgress.text(0 + " %");

    $('#embeddingTotalCount').text("-");
    $('#embeddingTotalProcessed').text("-");
    $('#trainingResults').text("");
}


function updateInfos() {
    $.ajax({
        type: "GET",
        url: faceServiceUrl + infoUrl,
        success: function (data) {
            if (trainingStatus === jobStatus.RUNNING) {
                updateFaceProcessingStats(data)
            } else if (trainingStatus === jobStatus.DONE) {
                updateFaceProcessingStats(data)
            }
        },
        error: function (xhr, status, error) {
            trainingStatus = jobStatus.FAILED;
            enableStartButton();
        },
        complete: function () {
            $('#faceProcessingLoadingSpinner').addClass('d-none');
            $('#faceProcessingFeedbackSpinner').addClass('d-none');
            setTrainingVisibility();
            faceProcessingControlTimeout = setTimeout(function () {
                updateInfos();
            }, 10000);
        }
    });
}