window.addEventListener('load', function() {
    document.querySelectorAll('.customer-select').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
