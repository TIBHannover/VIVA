
class GridSelectionFace extends GridSelection {

    face;

    getFaceOption() {
        let cookieVal = Cookies.get('face');
        if (cookieVal === 'undefined') {
            return "default";
        }
        return String(cookieVal);
    }

    constructor(id, apiUrl, queryParamHtmlMap = {}, annotationClassId = null) {
        super(id, apiUrl, queryParamHtmlMap, annotationClassId);
        this.elementTemplateClassSuffix = "selection";
        Cookies.set('face', this.getFaceOption(), {expires: 365, sameSite: 'Lax'});
        this.face = this.getFaceOption();

        $('#' + id).addClass('grid-selection-face');
    }

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
}
