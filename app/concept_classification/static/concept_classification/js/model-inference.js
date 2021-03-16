$(() => {
    let inferenceAction = new AsyncAction(
        InferenceConfig.asyncActionId,
        FlaskConfig.URL_BASE + FlaskConfig.URL_SSE,
        FlaskConfig.URL_BASE + FlaskConfig.Inference.URL_UPDATE,
        FlaskConfig.URL_BASE + FlaskConfig.Inference.URL_START,
        FlaskConfig.URL_BASE + FlaskConfig.Inference.URL_STOP,
        {},
        {
            'batch_size': new HTMLInputNumber('#' + InferenceConfig.asyncActionId + 'OptionsBatchSize'),
            'gpu_selection': inferenceHTMLGPUSelection
        },
        {},
        FlaskConfig.Sse.INF_INFO
    );
    // GPU selection needs to be build first otherwise 'set(...)' on 'inferenceHTMLGPUSelection' fails on first receive
    inferenceAction.on('contentReceived',
        data => inferenceGPUSelection.updateGPUSelection(data[AsyncActionConfig.KEY_OPTIONS]['gpu_info'],
            data[AsyncActionConfig.KEY_RUN]));
    inferenceAction.start();
    new AsyncLogBox(
        InferenceConfig.asyncLogId,
        FlaskConfig.URL_BASE + FlaskConfig.URL_SSE,
        FlaskConfig.URL_BASE + FlaskConfig.Inference.URL_LOG,
        FlaskConfig.Sse.INF_LOG
    );
});
