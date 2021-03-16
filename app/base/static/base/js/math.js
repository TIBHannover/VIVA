function getBaseLog(x, y) {
    return Math.log(x) / Math.log(y);
}

function preciseRound(num, decimals) {
    return Math.round(num * Math.pow(10, decimals)) / Math.pow(10, decimals);
}