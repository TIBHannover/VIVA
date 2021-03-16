let gpuUsageCharts = {};

function createGPUBox(gpu_data) {
    let newGpuBox = $('#hwInfoGpuBox').clone();
    newGpuBox.attr('id', 'hwInfoGpuBox' + gpu_data.index).removeClass('d-none');
    newGpuBox.find('.hw-info-gpu-num').text(gpu_data.index + 1);
    newGpuBox.find('.hw-info-gpu-name').attr('id', 'hwInfoGpuName' + gpu_data.index);
    newGpuBox.find('.hw-info-gpu-mem-total').attr('id', 'hwInfoGpuMemTotal' + gpu_data.index);
    newGpuBox.find('.hw-info-gpu-mem-use').attr('id', 'hwInfoGpuMemUse' + gpu_data.index);
    newGpuBox.find('.hw-info-gpu-chart').attr('id', 'hwInfoGpuChart' + gpu_data.index);
    if (gpu_data["tf_compatibility"]) {
        newGpuBox.find('.hw-info-gpu-tf-supp-warn').addClass('d-none');
    } else {
        newGpuBox.find('.hw-info-gpu-tf-supp-warn').removeClass('d-none');
    }
    newGpuBox.appendTo('#hwInfoGpuBoxInsert');
}

function updateGPUInfo(gpu_data, dateNow) {
    if (!$('#hwInfoGpuBox' + gpu_data.index).length) {
        createGPUBox(gpu_data);
        initGPUChart(gpu_data.index, gpu_data["utilization"] !== -1);
    }

    updateGPUInfoBox(gpu_data);

    let datasetIdx = 0;
    if (gpu_data["utilization"] !== -1) {
        gpuUsageCharts[gpu_data.index].data.datasets[0].data.push({
            x: dateNow,
            y: gpu_data["utilization"]
        });
        datasetIdx++;
    }
    gpuUsageCharts[gpu_data.index].data.datasets[datasetIdx].data.push({
        x: dateNow,
        y: Math.ceil((gpu_data["memory"]["used"] / gpu_data["memory"]["total"]) * 100)
    });
    gpuUsageCharts[gpu_data.index].data.datasets[datasetIdx + 1].data.push({
        x: dateNow,
        y: gpu_data["temperature"]
    });

    gpuUsageCharts[gpu_data.index].update({
        preservation: true
    });
}

function updateGPUInfoBox(gpu_data) {
    $('#hwInfoGpuName' + gpu_data.index).text(gpu_data["name"]);
    $('#hwInfoGpuMemTotal' + gpu_data.index).text(sizeofFmt(gpu_data["memory"]["total"]));
    $('#hwInfoGpuMemUse' + gpu_data.index).text(sizeofFmt(gpu_data["memory"]["used"]));
}

function initGPUChart(gpu_index, supportsUtilization) {
    let ctx = document.getElementById('hwInfoGpuChart' + gpu_index).getContext('2d');
    gpuUsageCharts[gpu_index] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory',
                backgroundColor: 'rgb(255, 159, 64)',
                borderColor: 'rgb(255, 159, 64)',
                data: [],
                fill: false
            }, {
                label: 'Temperature',
                backgroundColor: 'rgb(255, 99, 132)',
                borderColor: 'rgb(255, 99, 132)',
                data: [],
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: {
                point: {
                    radius: 2
                }
            },
            tooltips: {
                mode: 'index',
                intersect: false,
            },
            hover: {
                mode: 'nearest',
                intersect: true
            },
            scales: {
                xAxes: [{
                    display: false,
                    type: 'realtime',
                    realtime: {
                        duration: 50000,
                        delay: 1000,
                        ttl: 52000
                    },
                    time: {
                        format: undefined
                    }
                }],
                yAxes: [{
                    display: true,
                    scaleLabel: {
                        display: true,
                        labelString: 'Usage / Temp (°C)'
                    },
                    ticks: {
                        min: 0,
                        max: 100,
                        stepSize: 20
                    }
                }]
            }
        }
    });
    if (supportsUtilization) {
        gpuUsageCharts[gpu_index].data.datasets.unshift({
            label: 'Utilization',
            backgroundColor: 'rgb(54, 162, 235)',
            borderColor: 'rgb(54, 162, 235)',
            data: [],
            fill: false
        });
    }
    gpuUsageCharts[gpu_index].update();  // update otherwise datasets are not initialized
}

function hideGPUSpinnerAnimations() {
    $('#hwInfoGpuBoxSpinner').addClass('d-none');
}

function initGPUInfo() {
    $.ajax({
        type: "GET",
        url: FlaskConfig.URL_BASE + trainFlaskBasicURL,
        success: function (data) {
            setupSSEHwGPUListener(data.sse);
        },
        error: function () {
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An error occurred while instantiating hardware GPU information." +
                "Reload page to retry.", 5);
            hideGPUSpinnerAnimations();
            $('#hwInfoGpuBoxError').removeClass('d-none');
        }
    });
}

function setupSSEHwGPUListener(sseData) {
    let source = new EventSource(FlaskConfig.URL_BASE + sseData.url);
    source.addEventListener(sseData.types.hw_info, function (event) {
        let dateNow = Date.now();
        let data = JSON.parse(event.data);
        for (let i = 0; i < data.gpu.length; i++) {
            updateGPUInfo(data.gpu[i], dateNow);
        }
        if (data.gpu.length === 0) {
            $('#hwInfoGpuNotDetected').removeClass("d-none");
            if (data.gpu_support) {
                $('#hwInfoGpuNotDetectedFault').removeClass("d-none");
            } else {
                $('#hwInfoGpuNotDetectedFault').addClass("d-none");
            }
        } else {
            $('#hwInfoGpuNotDetected').addClass("d-none");
        }
        hideGPUSpinnerAnimations();
    }, false);
    source.addEventListener('open', function (event) {
        $('#hwInfoGpuBoxError').addClass('d-none');
        $('#hwInfoGpuBoxInsert').removeClass('d-none');
        $(window).on('beforeunload.hw_gpu', _ => source.close());
    }, false);
    source.addEventListener('error', function (event) {
        source.close();
        $(window).off('beforeunload.hw_gpu');
        $('#hwInfoGpuBoxError').removeClass('d-none');
        $('#hwInfoGpuBoxInsert').addClass('d-none');
        setTimeout(_ => setupSSEHwGPUListener(sseData), 5000);
    }, false);
}
