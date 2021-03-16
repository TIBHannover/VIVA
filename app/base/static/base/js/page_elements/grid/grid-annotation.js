const Annotation = {
    POSITIVE: 'annotation-positive',
    NEGATIVE: 'annotation-negative',
    NEUTRAL: 'annotation-neutral',
    NONE: 'annotation-none',
    FAILED: 'annotation-failed'
};

class GridAnnotation extends Grid {
    initialAnnotationState = [];
    gridStatus;
    annotationClassId;

    constructor(id, apiUrl, queryParamHtmlMap = {}, annotationClassId = null, reduceHeightElem = null) {
        super(id, apiUrl, queryParamHtmlMap, reduceHeightElem);
        super.elementTemplateClassSuffix = "annotation";

        this.gridStatus = Annotation.NONE;
        this.annotationClassId = annotationClassId;
        this.setHotkeyActions();
        $('#' + id).addClass('grid-annotation');
    }

    getUpdateParameters() {
        let queryParameters = super.getUpdateParameters();
        queryParameters[GridConfig.PARAMETER_ANNOTATION_CLASS] = this.annotationClassId;
        return queryParameters;
    }

    onGridUpdate() {
        if (!super.onGridUpdate()) {
            return false;
        }
        if (this.checkAnnotationChanged()) {
            let that = this;
            let warnModal = $('#' + this.id + 'ModalAnnotationUnsaved');
            warnModal.find('.modal-leave-btn').off('click').on('click', function () {
                that.update(true);
            });
            warnModal.find('#unsavedStay').off('click').on('click', function () {
                if (that.restoreHTMLonFail) {
                    that.undoHTMLInputs();
                }
            });
            warnModal.modal({backdrop: 'static', keyboard: false});
            return false;
        }
        return true;
    }

    onGridUpdated() {
        super.onGridUpdated();
        this.setWarnBeforeLeave();
    }

    /**
     * For every element add annotation state given by query results
     * @param element the element of query result
     * @param newGridElement the new element for the grid
     * @param idx the index of the element in the grid
     * @returns {*}
     */
    onElementCreate(element, newGridElement, idx) {
        newGridElement = super.onElementCreate(element, newGridElement, idx);
        if (idx === 0) {
            this.initialAnnotationState = [];
        }
        if ('download_error' in element && element['download_error']) {
            newGridElement.addClass(Annotation.FAILED).data('annotation', Annotation.FAILED);
            this.initialAnnotationState.push(Annotation.FAILED);
        } else if ('annotation' in element) {
            if (element['annotation']['difficult']) {
                newGridElement.addClass(Annotation.NEUTRAL).data('annotation', Annotation.NEUTRAL);
                this.initialAnnotationState.push(Annotation.NEUTRAL);
            } else if (element['annotation']['groundtruth']) {
                newGridElement.addClass(Annotation.POSITIVE).data('annotation', Annotation.POSITIVE);
                this.initialAnnotationState.push(Annotation.POSITIVE);
            } else {
                newGridElement.addClass(Annotation.NEGATIVE).data('annotation', Annotation.NEGATIVE);
                this.initialAnnotationState.push(Annotation.NEGATIVE);
            }
        } else {
            this.initialAnnotationState.push(Annotation.NONE);
            newGridElement.addClass(Annotation.NONE).data('annotation', Annotation.NONE);
        }
        return newGridElement;
    }

    /**
     * Toggle the annotation of an element if there is a click on it
     * @param element the element on that was clicked (the whole col element - not only the one with onclick event)
     * @param event the event of onclick
     */
    onElementClick(element, event) {
        if (super.onElementClick(element, event)) {
            // only click - no other keys pressed - no video in fullscreen - image without error (web crawler)
            if (pressedKeys.size === 0 && document.fullscreenElement === null && !element.data('load-failed')) {
                if (element.hasClass(Annotation.FAILED)) {
                    element.removeClass(Annotation.FAILED);
                    element.addClass(Annotation.NONE);
                }
                let oldAnnotation = Annotation.NONE;
                if (element.hasClass(Annotation.NEUTRAL)) {
                    oldAnnotation = Annotation.NEUTRAL;
                } else if (element.hasClass(Annotation.POSITIVE)) {
                    oldAnnotation = Annotation.POSITIVE;
                } else if (element.hasClass(Annotation.NEGATIVE)) {
                    oldAnnotation = Annotation.NEGATIVE;
                }
                let newAnnotation = this.rotateAnnotation(oldAnnotation);
                element.removeClass(oldAnnotation).addClass(newAnnotation).data('annotation', newAnnotation);
                this.setWarnBeforeLeave();
                return false;
            }
        } else {
            return false;
        }
        return true;
    }

