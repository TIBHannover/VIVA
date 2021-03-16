const jobStatus = {
    RUNNING: 1,
    STOPPED: 2,
    FAILED: 0
};

const gpuAvailMemMinGB = 3;
let lastJobStatus = null, currentRuntime = -1, currentTimeFinish = -1;

function gpuQualifiedForTraining(gpuDevice) {
    return (gpuDevice["memory"]["total"] - gpuDevice["memory"]["used"]) / (1024 * 1024 * 1024) > gpuAvailMemMinGB;
}

function setupGPUSelection(gpuDevices) {
    if (gpuDevices.length > 0) {
        $('#controlStartOptionGPUs').removeClass('d-none');
        let gpuSelector = $('#controlStartOptionsGPUSelection');
        gpuSelector.empty();
        for (let i = 0; i < gpuDevices.length; i++) {
            let gpuSelection = $('#controlGPUSelectTemplate').clone().removeClass("d-none");
            gpuSelection.attr("id", "trainingControlStartOptionGPU" + gpuDevices[i].index);
            gpuSelection.find(".training-control-gpu-checkbox").attr("data-gpu-idx", gpuDevices[i].index);
            gpuSelection.find(".training-control-gpu-text").val("[" + (gpuDevices[i].index + 1) + "] " + gpuDevices[i].name);
            if (gpuDevices[i]["tf_compatibility"]) {
                gpuSelection.find(".training-control-gpu-checkbox").removeClass('d-none')
                    .prop("checked", gpuQualifiedForTraining(gpuDevices[i]));
                gpuSelection.find(".training-control-gpu-warning").addClass('d-none');
            } else {
                gpuSelection.find(".training-control-gpu-checkbox").addClass('d-none');
                gpuSelection.find(".training-control-gpu-warning").removeClass('d-none');
                gpuSelection.find(".training-control-gpu-checkbox").prop("disabled", true);
                gpuSelection.removeClass("bg-success").addClass("bg-danger");
                gpuSelection.prop("title", "This GPU is not compatible for training");
            }
            gpuSelector.append(gpuSelection);
        }
        setGPUSelectionOnMemory(gpuDevices);
    } else {
        $('#controlStartOptionGPUs').addClass('d-none');
    }
}

function setGPUSelectionOnMemory(gpuDevices) {
    for (let i = 0; i < gpuDevices.length; i++) {
        let gpuSelection = $('#trainingControlStartOptionGPU' + gpuDevices[i].index);
        if (gpuDevices[i]["tf_compatibility"]) {
            if (gpuQualifiedForTraining(gpuDevices[i])) {
                gpuSelection.find(".training-control-gpu-checkbox").prop("disabled", false);
                gpuSelection.removeClass("bg-danger").addClass("bg-success");
                gpuSelection.removeAttr("title");
            } else {
                gpuSelection.find(".training-control-gpu-checkbox").prop("disabled", true);
                gpuSelection.removeClass("bg-success").addClass("bg-danger");
                gpuSelection.attr("title", "Not enough memory available on this GPU");
            }
        }
    }
    checkGPUSelection();
}

function checkGPUSelection() {
    let startButton = $('#controlStart');
    if (!$('#controlStartOptionGPUs').hasClass('d-none')) {
        let allowedSelectCount = 0;
        $('#controlStartOptionsGPUSelection').find('.training-control-gpu-checkbox').each(function (index, element) {
            if (!$(element).prop("disabled") && $(element).prop("checked")) {
                allowedSelectCount++;
            }
        });
        if (allowedSelectCount < 1) {
            startButton.prop("disabled", true).removeClass("btn-success").addClass("btn-secondary");
            return;
        }
    }
    startButton.prop("disabled", false).removeClass("btn-secondary").addClass("btn-success");
}
