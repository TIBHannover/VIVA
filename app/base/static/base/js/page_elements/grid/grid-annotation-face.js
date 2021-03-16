class GridAnnotationFace extends GridAnnotation {

    face;

    getFaceOption() {
        let cookieVal = Cookies.get('face');
        if (cookieVal === 'undefined') {
            return "default";
        }
        return String(cookieVal);
    }

    constructor(id, apiUrl, queryParamHtmlMap = {}, annotationClassId = null, reduceHeightElem = null) {
        super(id, apiUrl, queryParamHtmlMap, annotationClassId, reduceHeightElem);
        this.elementTemplateClassSuffix = "annotation";
        Cookies.set('face', this.getFaceOption(), {expires: 365, sameSite: 'Lax'});
        this.face = this.getFaceOption();

        $('#' + id).addClass('grid-annotation-face');
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

        if (element.bbox !== undefined) {
            if (element.bbox.x !== null && element.bbox.y !== null && element.bbox.w !== null && element.bbox.h !== null) {
                let innerElement = newGridElement.find('.' + this.id + 'Element');
                let outerDiv = innerElement[0].parentNode;
                // hide the inner photo so only the face is shown
                innerElement.css('visibility', "hidden");

                function setFace(that) {
                    // create new div with the correct dimensions to show the recognized face
                    let innerDiv = document.createElement("div");
                    outerDiv.appendChild(innerDiv);
                    innerDiv.style.height = "calc(" + innerElement[0].style.maxHeight + ")";
                    innerDiv.style.maxHeight = "calc(" + innerElement[0].style.maxHeight + ")";
                    innerDiv.style.maxWidth = "calc(((100vh - 150px) / " + that.rows + " - 2rem) * " + (element.bbox.w / element.bbox.h) + ")";
                    if (element.download_url !== undefined) {
                        innerDiv.style.backgroundImage = "url(" + element.download_url + ")";
                    } else if (element.url !== undefined) {
                        innerDiv.style.backgroundImage = "url(" + element.url + ")";
                    }
                    // calculate size and position of the background image
                    let bWidth = "calc((" + innerElement[0].naturalWidth + " * calc(((100vh - 150px) / " + that.rows + " - 2rem) * " + (element.bbox.w / element.bbox.h) + ") / " + element.bbox.w + "))";
                    let bHeight = "calc((" + innerElement[0].naturalHeight + " * " + innerElement[0].style.maxHeight + " / " + element.bbox.h + "))";
                    innerDiv.style.backgroundSize = "" + bWidth + " " + bHeight + "";
                    let bLeft = "calc((" + element.bbox.x + " * calc(((100vh - 150px) / " + that.rows + " - 2rem) * " + (element.bbox.w / element.bbox.h) + ") / " + element.bbox.w + ") * -1)";
                    let bTop = "calc((" + element.bbox.y + " * " + innerElement[0].style.maxHeight + " / " + element.bbox.h + ") * -1)";
                    innerDiv.style.backgroundPosition = "" + bLeft + " " + bTop + "";
                    // display the element in the middle of the box
                    innerDiv.style.position = "relative";
                    innerDiv.style.left = "max(0rem, calc(50% - " + innerDiv.style.maxWidth + " / 2))";
                    innerElement.css('position', "absolute");
                }

                // only calculate the faces once the images are fully loaded
                let that = this;
                let timerID = setTimeout(function checkTimeout(that) {
                    if (innerElement[0].naturalWidth !== 0 && innerElement[0].naturalHeight !== 0 && innerElement[0].complete) {
                        setFace(that);
                    } else {
                        timerID = setTimeout(checkTimeout, 500, that);
                    }
                }, 500, that);
            }
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
                if (element.hasClass(Annotation.POSITIVE)) {
                    oldAnnotation = Annotation.POSITIVE;
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
            return Annotation.NONE;
        }
    }

    saveAnnotations(goToNextPage = false) {
        if (this.face === 'photo') {
            addMessage("Info", "fa-info-circle text-warning", "Cannot change annotations and bounding boxes in Photo mode.", 3);
            return;
        }

        if (this.annotationClassId === null) {
            console.log("Forgot to set the annotate class id? Annotations cannot be saved!");
            addMessage("Error", "fa-exclamation-circle text-danger",
                "There is an implementation failure, please check browser log for more details!");
            return;
        }

        let elements = []
        let that = this
        $('#' + this.id + 'Content').find('.annotation').each(function (i, obj) {
            if ($(this).data('id') === that.elementBuffer[i].id && that.initialAnnotationState[$(this).data('idx')] !== $(this).data('annotation')) {
                if (that.elementBuffer[i].bbox !== undefined) {
                    if (that.elementBuffer[i].bbox.x !== null && that.elementBuffer[i].bbox.y !== null &&
                        that.elementBuffer[i].bbox.w !== null && that.elementBuffer[i].bbox.h !== null) {
                        let annotation = {};
                        switch ($(this).data('annotation')) {
                            case Annotation.POSITIVE:
                                annotation = {groundtruth: true};
                                break;
                            case Annotation.NONE:
                                annotation = {groundtruth: false};
                                break;
                            default:
                                return true;  // loop continue
                        }
                        if ($(this).data('id') !== undefined) {
                            elements.push({
                                'idx': $(this).data('idx'),
                                'id': $(this).data('id'),
                                'annotation': annotation,
                                'bbox': that.elementBuffer[i].bbox
                            });
                        } else {  // must be an image (not a video)
                            elements.push({
                                'idx': $(this).data('idx'),
                                'url': $(this).find('img').attr('src'),
                                'annotation': annotation,
                                'bbox': that.elementBuffer[i].bbox
                            });
                        }
                    }
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
/*
        for (let i = 0; i < elements.length; i++) {
            let check_id = elements[i].id
            for (let j = 0; j < elements.length; j++) {
                if (elements[j].id === check_id && i !== j) {
                    addMessage("Info", "fa-info-circle text-warning", "You cannot annotate two faces from the same image.", 3);
                    return;
                }
            }
        }
*/
        $('#' + this.id + 'ModalAnnotationSave').modal({backdrop: 'static', keyboard: false});
        $.ajax({
            type: "POST",
            url: GridConfig.URL_SAVE_ANNOTATION_BBOX,
            contentType: 'application/json',
            cache: false,
            data: JSON.stringify({
                elements: elements,
                class_id: that.annotationClassId
            }),
            success: function () {
                // that.setWarnBeforeLeave(false);
                addMessage("Success", "fa-check text-success",
                    "Your annotations and bounding boxes were saved successfully.", 7);
                that.updateAfterAnnotationSaveSuccess(goToNextPage, elements);
            },
            error: function () {
                addMessage("Error", "fa-exclamation-circle text-danger",
                    "An error occurred while saving your annotations and bounding boxes! " +
                    "Please contact your administrator if this error is reproducible.");
            },
            complete: function () {
                that.hideModalOnUpdatingFix(that.id + "ModalAnnotationSave");
            }
        });
    }
}
