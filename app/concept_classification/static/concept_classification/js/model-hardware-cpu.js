let cpuMemChart;

function initCPUChart() {
    let ctx = document.getElementById('cpuMemChart').getContext('2d');
    cpuMemChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU',
                backgroundColor: 'rgb(54, 162, 235)',
                borderColor: 'rgb(54, 162, 235)',
                data: [],
                fill: false
            }, {
                label: 'Memory',
                backgroundColor: 'rgb(255, 159, 64)',
                borderColor: 'rgb(255, 159, 64)',
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
                    scaleLabel: {
                        display: true,
                        labelString: 'Usage'
                    },
                    ticks: {
                        min: 0,
                        max: 100,
                        stepSize: 10
                    }
                }]
            }
        }
    });
}

function updateCpuInfoBox(data) {
    $('#hwInfoCpuName').text(data.cpu_name);
    $('#hwInfoCpuCores').text(data.cpu_cores);
    $('#hwInfoCpuThreads').text(data.cpu_count);
    $('#hwInfoMemTotal').text(sizeofFmt(data.mem_total));
    $('#hwInfoMemUse').text(sizeofFmt(data.mem_use));
}

function hideCPUSpinnerAnimations() {
    $('#hwInfoCpuBoxSpinner').addClass('d-none');
}

function initCPUInfo() {
    $.ajax({
        type: "GET",
        url: FlaskConfig.URL_BASE + trainFlaskBasicURL,
        success: function (data) {
            initCPUChart();
            setupSSEHwCPUListener(data.sse);
        },
        error: function () {
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An error occurred while instantiating hardware CPU information." +
                "Reload page to retry.", 5);
            hideCPUSpinnerAnimations();
            $('#hwInfoCpuBoxError').removeClass('d-none');
        }
    });
}

function setupSSEHwCPUListener(sseData) {
    let source = new EventSource(FlaskConfig.URL_BASE + sseData.url);
    source.addEventListener(sseData.types.hw_info, function (event) {
        let dateNow = Date.now();
        let data = JSON.parse(event.data);
        updateCpuInfoBox(data.cpu);
        cpuMemChart.data.datasets[0].data.push({
            x: dateNow,
            y: data.cpu.cpu_pct
        });
        cpuMemChart.data.datasets[1].data.push({
            x: dateNow,
            y: data.cpu.mem_pct
        });
        cpuMemChart.update({
            preservation: true
        });
        hideCPUSpinnerAnimations();
    }, false);
    source.addEventListener('open', function (event) {
        $('#hwInfoCpuBoxError').addClass('d-none');
        $('#hwInfoCpuContent').removeClass('d-none');
        $(window).on('beforeunload.hw_cpu', _ => source.close());
    }, false);
    source.addEventListener('error', function (event) {
        source.close();
        $(window).off('beforeunload.hw_cpu');
        $('#hwInfoCpuBoxError').removeClass('d-none');
        $('#hwInfoCpuContent').addClass('d-none');
        setTimeout(_ => setupSSEHwCPUListener(sseData), 5000);
    }, false);
}
