/**
 * Class to provide client functionality for training chart drawing
 */
class TrainingCharts {
    static htmlIdTemplate = "trainingCharts";
    static htmlIdChartMapLoss = TrainingCharts.htmlIdTemplate + "MapLoss";
    static htmlIdChartLearningRate = TrainingCharts.htmlIdTemplate + "Lr";
    charts;

    /**
     * Constructor
     */
    constructor() {
        this.initializeCharts();
    }

    /**
     * Initialize/Draw the charts with no data
     */
    initializeCharts() {
        this.charts = {
            'mapLoss': null,
            'lr': null
        };
        this.drawEmptyChartMapLoss();
        this.drawEmptyChartLearningRate();
    }

    /**
     * Draw the chart for mean average precision and loss with no data
     */
    drawEmptyChartMapLoss() {
        this.charts['mapLoss'] = new Chart($('#' + TrainingCharts.htmlIdChartMapLoss)[0].getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Mean average precision',
                    backgroundColor: 'rgb(54, 162, 235)',
                    borderColor: 'rgb(54, 162, 235)',
                    data: [],
                    fill: false,
                    yAxisID: 'y-axis-map'
                }, {
                    label: 'Loss',
                    backgroundColor: 'rgb(255, 99, 132)',
                    borderColor: 'rgb(255, 99, 132)',
                    data: [],
                    fill: false,
                    yAxisID: 'y-axis-loss'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Epoch'
                        },
                        ticks: {
                            stepSize: 1
                        }
                    }],
                    yAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Mean average precision'
                        },
                        ticks: {
                            min: 0,
                            max: 1,
                            stepSize: 0.1
                        },
                        gridLines: {
                            display: true,
                            drawBorder: true,
                            drawOnChartArea: false,
                        },
                        position: 'left',
                        id: 'y-axis-map'
                    }, {
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Loss'
                        },
                        gridLines: {
                            display: true,
                            drawBorder: true,
                            drawOnChartArea: false,
                        },
                        position: 'right',
                        id: 'y-axis-loss'
                    }]
                }
            }
        });
    }

    /**
     * Draw the chart for learning rate with no data
     */
    drawEmptyChartLearningRate() {
        this.charts['lr'] = new Chart($('#' + TrainingCharts.htmlIdChartLearningRate)[0].getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Learn rate',
                    backgroundColor: 'rgb(75, 192, 192)',
                    borderColor: 'rgb(75, 192, 192)',
                    data: [],
                    steppedLine: true,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: 'Epoch'
                        },
                        ticks: {
                            stepSize: 1
                        }
                    }],
                    yAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                        },
                        gridLines: {
                            display: true,
                            drawBorder: true,
                            drawOnChartArea: false,
                        },
                        position: 'left'
                    }]
                }
            }
        });
    }

    /**
     * Update the charts based on received information
     * @param {Object} receivedData the received information object
     */
    updateChartData(receivedData) {
        $('#' + TrainingCharts.htmlIdTemplate + 'Content').removeClass("d-none");
        this.updateChartDataMapLoss(receivedData['charts']['map'], receivedData['charts']['loss']);
        this.updateChartDataLearningRate(receivedData['charts']['lr']);
    }

    /**
     * Update the mean average precision and loss chart
     * @param {Object} dataMap the data array for mean average precision
     * @param {Object} dataLoss the data array for loss
     */
    updateChartDataMapLoss(dataMap, dataLoss) {
        if (!arraysEqual(this.charts['mapLoss'].data.datasets[0].data, dataMap) ||
            !arraysEqual(this.charts['mapLoss'].data.datasets[1].data, dataLoss)) {
            this.charts['mapLoss'].data.labels =
                [...Array(dataMap.length).keys()].map(i => i + 1);
            this.charts['mapLoss'].data.datasets[0].data = [...dataMap];
            this.charts['mapLoss'].data.datasets[1].data = [...dataLoss];
            this.charts['mapLoss'].update();
        }
    }

    /**
     * Update the learning rate chart
     * @param {Object} dataLr the data array for learning rate
     */
    updateChartDataLearningRate(dataLr) {
        if (!arraysEqual(this.charts['lr'].data.datasets[0].data, dataLr)) {
            this.charts['lr'].data.labels =
                [...Array(dataLr.length).keys()].map(i => i + 1);
            this.charts['lr'].data.datasets[0].data = [...dataLr];
            this.charts['lr'].update();
        }
    }
}