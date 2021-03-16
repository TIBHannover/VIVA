$(() => {
    let trainingCharts = new TrainingCharts();
    let trainingAction = new AsyncAction(
        TrainingConfig.asyncActionId,
        FlaskConfig.URL_BASE + FlaskConfig.URL_SSE,
        FlaskConfig.URL_BASE + FlaskConfig.Training.URL_UPDATE,
        FlaskConfig.URL_BASE + FlaskConfig.Training.URL_START,
        FlaskConfig.URL_BASE + FlaskConfig.Training.URL_STOP,
        {},
        {
            'batch_size': new HTMLInputNumber('#' + TrainingConfig.asyncActionId + 'OptionsBatchSize'),
            'gpu_selection': trainHTMLGPUSelection
        },
        {},
        FlaskConfig.Sse.TRAIN_INFO
    );
    // GPU selection needs to be build first otherwise 'set(...)' on 'trainHTMLGPUSelection' fails on first receive
    trainingAction.on('contentReceived', data => {
        // update GPU selection
        trainGPUSelection.updateGPUSelection(data[AsyncActionConfig.KEY_OPTIONS]['gpu_info'],
            data[AsyncActionConfig.KEY_RUN]);
    });
    trainingAction.on('updateContent', data => {
        // show success message
        if (!data[AsyncActionConfig.KEY_RUN] && !data[AsyncActionConfig.KEY_EXCEPTION] &&
            data['charts']['map'].length > 0) {
            $('#' + TrainingConfig.asyncActionId + 'StatusSuccess').removeClass("d-none");
        } else {
            $('#' + TrainingConfig.asyncActionId + 'StatusSuccess').addClass("d-none");
        }
        // set custom progress counters (converted to epochs)
        $('#' + TrainingConfig.asyncActionId + 'ProgressCurrentCustom')
            .text( Math.floor(data[AsyncActionConfig.KEY_CURRENT] / data['steps_per_epoch']));
        $('#' + TrainingConfig.asyncActionId + 'ProgressTotalCustom')
            .text(data[AsyncActionConfig.KEY_TOTAL] === 0 ? "?" :
                data[AsyncActionConfig.KEY_TOTAL] / data['steps_per_epoch']);
        // update training charts
        trainingCharts.updateChartData(data);
    });
    trainingAction.start();
    new AsyncLogBox(
        TrainingConfig.asyncLogId,
        FlaskConfig.URL_BASE + FlaskConfig.URL_SSE,
        FlaskConfig.URL_BASE + FlaskConfig.Training.URL_LOG,
        FlaskConfig.Sse.TRAIN_LOG
    );
});
