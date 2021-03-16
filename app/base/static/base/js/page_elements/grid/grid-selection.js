
class GridSelection extends Grid {

    constructor(id, apiUrl, queryParamHtmlMap = {}, prefetchElements = false, annotationClassId = null) {
        super(id, apiUrl, queryParamHtmlMap, prefetchElements);
        super.elementTemplateClassSuffix = "selection";

        $('#' + id).addClass('grid-selection');
    }

    /**
     * Toggle the annotation of an element if there is a click on it
     * @param element the element on that was clicked (the whole col element - not only the one with onclick event)
     * @param event the event of onclick
     */
    onElementClick(element, event) {
        if (super.onElementClick(element, event)) {
            // only click - no other keys pressed - no video in fullscreen
            if (pressedKeys.size === 0 && document.fullscreenElement === null) {
                this.setSelectedElement(element[0]);
            }
        }
    }

    /**
     * Set a given element of the grid as the selected image class
     * @param element the element that should be selected
     */
    setSelectedElement(element) {
        $('#' + this.id + "Content").find('.selection').each(function (i, obj) {
            if (obj === element) {
                $(this).addClass('selected-element');
            } else {
                $(this).removeClass('selected-element');
            }
        });
    }

    /**
     * Get the currently selected element or null if no element is selected
     * @returns {null} the selected element or null if no element is selected
     */
    getSelectedElement() {
        let selectedElement = null;
        $('#' + this.id + "Content").find('.selection').each(function (i, obj) {
            if ($(this).hasClass('selected-element')) {
                selectedElement = $(this);
                return false;  // = break
            }
        });
        return selectedElement;
    }
}
