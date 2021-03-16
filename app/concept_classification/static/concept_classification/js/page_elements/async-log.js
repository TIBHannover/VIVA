/**
 * Class to provide client functionality for front end logging
 */
class AsyncLog {
    static maxLines = 20000;
    id;
    urlSse;
    urlLog;
    sseType;
    fullLogFetched = false;

    /**
     * Constructor
     * @param {string} id the chosen id when including GPU selection HTML template
     * @param {string} urlSse URL to listen to asynchronous server side events
     * @param {string} urlLog URL to fetch the current log
     * @param {string} sseType type of server side event where log content will be received
     */
    constructor(id, urlSse, urlLog, sseType) {
        this.id = id;
        this.urlSse = urlSse;
        this.urlLog = urlLog;
        this.sseType = sseType;

        $('#' + id + 'Link').attr("href", this.urlLog);
        this.setupSSE();
    }

    /**
     * Clears the current log content
     */
    clearLogContent() {
        $('#' + this.id + 'TextArea').val("");
    }

    /**
     * Adds a new log content line - truncate current log content if new content exceeds max lines
     * @param {Object} receivedData the received object
     */
    addLogContent(receivedData) {
        let logBox = $('#' + this.id + 'TextArea');
        if (logBox.val().split("\n").length > AsyncLog.maxLines) {
            logBox.val(logBox.val().replace(/^.*\n/g, "") + "\n"
                + receivedData[FlaskConfig.Sse.KEY_LOG_MESSAGE]);
        } else {
            if (logBox.val() === "") {
                logBox.val(receivedData[FlaskConfig.Sse.KEY_LOG_MESSAGE]);
            } else {
                logBox.val(logBox.val() + "\n" + receivedData[FlaskConfig.Sse.KEY_LOG_MESSAGE]);
            }
        }
    }

    /**
     * Scrolls the log content to bottom if "scroll down" is enabled
     */
    scrollLogToBottom() {
        if ($('#' + this.id + 'AutoScroll').prop("checked")) {
            let logBox = $('#' + this.id + 'TextArea');
            // logBox.scrollTop(logBox[0].scrollHeight);
            logBox.animate({scrollTop: logBox[0].scrollHeight}, 50);
        }
    }

    /**
     * Fetch the full (truncated at max lines) log content
     */
    fetchFullLog() {
        $.ajax({
            type: "GET",
            url: this.urlLog + "?tail=" + AsyncLog.maxLines,
            success: data => {
                // Remove trailing new line
                $('#' + this.id + 'TextArea').val(data.replace(/\n+$/, "")).removeClass('d-none');
                $('#' + this.id + 'StatusFailedFetch').addClass("d-none");
                $('#' + this.id + 'Content').removeClass("d-none");
                this.scrollLogToBottom();
                this.fullLogFetched = true;
            },
            error: () => {
                $('#' + this.id + 'StatusFailedFetch').removeClass("d-none");
                setTimeout(() => {
                    if (!this.fullLogFetched) {
                        this.fetchFullLog();
                    }
                }, 5000);
            },
            complete: () => {
                $('#' + this.id + 'StatusLoading').addClass("d-none");
            }
        });
    }

    /**
     * Setup SSE listener
     */
    setupSSE() {
        let source = new EventSource(this.urlSse);

        // add event listener for log updates
        source.addEventListener(this.sseType, event => {
            if (this.fullLogFetched) {
                let dataJson = JSON.parse(event.data);
                if (dataJson[FlaskConfig.Sse.KEY_LOG_CLEAR]) {
                    this.clearLogContent();
                } else {
                    this.addLogContent(dataJson);
                }
                this.scrollLogToBottom();
            }
        }, false);

        // when sse connection is established
        source.addEventListener('open', _ => {
            this.fetchFullLog();
            $('#' + this.id + 'StatusDisconnected').addClass('d-none');
            $(window).on('beforeunload.' + this.id + '_sse', _ => source.close());
        }, false);

        // if see connection fails (before & after connection)
        source.addEventListener('error', _ => {
            this.fullLogFetched = false;
            source.close();
            $('#' + this.id + 'StatusDisconnected').removeClass('d-none');
            $(window).off('beforeunload.' + this.id + '_sse');
            setTimeout(_ => this.setupSSE(), 5000);
        }, false);
    }
}