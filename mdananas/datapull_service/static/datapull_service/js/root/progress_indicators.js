function disableOtherForms(active_input_id) {
    document.querySelectorAll('.file-input').forEach(input => {
        if (input.id != active_input_id) {
            input.disabled = true;
            console.log(input.id)
        }
    });
}

function addFileInputChangeListener(active_form, file_name) {
    active_form.querySelector('.file-input').addEventListener('change', function(e) {
        if (this.files.length > 0) {
            disableOtherForms(this.id);
            fetch(active_form.action, {method: 'POST', body: new FormData(active_form)})
            .then(response => response.json())
            .then(data => { 
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                }
            });
        }
    });
}

window.addEventListener('load', function() {
    addFileInputChangeListener(document.getElementById('invoice-file-upload-form'), 'sales');
});