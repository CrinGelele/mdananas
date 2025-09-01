function disableOtherForms(active_input_id) {
    document.querySelectorAll('.file-input').forEach(input => {
        if (input.id != active_input_id) {
            input.disabled = true;
            console.log(input.id)
        }
    });
}

function trackProgress(active_form, file_name) {
    const percentElement = active_form.querySelector('.progress-percent');
    const inputElement = active_form.querySelector('.file-input');
    percentElement.textContent = '0%';
    percentElement.style.fontSize = '20px';
    inputElement.disabled = true;
    const progressInterval = setInterval(() => {
        fetch('get-progress/')
            .then(response => response.json())
            .then(data => {
                if (file_name === 'invoice') {
                    percentElement.textContent = data.root_invoice_file_progress + '%';
                    if (!data.root_invoice_file_active) {
                        clearInterval(progressInterval);
                        percentElement.textContent = '100%';
                    }
                }
            });
    }, 500);
    return progressInterval
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
            setTimeout(() => {
                trackProgress(active_form, file_name);
            }, 1000);
        }
    });
}

window.addEventListener('load', function() {
    addFileInputChangeListener(document.getElementById('invoice-file-upload-form'), 'invoice');
});