/**
 * Class to enable control over an asynchronous action and receive asynchronous feedback.
 * Call "start()" to start the commands to automatically connect to server side event api, send requests to the backend
 * and update the frontend (HTML) accordingly
 */
class AsyncAction extends EventHandling {
    id;
    urlSse;
    urlUpdate;
    urlStart;
    urlStop;
    parameterMapUpdate;
    parameterMapStart;
    parameterMapStop;
    sseTypeInfo;
    time = null;
    lastCurrent = -1;
    eta = null;

    /**
     * @param {string} id the id of this class, used for HTML selector - has to be same as 'async_id' in HTML template
     * @param {string} urlSse url to listen to asynchronous server side events
     * @param {string} urlUpdate url which initiates the sending of required information over SSE
     * @param {string} urlStart url to start the asynchronous action
     * @param {string} urlStop url to stop the asynchronous action
     * @param {Object} parameterMapUpdate object containing additional parameters when sending request to update url.
     *                                    Object entries are specified the following:
     *                                    <ul>
     *                                    <li>key: will be used on API request</li>
     *                                    <li>value: instance of HTMLInput (html-input.js)</li>
     *                                    </ul>
     * @param {Object} parameterMapStart parameter map for request to start url
     * @param {Object} parameterMapStop parameter map for request to stop url
     * @param {String} sseTypeInfo type of server side event when information objects will be received
     */
    constructor(id, urlSse, urlUpdate, urlStart, urlStop, parameterMapUpdate,
                parameterMapStart, parameterMapStop, sseTypeInfo) {
        super();
        this.id = id;
        this.urlSse = urlSse;
        this.urlUpdate = urlUpdate;
        this.urlStart = urlStart;
        this.urlStop = urlStop;
        this.parameterMapUpdate = parameterMapUpdate;
        this.parameterMapStart = parameterMapStart;
        this.parameterMapStop = parameterMapStop;
        this.sseTypeInfo = sseTypeInfo;

        this.setHTMLHandlers();
    }

    /**
     * Collect the values of a given parameter map (containing HTMLInput instances)
     * @param {Object} parameterMap the parameter map to evaluate
     * @returns {Object} the evaluated parameter map
     */
    getQueryParameters(parameterMap) {
        let queryParameters = {};
        for (const [queryParameter, queryInputClass] of Object.entries(parameterMap)) {
            queryParameters[queryParameter] = queryInputClass.getParameterValue();
        }
        return queryParameters;
    }

    /**
     * Update the visibility and text of the status messages (not general status messages) based on received object
     * @param {Object} receivedData the received object
     */
    setStatusMessages(receivedData) {
        if (receivedData[AsyncActionConfig.KEY_RUN]) {
            $('#' + this.id + 'StatusDependencyPrerequisite, #' + this.id + 'StatusDependencyRun, ' +
                '#' + this.id + 'StatusException').addClass('d-none');
        } else {
            // dependency prerequisite
            if (receivedData[AsyncActionConfig.KEY_DEPENDENCY_PREREQUISITE]) {
                $('#' + this.id + 'StatusDependencyPrerequisite').removeClass('d-none');
            } else {
                $('#' + this.id + 'StatusDependencyPrerequisite').addClass('d-none');
            }
            // dependency running
            if (receivedData[AsyncActionConfig.KEY_DEPENDENCY_RUN]) {
                $('#' + this.id + 'StatusDependencyRun').removeClass('d-none');
            } else {
                $('#' + this.id + 'StatusDependencyRun').addClass('d-none');
            }
            // exception
            if (receivedData[AsyncActionConfig.KEY_EXCEPTION]) {
                $('#' + this.id + 'StatusException').removeClass('d-none');
                $('#' + this.id + 'StatusExceptionText').text(receivedData[AsyncActionConfig.KEY_EXCEPTION]);
            } else {
                $('#' + this.id + 'StatusException').addClass('d-none');
            }
        }
    }

    /**
     * Set the options based on received object - if the asynchronous action is running it will set the related HTML
     * element's value to the selected value (selected on start of asynchronous action)
     * @param {Object} receivedData the received object
     */
    setOptions(receivedData) {
        for (const [queryParameter, queryInputClass] of Object.entries(this.parameterMapStart)) {
            if (queryParameter in receivedData[AsyncActionConfig.KEY_OPTIONS]) {
                if (receivedData[AsyncActionConfig.KEY_RUN]) {
                    queryInputClass.setValue(receivedData[AsyncActionConfig.KEY_OPTIONS][queryParameter]);
                    $(queryInputClass.selector).attr('readonly', '');
                } else {
                    $(queryInputClass.selector).removeAttr('readonly');
                }
            }
        }
    }