    rotateAnnotation(oldAnnotation, includeNone = true) {
        if (oldAnnotation === Annotation.NONE) {
            return Annotation.POSITIVE;
        } else if (oldAnnotation === Annotation.POSITIVE) {
            return Annotation.NEGATIVE;
        } else if (oldAnnotation === Annotation.NEGATIVE) {
            return Annotation.NEUTRAL;
        } else if (oldAnnotation === Annotation.NEUTRAL) {
            return includeNone ? Annotation.NONE : Annotation.POSITIVE;
        }
    }

    cycleGridAnnotations() {
        this.gridStatus = this.rotateAnnotation(this.gridStatus, false);
        this.changeGridAnnotations(this.gridStatus);
    }

    /**
     * Determines whether the grid annotation state was changed or not
     * @returns {boolean}
     */
    checkAnnotationChanged() {
        let that = this;
        let stateChanged = false;
        $('#' + this.id + "Content").find('.annotation').each(function (i, obj) {
            if (that.initialAnnotationState[$(this).data('idx')] !== $(this).data('annotation')) {
                stateChanged = true;
                return false;  // loop break
            }
        });
        return stateChanged;
    }

    /**
     * Change the annotation of the whole grid
     * @param status the status that the all images should be assigned
     */
    changeGridAnnotations(status) {
        let statuses = [Annotation.NEUTRAL, Annotation.POSITIVE, Annotation.NEGATIVE];
        $('#' + this.id + "Content").find('.annotation').each(function (i, obj) {
            if (typeof $(this).data('load-failed') === 'undefined' || !$(this).data('load-failed')) {
                $(this).removeClass("annotation-failed annotation-none " + statuses.join(" ")).addClass(status).data('annotation', status);
            }
        });
        this.setWarnBeforeLeave();
    }

    /**
     * Save annotations by posting data containing information about labeled images
     * @param goToNextPage if set to true: after posting the next page will be loaded
     */
    saveAnnotations(goToNextPage = false) {
        if (this.annotationClassId === null) {
            console.log("Forgot to set the annotate class id? Annotations cannot be saved!");
            addMessage("Error", "fa-exclamation-circle text-danger",
                "An internal error occurred, please check browser log for more details!");
            return;
        }

        let elements = [];
        let that = this;
        $('#' + this.id + 'Content').find('.annotation').each(function (i, obj) {
            if (that.initialAnnotationState[$(this).data('idx')] !== $(this).data('annotation')) {
                let annotation = {};
                switch ($(this).data('annotation')) {
                    case Annotation.NEGATIVE:
                        annotation = {difficult: false, groundtruth: false};
                        break;
                    case Annotation.POSITIVE:
                        annotation = {difficult: false, groundtruth: true};
                        break;
                    case Annotation.NEUTRAL:
                        annotation = {difficult: true, groundtruth: false};
                        break;
                    case Annotation.NONE:
                        annotation = {difficult: true, groundtruth: true};
                        break;
                    default:
                        return true;  // loop continue
                }
                if ($(this).data('id') !== undefined) {
                    elements.push({'idx': $(this).data('idx'), 'id': $(this).data('id'), 'annotation': annotation});
                } else {  // must be an image (not a video)
                    elements.push({
                        'idx': $(this).data('idx'),
                        'url': $(this).find('img').attr('src'),
                        'annotation': annotation
                    });
                }
            }
        });
        if (elements.length === 0) {
            if (goToNextPage) {
                this.updateAfterAnnotationSaveSuccess(true, elements);
            }
            addMessage("Info", "fa-info-circle text-warning", "No annotations were changed.", 3);
            return;
        }

        $('#' + this.id + 'ModalAnnotationSave').modal({backdrop: 'static', keyboard: false});
        $.ajax({
            type: "POST",
            url: GridConfig.URL_SAVE_ANNOTATIONS,
            contentType: 'application/json',
            cache: false,
            data: JSON.stringify({
                elements: elements,
                class_id: that.annotationClassId
            }),
            success: function () {
                // that.setWarnBeforeLeave(false);
                addMessage("Success", "fa-check text-success",
                    "Your annotations were saved successfully.", 7);
                that.updateAfterAnnotationSaveSuccess(goToNextPage, elements);
            },
            error: function () {
                addMessage("Error", "fa-exclamation-circle text-danger",
                    "An error occurred while saving your annotations! " +
                    "Please contact your administrator if this error is reproducible.");
            },
            complete: function () {
                that.hideModalOnUpdatingFix(that.id + "ModalAnnotationSave");
            }
        });
    }

