$(document).ready(function () {
    let setPasswordModal = $('#setPasswordModal');
    let setPasswordError = $('#setPasswordError');
    let setPasswordForm = $('#setPasswordForm');
    setPasswordForm.on('submit',function () {
        $.ajax({
            type: "POST",
            //url: "/accounts/um/set_password/",
            url: setPasswordForm.attr('action'),
            data: setPasswordForm.serialize(),
            success: function (data) {
                setPasswordModal.modal('hide');
            },
            error: function (xhr, ajaxOptions, thrownError) {
                setPasswordError.html(xhr.responseText).removeClass('d-none');
            }
        });
        return false;
    });
    setPasswordModal.on('hidden.bs.modal', function () {
        setPasswordError.addClass('d-none');
        $('#inputPassword1').val("");
        $('#inputPassword2').val("");
    });
});