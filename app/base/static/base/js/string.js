function string_strip(str) {
    if (str === undefined) {
        return "";
    }
    return String(str).replace(/^\s+|\s+$/g, '');
}

function sizeofFmt(size, suffix = 'B') {
    try {
        size = Math.floor(size);
    } catch (e) {
        return null;
    }

    if (size <= 0) {
        return '0 %s' % suffix;
    }

    let size_name = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];
    let i = Math.floor(getBaseLog(size, 1024));
    if (i >= size_name.length) {
        i = size_name.length - 1;
    }
    let p = Math.pow(1024, i);
    let s = size / p;
    // round to 3 significant digits
    s = Math.round(preciseRound(s, 2 - Math.floor(getBaseLog(s, 10))));
    if (s > 0) {
        return s + ' ' + size_name[i] + suffix;
    } else {
        return '0 ' + suffix;
    }
}