    /**
     * Show the current progress information based on received object
     * @param {Object} receivedData the received object
     */
    setProgress(receivedData) {
        let current = 0, total = 0;
        if (receivedData[AsyncActionConfig.KEY_RUN]) {
            current = receivedData[AsyncActionConfig.KEY_CURRENT];
            total = receivedData[AsyncActionConfig.KEY_TOTAL];
            $('#' + this.id + 'Progress').removeClass('d-none');
        } else {
            $('#' + this.id + 'Progress').addClass('d-none');
        }
        let percent = total === 0 ? 0 : Math.round(current * 1000 / total) / 10;
        $('#' + this.id + 'Progress #' + this.id + 'ProgressCurrent').text(current);
        $('#' + this.id + 'Progress #' + this.id + 'ProgressTotal').text(total === 0 ? "?" : total);
        $('#' + this.id + 'Progress #' + this.id + 'ProgressPercent').text(percent);
        $('#' + this.id + 'Progress #' + this.id + 'ProgressBar').attr('aria-valuenow', percent)
            .css('width', percent + "%");
    }

    /**
     * Lock/Disable the control buttons
     */
    setControlsLocked() {
        $('#' + this.id + 'ControlStart, #' + this.id + 'ControlStop')
            .prop("disabled", true)
            .removeClass("btn-success btn-danger")
            .addClass("btn-secondary");
    }

    /**
     * Set the state of the control buttons (start, stop) based on received object
     * @param {Object} receivedData the received object
     */
    setControls(receivedData) {
        if (receivedData[AsyncActionConfig.KEY_DEPENDENCY_PREREQUISITE]
            || receivedData[AsyncActionConfig.KEY_DEPENDENCY_RUN]) {
            this.setControlsLocked();
        } else {
            if (receivedData[AsyncActionConfig.KEY_RUN]) {
                $('#' + this.id + 'ControlStart')
                    .prop("disabled", true)
                    .removeClass("btn-success")
                    .addClass("btn-secondary");
                $('#' + this.id + 'ControlStop')
                    .prop("disabled", false)
                    .addClass("btn-danger")
                    .removeClass("btn-secondary");
            } else {
                $('#' + this.id + 'ControlStop')
                    .prop("disabled", true)
                    .removeClass("btn-danger")
                    .addClass("btn-secondary");
                $('#' + this.id + 'ControlStart')
                    .prop("disabled", false)
                    .addClass("btn-success")
                    .removeClass("btn-secondary");
            }
        }
    }

    /**
     * Set the runtime text based on received object (when running this will be done by 'setRuntimeString')
     * @param {Object} receivedData the received object
     */
    setRuntime(receivedData) {
        if (receivedData[AsyncActionConfig.KEY_RUN]) {
            $('#' + this.id + 'ControlRuntime, #' + this.id + 'ControlETE').removeClass('d-none');
            this.time = receivedData[AsyncActionConfig.KEY_TIME];
            if (this.lastCurrent !== receivedData[AsyncActionConfig.KEY_CURRENT] &&
                receivedData[AsyncActionConfig.KEY_CURRENT] > 0 && receivedData[AsyncActionConfig.KEY_TOTAL] > 0) {
                this.lastCurrent = receivedData[AsyncActionConfig.KEY_CURRENT];
                let startTimeCalc = (receivedData[AsyncActionConfig.KEY_TIME_ETE] &&
                    receivedData[AsyncActionConfig.KEY_TIME_ETE] > 0) ?
                    receivedData[AsyncActionConfig.KEY_TIME_ETE] : this.time;
                this.eta = startTimeCalc + Math.ceil((new Date().getTime() / 1000 - startTimeCalc) /
                    receivedData[AsyncActionConfig.KEY_CURRENT] * receivedData[AsyncActionConfig.KEY_TOTAL]);
            }
        } else {
            $('#' + this.id + 'ControlETE').addClass('d-none');
            this.time = null;
            this.eta = null;
            let time = receivedData[AsyncActionConfig.KEY_TIME];
            if (time != null && time >= 0) {
                $('#' + this.id + 'ControlRuntime').removeClass('d-none');
                $('#' + this.id + 'ControlRuntimeString').text(getTimeDeltaString(time));
            } else {
                $('#' + this.id + 'ControlRuntime').addClass('d-none');
            }
        }
    }

