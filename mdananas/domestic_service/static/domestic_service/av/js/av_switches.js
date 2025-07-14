window.addEventListener('load', function() {
    document.querySelectorAll('.new-format-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.format-select').forEach(field => {
        field.addEventListener('change', function() {
            const newFormatField = field.closest('td').querySelector('.new-format-field');
            if (this.value === 'new') {
                newFormatField.style.display = 'flex';
                newFormatField.disabled = false;
                this.style.display = 'none';
            } else {
                newFormatField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