    updateAfterAnnotationSaveSuccess(goToNextPage, changedElements) {
        // update element buffer if elements are not fetched on every grid update
        if (this.elementsPrefetch) {
            changedElements.forEach((item, _) => {
                if (item['annotation']['difficult'] && item['annotation']['groundtruth']) {
                    delete this.elementBuffer[(this.page - 1) * this.rows * this.cols + item['idx']]['annotation'];
                } else {
                    this.elementBuffer[(this.page - 1) * this.rows * this.cols + item['idx']]['annotation'] = item['annotation'];
                }
                if ('download_error' in this.elementBuffer[(this.page - 1) * this.rows * this.cols + item['idx']]) {
                    delete this.elementBuffer[(this.page - 1) * this.rows * this.cols + item['idx']]['download_error'];
                }
            });
        }
        this.beforeUpdateFunction = function () {
            if (goToNextPage && this.page < Math.ceil(this.elementCount / (this.rows * this.cols))) {
                this.page += 1;
            }
        };
        this.update(true);
    }

    /**
     * Workaround method close a modal until it is safely closed (checking periodic until closed)
     * @param modalId
     */
    hideModalOnUpdatingFix(modalId) {
        let modal = $("#" + modalId);
        if ((modal.data("bs.modal") || {})._isShown) {
            modal.modal('hide');
            let that = this;
            window.setTimeout(function () {
                that.hideModalOnUpdatingFix(modalId);
            }, 100);
        }
    }

    setHotkeyActions() {
        let that = this;
        $(document).keydown(function (e) {
            let activeElement = $(document.activeElement);
            if (activeElement[0].tagName !== "BODY" &&  // avoid keypress registration if active in other elements (eg. input for web search)
                // excludes for scenarios if keypress after special actions
                // open & close modals
                activeElement[0].id !== (that.id + "ModalAnnotationSave") &&
                activeElement[0].id !== "unsavedStay" &&
                // pressed a button
                !activeElement.hasClass("btn") &&
                activeElement[0].tagName !== "BUTTON" &&
                // annotated an element
                !activeElement.hasClass((that.id + "Element"))) {
                return;
            }
            if (that.elementBuffer.length !== 0) {  // disable shortcuts if grid is empty
                if (e.which === "A".charCodeAt(0)) {
                    that.cycleGridAnnotations();
                } else if (e.which === "S".charCodeAt(0)) {
                    if (that.id === "gridReview") {
                        that.saveAnnotations(false);
                        that.update(true);
                    } else {
                        that.saveAnnotations(true);
                    }
                } else if (e.which === "D".charCodeAt(0)) {
                    if (that.id === "gridReview") {
                        that.proposeUpdate(function () {
                            if (that.page < Math.ceil(that.elementCount / (that.rows * that.cols))) {
                                that.page += 1;
                            }
                        });
                    }
                }
            }
        });
    }

    /**
     * Setup browser to warn before changing url, leaving or updating grid when grid annotations are changed
     */
    setWarnBeforeLeave() {
        if (this.checkAnnotationChanged()) {
            $(window).on('beforeunload', function () {
                return "Unsaved annotations - are you sure you want to leave?";
            });
        } else {
            $(window).off('beforeunload');
        }
    }
}