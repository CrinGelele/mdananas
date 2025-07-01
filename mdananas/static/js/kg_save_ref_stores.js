window.addEventListener('load', function() {
    const save_btn = this.document.getElementById('ref-stores-save-btn');
    save_btn.addEventListener('click', function() {
        document.querySelectorAll('.ref-stores-form').forEach(form => {
            fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
            });
        });
    });
});
