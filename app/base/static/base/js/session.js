function redirect_session_timeout(message_timeout_id) {
    let secondsLeft = get_session_time_left();
    if (secondsLeft > 0) {
        if (secondsLeft >= 500 && message_timeout_id !== null) {
            deleteMessage(message_timeout_id);
            message_timeout_id = null;
        }
        if (secondsLeft < 500 && message_timeout_id === null) {
            message_timeout_id = addMessage(MessageTitleSessionTimeout, "fa-exclamation-circle text-info",
                "Warning: Your session expires in less than 5 minutes. " +
                "Open/Refresh a page to avoid session timeout.");
        }
        setTimeout(function () {
            redirect_session_timeout(message_timeout_id);
        }, 5000);
    } else {
        window.location = LoginUrls[0] + "?session=expired&next=" + window.location.pathname;
    }
}

function get_session_time_left() {
    return parseInt(Cookies.get('session_timeout')) - Math.floor(new Date().getTime() / 1000);
}

$(function () {
    if (!LoginUrls.includes(window.location.pathname)) {
        redirect_session_timeout(null);
    }
});