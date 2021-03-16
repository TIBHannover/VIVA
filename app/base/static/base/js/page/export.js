/**
 * Sets the contents of the export history based on a received object
 * @param {Object} receivedData the received object
 */
function setExportHistory(receivedData) {
    if (receivedData['last_model']) {
        $('#exportHistoryModelDate').text(receivedData['last_model']).removeClass('d-none');
        $('#exportHistoryModelPre, #exportHistoryTable').removeClass('d-none');
        $('#exportHistoryNotFound').addClass('d-none');
        let files = receivedData['files'].map(file => {
            file['size'] = sizeofFmt(file['size']);
            file['download'] = '<i class="fas fa-download"></i>'
            return file;
        });
        // destroy table if it already had content
        $('#exportHistoryTable').bootstrapTable('destroy').bootstrapTable({data: files});
    } else {
        $('#exportHistoryModelPre, #exportHistoryModelDate, #exportHistoryTable').addClass('d-none');
        $('#exportHistoryNotFound').removeClass('d-none');
    }
}

$(() => {
    let exportAction = new AsyncAction(
        ExportConfig.asyncActionId,
        FlaskConfig.URL_BASE + FlaskConfig.URL_SSE,
        FlaskConfig.URL_BASE + FlaskConfig.Export.URL_UPDATE,
        FlaskConfig.URL_BASE + FlaskConfig.Export.URL_START,
        FlaskConfig.URL_BASE + FlaskConfig.Export.URL_STOP,
        {
            'app': new HTMLStaticField(ExportConfig.appName)
        },
        {
            'app': new HTMLStaticField(ExportConfig.appName),
            'threshold': new HTMLInputNumber('#' + ExportConfig.asyncActionId + 'OptionsThreshold')
        },
        {
            'app': new HTMLStaticField(ExportConfig.appName)
        },
        FlaskConfig.Sse.EXPORT_INFO.replace("{:s}", ExportConfig.appName)
    );
    exportAction.on('updateContent', setExportHistory);
    exportAction.start();

    $('#exportHistoryTable').on('click-row.bs.table', (row, element, _, __) => {
        $('#exportHistoryDownloadFrame')[0].src =
            ExportConfig.urlDownload + "?app=" + ExportConfig.appName + "&threshold=" + element.threshold;
        return false;
    });
});