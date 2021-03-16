/**
 * This function enables toggling the password visualization from dotted to clear and back.
 */
$(document).ready(function () {
    $('.toggle-password button').on('click', function (event) {
        event.stopImmediatePropagation();
        let showHideInput = $(this).parent().siblings();
        let showHideI = $(this).children();
        if (showHideInput.attr("type") === "text") {
            showHideInput.attr('type', 'password');
            showHideI.addClass("fa-eye-slash").removeClass("fa-eye");
        } else if (showHideInput.attr("type") === "password") {
            showHideInput.attr('type', 'text');
            showHideI.removeClass("fa-eye-slash").addClass("fa-eye");
        }
    });
});