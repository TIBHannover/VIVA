
class GridAnnotationPrediction extends GridAnnotation {

    constructor(id, apiUrl, queryParamHtmlMap = {}, annotationClassId = null, reduceHeightElem = null) {
        super(id, apiUrl, queryParamHtmlMap, annotationClassId, reduceHeightElem);
        this.elementTemplateClassSuffix = "annotation-prediction";

        $('#' + id).addClass('grid-annotation-prediction');
    }

    onElementCreate(element, newGridElement, idx) {
        newGridElement =  super.onElementCreate(element, newGridElement, idx);

        let score = parseFloat(element[GridConfig.ELEMENT_ADDITIONAL_VALUE_SCORE]);
        newGridElement.find('.grid-prediction-score').text(Math.round(score * 1000) / 10 + "%");

        return newGridElement;
    }

}