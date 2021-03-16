let pressedKeys = new Set();

function installKeyListener() {
    // $(window).on('keyup', function(e) { pressedKeys[e.keyCode] = false; });
    // $(window).on('keydown', function(e) { pressedKeys[e.keyCode] = true; });

    $(window).on('keyup', function (e) {
        pressedKeys.delete(e.keyCode);
    });
    $(window).on('keydown', function (e) {
        if (e.keyCode !== 9) {  // exclude tab since it might break logic
            pressedKeys.add(e.keyCode);
        }
    });
}
