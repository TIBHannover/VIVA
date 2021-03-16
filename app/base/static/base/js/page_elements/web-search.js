function webSearchLoadingAnimation(webSearchId) {
    $('#webSearch' + webSearchId + 'Submit').prop('disabled', true);
    $('#webSearch' + webSearchId + 'Submit #spinner').removeAttr('hidden');
    $('#webSearch' + webSearchId + 'Submit #spinner-text').removeAttr('hidden');
    $('#webSearch' + webSearchId + 'Submit #text').attr('hidden', true);
}

function webSearchLoadingReset(webSearchId) {
    $('#webSearch' + webSearchId + 'Submit').removeAttr('disabled');
    $('#webSearch' + webSearchId + 'Submit #spinner').attr('hidden', true);
    $('#webSearch' + webSearchId + 'Submit #spinner-text').attr('hidden', true);
    $('#webSearch' + webSearchId + 'Submit #text').removeAttr('hidden');
}