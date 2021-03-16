function addMessage(title, symbol, text, timeout = 0, show = true) {
    let messages = Cookies.getJSON('messages');
    let message;
    if (typeof messages === "undefined") {
        message = {
            id: Math.floor(Math.random() * 10000), title: title, symbol: symbol, text: text, timeout: timeout,
            timestamp: Date.now()
        };
        Cookies.set('messages', [message], {expires: 365, sameSite: 'Lax'});
    } else {
        let idCandidate;
        let doContinue = true;
        while (doContinue) {
            doContinue = false;
            idCandidate = Math.floor(Math.random() * 10000);
            $.each(messages, function (i, message) {
                if (idCandidate === message['id']) {
                    doContinue = true;
                    return false;
                }
            });
        }
        message = {id: idCandidate, title: title, symbol: symbol, text: text, timeout: timeout, timestamp: Date.now()};
        messages.push(message);
        Cookies.set('messages', messages, {expires: 365, sameSite: 'Lax'});
    }
    if (show) {
        addMessageToHtml(message);
        $('#message' + message.id).toast('show');
    }
    return message.id;
}

function deleteMessage(id) {
    let messages = Cookies.getJSON('messages');
    messages = messages.filter(item => item.id !== id);
    Cookies.set('messages', messages, {expires: 365, sameSite: 'Lax'});
    $('#messages #message' + id).remove();
}

function isMessageExpired(message) {
    if (message.title === MessageTitleSessionTimeout ||  // always delete session expiration message
        message.timeout !== 0 && (new Date() - message.timestamp) / 1000 - message.timeout > 0) {
        deleteMessage(message.id);
        return true;
    }
    return false;
}

function addMessageToHtml(message) {
    let messageClone = $('#templateMessage').clone();
    messageClone.attr('id', 'message' + message.id).addClass('page-messages');
    messageClone.find('.fas').addClass(message.symbol);
    messageClone.find('.message-title').text(message.title);
    messageClone.find('.message-text').text(message.text);
    messageClone.find('.message-timestamp').data('timestamp', message.timestamp);
    messageClone.find('.message-timestamp').text(timeSince(message.timestamp));
    messageClone.find('.message-close-button').on('click', function () {
        deleteMessage(message.id);
    });
    if (message.timeout !== 0) {
        messageClone.attr('data-autohide', true);
        messageClone.attr('data-delay', message.timeout * 1000);
    }
    messageClone.appendTo('#messages');
}

function showMessages() {
    let messages;
    try {
        messages = JSON.parse(Cookies.get('messages'));
    } catch (e) {
        console.log("Invalid JSON object when parsing messages cookie. Deleting!");
        Cookies.remove('messages');
        return;
    }
    if (typeof messages === "undefined") {
        return;
    }
    $.each(messages, function (i, message) {
        if (isMessageExpired(message)) return;
        addMessageToHtml(message);
    });
    $('.page-messages').each(function (i, obj) {
        $(obj).toast('show');
    });
}

function updateToastTimeTexts() {
    $(".message-timestamp").each(function (i, element) {
        $(element).text(timeSince($(element).data("timestamp")));
    });
    setTimeout(updateToastTimeTexts, 20000);
}

$(window).on('load', function () {
    showMessages();
    updateToastTimeTexts();
});