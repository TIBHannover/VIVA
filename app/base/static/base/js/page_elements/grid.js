class Grid extends EventHandling {
    id;
    apiUrl;
    queryParamClassMap;
    reduceHeightElem;

    beforeUpdateFunction = null;  // Actions that should be done before updating the grid but might get delayed due to special circumstances (eg. unsaved annotations)
    updateAjax;
    elementTemplateClassSuffix = "basic";
    elementBuffer = [];
    elementCount = 0;
    elementsPrefetch = false;  // only query API once - then use the elements returned by the first API call for pagination
    restoreHTMLonFail = false;
    reduceHeightVal;
    cols;
    rows;
    page = 1;

    constructor(id, apiUrl, queryParamClassMap = {}, reduceHeightElem = null) {
        super();
        this.id = id;
        this.apiUrl = apiUrl;
        this.queryParamClassMap = queryParamClassMap;
        this.reduceHeightElem = reduceHeightElem;

        this.cols = this.getGridDimension('grid_cols');
        this.rows = this.getGridDimension('grid_rows');

        installKeyListener();
        this.addResizeListener();
    }

    getGridDimension(cookieKey) {
        let cookieVal = Cookies.get(cookieKey);
        if (typeof cookieVal === 'undefined' || isNaN(cookieVal) || parseInt(cookieVal) > 10 || parseInt(cookieVal) < 1) {
            return 3;
        }
        return parseInt(cookieVal);
    }

    addResizeListener() {
        if (this.reduceHeightElem) {
            this.reduceHeightVal = $(this.reduceHeightElem)[0].offsetHeight;
            try {
                let that = this;
                new ResizeObserver(function () {
                    let newVal = $(that.reduceHeightElem)[0].offsetHeight;
                    if (newVal !== that.reduceHeightVal) {
                        that.reduceHeightVal = newVal;
                        $('#' + that.id + 'Content .' + that.id + 'Element').each((i, element) => {
                            $(element).css('max-height', that.getMaxElementHeight());
                        });
                    }
                }).observe($(this.reduceHeightElem)[0]);
            } catch (Exception) {
                console.log("You browser does not support ResizeObserver - your browser is very likely outdated!")
            }
        }
    }

    enableElementPrefetching() {
        this.elementsPrefetch = true;
    }

    enableRestoreHTMLonError() {
        this.restoreHTMLonFail = true;
    }

    getUpdateParameters() {
        let queryParameters = {};
        queryParameters[GridConfig.PARAMETER_PAGE] = this.page;
        queryParameters[GridConfig.PARAMETER_ELEMENT_COUNT] = this.cols * this.rows;
        return queryParameters;
    }

    readHTMLQueryParameters() {
        let queryParameters = {};
        for (const [queryParameter, queryInputClass] of Object.entries(this.queryParamClassMap)) {
            queryParameters[queryParameter] = queryInputClass.getParameterValue();
        }
        return queryParameters;
    }

    storeHTMLInputValues() {
        for (const [, inputClass] of Object.entries(this.queryParamClassMap)) {
            inputClass.savePreviousValue();
        }
    }

    undoHTMLInputs() {
        for (const [, inputClass] of Object.entries(this.queryParamClassMap)) {
            inputClass.setPreviousValue();
        }
    }

    /**
     * Gets called before grid will be updated - can interrupt the update process by returning false
     * @returns {boolean}
     */
    onGridUpdate() {
        return true;
    }

    /**
     * Gets called when grid update was canceled - before(!) the decision is made
     */
    onGridUpdateAbort() {
        let that = this;
        $('#' + this.id + ' .grid-bar .grid-bar-pagination .grid-bar-pagination-current').each(function (i, obj) {
            obj.value = that.page;
        });
    }

    proposeUpdate(beforeUpdateFunction = null) {
        this.beforeUpdateFunction = beforeUpdateFunction;
        this.update();
    }

    update(force = false) {
        // before update checks and function
        if (!force && !this.onGridUpdate()) {
            this.onGridUpdateAbort();
            return;
        }
        if (this.beforeUpdateFunction) {
            this.beforeUpdateFunction();
        }
        this.beforeUpdateFunction = null;
        if (this.updateAjax) {
            this.updateAjax.abort();
        }

        // create FormData object
        let formData = new FormData();
        for (const [key, value] of Object.entries({...this.getUpdateParameters(), ...this.readHTMLQueryParameters()})) {
            if (typeof value === 'undefined') {
                continue;
            }
            if (typeof (value.name) === 'string') {  // identify if field is of object File
                formData.append(key, value, value.name);
            } else {
                formData.append(key, value);
            }
        }

        // check if API has to be queried
        if (!this.elementsPrefetch || this.elementBuffer.length === 0) {
            // change div visibilities
            $('#' + this.id).addClass('d-none');
            $('#' + this.id + 'Loading').removeClass('d-none');
            $('#' + this.id + "NoElements").addClass('d-none');
            $('#' + this.id + "Exception").addClass('d-none');

            // query the API for elements
            let that = this;
            this.updateAjax = $.ajax({
                type: "POST",
                url: this.apiUrl,
                data: formData,
                cache: false,
                contentType: false,
                processData: false,
                dataType: 'json',
                success: function (data) {
                    that.elementBuffer = data['elements'];
                    that.elementCount = data['count'];
                    if (that.elementBuffer.length === 0) {
                        $('#' + that.id + "NoElements").removeClass('d-none');
                        $('#' + that.id).addClass('d-none');
                        $('#' + that.id + "Content").empty();
                    } else {
                        that.buildGrid();
                        that.updateBars();
                        $('#' + that.id + "NoElements").addClass('d-none');
                        $('#' + that.id).removeClass('d-none');
                    }
                    $('#' + that.id + "Exception").addClass('d-none');
                    that.storeHTMLInputValues();
                    that.triggerHandler('updatedSuccess', data);
                },
                error: function (data) {
                    if (data.status !== 0) { // do not handle on "abort()" call
                        that.showErrorMessage(data.status + " - " + data.statusText);
                        if (that.restoreHTMLonFail) {
                            that.undoHTMLInputs();
                        }
                        that.triggerHandler('updatedError', data.responseText);
                    }
                },
                complete: function (data) {
                    $('#' + that.id + "Loading").addClass('d-none');
                    that.updateAjax = null;
                    that.triggerHandler('updated', data.responseJSON);
                    that.onGridUpdated();
                }
            });
        } else {
            this.buildGrid();
            this.updateBars();
            this.onGridUpdated();
        }
    }

    onGridUpdated() {
    }

    buildGrid() {
        let gridContent = $('#' + this.id + "Content");
        gridContent.empty();
        let rowContainer;
        for (let i = 0; i < this.rows * this.cols; i++) {
            if (i % this.cols === 0) {
                rowContainer = $($.parseHTML('<div class="row align-items-stretch mt-1 mb-1"></div>'));
            }
            if ((this.elementsPrefetch && (this.page - 1) * this.rows * this.cols + i < this.elementBuffer.length) ||
                (!this.elementsPrefetch && i < this.elementBuffer.length)) {  // Enough elements in buffer for all grid items?
                let element = this.elementBuffer[this.elementsPrefetch ? (this.page - 1) * this.rows * this.cols + i : i];
                let newGridElement;
                newGridElement = this.onElementCreate(element, newGridElement, i);
                rowContainer.append(newGridElement);
            } else {
                rowContainer.append('<div class="col"></div>');
            }
            if ((i + 1) % this.cols === 0) {
                gridContent.append(rowContainer);
            }
        }
    }

    getMaxElementHeight() {
        if (this.reduceHeightElem) {
            return "calc((100vh - 150px) / " + this.rows + " - 2rem - "
                + ($(this.reduceHeightElem)[0].offsetHeight + this.rows) / this.rows + "px)";
        }
        return "calc((100vh - 150px) / " + this.rows + " - 2rem)";
    }

    onElementCreate(element, newGridElement, idx) {
        if (element['media_type'] === 'image') {
            // element is an image
            newGridElement = $('#' + this.id + 'ElementTemplates').find('.grid-image' +
                ((this.elementTemplateClassSuffix === "") ? "" : "-" + this.elementTemplateClassSuffix)).clone();
            newGridElement = this.createImageElement(element, newGridElement, idx);
        } else if (element['media_type'] === 'video') {
            // element is a video
            newGridElement = $('#' + this.id + 'ElementTemplates').find('.grid-video' +
                ((this.elementTemplateClassSuffix === "") ? "" : "-" + this.elementTemplateClassSuffix)).clone();
            newGridElement = this.createVideoElement(element, newGridElement, idx);
        }
        newGridElement.data('idx', idx);
        if ("id" in element) {
            newGridElement.data('id', element['id']);
        }
        let innerElement = newGridElement.find('.' + this.id + 'Element');
        innerElement.css('max-height', this.getMaxElementHeight());
        let that = this;
        newGridElement.on('click', function (event) {
            that.onElementClick(newGridElement, event);
        });
        return newGridElement;
    }

    createImageElement(element, newGridElement, i) {
        let imgElement = newGridElement.find('.' + this.id + 'Element');
        let webImage = "download_url" in element && (!element['downloaded'] || element['download_error']);
        imgElement.attr('src', webImage ? element['download_url'] : element['url']);
        imgElement.attr('alt', 'Image ' + (i + 1));
        imgElement.on('error', function () {
            imgElement.attr('src', GridConfig.URL_IMAGE_NOT_FOUND);
            newGridElement.data('load-failed', true);
        });
        return newGridElement;
    }

    createVideoElement(element, newGridElement, i) {
        let videoElement = newGridElement.find('.' + this.id + 'Element');
        let videoSrc = "/media/" + element['video']['url'] + "#t=" + element['video']['startframe'] + "," + element['video']['endframe'];
        videoElement.attr('poster', element['url']);
        videoElement.attr('alt', 'Video ' + (i + 1));
        let playPauseToggle = function () {
            if (videoElement[0].paused) {
                videoElement.attr('src', videoSrc);
                videoElement[0].play();
            } else {
                videoElement[0].pause();
            }
        };
        let toggleVideoHandler = function (event) {
            // only if space is pressed - no other keys - no video in fullscreen
            if (pressedKeys.size === 1 && pressedKeys.has(32)) {
                playPauseToggle();
                event.preventDefault();
            }
        };
        videoElement.on({
            'play': function () {
                newGridElement.find('.grid-video-play-pause').removeClass('fa-play').addClass('fa-stop');
            },
            'pause': function () {
                if (document.fullscreenElement === null) {
                    $(this).removeAttr('src');  // this enforces browsers to display the poster
                    $(this).trigger('load');
                    $(this)[0].poster = element['url'];  // fix Chrome fullscreen exit (white video)
                    newGridElement.find('.grid-video-play-pause').removeClass('fa-stop').addClass('fa-play');
                }
            },
            'fullscreenchange': function () {
                if (document.fullscreenElement !== null) {
                    // video is in fullscreen now
                    if ($(this)[0].paused) {
                        $(this).attr('src', videoSrc);
                    }
                    $(this).attr('controls', 'controls');
                } else {
                    // reset paused video when existing fullscreen
                    if ($(this)[0].paused) {
                        $(this).trigger('pause');
                    }
                    $(this).removeAttr('controls');
                }
            },
            'mouseenter': function () {
                // on fullscreen disable key space for toggle
                if (document.fullscreenElement === null) {
                    $(window).on('keydown', toggleVideoHandler);
                } else {
                    $(window).unbind('keydown', toggleVideoHandler);
                }
            },
            'mouseleave': function () {
                $(window).unbind('keydown', toggleVideoHandler);
            }
        });
        newGridElement.find('.grid-video-play-pause').on('click', function (event) {
            playPauseToggle();
            event.stopPropagation();
        });
        newGridElement.find('.grid-video-full-screen').on('click', function (event) {
            videoElement[0].requestFullscreen();
            event.stopPropagation();
        });
        return newGridElement;
    }

    updateBars() {
        let that = this;
        // prepare bar template twice since clone() does not work for onclick events
        // code designed for old design with two bars - now only one bar on top
        ['Top'].forEach(function (item, idx) {
            let barTemplate = $('#' + that.id + "BarTemplate").children().clone();

            // dimensions
            if (barTemplate.find('.grid-bar-dimensions').length !== 0) {
                barTemplate = setupGridBarDimensions(that, barTemplate);
            }

            // pagination
            if (barTemplate.find('.grid-bar-pagination').length !== 0) {
                barTemplate = setupGridBarPagination(that, barTemplate);
            }

            // face option
            if (barTemplate.find('.grid-bar-face').length !== 0) {
                barTemplate = setupGridBarFace(that, barTemplate);
            }

            // annotation
            if (barTemplate.find('.grid-bar-annotation').length !== 0) {
                barTemplate = setupGridBarAnnotation(that, barTemplate);
            }

            let bar = $('#' + that.id + 'Bar' + item);
            bar.empty();
            bar.append(barTemplate);
        });
    }

    // enlarge image handler (always used)
    // returns false if click was consumed otherwise true if click was not handled
    onElementClick(element, event) {
        // only shift key is allowed - no other keys at the same time - no video in fullscreen
        if (pressedKeys.size === 1 && pressedKeys.has(16) && document.fullscreenElement === null) {
            let elementModal = $('#' + this.id + 'ModalElement');
            let innerElement = element.find('.' + this.id + 'Element');
            if (element.hasClass('grid-image')) {
                elementModal.find('#enlargedImage').attr('src', innerElement.attr('src'));
            } else {
                elementModal.find('#enlargedImage').attr('src', innerElement.attr('poster'));
            }
            elementModal.modal('show');
            return false;
        }
        return true;
    }

    showErrorMessage(message) {
        $('#' + this.id).addClass('d-none');
        $('#' + this.id + "Loading").addClass('d-none');
        $('#' + this.id + "NoElements").addClass('d-none');
        $('#' + this.id + "Exception").removeClass('d-none');
        $('#' + this.id + "ExceptionText").html(message);
        $('#' + this.id + "Content").empty();
    }

}
