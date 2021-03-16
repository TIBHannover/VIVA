/**
 * Returns a string describing how much time passed since given date
 * @param {number|jQuery|Date} date
 */
function timeSince(date) {
    let seconds = Math.floor((new Date() - date) / 1000);
    let interval = Math.floor(seconds / 31536000);
    if (interval > 1) {
        return interval + " years ago";
    }
    interval = Math.floor(seconds / 2592000);
    if (interval > 1) {
        return interval + " months ago";
    }
    interval = Math.floor(seconds / 604800);
    if (interval > 1) {
        return interval + " weeks ago";
    }
    interval = Math.floor(seconds / 86400);
    if (interval > 1) {
        return interval + " days ago";
    }
    interval = Math.floor(seconds / 3600);
    if (interval > 1) {
        return interval + " hours ago";
    }
    interval = Math.floor(seconds / 60);
    if (interval > 1) {
        return interval + " minutes ago";
    }
    return "just now";
}

function pad(num, size) {
    let s = "0".repeat(size - 1) + num;
    return s.substr(s.length - size);
}

function getTimeDeltaString(secs) {
    let days = Math.floor(secs / (60 * 60 * 24));
    let hours = Math.floor((secs % (60 * 60 * 24)) / (60 * 60));
    let minutes = Math.floor((secs % (60 * 60)) / 60);
    let seconds = secs % 60;
    return (days === 0 ? "" : days + " day" + (days === 1 ? " " : "s "))
        + pad(hours, 2) + ":" + pad(minutes, 2) + ":" + pad(seconds, 2);
}

function convertUTCDateToLocalDate(date) {
    let newDate = new Date(date.getTime() + date.getTimezoneOffset() * 60 * 1000);
    let offset = date.getTimezoneOffset() / 60;
    let hours = date.getHours();
    newDate.setHours(hours - offset);
    return newDate;
}

function timeConverter(UNIX_timestamp) {
    let a = new Date(UNIX_timestamp * 1000);
    let months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    let year = a.getFullYear();
    let month = months[a.getMonth()];
    let date = a.getDate();
    let hour = a.getHours();
    let min = a.getMinutes();
    let sec = a.getSeconds();
    return date + ' ' + month + ' ' + year + ' ' + pad(hour, 2) + ':' + pad(min, 2) + ':' + pad(sec, 2);
}