    /**
     * Updates the runtime text if the asynchronous action is running
     * (called on construction of this class - timeout is set to get called every second)
     */
    setRuntimeString() {
        if (this.time) {
            let currentSeconds = Math.floor(new Date().getTime() / 1000);
            $('#' + this.id + 'ControlRuntimeString').text(getTimeDeltaString(currentSeconds - this.time));
            $('#' + this.id + 'ControlETEString').text(this.eta && this.eta - currentSeconds >= 0 ?
                getTimeDeltaString(this.eta - currentSeconds) : "...");
        }
        setTimeout(_ => this.setRuntimeString(), 1000);
    }

    /**
     * Method that gets called when a new information object was received
     * @param {Object} receivedData the received object
     */
    updateContent(receivedData) {
        this.triggerHandler('contentReceived', receivedData);
        this.setStatusMessages(receivedData);
        this.setOptions(receivedData);
        this.setProgress(receivedData);
        this.setControls(receivedData);
        this.setRuntime(receivedData);
        this.triggerHandler('updateContent', receivedData);
    }

    /**
     * Send a request to send information object over SSE
     */
    requestUpdateOverSSE() {
        $.ajax({
            type: "POST",
            url: this.urlUpdate,
            data: this.getQueryParameters(this.parameterMapUpdate),
            success: _ => {
                $('.' + this.id + '-status-failed').addClass('d-none');
            },
            error: () => {
                $('.' + this.id + '-status-failed').removeClass('d-none');
            },
            complete: () => {
                $('.' + this.id + '-status-loading').addClass('d-none');
            }
        });
    }

    /**
     * Setup SSE listener
     * (action for receiving information that matches the type provided in constructor & actions for connection errors)
     */
    setupSSE() {
        let source = new EventSource(this.urlSse);

        // add event listener for information updates that do not require query of Django based API
        source.addEventListener(this.sseTypeInfo, event => {
            let data = JSON.parse(event.data);
            this.updateContent(data);
            $('.' + this.id + '-content').removeClass('d-none');
            $('#' + this.id + 'ControlLoading').addClass('d-none');
        }, false);

        // when sse connection is established
        source.addEventListener('open', _ => {
            this.requestUpdateOverSSE();
            $('.' + this.id + '-status-disconnected').addClass('d-none');
            $(window).on('beforeunload.' + this.id + '_sse', _ => source.close());
        }, false);

        // if see connection fails (before & after connection)
        source.addEventListener('error', _ => {
            this.setControlsLocked();
            source.close();
            $(window).off('beforeunload.' + this.id + '_sse');
            $('.' + this.id + '-status-disconnected, #' + this.id + 'ControlLoading').removeClass('d-none');
            setTimeout(_ => this.setupSSE(), 5000);
        }, false);
    }

    /**
     * Sends ajax request to start the asynchronous action
     */
    startAction() {
        $.ajax({
            type: "POST",
            url: this.urlStart,
            data: this.getQueryParameters(this.parameterMapStart),
            success: _ => {
                addMessage("Success", "fa-check text-success",
                    "The request to start has been processed successfully.", 2);
            },
            error: xhr => {
                addMessage("Error", "fa-exclamation-circle text-danger",
                    "An error occurred while processing the request to start:\n"
                    + xhr.responseJSON.message);
            }
        });
    }

    /**
     * Sends ajax request to stop the asynchronous action
     */
    stopAction() {
        $.ajax({
            type: "POST",
            url: this.urlStop,
            data: this.getQueryParameters(this.parameterMapStop),
            success: _ => {
                addMessage("Success", "fa-check text-success",
                    "The request to stop has been processed successfully.", 2);
            },
            error: xhr => {
                addMessage("Error", "fa-exclamation-circle text-danger",
                    "An error occurred while processing the request to stop:\n"
                    + xhr.responseJSON.message);
            }
        });
    }

    /**
     * Sets the onclick handlers for HTML elements of template
     */
    setHTMLHandlers() {
        $('#' + this.id + 'ControlStart').on('click', _ => this.startAction());
        $('#' + this.id + 'ModalControlStopSubmit').on('click', _ => this.stopAction());
    }

    /**
     * Start the communication for the asynchronous action
     */
    start() {
        this.setupSSE();
        this.setRuntimeString();
    }
}